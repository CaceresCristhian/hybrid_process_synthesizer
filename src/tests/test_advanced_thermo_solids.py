"""
Unit Tests for Advanced Thermodynamics & Solids Processing.
Covers:
1. UNIFAC functional group activity coefficient engine (combinatorial & residual).
2. UNIFAC isobaric VLE phase diagram generation & minimum-boiling azeotrope detection.
3. PC-SAFT equation of state (hard chain, dispersion attraction, Wertheim association).
4. PC-SAFT fluid isotherm generation and compressibility factor calculation.
5. Continuous MSMPR Crystallizer with Population Balance Modeling (moments m0-m4, CSD).
6. Industrial Convective Spray Dryer with psychrometric air-solid balances.
7. Flowsheet-wide solids compiler integration.
"""

import unittest
import numpy as np
from src.chemical_phenomena.unifac import UNIFACModel
from src.chemical_phenomena.pc_saft import PCSAFTModel
from src.units.solids import ContinuousCrystallizer, SprayDryer
from src.units.stream import MaterialStream
from src.control.flowsheet_solver import FlowsheetSolver


class TestAdvancedThermoSolids(unittest.TestCase):
    """Test suite for UNIFAC, PC-SAFT, and solids unit operations."""

    def test_unifac_activity_coefficients(self):
        """Test 1: UNIFAC activity coefficients on ethanol-water system."""
        # Equimolar mixture at 340 K
        comp = {"ethanol": 0.5, "water": 0.5}
        res = UNIFACModel.calculate_gammas(comp, temperature_k=340.0)

        self.assertIn("gammas", res)
        self.assertIn("ln_gamma_c", res)
        self.assertIn("ln_gamma_r", res)

        gamma_eth = res["gammas"]["ethanol"]
        gamma_water = res["gammas"]["water"]

        # Positive deviations from Raoult's law (gamma > 1)
        self.assertGreater(gamma_eth, 1.0)
        self.assertGreater(gamma_water, 1.0)

        # Dilute ethanol (infinite dilution)
        comp_dilute = {"ethanol": 0.001, "water": 0.999}
        res_dilute = UNIFACModel.calculate_gammas(comp_dilute, temperature_k=340.0)
        gamma_inf_eth = res_dilute["gammas"]["ethanol"]

        # Infinite dilution activity coefficient of ethanol in water is typically 4.0 - 6.0
        self.assertGreater(gamma_inf_eth, 3.5)
        self.assertGreater(gamma_inf_eth, gamma_eth)

    def test_unifac_vle_azeotrope(self):
        """Test 2: UNIFAC isobaric VLE phase envelope and minimum-boiling azeotrope detection."""
        # Test ethanol-benzene mixture which exhibits a well-defined minimum-boiling azeotrope
        vle = UNIFACModel.generate_vle_diagram("ethanol", "benzene", P_pa=101325.0, num_points=31)

        self.assertIn("x1", vle)
        self.assertIn("y1", vle)
        self.assertIn("T_C", vle)
        self.assertEqual(len(vle["x1"]), len(vle["y1"]))

        # Ethanol-benzene forms a minimum-boiling azeotrope at x ~ 0.47 and T ~ 67.6 C
        self.assertTrue(vle["azeotrope_found"])
        self.assertGreater(vle["azeotrope_x"], 0.35)
        self.assertLess(vle["azeotrope_x"], 0.65)
        self.assertLess(vle["azeotrope_t_c"], 78.0)  # Lower than pure ethanol (78.3 C) and benzene (80.1 C)

    def test_pc_saft_compressibility(self):
        """Test 3: PC-SAFT compressibility factor for non-polar and associating fluids."""
        # Non-polar fluid: Octane at 300 K, liquid density ~6000 mol/m3
        z_oct = PCSAFTModel.calculate_compressibility("octane", rho_mol_m3=6000.0, T_k=300.0)
        self.assertIn("Z", z_oct)
        self.assertIn("Z_hc", z_oct)
        self.assertIn("Z_disp", z_oct)
        self.assertGreater(z_oct["Z_hc"], 0.0)    # Hard-chain repulsion is positive
        self.assertLess(z_oct["Z_disp"], 0.0)    # Dispersion attraction is negative
        self.assertEqual(z_oct["Z_assoc"], 0.0)  # No hydrogen bonding for octane

        # Associating fluid: Water at 350 K, high density liquid ~55,000 mol/m3
        z_water = PCSAFTModel.calculate_compressibility("water", rho_mol_m3=55000.0, T_k=350.0)
        self.assertLess(z_water["Z_assoc"], 0.0)  # Wertheim association contribution is negative
        self.assertGreater(z_water["P_bar"], 0.0)

    def test_pc_saft_isotherms(self):
        """Test 4: PC-SAFT isotherm generator across density spectrum."""
        iso = PCSAFTModel.generate_isotherms("co2", temperatures_k=[320.0], num_points=20)

        self.assertIn("molar_densities_mol_m3", iso)
        self.assertIn("isotherms", iso)
        self.assertIn("320K", iso["isotherms"])
        self.assertEqual(len(iso["molar_densities_mol_m3"]), 20)

        p_bars = iso["isotherms"]["320K"]["P_bar"]
        # High density pressure should exceed low density pressure
        self.assertGreater(p_bars[-1], p_bars[0])

    def test_continuous_crystallizer_pbm(self):
        """Test 5: Continuous MSMPR Crystallizer PBM moments and CSD distribution."""
        cryst = ContinuousCrystallizer(
            unit_id="CR-101",
            name="Sugar Crystallizer",
            cryst_volume_m3=10.0,
            temp_cryst_k=298.15,
            growth_k=0.06,       # um / s
            nucleation_k=1.5e6   # # / (m3 s)
        )

        feed = MaterialStream("Feed-Aq")
        feed.T = 325.15
        feed.P = 101325.0
        feed.F = 40.0
        feed.z = {"water": 0.6, "sucrose": 0.4}
        feed.MW = 0.120
        cryst.connect_inlet(feed)

        res = cryst.run_simulation((0, 1), [0])

        self.assertIn("residence_time_min", res)
        self.assertGreater(res["residence_time_min"], 10.0)
        self.assertGreater(res["magma_density_kg_m3"], 10.0)
        self.assertGreater(res["solids_production_kg_h"], 100.0)
        self.assertGreater(res["L_43_um"], res["L_10_um"])
        self.assertEqual(len(res["psd_size_bins_um"]), len(res["psd_volume_density"]))

        # Check equipment sizing
        sizing = cryst.size_equipment()
        self.assertIn("vessel_diameter_m", sizing)
        self.assertIn("vessel_height_m", sizing)
        self.assertGreater(sizing["vessel_diameter_m"], 0.5)

    def test_spray_dryer_psychrometrics(self):
        """Test 6: Industrial Convective Spray Dryer psychrometric balances."""
        dryer = SprayDryer(
            unit_id="SD-101",
            name="Milk Powder Spray Dryer",
            inlet_gas_temp_c=195.0,
            outlet_target_moisture_pct=3.5,
            cyclone_efficiency_pct=99.0
        )

        feed = MaterialStream("Slurry-Feed")
        feed.T = 300.15
        feed.P = 101325.0
        feed.F = 25.0
        feed.z = {"water": 0.6, "solids": 0.4}
        feed.MW = 0.080
        dryer.connect_inlet(feed)

        res = dryer.run_simulation((0, 1), [0])

        self.assertIn("water_evaporated_kg_h", res)
        self.assertGreater(res["water_evaporated_kg_h"], 100.0)
        self.assertGreater(res["powder_produced_kg_h"], 100.0)
        self.assertGreater(res["burner_heat_duty_kW"], 50.0)
        self.assertGreater(res["thermal_efficiency_pct"], 35.0)
        self.assertLess(res["outlet_air_temp_C"], dryer.inlet_gas_temp_c)

        # Check equipment sizing
        sizing = dryer.size_equipment()
        self.assertIn("chamber_diameter_m", sizing)
        self.assertIn("chamber_volume_m3", sizing)
        self.assertGreater(sizing["chamber_diameter_m"], 1.0)

    def test_flowsheet_solids_compilation(self):
        """Test 7: Flowsheet solver solids compilation with crystallizer & spray dryer."""
        cryst = ContinuousCrystallizer("CR-101", "MSMPR Crystallizer", cryst_volume_m3=8.0)
        feed_c = MaterialStream("Saturated-Feed")
        feed_c.T = 320.15
        feed_c.P = 101325.0
        feed_c.F = 30.0
        feed_c.z = {"water": 0.7, "salt": 0.3}
        feed_c.MW = 0.080
        cryst.connect_inlet(feed_c)

        dryer = SprayDryer("SD-101", "Product Spray Dryer", inlet_gas_temp_c=185.0)
        feed_d = MaterialStream("Slurry-In")
        feed_d.T = 300.15
        feed_d.P = 101325.0
        feed_d.F = 20.0
        feed_d.z = {"water": 0.6, "solids": 0.4}
        feed_d.MW = 0.060
        dryer.connect_inlet(feed_d)

        flowsheet = {
            "CR-101": cryst,
            "SD-101": dryer
        }

        solids_summary = FlowsheetSolver.compile_flowsheet_solids(flowsheet)

        self.assertEqual(solids_summary["total_crystallizer_units"], 1)
        self.assertEqual(solids_summary["total_dryer_units"], 1)
        self.assertEqual(len(solids_summary["crystallizers"]), 1)
        self.assertEqual(len(solids_summary["dryers"]), 1)

        summary = solids_summary["summary"]
        self.assertGreater(summary["total_crystal_production_kg_h"], 0.0)
        self.assertGreater(summary["total_powder_production_kg_h"], 0.0)
        self.assertGreater(summary["total_water_evaporated_kg_h"], 0.0)


if __name__ == "__main__":
    unittest.main()
