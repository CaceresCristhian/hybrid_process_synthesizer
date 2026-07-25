from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class MicroScaleData:
    """Atomic and molecular level features (typically sourced from PubChem/QM9)."""
    molecular_weight: float  # g/mol
    electronegativities: Dict[str, float] = field(default_factory=dict)  # Element symbol -> Pauling value
    dipole_moment: Optional[float] = None  # Debye
    polarizability: Optional[float] = None  # Angstrom^3
    smiles: Optional[str] = None  # Structural notation

@dataclass
class MacroScaleData:
    """Pure component bulk properties (typically sourced from NIST Chemistry WebBook/DIPPR)."""
    boiling_point: float  # Kelvin
    melting_point: float  # Kelvin
    critical_temperature: float  # Kelvin
    critical_pressure: float  # Pascals
    critical_volume: Optional[float] = None  # m^3/kmol
    acentric_factor: Optional[float] = None  # Dimensionless (omega)
    # Temperature-dependent heat capacity polynomial constants: Cp = A + B*T + C*T^2 + D*T^3
    cp_constants: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])

@dataclass
class SystemScaleData:
    """Mixture level properties, thermodynamic parameters, and phase equilibria."""
    # Antoine equation coefficients: log10(Ps) = A - (B / (T + C)) where Ps is in bar, T is in Kelvin
    antoine_coefficients: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    # Activity model parameters (e.g., UNIQUAC r/q, or NRTL binary interaction parameters)
    nrtl_alpha: Optional[float] = 0.3
    nrtl_tau: Dict[str, float] = field(default_factory=dict)  # Partner species key -> interaction parameter
    # Vapor-Liquid Equilibrium data points: x-y-T-P lists
    vle_data_points: List[Dict[str, float]] = field(default_factory=list)

@dataclass
class ChemicalSpecies:
    """Unified chemical species data structure spanning micro, macro, and system scales."""
    id: str
    name: str
    formula: str
    micro: MicroScaleData
    macro: MacroScaleData
    system: SystemScaleData
