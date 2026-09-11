import unittest
import numpy as np
from src.database.loader import ChemicalDatabaseLoader
from src.chemical_phenomena.activity_models import NRTLModel, WilsonModel, VLEPhaseDiagramGenerator
from src.chemical_phenomena.thermodynamics import Thermodynamics
from src.chemical_phenomena.reactions import Reaction, ReactionNetwork, REACTION_PACKAGES
from src.units.reactors import IdealCSTR, IdealPFR, EquilibriumReactor
from src.units.stream import MaterialStream

class TestThermoReactions(unittest.TestCase):

    def setUp(self):
        self.water = ChemicalDatabaseLoader.get_water_metadata()
        self.ethanol = ChemicalDatabaseLoader.get_ethanol_metadata()
        self.hydrogen = ChemicalDatabaseLoader.get_hydrogen_metadata()
        self.nitrogen = ChemicalDatabaseLoader.get_nitrogen_metadata()
        self.ammonia = ChemicalDatabaseLoader.get_ammonia_metadata()
        self.glucose = ChemicalDatabaseLoader.get_glucose_metadata()
        self.co2 = ChemicalDatabaseLoader.get_co2_metadata()

    def test_nrtl_ethanol_water_azeotrope(self):
        """Verify NRTL activity coefficients and azeotrope detection for Ethanol-Water."""
        comp = {"ethanol": 0.89, "water": 0.11}
        gammas = NRTLModel.calculate_gammas(comp, 351.4)
        
        self.assertIn("ethanol", gammas)
        self.assertIn("water", gammas)
        # Water exhibits strong positive deviation in ethanol-rich liquid
        self.assertGreater(gammas["water"], 3.0)
        self.assertAlmostEqual(gammas["ethanol"], 1.04, delta=0.2)

        # Test phase diagram and azeotrope identification
        diag = VLEPhaseDiagramGenerator.generate_diagram(self.ethanol, self.water, 101325.0, model="nrtl", num_points=50)
        self.assertTrue(diag["has_azeotrope"])
        self.assertIsNotNone(diag["azeotrope_x1"])
        self.assertIsNotNone(diag["azeotrope_T_K"])
        # Atmospheric azeotrope occurs in the 70-95 mol% region and 345-352 K
        self.assertTrue(0.65 <= diag["azeotrope_x1"] <= 0.95)
        self.assertTrue(344.0 <= diag["azeotrope_T_K"] <= 352.5)

    def test_wilson_activity_model(self):
        """Verify Wilson activity model consistency and pure component limits."""
        # Pure ethanol limit: gamma = 1.0
        pure_comp = {"ethanol": 1.0}
        gammas_pure = WilsonModel.calculate_gammas(pure_comp, 350.0)
        self.assertAlmostEqual(gammas_pure["ethanol"], 1.0, places=4)

        # Binary mixture
        comp = {"ethanol": 0.5, "water": 0.5}
        gammas = WilsonModel.calculate_gammas(comp, 350.0)
        self.assertGreater(gammas["ethanol"], 1.0)
        self.assertGreater(gammas["water"], 1.0)

    def test_thermodynamics_tp_flash_nrtl(self):
        """Verify Thermodynamics.solve_tp_flash with method='nrtl'."""
        feed_comp = {"ethanol": 0.40, "water": 0.60}
        res = Thermodynamics.solve_tp_flash([self.ethanol, self.water], feed_comp, 355.0, 101325.0, method="nrtl")
        
        self.assertIn("beta", res)
        self.assertIn("x", res)
        self.assertIn("y", res)
        self.assertTrue(0.0 < res["beta"] < 1.0)
        # Vapor is enriched in light component ethanol
        self.assertGreater(res["y"]["ethanol"], res["x"]["ethanol"])
        # Liquid and vapor fractions sum to 1.0
        self.assertAlmostEqual(sum(res["x"].values()), 1.0, places=4)
        self.assertAlmostEqual(sum(res["y"].values()), 1.0, places=4)

    def test_reaction_arrhenius_rates(self):
        """Verify temperature-dependent Arrhenius rate kinetics and reversibility."""
        rxn = Reaction(
            reaction_id="TEST-01",
            name="A <-> B",
            stoichiometry={"a": -1.0, "b": 1.0},
            reaction_type="kinetic",
            A_forward=1.0e6,
            Ea_forward=50000.0,
            delta_H_298=-40000.0,
            delta_G_298=-15000.0
        )
        
        k_300 = rxn.k_forward(300.0)
        k_400 = rxn.k_forward(400.0)
        self.assertGreater(k_400, k_300, "Reaction rate constant must increase with temperature.")
        
        # Exothermic reaction: K_eq decreases as temperature increases (Le Chatelier)
        K_300 = rxn.K_equilibrium(300.0)
        K_400 = rxn.K_equilibrium(400.0)
        self.assertGreater(K_300, K_400, "Exothermic equilibrium constant must decrease with increasing temperature.")

    def test_haber_bosch_equilibrium_solver(self):
        """Verify chemical equilibrium extent solver for Haber-Bosch ammonia synthesis."""
        hb = REACTION_PACKAGES["Haber-Bosch Ammonia Synthesis"]
        feed = {"nitrogen": 10.0, "hydrogen": 30.0, "ammonia": 0.0}
        
        # 400 °C (673.15 K) and 15 MPa
        out = hb.solve_chemical_equilibrium(feed, temperature=673.15, pressure=15.0e6)
        
        self.assertGreater(out["ammonia"], 5.0, "Ammonia should be synthesized at 150 bar.")
        self.assertLess(out["nitrogen"], 10.0)
        self.assertLess(out["hydrogen"], 30.0)
        
        # Exact atomic nitrogen and hydrogen conservation
        n_atoms_in = 10.0 * 2.0
        n_atoms_out = out["nitrogen"] * 2.0 + out["ammonia"] * 1.0
        self.assertAlmostEqual(n_atoms_in, n_atoms_out, places=3)

        h_atoms_in = 30.0 * 2.0
        h_atoms_out = out["hydrogen"] * 2.0 + out["ammonia"] * 3.0
        self.assertAlmostEqual(h_atoms_in, h_atoms_out, places=3)

    def test_cstr_rigorous_reaction_solver(self):
        """Verify IdealCSTR with Bio-Ethanol fermentation package."""
        cstr = IdealCSTR("R-101", "Fermenter", volume=10.0, reaction_package="Bio-Ethanol Fermentation")
        s_in = MaterialStream("S-101")
        s_in.T = 305.15
        s_in.P = 101325.0
        s_in.F = 15.0
        s_in.z = {"glucose": 0.20, "water": 0.80}
        
        s_out = MaterialStream("S-102")
        cstr.connect_inlet(s_in)
        cstr.connect_outlet(s_out)
        
        res = cstr.run_simulation((0,0), [])
        self.assertIn("conversion", res)
        self.assertGreater(s_out.z.get("ethanol", 0.0), 0.0)
        self.assertGreater(s_out.z.get("co2", 0.0), 0.0)
        self.assertLess(s_out.z.get("glucose", 0.20), 0.20)
        # Exothermic reaction heat
        self.assertLess(cstr.heat_duty, 0.0)

    def test_pfr_axial_solver(self):
        """Verify IdealPFR axial profile solver and conversion."""
        pfr = IdealPFR("PFR-101", "Tubular Reactor", volume=4.0, reaction_package="Generic 1st-Order Exothermic")
        s_in = MaterialStream("S-101")
        s_in.T = 350.0
        s_in.P = 200000.0
        s_in.F = 10.0
        s_in.z = {"a": 1.0}
        
        s_out = MaterialStream("S-102")
        pfr.connect_inlet(s_in)
        pfr.connect_outlet(s_out)
        
        res = pfr.run_simulation((0,0), [])
        self.assertIn("conversion", res)
        self.assertGreater(s_out.z.get("b", 0.0), 0.0)
        self.assertLess(s_out.z.get("a", 1.0), 1.0)
        self.assertAlmostEqual(s_out.z.get("a", 0.0) + s_out.z.get("b", 0.0), 1.0, places=4)

    def test_equilibrium_reactor(self):
        """Verify EquilibriumReactor (REquil) synthesis of ammonia."""
        requil = EquilibriumReactor("R-101", "Ammonia Converter", volume=5.0, reaction_package="Haber-Bosch Ammonia Synthesis")
        s_in = MaterialStream("S-101")
        s_in.T = 673.15
        s_in.P = 15.0e6
        s_in.F = 40.0
        s_in.z = {"nitrogen": 0.25, "hydrogen": 0.75}
        
        s_out = MaterialStream("S-102")
        requil.connect_inlet(s_in)
        requil.connect_outlet(s_out)
        
        res = requil.run_simulation((0,0), [])
        self.assertGreater(s_out.z.get("ammonia", 0.0), 0.15)
        # Exothermic heat generated
        self.assertLess(requil.heat_duty, 0.0)
        # Sizing checks
        sizing = requil.size_equipment()
        self.assertIn("catalyst_volume_m3", sizing)
        self.assertIn("design_diameter_m", sizing)

if __name__ == "__main__":
    unittest.main()
