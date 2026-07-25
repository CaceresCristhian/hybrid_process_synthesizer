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

    def test_additional_compounds(self):
        # Methanol
        methanol = ChemicalDatabaseLoader.get_methanol_metadata()
        self.assertEqual(methanol.formula, "CH4O")
        self.assertAlmostEqual(methanol.macro.boiling_point, 337.8)
        
        # Acetone
        acetone = ChemicalDatabaseLoader.get_acetone_metadata()
        self.assertEqual(acetone.formula, "C3H6O")
        self.assertAlmostEqual(acetone.macro.critical_temperature, 508.1)
        
        # Propane
        propane = ChemicalDatabaseLoader.get_propane_metadata()
        self.assertEqual(propane.formula, "C3H8")
        self.assertAlmostEqual(propane.macro.acentric_factor, 0.152)
        
        # Butane
        butane = ChemicalDatabaseLoader.get_butane_metadata()
        self.assertEqual(butane.formula, "C4H10")
        self.assertAlmostEqual(butane.macro.critical_pressure, 3.796e6)
        
        # Benzene
        benzene = ChemicalDatabaseLoader.get_benzene_metadata()
        self.assertEqual(benzene.formula, "C6H6")
        self.assertAlmostEqual(benzene.micro.molecular_weight, 78.11)
        
        # Toluene
        toluene = ChemicalDatabaseLoader.get_toluene_metadata()
        self.assertEqual(toluene.formula, "C7H8")
        self.assertAlmostEqual(toluene.macro.boiling_point, 383.8)

if __name__ == "__main__":
    unittest.main()
