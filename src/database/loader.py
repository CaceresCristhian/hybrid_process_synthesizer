from src.database.chemical_db import (
    ChemicalSpecies,
    MicroScaleData,
    MacroScaleData,
    SystemScaleData
)

class ChemicalDatabaseLoader:
    """ETL connector and database loader for chemical species."""
    
    @staticmethod
    def get_water_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Water (H2O)."""
        return ChemicalSpecies(
            id="water",
            name="Water",
            formula="H2O",
            micro=MicroScaleData(
                molecular_weight=18.015,
                electronegativities={"H": 2.20, "O": 3.44},
                dipole_moment=1.85,
                polarizability=1.45,
                smiles="O"
            ),
            macro=MacroScaleData(
                boiling_point=373.15,
                melting_point=273.15,
                critical_temperature=647.1,
                critical_pressure=22.06e6,
                critical_volume=0.056,
                acentric_factor=0.344,
                cp_constants=[75.3, 0.0, 0.0, 0.0]  # constant Cp liquid approx J/mol K
            ),
            system=SystemScaleData(
                # Antoine constants for log10(P_bar) = A - B / (T_K + C)
                antoine_coefficients=[5.20389, 1733.926, -39.485]
            )
        )

    @staticmethod
    def get_ethanol_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Ethanol (C2H5OH)."""
        return ChemicalSpecies(
            id="ethanol",
            name="Ethanol",
            formula="C2H6O",
            micro=MicroScaleData(
                molecular_weight=46.07,
                electronegativities={"H": 2.20, "C": 2.55, "O": 3.44},
                dipole_moment=1.69,
                polarizability=5.41,
                smiles="CCO"
            ),
            macro=MacroScaleData(
                boiling_point=351.5,
                melting_point=159.0,
                critical_temperature=514.0,
                critical_pressure=6.14e6,
                critical_volume=0.167,
                acentric_factor=0.649,
                cp_constants=[112.4, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[5.24677, 1598.673, -46.424]
            )
        )

    @staticmethod
    def get_methane_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Methane (CH4)."""
        return ChemicalSpecies(
            id="methane",
            name="Methane",
            formula="CH4",
            micro=MicroScaleData(
                molecular_weight=16.04,
                electronegativities={"H": 2.20, "C": 2.55},
                dipole_moment=0.0,
                polarizability=2.59,
                smiles="C"
            ),
            macro=MacroScaleData(
                boiling_point=111.6,
                melting_point=90.7,
                critical_temperature=190.56,
                critical_pressure=4.599e6,
                critical_volume=0.099,
                acentric_factor=0.011,
                cp_constants=[35.7, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[3.9895, 343.51, -15.15]
            )
        )

    @staticmethod
    def get_ethane_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Ethane (C2H6)."""
        return ChemicalSpecies(
            id="ethane",
            name="Ethane",
            formula="C2H6",
            micro=MicroScaleData(
                molecular_weight=30.07,
                electronegativities={"H": 2.20, "C": 2.55},
                dipole_moment=0.0,
                polarizability=4.47,
                smiles="CC"
            ),
            macro=MacroScaleData(
                boiling_point=184.5,
                melting_point=90.3,
                critical_temperature=305.32,
                critical_pressure=4.872e6,
                critical_volume=0.148,
                acentric_factor=0.099,
                cp_constants=[52.6, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[3.93835, 659.739, -16.719]
            )
        )

    @staticmethod
    def get_octane_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Octane (C8H18)."""
        return ChemicalSpecies(
            id="octane",
            name="Octane",
            formula="C8H18",
            micro=MicroScaleData(
                molecular_weight=114.23,
                electronegativities={"H": 2.20, "C": 2.55},
                dipole_moment=0.0,
                polarizability=15.6,
                smiles="CCCCCCCC"
            ),
            macro=MacroScaleData(
                boiling_point=398.8,
                melting_point=216.4,
                critical_temperature=568.7,
                critical_pressure=2.49e6,
                critical_volume=0.492,
                acentric_factor=0.398,
                cp_constants=[254.0, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[4.04867, 1355.126, -63.633]
            )
        )

    @staticmethod
    def get_phenol_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Phenol (C6H5OH)."""
        return ChemicalSpecies(
            id="phenol",
            name="Phenol",
            formula="C6H6O",
            micro=MicroScaleData(
                molecular_weight=94.11,
                electronegativities={"H": 2.20, "C": 2.55, "O": 3.44},
                dipole_moment=1.22,
                polarizability=11.1,
                smiles="Oc1ccccc1"
            ),
            macro=MacroScaleData(
                boiling_point=455.0,
                melting_point=314.1,
                critical_temperature=694.2,
                critical_pressure=6.13e6,
                critical_volume=0.268,
                acentric_factor=0.444,
                cp_constants=[124.0, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[4.11475, 1516.075, -98.985]
            )
        )

    @staticmethod
    def get_methanol_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Methanol (CH3OH)."""
        return ChemicalSpecies(
            id="methanol",
            name="Methanol",
            formula="CH4O",
            micro=MicroScaleData(
                molecular_weight=32.04,
                electronegativities={"H": 2.20, "C": 2.55, "O": 3.44},
                dipole_moment=1.70,
                polarizability=3.2,
                smiles="CO"
            ),
            macro=MacroScaleData(
                boiling_point=337.8,
                melting_point=175.6,
                critical_temperature=512.6,
                critical_pressure=8.09e6,
                critical_volume=0.118,
                acentric_factor=0.556,
                cp_constants=[81.1, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[5.20409, 1581.341, -33.5]
            )
        )

    @staticmethod
    def get_acetone_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Acetone (C3H6O)."""
        return ChemicalSpecies(
            id="acetone",
            name="Acetone",
            formula="C3H6O",
            micro=MicroScaleData(
                molecular_weight=58.08,
                electronegativities={"H": 2.20, "C": 2.55, "O": 3.44},
                dipole_moment=2.91,
                polarizability=6.4,
                smiles="CC(=O)C"
            ),
            macro=MacroScaleData(
                boiling_point=329.4,
                melting_point=178.2,
                critical_temperature=508.1,
                critical_pressure=4.7e6,
                critical_volume=0.209,
                acentric_factor=0.304,
                cp_constants=[125.0, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[4.42448, 1312.253, -32.445]
            )
        )

    @staticmethod
    def get_propane_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Propane (C3H8)."""
        return ChemicalSpecies(
            id="propane",
            name="Propane",
            formula="C3H8",
            micro=MicroScaleData(
                molecular_weight=44.10,
                electronegativities={"H": 2.20, "C": 2.55},
                dipole_moment=0.08,
                polarizability=6.3,
                smiles="CCC"
            ),
            macro=MacroScaleData(
                boiling_point=231.1,
                melting_point=85.5,
                critical_temperature=369.83,
                critical_pressure=4.25e6,
                critical_volume=0.203,
                acentric_factor=0.152,
                cp_constants=[73.5, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[3.92724, 803.292, -26.11]
            )
        )

    @staticmethod
    def get_butane_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Butane (C4H10)."""
        return ChemicalSpecies(
            id="butane",
            name="Butane",
            formula="C4H10",
            micro=MicroScaleData(
                molecular_weight=58.12,
                electronegativities={"H": 2.20, "C": 2.55},
                dipole_moment=0.0,
                polarizability=8.2,
                smiles="CCCC"
            ),
            macro=MacroScaleData(
                boiling_point=272.7,
                melting_point=134.9,
                critical_temperature=425.12,
                critical_pressure=3.796e6,
                critical_volume=0.255,
                acentric_factor=0.200,
                cp_constants=[97.5, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[4.35576, 1175.581, -2.071]
            )
        )

    @staticmethod
    def get_benzene_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Benzene (C6H6)."""
        return ChemicalSpecies(
            id="benzene",
            name="Benzene",
            formula="C6H6",
            micro=MicroScaleData(
                molecular_weight=78.11,
                electronegativities={"H": 2.20, "C": 2.55},
                dipole_moment=0.0,
                polarizability=10.3,
                smiles="c1ccccc1"
            ),
            macro=MacroScaleData(
                boiling_point=353.2,
                melting_point=278.7,
                critical_temperature=562.05,
                critical_pressure=4.895e6,
                critical_volume=0.259,
                acentric_factor=0.210,
                cp_constants=[136.1, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[4.02232, 1206.531, -52.886]
            )
        )

    @staticmethod
    def get_toluene_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Toluene (C7H8)."""
        return ChemicalSpecies(
            id="toluene",
            name="Toluene",
            formula="C7H8",
            micro=MicroScaleData(
                molecular_weight=92.14,
                electronegativities={"H": 2.20, "C": 2.55},
                dipole_moment=0.36,
                polarizability=12.3,
                smiles="Cc1ccccc1"
            ),
            macro=MacroScaleData(
                boiling_point=383.8,
                melting_point=178.2,
                critical_temperature=591.8,
                critical_pressure=4.1e6,
                critical_volume=0.316,
                acentric_factor=0.264,
                cp_constants=[156.0, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[4.07827, 1343.943, -53.773]
            )
        )

    @staticmethod
    def get_hydrogen_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Hydrogen (H2)."""
        return ChemicalSpecies(
            id="hydrogen",
            name="Hydrogen",
            formula="H2",
            micro=MicroScaleData(
                molecular_weight=2.016,
                electronegativities={"H": 2.20},
                dipole_moment=0.0,
                polarizability=0.8,
                smiles="[H][H]"
            ),
            macro=MacroScaleData(
                boiling_point=20.28,
                melting_point=14.01,
                critical_temperature=33.19,
                critical_pressure=1.296e6,
                critical_volume=0.065,
                acentric_factor=-0.216,
                cp_constants=[28.8, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[3.543, 99.3, 7.7]
            )
        )

    @staticmethod
    def get_co2_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Carbon Dioxide (CO2)."""
        return ChemicalSpecies(
            id="co2",
            name="Carbon Dioxide",
            formula="CO2",
            micro=MicroScaleData(
                molecular_weight=44.01,
                electronegativities={"C": 2.55, "O": 3.44},
                dipole_moment=0.0,
                polarizability=2.9,
                smiles="O=C=O"
            ),
            macro=MacroScaleData(
                boiling_point=194.7,
                melting_point=216.6,
                critical_temperature=304.13,
                critical_pressure=7.377e6,
                critical_volume=0.094,
                acentric_factor=0.224,
                cp_constants=[37.1, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[6.812, 1301.6, -3.49]
            )
        )

    @staticmethod
    def get_nitrogen_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Nitrogen (N2)."""
        return ChemicalSpecies(
            id="nitrogen",
            name="Nitrogen",
            formula="N2",
            micro=MicroScaleData(
                molecular_weight=28.013,
                electronegativities={"N": 3.04},
                dipole_moment=0.0,
                polarizability=1.74,
                smiles="N#N"
            ),
            macro=MacroScaleData(
                boiling_point=77.36,
                melting_point=63.15,
                critical_temperature=126.2,
                critical_pressure=3.39e6,
                critical_volume=0.090,
                acentric_factor=0.037,
                cp_constants=[29.1, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[3.736, 264.65, -6.78]
            )
        )

    @staticmethod
    def get_ammonia_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Ammonia (NH3)."""
        return ChemicalSpecies(
            id="ammonia",
            name="Ammonia",
            formula="NH3",
            micro=MicroScaleData(
                molecular_weight=17.031,
                electronegativities={"N": 3.04, "H": 2.20},
                dipole_moment=1.47,
                polarizability=2.2,
                smiles="N"
            ),
            macro=MacroScaleData(
                boiling_point=239.8,
                melting_point=195.4,
                critical_temperature=405.4,
                critical_pressure=11.33e6,
                critical_volume=0.0725,
                acentric_factor=0.256,
                cp_constants=[35.1, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[4.868, 1113.9, -10.4]
            )
        )

    @staticmethod
    def get_pentane_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for n-Pentane (C5H12)."""
        return ChemicalSpecies(
            id="pentane",
            name="Pentane",
            formula="C5H12",
            micro=MicroScaleData(
                molecular_weight=72.15,
                electronegativities={"C": 2.55, "H": 2.20},
                dipole_moment=0.0,
                polarizability=10.0,
                smiles="CCCCC"
            ),
            macro=MacroScaleData(
                boiling_point=309.2,
                melting_point=143.4,
                critical_temperature=469.7,
                critical_pressure=3.37e6,
                critical_volume=0.311,
                acentric_factor=0.251,
                cp_constants=[120.0, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[3.989, 1070.6, -40.4]
            )
        )

    @staticmethod
    def get_hexane_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for n-Hexane (C6H14)."""
        return ChemicalSpecies(
            id="hexane",
            name="Hexane",
            formula="C6H14",
            micro=MicroScaleData(
                molecular_weight=86.18,
                electronegativities={"C": 2.55, "H": 2.20},
                dipole_moment=0.0,
                polarizability=11.8,
                smiles="CCCCCC"
            ),
            macro=MacroScaleData(
                boiling_point=341.9,
                melting_point=177.8,
                critical_temperature=507.6,
                critical_pressure=3.025e6,
                critical_volume=0.370,
                acentric_factor=0.301,
                cp_constants=[143.0, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[4.002, 1171.5, -48.7]
            )
        )

    @staticmethod
    def get_decane_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for n-Decane (C10H22)."""
        return ChemicalSpecies(
            id="decane",
            name="Decane",
            formula="C10H22",
            micro=MicroScaleData(
                molecular_weight=142.29,
                electronegativities={"C": 2.55, "H": 2.20},
                dipole_moment=0.0,
                polarizability=19.3,
                smiles="CCCCCCCCCC"
            ),
            macro=MacroScaleData(
                boiling_point=447.3,
                melting_point=243.5,
                critical_temperature=617.7,
                critical_pressure=2.11e6,
                critical_volume=0.600,
                acentric_factor=0.492,
                cp_constants=[314.0, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[4.078, 1501.2, -78.9]
            )
        )

    @staticmethod
    def get_pxylene_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for p-Xylene (C8H10)."""
        return ChemicalSpecies(
            id="pxylene",
            name="p-Xylene",
            formula="C8H10",
            micro=MicroScaleData(
                molecular_weight=106.17,
                electronegativities={"C": 2.55, "H": 2.20},
                dipole_moment=0.0,
                polarizability=14.2,
                smiles="Cc1ccc(C)cc1"
            ),
            macro=MacroScaleData(
                boiling_point=411.5,
                melting_point=286.4,
                critical_temperature=616.2,
                critical_pressure=3.51e6,
                critical_volume=0.379,
                acentric_factor=0.322,
                cp_constants=[181.0, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[4.113, 1453.4, -59.3]
            )
        )

    @staticmethod
    def get_glucose_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Glucose (C6H12O6)."""
        return ChemicalSpecies(
            id="glucose",
            name="Glucose",
            formula="C6H12O6",
            micro=MicroScaleData(
                molecular_weight=180.16,
                electronegativities={"C": 2.55, "H": 2.20, "O": 3.44},
                dipole_moment=2.8,
                polarizability=16.0,
                smiles="C(C1C(C(C(C(O1)O)O)O)O)O"
            ),
            macro=MacroScaleData(
                boiling_point=683.0,
                melting_point=419.0,
                critical_temperature=850.0,
                critical_pressure=5.0e6,
                critical_volume=0.45,
                acentric_factor=0.90,
                cp_constants=[218.0, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[6.5, 3500.0, -100.0]
            )
        )

    @staticmethod
    def get_acetic_acid_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Acetic Acid (C2H4O2)."""
        return ChemicalSpecies(
            id="acetic_acid",
            name="Acetic Acid",
            formula="C2H4O2",
            micro=MicroScaleData(
                molecular_weight=60.05,
                electronegativities={"C": 2.55, "H": 2.20, "O": 3.44},
                dipole_moment=1.74,
                polarizability=5.3,
                smiles="CC(=O)O"
            ),
            macro=MacroScaleData(
                boiling_point=391.2,
                melting_point=289.8,
                critical_temperature=592.7,
                critical_pressure=5.79e6,
                critical_volume=0.171,
                acentric_factor=0.467,
                cp_constants=[123.0, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[4.682, 1642.5, -39.8]
            )
        )

    @staticmethod
    def get_glycerol_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Glycerol (C3H8O3)."""
        return ChemicalSpecies(
            id="glycerol",
            name="Glycerol",
            formula="C3H8O3",
            micro=MicroScaleData(
                molecular_weight=92.09,
                electronegativities={"C": 2.55, "H": 2.20, "O": 3.44},
                dipole_moment=2.68,
                polarizability=8.1,
                smiles="OCC(O)CO"
            ),
            macro=MacroScaleData(
                boiling_point=563.0,
                melting_point=291.0,
                critical_temperature=726.0,
                critical_pressure=6.68e6,
                critical_volume=0.255,
                acentric_factor=0.813,
                cp_constants=[222.0, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[5.2, 2800.0, -90.0]
            )
        )

    @staticmethod
    def get_nacl_metadata() -> ChemicalSpecies:
        """Returns physical and chemical property metadata for Sodium Chloride (NaCl)."""
        return ChemicalSpecies(
            id="nacl",
            name="Sodium Chloride",
            formula="NaCl",
            micro=MicroScaleData(
                molecular_weight=58.44,
                electronegativities={"Na": 0.93, "Cl": 3.16},
                dipole_moment=9.0,
                polarizability=3.5,
                smiles="[Na+].[Cl-]"
            ),
            macro=MacroScaleData(
                boiling_point=1738.0,
                melting_point=1074.0,
                critical_temperature=3400.0,
                critical_pressure=3.5e7,
                critical_volume=0.15,
                acentric_factor=0.10,
                cp_constants=[50.5, 0.0, 0.0, 0.0]
            ),
            system=SystemScaleData(
                antoine_coefficients=[4.0, 5000.0, -100.0]
            )
        )

    @classmethod
    def load_binary_system(cls, system_type: str = "ethanol_water") -> dict:
        """Loads a standard validation binary system."""
        if system_type == "methane_ethane":
            return {
                "methane": cls.get_methane_metadata(),
                "ethane": cls.get_ethane_metadata()
            }
        else:
            return {
                "ethanol": cls.get_ethanol_metadata(),
                "water": cls.get_water_metadata()
            }
