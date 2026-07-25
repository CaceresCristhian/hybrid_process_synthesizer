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
