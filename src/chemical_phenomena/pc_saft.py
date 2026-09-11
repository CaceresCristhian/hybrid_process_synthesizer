"""
PC-SAFT (Perturbed-Chain Statistical Associating Fluid Theory) Equation of State.
Rigorous molecular equation of state modeling hard chain reference fluids (a_hc),
dispersion attraction (a_disp), and directional hydrogen-bonding association (a_assoc).
Based on Gross & Sadowski (2001, 2002).
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional

# Boltzmann constant and universal constants
K_B = 1.380649e-23     # J / K
N_A = 6.02214076e23    # molecules / mol
R_GAS = 8.314462618    # J / (mol K)

# Universal PC-SAFT Model Constants (Table 1, Gross & Sadowski 2001)
A_CONSTS = [
    [0.9105631445, -0.3084016918, -0.0906148351],
    [0.6361281449, 0.1860531159, 0.4527842806],
    [2.6861347891, -2.5030047259, 0.5962700728],
    [-26.547362491, 21.419793629, -1.7241829131],
    [97.759208784, -65.255885330, -4.1302112531],
    [-159.59154087, 83.318680481, 13.776631870],
    [91.297774084, -33.746922902, -8.6728470368]
]

B_CONSTS = [
    [0.7240946941, -0.5755498075, 0.0976883116],
    [2.2382791861, -0.2177020511, -0.6590957149],
    [-4.0025849485, -0.6405007730, 0.9400882198],
    [-21.003576815, 16.555071349, -2.8276218551],
    [98.541093490, -60.751369541, 4.3764929437],
    [-182.16621247, 82.357622240, -16.560198880],
    [108.88781608, -32.748782038, 12.016324363]
]


@dataclass
class PCSAFTParameters:
    """PC-SAFT pure component molecular parameters."""
    name: str
    m: float             # Segment number (dimensionless)
    sigma: float         # Segment diameter (Angstroms)
    eps_k: float         # Dispersion energy (Kelvin)
    eps_assoc_k: float = 0.0  # Association energy (Kelvin)
    kappa_assoc: float = 0.0  # Association volume (dimensionless)
    mw: float = 0.0      # Molecular weight (g/mol)


# Pure Component PC-SAFT Parameters Database
PCSAFT_DATABASE: Dict[str, PCSAFTParameters] = {
    "methane": PCSAFTParameters("Methane", 1.0000, 3.7039, 150.03, mw=16.04),
    "ethane": PCSAFTParameters("Ethane", 1.6069, 3.5206, 191.42, mw=30.07),
    "propane": PCSAFTParameters("Propane", 2.0020, 3.6184, 208.11, mw=44.10),
    "butane": PCSAFTParameters("Butane", 2.3316, 3.7086, 222.88, mw=58.12),
    "pentane": PCSAFTParameters("Pentane", 2.6896, 3.7729, 231.20, mw=72.15),
    "hexane": PCSAFTParameters("Hexane", 3.0576, 3.7983, 236.77, mw=86.18),
    "octane": PCSAFTParameters("Octane", 3.8176, 3.8373, 242.78, mw=114.23),
    "benzene": PCSAFTParameters("Benzene", 2.4653, 3.6478, 287.35, mw=78.11),
    "toluene": PCSAFTParameters("Toluene", 2.8149, 3.7169, 285.69, mw=92.14),
    "water": PCSAFTParameters("Water", 1.0656, 3.0007, 366.51, eps_assoc_k=2500.7, kappa_assoc=0.03487, mw=18.015),
    "ethanol": PCSAFTParameters("Ethanol", 2.3827, 3.1771, 198.24, eps_assoc_k=2654.3, kappa_assoc=0.03238, mw=46.07),
    "methanol": PCSAFTParameters("Methanol", 1.5255, 3.2300, 188.90, eps_assoc_k=2899.5, kappa_assoc=0.03518, mw=32.04),
    "co2": PCSAFTParameters("Carbon Dioxide", 2.0729, 2.7852, 169.21, mw=44.01),
    "nitrogen": PCSAFTParameters("Nitrogen", 1.2053, 3.3130, 90.96, mw=28.01)
}


class PCSAFTModel:
    """PC-SAFT Thermodynamic Equation of State calculation engine."""

    @classmethod
    def get_parameters(cls, species_name: str) -> PCSAFTParameters:
        """Retrieves PC-SAFT molecular parameters."""
        sp = species_name.lower().replace(" ", "_")
        if sp in PCSAFT_DATABASE:
            return PCSAFT_DATABASE[sp]
        # Default fallback to octane-like fluid
        return PCSAFTParameters(species_name, 3.5, 3.8, 240.0, mw=100.0)

    @classmethod
    def calculate_compressibility(cls, species_name: str, rho_mol_m3: float, T_k: float) -> Dict[str, float]:
        """
        Computes compressibility factor Z = 1 + Z_hc + Z_disp + Z_assoc
        at given molar density rho (mol/m3) and temperature T (K).
        """
        params = cls.get_parameters(species_name)
        m = params.m
        sigma_m = params.sigma * 1e-10  # Angstroms to meters
        eps_k = params.eps_k

        # Temperature-dependent segment diameter d(T) in meters
        d = sigma_m * (1.0 - 0.12 * np.exp(-3.0 * eps_k / T_k))

        # Molecular number density (molecules / m3)
        rho_n = max(1e15, rho_mol_m3 * N_A)

        # Packing fraction eta
        eta = (np.pi / 6.0) * rho_n * m * (d ** 3)
        eta = max(1e-6, min(0.68, eta))

        # 1. Hard Chain Reference Contribution Z_hc
        # Hard sphere compressibility Z_hs
        z_hs = (1.0 + eta + (eta ** 2) - (eta ** 3)) / ((1.0 - eta) ** 3)
        # Radial distribution at contact g_hs
        g_hs = (1.0 - 0.5 * eta) / ((1.0 - eta) ** 3)
        d_lng_deta = (5.0 - 2.0 * eta) / (2.0 * (1.0 - eta) * (1.0 - 0.5 * eta))

        z_hc = m * z_hs - (m - 1.0) * (1.0 + eta * d_lng_deta)

        # 2. Dispersion Attraction Contribution Z_disp
        # Compute I1 and I2 polynomial integrals
        a_coeffs = [A_CONSTS[j][0] + (m - 1.0)/m * A_CONSTS[j][1] + ((m - 1.0)/m)*((m - 2.0)/m) * A_CONSTS[j][2] for j in range(7)]
        b_coeffs = [B_CONSTS[j][0] + (m - 1.0)/m * B_CONSTS[j][1] + ((m - 1.0)/m)*((m - 2.0)/m) * B_CONSTS[j][2] for j in range(7)]

        # d(eta*I1)/d_eta
        d_eta_I1 = sum((j + 1.0) * a_coeffs[j] * (eta ** j) for j in range(7))
        # d(eta*I2)/d_eta
        d_eta_I2 = sum((j + 1.0) * b_coeffs[j] * (eta ** j) for j in range(7))
        I2 = sum(b_coeffs[j] * (eta ** j) for j in range(7))

        c1 = 1.0 / (1.0 + m * (8.0 * eta - 2.0 * (eta ** 2)) / ((1.0 - eta) ** 4) + (1.0 - m) * (20.0 * eta - 27.0 * (eta ** 2) + 12.0 * (eta ** 3) - 2.0 * (eta ** 4)) / (((1.0 - eta) * (2.0 - eta)) ** 2))
        c2 = -c1 * c1 * (m * (-4.0 * (eta ** 2) + 20.0 * eta + 8.0) / ((1.0 - eta) ** 5) + (1.0 - m) * (2.0 * (eta ** 3) + 12.0 * (eta ** 2) - 48.0 * eta + 40.0) / (((1.0 - eta) * (2.0 - eta)) ** 3))

        u_kt = eps_k / T_k
        term_disp1 = -2.0 * np.pi * rho_n * d_eta_I1 * (m ** 2) * u_kt * (sigma_m ** 3)
        term_disp2 = -np.pi * rho_n * m * (c1 * d_eta_I2 + c2 * eta * I2) * (m ** 2) * (u_kt ** 2) * (sigma_m ** 3)
        z_disp = term_disp1 + term_disp2

        # 3. Association Contribution Z_assoc (Wertheim 2B Site)
        z_assoc = 0.0
        if params.eps_assoc_k > 0:
            delta_ab = (d ** 3) * g_hs * params.kappa_assoc * (np.exp(params.eps_assoc_k / T_k) - 1.0)
            # Fraction of non-bonded sites X_A: X_A = (-1 + sqrt(1 + 4*rho_n*delta_ab)) / (2*rho_n*delta_ab)
            val = max(0.0, 1.0 + 4.0 * rho_n * delta_ab)
            x_a = (-1.0 + np.sqrt(val)) / max(1e-12, 2.0 * rho_n * delta_ab)
            z_assoc = -(1.0 - x_a) * (1.0 + eta * d_lng_deta)

        # Total Compressibility Factor Z
        total_z = 1.0 + (z_hc - 1.0) + z_disp + z_assoc
        # Pressure (Pa) = Z * rho_mol * R * T
        p_pa = total_z * rho_mol_m3 * R_GAS * T_k

        return {
            "Z": float(total_z),
            "Z_hc": float(z_hc),
            "Z_disp": float(z_disp),
            "Z_assoc": float(z_assoc),
            "P_Pa": float(p_pa),
            "P_bar": float(p_pa / 1e5),
            "packing_fraction_eta": float(eta),
            "segment_diameter_A": float(d * 1e10)
        }

    @classmethod
    def generate_isotherms(cls, species_name: str, temperatures_k: List[float] = None,
                           num_points: int = 50) -> Dict[str, Any]:
        """
        Generates P-rho fluid isotherms across vapor and liquid densities.
        """
        temps = temperatures_k or [298.15, 350.0, 420.0, 500.0]
        params = cls.get_parameters(species_name)

        # Molar densities from gas (10 mol/m3) to dense liquid (10,000 mol/m3)
        rho_vals = np.geomspace(5.0, 12000.0, num_points)

        isotherms = {}
        for T in temps:
            p_bars = []
            z_vals = []
            for rho in rho_vals:
                res = cls.calculate_compressibility(species_name, rho, T)
                p_bars.append(res["P_bar"])
                z_vals.append(res["Z"])

            isotherms[f"{T:.0f}K"] = {
                "temperature_K": T,
                "P_bar": [round(float(p), 2) for p in p_bars],
                "Z": [round(float(z), 3) for z in z_vals]
            }

        return {
            "species": species_name,
            "molar_densities_mol_m3": [round(float(r), 1) for r in rho_vals],
            "isotherms": isotherms,
            "parameters": {
                "m": params.m,
                "sigma_A": params.sigma,
                "eps_k_K": params.eps_k,
                "eps_assoc_K": params.eps_assoc_k,
                "kappa_assoc": params.kappa_assoc
            }
        }
