"""
Unit tests for Pinch Analysis, Linnhoff Problem Table Algorithm,
Composite Curves, Grand Composite Curve, and Energy Integration Savings.
"""

import unittest
from src.economics.pinch_analysis import PinchAnalyzer, ThermalStream
from src.units.thermal import Heater, Cooler, HeatExchanger
from src.units.stream import MaterialStream
from src.control.flowsheet_solver import FlowsheetSolver

class TestPinchAnalysis(unittest.TestCase):

    def setUp(self):
        # Classical Linnhoff 4-stream benchmark problem
        self.stream_h1 = ThermalStream("H1", "HOT", 170.0, 60.0, 330.0, 3.0)
        self.stream_h2 = ThermalStream("H2", "HOT", 150.0, 30.0, 180.0, 1.5)
        self.stream_c1 = ThermalStream("C1", "COLD", 20.0, 135.0, 230.0, 2.0)
        self.stream_c2 = ThermalStream("C2", "COLD", 80.0, 140.0, 240.0, 4.0)
        self.benchmark_streams = [self.stream_h1, self.stream_h2, self.stream_c1, self.stream_c2]

    def test_linnhoff_problem_table_benchmark(self):
        """Verify Problem Table Algorithm against analytical Linnhoff 4-stream solution."""
        res = PinchAnalyzer.solve_problem_table_algorithm(self.benchmark_streams, delta_T_min=10.0)

        # Total heat duties
        self.assertEqual(res["total_hot_duty_kW"], 510.0)
        self.assertEqual(res["total_cold_duty_kW"], 470.0)

        # Minimum utility targets
        self.assertAlmostEqual(res["Q_hot_utility_min_kW"], 20.0, delta=0.1)
        self.assertAlmostEqual(res["Q_cold_utility_min_kW"], 60.0, delta=0.1)
        self.assertAlmostEqual(res["Q_heat_recovery_max_kW"], 450.0, delta=0.1)

        # Exact Pinch temperatures
        self.assertAlmostEqual(res["pinch_temperature_hot_C"], 90.0, delta=0.1)
        self.assertAlmostEqual(res["pinch_temperature_cold_C"], 80.0, delta=0.1)
        self.assertAlmostEqual(res["pinch_temperature_shifted_C"], 85.0, delta=0.1)

    def test_composite_curves_structure(self):
        """Verify Hot and Cold Composite Curve enthalpy coordinates."""
        curves = PinchAnalyzer.generate_composite_curves(self.benchmark_streams, delta_T_min=10.0)
        h_hot = curves["hot_composite"]["enthalpy_kW"]
        t_hot = curves["hot_composite"]["temperature_C"]
        h_cold = curves["cold_composite"]["enthalpy_kW"]
        t_cold = curves["cold_composite"]["temperature_C"]

        self.assertGreater(len(h_hot), 2)
        self.assertGreater(len(h_cold), 2)
        # Cold curve is shifted by Q_cold_min = 60 kW
        self.assertEqual(h_cold[0], 60.0)
        # Hot curve starts at 0 kW
        self.assertEqual(h_hot[0], 0.0)

    def test_grand_composite_curve(self):
        """Verify Grand Composite Curve (GCC) pinch point zero crossing."""
        gcc = PinchAnalyzer.generate_grand_composite_curve(self.benchmark_streams, delta_T_min=10.0)
        t_stars = gcc["shifted_temperature_C"]
        cascade = gcc["cascaded_heat_flow_kW"]

        self.assertEqual(len(t_stars), len(cascade))
        self.assertIn(85.0, t_stars)
        # Pinch point has minimum heat cascade of 0 kW
        self.assertAlmostEqual(min(cascade), 0.0, delta=0.01)

    def test_utility_savings_calculation(self):
        """Verify economic utility cost reduction calculations."""
        savings = PinchAnalyzer.calculate_utility_savings(
            self.benchmark_streams,
            delta_T_min=10.0,
            operating_hours=8000.0,
            utility_rates={"steam_usd_per_gj": 5.0, "cooling_water_usd_per_gj": 0.5}
        )

        self.assertEqual(savings["unintegrated_steam_duty_kW"], 470.0)
        self.assertEqual(savings["unintegrated_cooling_duty_kW"], 510.0)
        self.assertEqual(savings["pinch_steam_duty_kW"], 20.0)
        self.assertEqual(savings["pinch_cooling_duty_kW"], 60.0)

        # Huge savings from recovering 450 kW of heat
        self.assertGreater(savings["annual_savings_usd"], 50000.0)
        self.assertGreater(savings["energy_reduction_pct"], 90.0)
        self.assertEqual(savings["min_number_of_heat_exchangers"], 5)  # 4 streams + 2 utilities - 1 = 5

    def test_flowsheet_stream_extraction(self):
        """Verify automatic extraction of thermal loads from flowsheet units."""
        h1 = Heater("H-101", "Feed Heater", t_target=380.0)
        c1 = Cooler("E-101", "Product Cooler", t_target=300.0)

        s_in1 = MaterialStream("S1")
        s_in1.T, s_in1.P, s_in1.F = 310.0, 101325.0, 20.0
        s_out1 = MaterialStream("S2")
        h1.connect_inlet(s_in1)
        h1.connect_outlet(s_out1)
        h1.run_simulation((0,0), [])

        s_in2 = MaterialStream("S3")
        s_in2.T, s_in2.P, s_in2.F = 390.0, 101325.0, 20.0
        s_out2 = MaterialStream("S4")
        c1.connect_inlet(s_in2)
        c1.connect_outlet(s_out2)
        c1.run_simulation((0,0), [])

        units = {"H-101": h1, "E-101": c1}
        streams = {"S1": s_in1, "S2": s_out1, "S3": s_in2, "S4": s_out2}

        extracted = PinchAnalyzer.extract_streams_from_flowsheet(units, streams)
        self.assertEqual(len(extracted), 2)
        types = [s.stream_type for s in extracted]
        self.assertIn("HOT", types)
        self.assertIn("COLD", types)

        # Flowsheet solver compilation
        fs_pinch = FlowsheetSolver.compile_flowsheet_pinch(list(units.values()), list(streams.values()), delta_T_min=10.0)
        self.assertIn("problem_table", fs_pinch)
        self.assertIn("composite_curves", fs_pinch)
        self.assertIn("savings", fs_pinch)

if __name__ == "__main__":
    unittest.main()
