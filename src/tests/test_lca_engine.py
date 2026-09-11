"""
Unit tests for Environmental Life Cycle Assessment (LCA) and Decarbonization Engine.
Validates Scope 1/2/3 GHG accounting, carbon intensity, carbon tax sensitivity,
electrification pathways (MVR and Heat Pumps), and FlowsheetSolver compiler integration.
"""

import unittest
from src.economics.lca_engine import (
    LCAAnalyzer,
    REGIONAL_GRID_FACTORS,
    STEAM_FUEL_FACTORS,
    FEEDSTOCK_EMBODIED_FACTORS
)
from src.units.thermal import Heater
from src.units.stream import MaterialStream
from src.database.loader import ChemicalDatabaseLoader
from src.control.flowsheet_solver import FlowsheetSolver


class TestLCAEngine(unittest.TestCase):

    def setUp(self):
        self.species_map = {
            "water": ChemicalDatabaseLoader.get_water_metadata(),
            "ethanol": ChemicalDatabaseLoader.get_ethanol_metadata(),
            "methane": ChemicalDatabaseLoader.get_methane_metadata(),
            "co2": ChemicalDatabaseLoader.get_co2_metadata()
        }

    def test_scope_1_combustion_and_vent(self):
        # Heater with 500 kW duty
        h1 = Heater("H-101", "Furnace Preheater")
        h1.heat_duty = 500000.0  # 500 kW (Watts)

        # Vent stream with 50 mol% CO2 at 2 mol/s
        vent = MaterialStream("Vent-1")
        vent.F = 2.0
        vent.z = {"co2": 0.50, "water": 0.50}

        s1_res = LCAAnalyzer.calculate_scope_1_emissions([h1], [vent], fuel_type="natural_gas_boiler", operating_hours=8000.0)
        self.assertGreater(s1_res["combustion_co2_kg_yr"], 0.0)
        self.assertGreater(s1_res["reaction_vent_co2_kg_yr"], 0.0)
        self.assertEqual(s1_res["total_scope_1_kg_yr"], s1_res["combustion_co2_kg_yr"] + s1_res["reaction_vent_co2_kg_yr"])
        self.assertGreater(s1_res["total_scope_1_tonnes_yr"], 500.0)

    def test_scope_2_grid_sensitivity(self):
        utility_opex = {
            "operating_hours_per_year": 8000.0,
            "total_electricity_kW": 100.0,
            "total_heating_duty_kW": 200.0,
            "total_cooling_duty_kW": 150.0,
            "total_refrigeration_duty_kW": 0.0
        }

        # Compare Green PPA (0.0 kg/kWh) vs Coal Heavy (0.820 kg/kWh)
        s2_green = LCAAnalyzer.calculate_scope_2_emissions(utility_opex, grid_region="Green_PPA_100Pct_Renewable", steam_source="waste_heat_boiler")
        s2_coal = LCAAnalyzer.calculate_scope_2_emissions(utility_opex, grid_region="Coal_Heavy_Grid", steam_source="natural_gas_boiler")

        self.assertEqual(s2_green["electricity_co2_kg_yr"], 0.0)
        self.assertGreater(s2_coal["electricity_co2_kg_yr"], 600000.0)
        self.assertGreater(s2_coal["total_scope_2_tonnes_yr"], s2_green["total_scope_2_tonnes_yr"])

    def test_scope_3_feedstock_embodied(self):
        feed = MaterialStream("Feed-101")
        feed.upstream_unit = None
        feed.F = 10.0  # mol/s
        feed.z = {"methane": 0.80, "water": 0.20}

        s3_res = LCAAnalyzer.calculate_scope_3_emissions([feed], self.species_map, operating_hours=8000.0)
        self.assertGreater(s3_res["total_scope_3_kg_yr"], 0.0)
        self.assertEqual(len(s3_res["feedstock_breakdown"]), 2)
        # Verify methane was identified
        sp_ids = [item["species_id"] for item in s3_res["feedstock_breakdown"]]
        self.assertIn("methane", sp_ids)

    def test_carbon_intensity_normalization(self):
        prod = MaterialStream("Ethanol-Product")
        prod.downstream_units = []
        prod.F = 15.0  # mol/s
        prod.z = {"ethanol": 0.95, "water": 0.05}

        s1 = {"total_scope_1_kg_yr": 100000.0}
        s2 = {"total_scope_2_kg_yr": 200000.0}
        s3 = {"total_scope_3_kg_yr": 150000.0}

        ci_gate = LCAAnalyzer.calculate_carbon_intensity(s1, s2, s3, [prod], self.species_map, include_scope_3=False)
        ci_cradle = LCAAnalyzer.calculate_carbon_intensity(s1, s2, s3, [prod], self.species_map, include_scope_3=True)

        self.assertGreater(ci_cradle["carbon_intensity_kg_co2_per_kg_product"], ci_gate["carbon_intensity_kg_co2_per_kg_product"])
        self.assertEqual(ci_cradle["primary_product"], "ethanol")

    def test_carbon_tax_economic_sensitivity(self):
        lca_mock = {
            "scope_1": {"total_scope_1_tonnes_yr": 500.0},
            "scope_2": {"total_scope_2_tonnes_yr": 500.0},
            "scope_3": {"total_scope_3_tonnes_yr": 200.0}
        }
        profitability_mock = {
            "gross_profit_usd": 1000000.0,
            "depreciation_annual_usd": 100000.0,
            "net_present_value_NPV_usd": 5000000.0,
            "fixed_capital_investment_FCI": 2000000.0,
            "project_lifetime_years": 15,
            "discount_rate_pct": 10.0
        }

        tax_res = LCAAnalyzer.calculate_carbon_tax_impact(lca_mock, profitability_mock, carbon_tax_usd_per_tonne=75.0)
        self.assertEqual(tax_res["taxed_emissions_tonnes_yr"], 1000.0)  # Scope 1 + Scope 2
        self.assertEqual(tax_res["annual_carbon_tax_usd"], 75000.0)
        self.assertLess(tax_res["adjusted_net_present_value_usd"], 5000000.0)
        self.assertGreater(tax_res["npv_reduction_usd"], 0.0)

    def test_decarbonization_pathways(self):
        units = []
        utility_opex = {"total_heating_duty_kW": 300.0, "total_annual_utility_opex_usd": 40000.0}
        lca_res = {
            "scope_1": {"total_scope_1_tonnes_yr": 100.0},
            "scope_2": {"total_scope_2_tonnes_yr": 200.0}
        }

        pathways = LCAAnalyzer.evaluate_decarbonization_pathways(units, utility_opex, lca_res)
        self.assertIn("mvr_electrification", pathways)
        self.assertIn("heat_pump_electrification", pathways)
        self.assertIn("carbon_capture_ccus", pathways)

        mvr = pathways["mvr_electrification"]
        self.assertGreater(mvr["co2_abated_tonnes_yr"], 0.0)
        self.assertLess(mvr["post_retrofit_emissions_tonnes"], pathways["baseline"]["annual_emissions_tonnes"])

    def test_flowsheet_solver_compile_lca(self):
        h = Heater("H-101", "Preheater")
        h.heat_duty = 100000.0
        s_in = MaterialStream("S-in")
        s_in.F = 10.0
        s_in.z = {"ethanol": 0.5, "water": 0.5}
        s_out = MaterialStream("S-out")
        h.connect_inlet(s_in)
        h.connect_outlet(s_out)

        utility_opex = {"total_electricity_kW": 10.0, "total_heating_duty_kW": 100.0, "total_cooling_duty_kW": 0.0, "total_refrigeration_duty_kW": 0.0, "operating_hours_per_year": 8000.0}
        prof = {"gross_profit_usd": 500000.0, "depreciation_annual_usd": 50000.0, "net_present_value_NPV_usd": 2000000.0, "fixed_capital_investment_FCI": 800000.0, "project_lifetime_years": 15, "discount_rate_pct": 10.0}

        lca_full = FlowsheetSolver.compile_flowsheet_lca(
            units_list=[h],
            streams_list=[s_in, s_out],
            utility_opex_dict=utility_opex,
            profitability_dict=prof,
            species_map=self.species_map,
            grid_region="EU27_Average",
            carbon_tax_usd_per_tonne=60.0
        )

        self.assertIn("scope_1", lca_full)
        self.assertIn("scope_2", lca_full)
        self.assertIn("scope_3", lca_full)
        self.assertIn("carbon_intensity", lca_full)
        self.assertIn("carbon_tax_impact", lca_full)
        self.assertIn("decarbonization_pathways", lca_full)
        self.assertGreater(lca_full["carbon_tax_impact"]["annual_carbon_tax_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
