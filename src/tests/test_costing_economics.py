"""
Unit tests for Techno-Economic Assessment (TEA) and Equipment Costing.
Verifies Turton & Guthrie bare module costing, ASME pressure factors,
material factors, utility OPEX, and project profitability.
"""

import unittest
from src.database.loader import ChemicalDatabaseLoader
from src.units.stream import MaterialStream
from src.units.thermal import Heater, Cooler, HeatExchanger
from src.units.pump import FlowsheetPump
from src.units.compressor import Compressor
from src.units.distillation import BinaryDistillationColumn
from src.units.reactors import IdealCSTR, EquilibriumReactor
from src.units.separators import FlashDrum, MembraneUnit
from src.control.flowsheet_solver import FlowsheetSolver
from src.economics.cost_correlations import CostCorrelations, BASE_CEPCI, DEFAULT_CEPCI
from src.economics.equipment_costing import EquipmentCosting
from src.economics.capital_costing import CapitalCosting
from src.economics.utility_costing import UtilityCosting
from src.economics.profitability import EconomicAnalyzer

class TestCostingEconomics(unittest.TestCase):

    def setUp(self):
        self.water = ChemicalDatabaseLoader.get_water_metadata()
        self.ethanol = ChemicalDatabaseLoader.get_ethanol_metadata()
        self.species_map = {
            "water": self.water,
            "ethanol": self.ethanol
        }

    def test_base_cp0_correlations(self):
        """Verify Turton base purchased cost regressions for standard equipment."""
        # Heat Exchanger (Fixed Tubesheet, Area = 50 m2)
        cp0_hx = CostCorrelations.calculate_cp0("heat_exchanger_fixed_tubesheet", 50.0)
        self.assertGreater(cp0_hx, 10000.0)
        self.assertLess(cp0_hx, 100000.0)

        # Centrifugal Pump (Power = 15 kW)
        cp0_pump = CostCorrelations.calculate_cp0("pump_centrifugal", 15.0)
        self.assertGreater(cp0_pump, 2000.0)
        self.assertLess(cp0_pump, 25000.0)

        # Vertical Vessel (Volume = 10 m3)
        cp0_vess = CostCorrelations.calculate_cp0("vessel_vertical", 10.0)
        self.assertGreater(cp0_vess, 10000.0)
        self.assertLess(cp0_vess, 80000.0)

    def test_pressure_factors(self):
        """Verify pressure design factors (F_P)."""
        # Atmospheric pressure -> F_P = 1.0
        fp_atm = CostCorrelations.calculate_pressure_factor("vessel_vertical", 101325.0)
        self.assertEqual(fp_atm, 1.0)

        # High pressure (40 bar = 4 MPa) -> F_P > 1.0
        fp_high = CostCorrelations.calculate_pressure_factor("vessel_vertical", 4.0e6, diameter_m=1.2)
        self.assertGreater(fp_high, 1.1)

        # Heat exchanger at 25 bar -> F_P > 1.0
        fp_hx = CostCorrelations.calculate_pressure_factor("heat_exchanger_fixed_tubesheet", 2.5e6)
        self.assertGreater(fp_hx, 1.05)

    def test_material_factors(self):
        """Verify material factors (F_M)."""
        fm_cs = CostCorrelations.get_material_factor("heat_exchanger_fixed_tubesheet", "Carbon Steel")
        self.assertEqual(fm_cs, 1.0)

        fm_ss = CostCorrelations.get_material_factor("heat_exchanger_fixed_tubesheet", "Stainless Steel 316")
        self.assertGreater(fm_ss, 2.0)

        fm_ti = CostCorrelations.get_material_factor("heat_exchanger_fixed_tubesheet", "Titanium")
        self.assertGreater(fm_ti, 5.0)

    def test_bare_module_cost_calculation(self):
        """Verify full bare module cost C_BM with CEPCI adjustment."""
        res_cs = CostCorrelations.calculate_bare_module_cost(
            equip_type="heat_exchanger_fixed_tubesheet",
            capacity=40.0,
            design_pressure_pa=101325.0,
            material="Carbon Steel",
            cepci=DEFAULT_CEPCI
        )
        self.assertIn("C_BM", res_cs)
        self.assertGreater(res_cs["C_BM"], res_cs["Cp"])
        self.assertAlmostEqual(res_cs["F_P"], 1.0)
        self.assertAlmostEqual(res_cs["F_M"], 1.0)

        # Stainless Steel should have higher C_BM
        res_ss = CostCorrelations.calculate_bare_module_cost(
            equip_type="heat_exchanger_fixed_tubesheet",
            capacity=40.0,
            design_pressure_pa=101325.0,
            material="Stainless Steel 316",
            cepci=DEFAULT_CEPCI
        )
        self.assertGreater(res_ss["C_BM"], res_cs["C_BM"])

    def test_equipment_costing_various_units(self):
        """Verify EquipmentCosting across different unit operation types."""
        # 1. Heater
        h = Heater("H-101", "Feed Heater", t_target=360.0)
        s_in = MaterialStream("S-1")
        s_in.T, s_in.P, s_in.F, s_in.z = 300.0, 101325.0, 10.0, {"water": 1.0}
        s_out = MaterialStream("S-2")
        h.connect_inlet(s_in)
        h.connect_outlet(s_out)
        h.run_simulation((0, 0), [], species_map=self.species_map)
        cost_h = EquipmentCosting.cost_unit(h)
        self.assertGreater(cost_h["C_BM"], 5000.0)
        self.assertEqual(cost_h["sizing_parameter"], "Heat Transfer Area")

        # 2. Pump
        p = FlowsheetPump("P-101", "Booster Pump", p_boost=300000.0)
        s_p_out = MaterialStream("S-3")
        p.connect_inlet(s_out)
        p.connect_outlet(s_p_out)
        p.run_simulation((0, 0), [], species_map=self.species_map)
        cost_p = EquipmentCosting.cost_unit(p)
        self.assertGreater(cost_p["C_BM"], 1000.0)

        # 3. Distillation Column
        col = BinaryDistillationColumn("C-101", "Ethanol Column", num_stages=10, feed_stage=5, reflux_ratio=2.5)
        cost_col = EquipmentCosting.cost_unit(col)
        self.assertGreater(cost_col["C_BM"], 5000.0)
        self.assertGreater(cost_col["internals_cost"], 0.0)

        # 4. Reactor
        cstr = IdealCSTR("R-101", "Bio Reactor", volume=5.0)
        cost_r = EquipmentCosting.cost_unit(cstr)
        self.assertGreater(cost_r["C_BM"], 20000.0)

        # 5. BaseUnit method call
        base_cost = cstr.cost_equipment(material="Stainless Steel 316")
        self.assertEqual(base_cost["material"], "Stainless Steel 316")
        self.assertGreater(base_cost["C_BM"], cost_r["C_BM"])

    def test_capital_costing_capex(self):
        """Verify CapitalCosting aggregation (C_BM, C_TM, C_GR, FCI, TCI)."""
        mock_costs = [
            {"Cp0": 20000.0, "Cp": 41500.0, "C_BM": 120000.0},
            {"Cp0": 15000.0, "Cp": 31100.0, "C_BM": 90000.0}
        ]
        capex = CapitalCosting.calculate_capex(mock_costs, plant_mode="Grassroots Plant")
        self.assertEqual(capex["total_bare_module_cost_C_BM"], 210000.0)
        # C_TM = 210000 * 1.18 = 247800
        self.assertAlmostEqual(capex["total_module_cost_C_TM"], 247800.0, places=1)
        # C_GR = C_TM + 0.50 * sum(Cp)
        self.assertGreater(capex["grassroots_capital_cost_C_GR"], capex["total_module_cost_C_TM"])
        self.assertEqual(capex["fixed_capital_investment_FCI"], capex["grassroots_capital_cost_C_GR"])
        self.assertGreater(capex["total_capital_investment_TCI"], capex["fixed_capital_investment_FCI"])

    def test_utility_costing_opex(self):
        """Verify utility OPEX calculations."""
        h = Heater("H-101", "Heater")
        h.heat_duty = 50000.0 # 50 kW
        h.outlets = [MaterialStream("S-out")]
        h.outlets[0].T = 360.0

        c = Cooler("C-101", "Cooler")
        c.heat_duty = -40000.0 # -40 kW cooling
        c.outlets = [MaterialStream("S-c-out")]
        c.outlets[0].T = 300.0

        p = FlowsheetPump("P-101", "Pump")
        p.work_input = 5000.0 # 5 kW electric

        opex = UtilityCosting.calculate_utility_opex([h, c, p], operating_hours_per_year=8000.0)
        self.assertEqual(opex["total_electricity_kW"], 5.0)
        self.assertEqual(opex["total_heating_duty_kW"], 50.0)
        self.assertEqual(opex["total_cooling_duty_kW"], 40.0)
        self.assertGreater(opex["annual_electricity_cost_usd"], 0.0)
        self.assertGreater(opex["annual_steam_cost_usd"], 0.0)
        self.assertGreater(opex["annual_cooling_water_cost_usd"], 0.0)
        self.assertGreater(opex["total_annual_utility_opex_usd"], 0.0)

    def test_profitability_analysis(self):
        """Verify cash flow, payback period, ROI, and NPV."""
        capex = {
            "fixed_capital_investment_FCI": 500000.0,
            "working_capital_WC": 75000.0,
            "total_capital_investment_TCI": 575000.0
        }
        opex = {
            "total_annual_utility_opex_usd": 40000.0,
            "operating_hours_per_year": 8000.0
        }
        s_in = MaterialStream("S-in")
        s_in.F = 10.0
        s_in.z = {"water": 1.0}
        s_out = MaterialStream("S-out")
        s_out.F = 10.0
        s_out.z = {"ethanol": 1.0}

        prof = EconomicAnalyzer.analyze_profitability(
            capex_dict=capex,
            utility_opex_dict=opex,
            streams_list=[s_in, s_out],
            species_map=self.species_map,
            project_lifetime_years=15,
            discount_rate=0.10
        )
        self.assertIn("annual_revenue_usd", prof)
        self.assertIn("cost_of_manufacturing_COM_usd", prof)
        self.assertIn("payback_period_years", prof)
        self.assertIn("return_on_investment_ROI_pct", prof)
        self.assertIn("net_present_value_NPV_usd", prof)
        self.assertEqual(len(prof["cumulative_cash_flow"]), 16) # Year 0 to 15
        self.assertEqual(prof["cumulative_cash_flow"][0], -capex["total_capital_investment_TCI"])

    def test_flowsheet_solver_compile_economics(self):
        """Verify full FlowsheetSolver economic compilation."""
        h = Heater("H-101", "Feed Heater", t_target=350.0)
        s1 = MaterialStream("S-1")
        s1.T, s1.P, s1.F, s1.z = 300.0, 101325.0, 10.0, {"ethanol": 0.5, "water": 0.5}
        s2 = MaterialStream("S-2")
        h.connect_inlet(s1)
        h.connect_outlet(s2)
        h.run_simulation((0, 0), [], species_map=self.species_map)

        units = [h]
        streams = [s1, s2]
        econ = FlowsheetSolver.compile_flowsheet_economics(units, streams, self.species_map)

        self.assertIn("equipment_costs", econ)
        self.assertIn("capex", econ)
        self.assertIn("opex", econ)
        self.assertIn("profitability", econ)
        self.assertEqual(len(econ["equipment_costs"]), 1)
        self.assertGreater(econ["capex"]["total_bare_module_cost_C_BM"], 0.0)

if __name__ == "__main__":
    unittest.main()
