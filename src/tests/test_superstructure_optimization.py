"""
Unit Tests for Distillation Superstructure Optimization & Sequence Synthesis.
Covers FUG shortcut sizing, Direct/Indirect/Distributed/DWC sequences,
Turton bare module CAPEX, utility OPEX, carbon emissions,
multi-objective Pareto non-dominated frontier sorting, and flowsheet compiler integration.
"""

import unittest
import numpy as np
from src.optimization.sequence_synthesizer import SeparationSequencer, SequenceCandidate
from src.optimization.pareto_optimizer import ParetoOptimizer
from src.control.flowsheet_solver import FlowsheetSolver
from src.units.stream import MaterialStream


class TestSuperstructureOptimization(unittest.TestCase):
    """Test suite for algorithmic separation superstructure optimization."""

    def setUp(self):
        """Sets up baseline ternary feed: Benzene (A) / Toluene (B) / Octane (C)."""
        self.components = ["benzene", "toluene", "octane"]
        self.feed_flow_mol_s = 100.0  # 100 mol/s
        self.feed_fractions = [0.35, 0.40, 0.25]
        self.species_map = {}

    def test_relative_volatilities_and_underwood(self):
        """Test 1: Relative volatilities ordering and Underwood root solving."""
        sorted_comps, alphas, alpha_dict = SeparationSequencer.calculate_relative_volatilities(
            self.components, self.species_map
        )
        self.assertEqual(len(sorted_comps), 3)
        self.assertEqual(sorted_comps[0], "benzene")  # Lightest
        self.assertEqual(sorted_comps[2], "octane")   # Heaviest
        self.assertAlmostEqual(alphas[2], 1.0, places=2)
        self.assertGreater(alphas[0], alphas[1])
        self.assertGreater(alphas[1], alphas[2])

        # Test Underwood root solving between light key (idx 0) and heavy key (idx 1)
        theta, r_min = SeparationSequencer.solve_underwood(alphas, self.feed_fractions, q=1.0, lk_idx=0, hk_idx=1)
        self.assertGreater(theta, alphas[1])
        self.assertLess(theta, alphas[0])
        self.assertGreater(r_min, 0.2)

    def test_direct_sequence_sizing(self):
        """Test 2: Direct sequence FUG sizing and Turton bare module costing."""
        _, alphas, _ = SeparationSequencer.calculate_relative_volatilities(
            self.components, self.species_map
        )
        cand = SeparationSequencer.evaluate_direct_sequence(
            self.feed_flow_mol_s, self.feed_fractions, alphas,
            steam_price_usd_per_gj=7.50, cooling_price_usd_per_gj=0.354,
            carbon_tax_usd_per_tonne=50.0, crf=0.16275
        )
        self.assertEqual(cand.columns_count, 2)
        self.assertEqual(len(cand.column_diameters_m), 2)
        self.assertGreater(cand.total_reboiler_duty_kW, 1000.0)
        self.assertGreater(cand.capex_usd, 500000.0)
        self.assertGreater(cand.annual_utility_opex_usd, 100000.0)
        self.assertGreater(cand.total_annualized_cost_tac_usd, 0.0)
        self.assertIn("Direct Sequence", cand.sequence_name)

    def test_indirect_sequence_sizing(self):
        """Test 3: Indirect sequence FUG sizing and Turton bare module costing."""
        _, alphas, _ = SeparationSequencer.calculate_relative_volatilities(
            self.components, self.species_map
        )
        cand = SeparationSequencer.evaluate_indirect_sequence(
            self.feed_flow_mol_s, self.feed_fractions, alphas,
            steam_price_usd_per_gj=7.50, cooling_price_usd_per_gj=0.354,
            carbon_tax_usd_per_tonne=50.0, crf=0.16275
        )
        self.assertEqual(cand.columns_count, 2)
        self.assertEqual(len(cand.column_diameters_m), 2)
        self.assertGreater(cand.total_reboiler_duty_kW, 1000.0)
        self.assertGreater(cand.capex_usd, 500000.0)
        self.assertIn("Indirect Sequence", cand.sequence_name)

    def test_dwc_petlyuk_thermodynamic_savings(self):
        """Test 4: Dividing-Wall Column (DWC Petlyuk) 30% thermal and CAPEX savings."""
        res = SeparationSequencer.synthesize_all_sequences(
            self.feed_flow_mol_s, self.feed_fractions, self.components, self.species_map
        )
        benchmarks = res["dwc_benchmarks"]
        self.assertAlmostEqual(benchmarks["energy_savings_pct"], 30.0, delta=0.5)
        self.assertAlmostEqual(benchmarks["capex_savings_pct"], 30.0, delta=0.5)
        self.assertGreater(benchmarks["energy_savings_kW"], 500.0)
        self.assertGreater(benchmarks["capex_savings_usd"], 200000.0)
        self.assertGreater(benchmarks["carbon_abatement_tonnes_yr"], 100.0)

        # DWC candidate check
        dwc_dict = next(c for c in res["candidates"] if "Dividing-Wall" in c["sequence_name"])
        self.assertEqual(dwc_dict["columns_count"], 1)

    def test_pareto_non_dominated_sorting(self):
        """Test 5: Multi-objective non-dominated Pareto frontier extraction."""
        params = {
            "feed_flow_mol_s": self.feed_flow_mol_s,
            "feed_fractions": self.feed_fractions,
            "alphas": [7.5, 3.0, 1.0],
            "steam_price_usd_per_gj": 7.50,
            "cooling_price_usd_per_gj": 0.354,
            "carbon_tax_usd_per_tonne": 50.0,
            "crf": 0.16275
        }
        pareto_res = ParetoOptimizer.generate_pareto_frontier([], synthesis_params=params)
        self.assertGreater(pareto_res["total_designs_evaluated"], 10)
        self.assertGreater(pareto_res["pareto_count"], 0)

        pts = pareto_res["pareto_points"]
        for i in range(len(pts) - 1):
            self.assertLessEqual(pts[i]["capex_usd"], pts[i+1]["capex_usd"])
            self.assertGreaterEqual(pts[i]["annual_carbon_emissions_tonnes"], pts[i+1]["annual_carbon_emissions_tonnes"])
            self.assertGreaterEqual(pts[i+1]["marginal_abatement_cost_usd_per_tonne"], 0.0)

    def test_flowsheet_solver_superstructure_compiler(self):
        """Test 6: FlowsheetSolver.compile_flowsheet_superstructure integration."""
        s_feed = MaterialStream("S-FEED")
        s_feed.T = 360.0
        s_feed.P = 101325.0
        s_feed.F = 100.0
        s_feed.z = {"benzene": 0.35, "toluene": 0.40, "octane": 0.25}

        compiler_res = FlowsheetSolver.compile_flowsheet_superstructure(
            feed_stream=s_feed,
            species_map=self.species_map,
            steam_price=8.0,
            electricity_price=0.09,
            carbon_tax_rate=75.0
        )

        self.assertIn("synthesis_result", compiler_res)
        self.assertIn("pareto_result", compiler_res)
        self.assertIn("optimal_sequence", compiler_res)
        self.assertIn("summary", compiler_res)
        self.assertEqual(compiler_res["summary"]["dwc_energy_savings_pct"], 30.0)
        self.assertIn("Dividing-Wall", compiler_res["optimal_candidate_name"])
        self.assertEqual(len(compiler_res["candidates"]), 4)


if __name__ == "__main__":
    unittest.main()
