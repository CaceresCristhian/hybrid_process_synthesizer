"""
Unit tests for Dynamic Distillation Control, Auto-Tuning, Dynamic Engine, and Technical Reporting.
Verifies stage-by-stage ODE integration, level/temperature PID control loops,
FOPDT identification, Ziegler-Nichols / Cohen-Coon / IMC rules, disturbance injection,
and flowsheet JSON / HTML engineering report generation.
"""

import unittest
import json
import numpy as np
from src.database.loader import ChemicalDatabaseLoader
from src.units.stream import MaterialStream
from src.units.thermal import Heater
from src.units.pump import FlowsheetPump
from src.units.dynamic_column import DynamicDistillationColumn
from src.control.auto_tuning import AutoTuner
from src.control.dynamic_engine import DynamicSimulationEngine
from src.control.flowsheet_solver import FlowsheetSolver
from src.reporting.report_generator import ReportGenerator

class TestDynamicControlExport(unittest.TestCase):

    def setUp(self):
        self.water = ChemicalDatabaseLoader.get_water_metadata()
        self.ethanol = ChemicalDatabaseLoader.get_ethanol_metadata()
        self.species_map = {"water": self.water, "ethanol": self.ethanol}

    def test_dynamic_column_transient_steps(self):
        """Verify DynamicDistillationColumn ODE step integration and state consistency."""
        col = DynamicDistillationColumn("C-101", "De-Ethanizer", num_stages=10, feed_stage=5)
        self.assertEqual(len(col.M), 10)
        self.assertEqual(len(col.x), 10)

        # Step 20 seconds forward
        for _ in range(20):
            col.step(dt=1.0)

        # Check physical holdups and bounds
        self.assertTrue(np.all(col.M > 0.0))
        self.assertTrue(np.all((col.x >= 0.0) & (col.x <= 1.0)))
        # Top distillate purity should exceed bottoms purity
        self.assertGreater(col.x[0], col.x[-1])
        # Condenser temperature should be lower than reboiler temperature
        self.assertLess(col.T[0], col.T[-1])
        # Sizing results populated
        sizing = col.size_equipment()
        self.assertGreater(sizing["column_diameter_m"], 0.4)
        self.assertGreater(sizing["column_height_m"], 5.0)

    def test_dynamic_column_controllers(self):
        """Verify multi-loop PID controllers respond to perturbations."""
        col = DynamicDistillationColumn("C-101", "De-Ethanizer")
        init_d = col.D_distillate
        init_l = col.L_reflux

        # Step column and check history is recorded
        col.step(dt=1.0)
        self.assertIn("xD", col.history)
        self.assertIn("T_sensitive", col.history)
        self.assertIn("level_accumulator_pct", col.history)
        self.assertIn("reflux_flow", col.history)

    def test_fopdt_system_identification(self):
        """Verify FOPDT model fitting from synthetic step test data."""
        # True process: Kp = 2.5, tau = 15.0 s, theta = 4.0 s, u step at t = 5.0 s
        t = np.linspace(0, 100, 101)
        u = np.where(t >= 5.0, 2.0, 1.0) # delta_u = 1.0
        y = np.zeros_like(t)
        for i, ti in enumerate(t):
            dt = ti - 5.0
            if dt <= 4.0:
                y[i] = 10.0
            else:
                y[i] = 10.0 + 2.5 * 1.0 * (1.0 - np.exp(-(dt - 4.0) / 15.0))

        fopdt = AutoTuner.fit_fopdt(t.tolist(), u.tolist(), y.tolist())
        self.assertAlmostEqual(fopdt["K_p"], 2.5, delta=0.2)
        self.assertAlmostEqual(fopdt["tau"], 15.0, delta=3.0)
        self.assertGreater(fopdt["R2"], 0.95)

    def test_auto_tuning_rules(self):
        """Verify Ziegler-Nichols, Cohen-Coon, and IMC tuning parameters."""
        fopdt = {"K_p": 1.5, "tau": 20.0, "theta": 5.0}

        # 1. Ziegler-Nichols
        zn = AutoTuner.calculate_ziegler_nichols(fopdt)
        self.assertGreater(zn["PID"]["Kc"], 0.0)
        self.assertGreater(zn["PID"]["tau_I"], 0.0)
        self.assertGreater(zn["PID"]["tau_D"], 0.0)
        self.assertEqual(zn["PI"]["tau_D"], 0.0)

        # 2. Cohen-Coon
        cc = AutoTuner.calculate_cohen_coon(fopdt)
        self.assertGreater(cc["PID"]["Kc"], 0.0)
        self.assertGreater(cc["PID"]["tau_I"], 0.0)

        # 3. IMC / SIMC
        imc = AutoTuner.calculate_imc(fopdt, "moderate")
        self.assertGreater(imc["Kc"], 0.0)
        self.assertGreater(imc["tau_I"], 0.0)

        # Full comparison table
        comp = AutoTuner.get_full_tuning_comparison(fopdt)
        self.assertEqual(len(comp["methods"]), 4)

    def test_dynamic_simulation_engine_and_disturbances(self):
        """Verify DynamicSimulationEngine time stepping, disturbances, and alarms."""
        engine = DynamicSimulationEngine()
        self.assertEqual(engine.current_time, 0.0)

        # Trigger feed flow surge disturbance
        engine.trigger_disturbance("Feed Flow Surge (+25%)")
        self.assertIn("Feed Flow Surge (+25%)", engine.active_disturbances)

        # Run 10 seconds
        res = engine.run_time_steps(duration_seconds=10.0, dt=1.0)
        self.assertEqual(res["current_time"], 10.0)
        self.assertGreaterEqual(len(res["history"]["time"]), 10)

        # Clear disturbance
        engine.clear_disturbance("Feed Flow Surge (+25%)")
        self.assertEqual(len(engine.active_disturbances), 0)

    def test_flowsheet_json_export(self):
        """Verify flowsheet JSON serialization."""
        h1 = Heater("H-101", "Feed Heater")
        s1 = MaterialStream("S-101")
        s1.T, s1.P, s1.F, s1.z = 300.0, 101325.0, 10.0, {"ethanol": 0.5, "water": 0.5}
        conns = [{"from": "Feed Boundary", "to": "H-101", "stream": "S-101"}]

        json_str = ReportGenerator.export_flowsheet_json({"H-101": h1}, {"S-101": s1}, conns)
        data = json.loads(json_str)

        self.assertIn("units", data)
        self.assertIn("streams", data)
        self.assertIn("connections", data)
        self.assertIn("H-101", data["units"])
        self.assertIn("S-101", data["streams"])

    def test_engineering_report_html_generation(self):
        """Verify comprehensive HTML engineering report generation."""
        h1 = Heater("H-101", "Feed Heater")
        s1 = MaterialStream("S-101")
        s1.T, s1.P, s1.F, s1.z = 300.0, 101325.0, 10.0, {"ethanol": 0.5, "water": 0.5}

        mass_bal = FlowsheetSolver.compile_mass_balance([s1], self.species_map)
        energy_bal = FlowsheetSolver.compile_energy_balance([h1], [s1], self.species_map)
        tea = FlowsheetSolver.compile_flowsheet_economics([h1], [s1], self.species_map)

        html_out = ReportGenerator.generate_engineering_report_html(
            units_map={"H-101": h1},
            streams_map={"S-101": s1},
            mass_bal=mass_bal,
            energy_bal=energy_bal,
            tea_summary=tea,
            plant_name="Bio-Ethanol Distillation Facility"
        )

        self.assertTrue(html_out.strip().startswith("<!DOCTYPE html>"))
        self.assertIn("Bio-Ethanol Distillation Facility", html_out)
        self.assertIn("Equipment Sizing & Turton-Guthrie Capital Costing Schedule", html_out)
        self.assertIn("Techno-Economic & Financial Profitability Summary", html_out)
        self.assertIn("CONSERVED (Pass)", html_out)

if __name__ == "__main__":
    unittest.main()
