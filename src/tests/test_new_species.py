import unittest
from src.database.loader import ChemicalDatabaseLoader
from src.chemical_phenomena.thermodynamics import Thermodynamics

class TestNewSpecies(unittest.TestCase):
    
    def test_octane_metadata(self):
        octane = ChemicalDatabaseLoader.get_octane_metadata()
        self.assertEqual(octane.id, "octane")
        self.assertEqual(octane.name, "Octane")
        self.assertEqual(octane.formula, "C8H18")
        self.assertAlmostEqual(octane.micro.molecular_weight, 114.23)
        self.assertAlmostEqual(octane.macro.critical_temperature, 568.7)
        self.assertAlmostEqual(octane.macro.critical_pressure, 2.49e6)
        self.assertAlmostEqual(octane.macro.acentric_factor, 0.398)
        self.assertEqual(len(octane.system.antoine_coefficients), 3)

    def test_phenol_metadata(self):
        phenol = ChemicalDatabaseLoader.get_phenol_metadata()
        self.assertEqual(phenol.id, "phenol")
        self.assertEqual(phenol.name, "Phenol")
        self.assertEqual(phenol.formula, "C6H6O")
        self.assertAlmostEqual(phenol.micro.molecular_weight, 94.11)
        self.assertAlmostEqual(phenol.macro.critical_temperature, 694.2)
        self.assertAlmostEqual(phenol.macro.critical_pressure, 6.13e6)
        self.assertAlmostEqual(phenol.macro.acentric_factor, 0.444)
        
    def test_octane_phenol_flash(self):
        octane = ChemicalDatabaseLoader.get_octane_metadata()
        phenol = ChemicalDatabaseLoader.get_phenol_metadata()
        
        # Test basic TP flash at 420 K, 200 kPa (2.0 bar)
        species_list = [octane, phenol]
        composition = {octane.id: 0.50, phenol.id: 0.50}
        
        flash_res = Thermodynamics.solve_tp_flash(species_list, composition, 420.0, 200e3)
        self.assertTrue(0.0 <= flash_res["beta"] <= 1.0)
        self.assertIn(octane.id, flash_res["x"])
        self.assertIn(phenol.id, flash_res["y"])
        print(f"Octane-Phenol Flash at 420 K, 2 bar Vapor Fraction: {flash_res['beta']*100:.2f}%")

if __name__ == "__main__":
    unittest.main()
