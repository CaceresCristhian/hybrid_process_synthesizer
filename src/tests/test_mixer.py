import unittest
from src.database.loader import ChemicalDatabaseLoader
from src.units.stream import MaterialStream
from src.units.mixer import FlowsheetMixer

class TestFlowsheetMixer(unittest.TestCase):
    
    def test_adiabatic_mixer_balances(self):
        water = ChemicalDatabaseLoader.get_water_metadata()
        ethanol = ChemicalDatabaseLoader.get_ethanol_metadata()
        species_map = {water.id: water, ethanol.id: ethanol}
        
        # Input Stream 1: Pure Water, 300 K, 101325 Pa, 10.0 mol/s
        s1 = MaterialStream("S-101", "Feed 1")
        s1.T = 300.0
        s1.P = 101325.0
        s1.F = 10.0
        s1.z = {water.id: 1.0, ethanol.id: 0.0}
        
        # Input Stream 2: Pure Ethanol, 350 K, 200000 Pa, 5.0 mol/s
        s2 = MaterialStream("S-102", "Feed 2")
        s2.T = 350.0
        s2.P = 200000.0
        s2.F = 5.0
        s2.z = {water.id: 0.0, ethanol.id: 1.0}
        
        # Outlet Stream
        s3 = MaterialStream("S-103", "Mixed Outlet")
        
        # Mixer
        mixer = FlowsheetMixer("M-101", "Process Mixer")
        mixer.connect_inlet(s1)
        mixer.connect_inlet(s2)
        mixer.connect_outlet(s3)
        
        # Run simulation
        res = mixer.run_simulation((0,0), [], species_map=species_map)
        
        # Asserts
        # Molar flow conservation
        self.assertEqual(s3.F, 15.0)
        self.assertEqual(res["outlet_flow_mol_s"], 15.0)
        
        # Pressure selection (min of inlets)
        self.assertEqual(s3.P, 101325.0)
        
        # Composition mixing fractions
        self.assertAlmostEqual(s3.z[water.id], 10.0 / 15.0)
        self.assertAlmostEqual(s3.z[ethanol.id], 5.0 / 15.0)
        
        # Adiabatic temperature mixing
        # Enthalpy flow matches: H3 * F3 == H1 * F1 + H2 * F2
        h1 = s1.get_enthalpy(species_map)
        h2 = s2.get_enthalpy(species_map)
        h3 = s3.get_enthalpy(species_map)
        
        expected_energy_flow = 10.0 * h1 + 5.0 * h2
        actual_energy_flow = 15.0 * h3
        self.assertAlmostEqual(actual_energy_flow, expected_energy_flow, places=3)
        
        # Temperature is intermediate
        self.assertTrue(300.0 < s3.T < 350.0)
        print(f"Mixer simulation run successfully. Mixed Temp: {s3.T:.2f} K")

if __name__ == "__main__":
    unittest.main()
