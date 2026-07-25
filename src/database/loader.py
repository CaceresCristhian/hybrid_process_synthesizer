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
