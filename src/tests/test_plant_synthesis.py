import unittest
from src.database.loader import ChemicalDatabaseLoader
from src.units.stream import MaterialStream
from src.units.thermal import Heater, Cooler, HeatExchanger
from src.units.separators import FlashDrum, Splitter, SolidLiquidSeparator, MembraneUnit
from src.units.compressor import Compressor, Expander
from src.units.columns import AbsorptionColumn
from src.units.distillation import BinaryDistillationColumn
from src.units.mixer import FlowsheetMixer
from src.units.reactors import IdealCSTR
from src.control.flowsheet_solver import FlowsheetSolver

class TestPlantSynthesis(unittest.TestCase):

    def setUp(self):
        self.species_map = {
            "water": ChemicalDatabaseLoader.get_water_metadata(),
            "ethanol": ChemicalDatabaseLoader.get_ethanol_metadata(),
            "hydrogen": ChemicalDatabaseLoader.get_hydrogen_metadata(),
            "nitrogen": ChemicalDatabaseLoader.get_nitrogen_metadata(),
            "ammonia": ChemicalDatabaseLoader.get_ammonia_metadata(),
            "pentane": ChemicalDatabaseLoader.get_pentane_metadata(),
            "octane": ChemicalDatabaseLoader.get_octane_metadata(),
            "glucose": ChemicalDatabaseLoader.get_glucose_metadata(),
            "co2": ChemicalDatabaseLoader.get_co2_metadata()
        }

    def test_out_of_order_solver(self):
        """Verify multi-pass solver solves C-101 fed by P-101 regardless of alphabetical order."""
        # C-101 comes alphabetically before P-101
        c101 = BinaryDistillationColumn("C-101", "C-101", num_stages=12, feed_stage=6, reflux_ratio=2.5)
        
        class MockPump(Heater):
            def run_simulation(self, time_span, initial_state, **kwargs):
                if self.inlets and self.inlets[0].F:
                    self.outlets[0].T = self.inlets[0].T
                    self.outlets[0].P = self.inlets[0].P + 200000.0
                    self.outlets[0].F = self.inlets[0].F
                    self.outlets[0].z = self.inlets[0].z.copy()
        p101 = MockPump("P-101", "P-101")
        
        s1 = MaterialStream("S-101")
        s1.T, s1.P, s1.F, s1.z = 350.0, 101325.0, 10.0, {"ethanol": 0.5, "water": 0.5}
        s2 = MaterialStream("S-102")
        s3 = MaterialStream("S-103")
        s4 = MaterialStream("S-104")
        
        p101.connect_inlet(s1)
        p101.connect_outlet(s2)
        c101.connect_inlet(s2)
        c101.connect_outlet(s3)
        c101.connect_outlet(s4)
        
        units = {"C-101": c101, "P-101": p101}
        streams = {"S-101": s1, "S-102": s2, "S-103": s3, "S-104": s4}
        
        res = FlowsheetSolver.solve_flowsheet_topology(units, streams, self.species_map)
        self.assertTrue(res["converged"])
        self.assertIsNotNone(s3.F)
        self.assertIsNotNone(s4.F)
        self.assertAlmostEqual(s3.F + s4.F, s1.F, places=4)

    def test_thermal_units(self):
        """Test Heater and Cooler energy duties."""
        heater = Heater("H-101", "Heater", t_target=380.0)
        s_in = MaterialStream("S-in")
        s_in.T, s_in.P, s_in.F, s_in.z = 300.0, 101325.0, 5.0, {"water": 1.0}
        s_out = MaterialStream("S-out")
        heater.connect_inlet(s_in)
        heater.connect_outlet(s_out)
        
        heater.run_simulation((0,0), [], species_map=self.species_map)
        self.assertEqual(s_out.T, 380.0)
        self.assertGreater(heater.heat_duty, 0.0)
        
        cooler = Cooler("C-101", "Cooler", t_target=280.0)
        s_c_out = MaterialStream("S-c-out")
        cooler.connect_inlet(s_out)
        cooler.connect_outlet(s_c_out)
        cooler.run_simulation((0,0), [], species_map=self.species_map)
        self.assertEqual(s_c_out.T, 280.0)
        self.assertLess(cooler.heat_duty, 0.0)

    def test_flash_drum_and_splitter(self):
        """Test 2-Phase Separator and Splitter conservation."""
        flash = FlashDrum("F-101", "Flash", temp_vessel=360.0)
        s_in = MaterialStream("S-in")
        s_in.T, s_in.P, s_in.F, s_in.z = 350.0, 101325.0, 10.0, {"ethanol": 0.4, "water": 0.6}
        s_vap = MaterialStream("S-vap")
        s_liq = MaterialStream("S-liq")
        flash.connect_inlet(s_in)
        flash.connect_outlet(s_vap)
        flash.connect_outlet(s_liq)
        
        flash.run_simulation((0,0), [], species_map=self.species_map)
        self.assertAlmostEqual(s_vap.F + s_liq.F, s_in.F, places=4)
        
        splitter = Splitter("SP-101", "Splitter", split_ratios=[0.7, 0.3])
        s_out1 = MaterialStream("S-out1")
        s_out2 = MaterialStream("S-out2")
        splitter.connect_inlet(s_vap)
        splitter.connect_outlet(s_out1)
        splitter.connect_outlet(s_out2)
        splitter.run_simulation((0,0), [], species_map=self.species_map)
        self.assertAlmostEqual(s_out1.F + s_out2.F, s_vap.F, places=4)
        self.assertAlmostEqual(s_out1.F, s_vap.F * 0.7, places=4)

    def test_compressor_work(self):
        """Test gas compressor work input and pressure rise."""
        comp = Compressor("K-101", "Compressor", pressure_ratio=4.0)
        s_in = MaterialStream("S-in")
        s_in.T, s_in.P, s_in.F, s_in.z = 300.0, 100000.0, 8.0, {"hydrogen": 1.0}
        s_out = MaterialStream("S-out")
        comp.connect_inlet(s_in)
        comp.connect_outlet(s_out)
        comp.run_simulation((0,0), [], species_map=self.species_map)
        
        self.assertEqual(s_out.P, 400000.0)
        self.assertGreater(s_out.T, s_in.T)
        self.assertGreater(comp.work_input, 0.0)

    def test_brewery_plant_mass_balance(self):
        """Verify multi-unit brewery flowsheet mass conservation."""
        m101 = FlowsheetMixer("M-101", "Mash Mixer")
        h101 = Heater("H-101", "Mash Kettle", t_target=370.0)
        s101 = SolidLiquidSeparator("S-101", "Lauter Tun", recovery_liquid=0.90)
        
        s_water = MaterialStream("S-water")
        s_water.T, s_water.P, s_water.F, s_water.z = 295.0, 101325.0, 30.0, {"water": 1.0}
        
        s_grist = MaterialStream("S-grist")
        s_grist.T, s_grist.P, s_grist.F, s_grist.z = 295.0, 101325.0, 10.0, {"glucose": 0.85, "water": 0.15}
        
        s_mash = MaterialStream("S-mash")
        s_hot_mash = MaterialStream("S-hot-mash")
        s_wort = MaterialStream("S-wort")
        s_spent = MaterialStream("S-spent")
        
        m101.connect_inlet(s_water)
        m101.connect_inlet(s_grist)
        m101.connect_outlet(s_mash)
        
        h101.connect_inlet(s_mash)
        h101.connect_outlet(s_hot_mash)
        
        s101.connect_inlet(s_hot_mash)
        s101.connect_outlet(s_wort)
        s101.connect_outlet(s_spent)
        
        units = {"M-101": m101, "H-101": h101, "S-101": s101}
        streams = {
            "S-water": s_water, "S-grist": s_grist, "S-mash": s_mash, 
            "S-hot-mash": s_hot_mash, "S-wort": s_wort, "S-spent": s_spent
        }
        
        res = FlowsheetSolver.solve_flowsheet_topology(units, streams, self.species_map)
        self.assertTrue(res["converged"])
        
        # Check overall mass balance
        mb = FlowsheetSolver.compile_mass_balance(list(streams.values()), self.species_map)
        self.assertAlmostEqual(mb["mass_balance_error_kg_h"], 0.0, places=2)

if __name__ == "__main__":
    unittest.main()
