"""
Unit tests for Process Safety, HAZOP & API 520/521/526 Relief Sizing Engine.
"""

import unittest
from src.safety.relief_sizing import ReliefValveSizer, API_ORIFICE_SIZES
from src.safety.hazop_analyzer import HAZOPAnalyzer
from src.units.distillation import BinaryDistillationColumn
from src.units.reactors import IdealCSTR
from src.units.thermal import Heater
from src.units.stream import MaterialStream
from src.control.flowsheet_solver import FlowsheetSolver
from src.database.loader import ChemicalDatabaseLoader


class TestSafetyHAZOP(unittest.TestCase):

    def setUp(self):
        self.species_map = {
            "water": ChemicalDatabaseLoader.get_water_metadata(),
            "ethanol": ChemicalDatabaseLoader.get_ethanol_metadata()
        }

    def test_api520_vapor_relief_critical(self):
        # 10,000 kg/h vapor at 373 K, 500 kPa gauge, M=44 g/mol
        res = ReliefValveSizer.size_vapor_relief_api520(
            W_kg_h=10000.0,
            T_K=373.15,
            P_set_kPa_g=500.0,
            M_g_mol=44.0,
            k_ratio=1.30,
            overpressure_pct=10.0
        )
        self.assertTrue(res["is_critical_flow"])
        self.assertGreater(res["required_area_mm2"], 1000.0)
        self.assertIn(res["selected_orifice"]["letter"], ["L", "M", "K"])
        self.assertLessEqual(res["selected_orifice"]["capacity_utilization_pct"], 100.0)
        self.assertGreater(res["selected_orifice"]["margin_pct"], 0.0)

    def test_api520_liquid_relief(self):
        # 25 m3/h water at 600 kPa gauge
        res = ReliefValveSizer.size_liquid_relief_api520(
            Q_m3_h=25.0,
            P_set_kPa_g=600.0,
            specific_gravity=1.0,
            overpressure_pct=10.0
        )
        self.assertGreater(res["required_area_mm2"], 10.0)
        self.assertIn(res["selected_orifice"]["letter"], API_ORIFICE_SIZES)

    def test_api521_fire_relief(self):
        # Wetted area 30 m2, latent heat 850 kJ/kg
        res = ReliefValveSizer.calculate_fire_relief_api521(
            wetted_area_m2=30.0,
            latent_heat_kJ_kg=850.0,
            P_set_kPa_g=400.0,
            T_relieving_K=370.0,
            M_g_mol=46.07
        )
        self.assertGreater(res["fire_heat_ingress_kW"], 500.0)
        self.assertGreater(res["relieving_rate_kg_h"], 2000.0)
        self.assertEqual(res["overpressure_pct"], 21.0)
        self.assertIn(res["selected_orifice"]["letter"], API_ORIFICE_SIZES)

    def test_api521_thermal_expansion(self):
        # 150 kW heat exchanger liquid expansion
        res = ReliefValveSizer.calculate_thermal_expansion_api521(
            heat_duty_kW=150.0,
            P_set_kPa_g=700.0,
            liquid_density_kg_m3=1000.0
        )
        self.assertGreater(res["expansion_flow_m3_h"], 0.0)
        # Expansion area is small, so Orifice D or E
        self.assertIn(res["selected_orifice"]["letter"], ["D", "E"])

    def test_api526_orifice_selection(self):
        d_res = ReliefValveSizer.select_api_orifice(50.0)
        self.assertEqual(d_res["letter"], "D")
        self.assertEqual(d_res["standard_area_mm2"], 71.0)

        l_res = ReliefValveSizer.select_api_orifice(1500.0)
        self.assertEqual(l_res["letter"], "L")
        self.assertEqual(l_res["standard_area_mm2"], 1841.0)

    def test_equipment_relief_scenarios(self):
        col = BinaryDistillationColumn("C-101", "Fractionator", num_stages=12, feed_stage=6, reflux_ratio=2.0)
        eval_res = ReliefValveSizer.evaluate_equipment_relief_scenarios(col, self.species_map)
        self.assertEqual(eval_res["unit_id"], "C-101")
        self.assertIn(eval_res["governing_selected_orifice"], API_ORIFICE_SIZES)
        self.assertEqual(len(eval_res["scenarios_evaluated"]), 3)

    def test_hazop_matrix_generator(self):
        col = BinaryDistillationColumn("C-101", "Fractionator", num_stages=12, feed_stage=6, reflux_ratio=2.0)
        rx = IdealCSTR("R-101", "CSTR Reactor")
        htr = Heater("E-101", "Reboiler Heater")

        units = {"C-101": col, "R-101": rx, "E-101": htr}
        hazop_rows = HAZOPAnalyzer.generate_flowsheet_hazop(units, {}, [])
        self.assertGreaterEqual(len(hazop_rows), 6)

        # Check presence of HIGH risk deviations
        levels = [r["risk_level"] for r in hazop_rows]
        self.assertIn("HIGH", levels)
        params = [r["parameter"] for r in hazop_rows]
        self.assertIn("PRESSURE", params)
        self.assertIn("TEMPERATURE", params)

    def test_flowsheet_solver_compile_safety(self):
        col = BinaryDistillationColumn("C-101", "Fractionator", num_stages=12, feed_stage=6, reflux_ratio=2.0)
        s_in = MaterialStream("S-feed")
        s_in.F = 15.0
        s_in.z = {"ethanol": 0.5, "water": 0.5}
        col.connect_inlet(s_in)

        safety_comp = FlowsheetSolver.compile_flowsheet_safety(
            units_list=[col],
            streams_list=[s_in],
            connections=[],
            species_map=self.species_map
        )
        self.assertIn("relief_schedule", safety_comp)
        self.assertIn("hazop_study", safety_comp)
        self.assertGreater(len(safety_comp["relief_schedule"]), 0)
        self.assertGreater(len(safety_comp["hazop_study"]), 0)


if __name__ == "__main__":
    unittest.main()
