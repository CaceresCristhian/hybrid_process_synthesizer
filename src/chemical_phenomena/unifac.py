"""
UNIFAC (Universal Quasi-Chemical Functional Group Activity Coefficients) Engine.
Provides predictive liquid activity coefficients for arbitrary organic and biochemical
molecules based on functional group decomposition without requiring experimental BIPs.
Based on Fredenslund et al. (1975, 1977) and Hansen et al. (1991).
"""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from config.settings import GAS_CONSTANT_R

# Standard UNIFAC Subgroup Database: R_k (volume), Q_k (surface area), main group ID
SUBGROUPS = {
    "CH3": {"R": 0.9011, "Q": 0.848, "main": 1, "name": "CH3 (Alkane)"},
    "CH2": {"R": 0.6744, "Q": 0.540, "main": 1, "name": "CH2 (Alkane)"},
    "CH": {"R": 0.4469, "Q": 0.228, "main": 1, "name": "CH (Alkane)"},
    "C": {"R": 0.2195, "Q": 0.000, "main": 1, "name": "C (Alkane)"},
    "CH2=CH": {"R": 1.3454, "Q": 1.176, "main": 2, "name": "CH2=CH (Alkene)"},
    "ACH": {"R": 0.5313, "Q": 0.400, "main": 3, "name": "ACH (Aromatic)"},
    "AC": {"R": 0.3652, "Q": 0.120, "main": 3, "name": "AC (Aromatic Substituted)"},
    "ACCH3": {"R": 1.2663, "Q": 0.968, "main": 4, "name": "ACCH3 (Aromatic Methyl)"},
    "ACCH2": {"R": 1.0396, "Q": 0.660, "main": 4, "name": "ACCH2 (Aromatic Alkyl)"},
    "OH": {"R": 1.0000, "Q": 1.200, "main": 5, "name": "OH (Alcohol)"},
    "H2O": {"R": 0.9200, "Q": 1.400, "main": 7, "name": "H2O (Water)"},
    "CH2CO": {"R": 1.4457, "Q": 1.180, "main": 9, "name": "CH2CO (Ketone)"},
    "CHO": {"R": 0.9980, "Q": 0.948, "main": 10, "name": "CHO (Aldehyde)"},
    "COO": {"R": 1.3800, "Q": 1.200, "main": 11, "name": "COO (Ester)"},
    "COOH": {"R": 1.3013, "Q": 1.224, "main": 13, "name": "COOH (Carboxylic Acid)"}
}

# Main Group Interaction Parameters a_mn (Kelvin): row m, column n
A_MN = {
    (1, 2): 86.02, (2, 1): -35.60,
    (1, 3): 61.13, (3, 1): -11.43,
    (1, 4): 76.50, (4, 1): -69.70,
    (1, 5): 986.5, (5, 1): 156.4,
    (1, 7): 1318.0, (7, 1): 300.0,
    (1, 9): 476.4, (9, 1): 26.76,
    (1, 10): 677.0, (10, 1): 505.0,
    (1, 11): 232.1, (11, 1): 114.8,
    (1, 13): 663.5, (13, 1): 315.3,
    (2, 3): 38.81, (3, 2): 3.24,
    (2, 5): 524.1, (5, 2): 457.0,
    (2, 7): 270.6, (7, 2): 493.8,
    (3, 4): 167.0, (4, 3): -146.8,
    (3, 5): 636.1, (5, 3): 89.60,
    (3, 7): 903.8, (7, 3): 362.3,
    (3, 9): 25.77, (9, 3): -52.10,
    (3, 13): 62.11, (13, 3): 268.2,
    (4, 5): 803.2, (5, 4): -22.64,
    (4, 7): 562.2, (7, 4): 377.6,
    (5, 7): -229.1, (7, 5): 289.6,
    (5, 9): 164.5, (9, 5): -139.7,
    (5, 13): 199.0, (13, 5): -243.2,
    (7, 9): -195.4, (9, 7): 472.5,
    (7, 11): 72.87, (11, 7): 200.8,
    (7, 13): -66.17, (13, 7): -14.09,
    (9, 11): -37.36, (11, 9): 178.6,
    (11, 13): -236.0, (13, 11): 664.6
}

# Pre-defined Functional Group Breakdowns for Standard Species
SPECIES_FRAGMENTS = {
    "ethanol": {"CH3": 1, "CH2": 1, "OH": 1},
    "water": {"H2O": 1},
    "methanol": {"CH3": 1, "OH": 1},
    "propanol": {"CH3": 1, "CH2": 2, "OH": 1},
    "butanol": {"CH3": 1, "CH2": 3, "OH": 1},
    "acetone": {"CH3": 2, "CH2CO": 1},
    "benzene": {"ACH": 6},
    "toluene": {"ACH": 5, "ACCH3": 1},
    "octane": {"CH3": 2, "CH2": 6},
    "hexane": {"CH3": 2, "CH2": 4},
    "pentane": {"CH3": 2, "CH2": 3},
    "butane": {"CH3": 2, "CH2": 2},
    "propane": {"CH3": 2, "CH2": 1},
    "acetic_acid": {"CH3": 1, "COOH": 1},
    "ethyl_acetate": {"CH3": 2, "CH2": 1, "COO": 1},
    "glycerol": {"CH2": 2, "CH": 1, "OH": 3},
    "pxylene": {"ACH": 4, "ACCH3": 2}
}


class UNIFACModel:
    """Predictive UNIFAC functional group activity coefficient calculation engine."""

    @classmethod
    def get_interaction_a(cls, m: int, n: int) -> float:
        """Retrieves binary group interaction energy a_mn in Kelvin."""
        if m == n:
            return 0.0
        return A_MN.get((m, n), 0.0)

    @classmethod
    def get_species_groups(cls, species_name: str) -> Dict[str, int]:
        """Returns functional group fragmentation for a species."""
        sp = species_name.lower().replace(" ", "_")
        if sp in SPECIES_FRAGMENTS:
            return SPECIES_FRAGMENTS[sp]
        # Fallback heuristic
        if "alcohol" in sp:
            return {"CH3": 1, "CH2": 1, "OH": 1}
        if "acid" in sp:
            return {"CH3": 1, "COOH": 1}
        return {"CH3": 2, "CH2": 4}

    @classmethod
    def calculate_gammas(cls, composition: Dict[str, float], temperature_k: float,
                         custom_fragmentation: Optional[Dict[str, Dict[str, int]]] = None) -> Dict[str, Any]:
        """
        Calculates UNIFAC activity coefficients for a multi-component liquid mixture.
        Returns:
            gammas: Dict[species, gamma_i]
            combinatorial: Dict[species, ln(gamma_i^C)]
            residual: Dict[species, ln(gamma_i^R)]
        """
        z_coord = 10.0  # Coordination number
        t = max(250.0, min(500.0, temperature_k))

        # Build species group map
        frag_map = {}
        for sp in composition.keys():
            if custom_fragmentation and sp in custom_fragmentation:
                frag_map[sp] = custom_fragmentation[sp]
            else:
                frag_map[sp] = cls.get_species_groups(sp)

        # Normalize mole fractions
        tot_x = sum(composition.values())
        x_norm = {sp: val / tot_x for sp, val in composition.items()}

        # 1. Molecular Parameters: r_i and q_i
        r = {}
        q = {}
        l_param = {}
        for sp, grps in frag_map.items():
            r[sp] = sum(count * SUBGROUPS[k]["R"] for k, count in grps.items() if k in SUBGROUPS)
            q[sp] = sum(count * SUBGROUPS[k]["Q"] for k, count in grps.items() if k in SUBGROUPS)
            # Staverman-Guggenheim parameter l_i = (z/2)*(r_i - q_i) - (r_i - 1)
            l_param[sp] = (z_coord / 2.0) * (r[sp] - q[sp]) - (r[sp] - 1.0)

        sum_xr = sum(x_norm[sp] * r[sp] for sp in x_norm)
        sum_xq = sum(x_norm[sp] * q[sp] for sp in x_norm)
        sum_xl = sum(x_norm[sp] * l_param[sp] for sp in x_norm)

        # 2. Combinatorial Activity Coefficients ln(gamma_i^C)
        ln_gamma_c = {}
        for sp in x_norm:
            xi = max(1e-12, x_norm[sp])
            phi_i = (xi * r[sp]) / max(1e-12, sum_xr)
            theta_i = (xi * q[sp]) / max(1e-12, sum_xq)
            ln_gc = np.log(phi_i / xi) + (z_coord / 2.0) * q[sp] * np.log(theta_i / phi_i) + l_param[sp] - (phi_i / xi) * sum_xl
            ln_gamma_c[sp] = float(ln_gc)

        # 3. Residual Activity Coefficients ln(gamma_i^R)
        all_subgroups = sorted(list(set(k for grps in frag_map.values() for k in grps if k in SUBGROUPS)))

        # Group mole fractions in mixture X_m
        tot_grps = sum(x_norm[sp] * sum(grps.values()) for sp, grps in frag_map.items())
        X_m = {}
        for k in all_subgroups:
            X_m[k] = sum(x_norm[sp] * grps.get(k, 0) for sp, grps in frag_map.items()) / max(1e-12, tot_grps)

        sum_XQ = sum(X_m[k] * SUBGROUPS[k]["Q"] for k in all_subgroups)
        Theta_m = {k: (X_m[k] * SUBGROUPS[k]["Q"]) / max(1e-12, sum_XQ) for k in all_subgroups}

        def calc_ln_Gamma(Theta_dict: Dict[str, float], active_subgroups: List[str]) -> Dict[str, float]:
            ln_Gamma = {}
            for k in active_subgroups:
                main_k = SUBGROUPS[k]["main"]
                Q_k = SUBGROUPS[k]["Q"]

                # Sum_m (Theta_m * psi_mk)
                term1 = 0.0
                for m in active_subgroups:
                    main_m = SUBGROUPS[m]["main"]
                    psi_mk = np.exp(-cls.get_interaction_a(main_m, main_k) / t)
                    term1 += Theta_dict[m] * psi_mk

                # Sum_m [ (Theta_m * psi_km) / Sum_n (Theta_n * psi_nm) ]
                term2 = 0.0
                for m in active_subgroups:
                    main_m = SUBGROUPS[m]["main"]
                    psi_km = np.exp(-cls.get_interaction_a(main_k, main_m) / t)
                    denom = sum(Theta_dict[n] * np.exp(-cls.get_interaction_a(SUBGROUPS[n]["main"], main_m) / t) for n in active_subgroups)
                    term2 += (Theta_dict[m] * psi_km) / max(1e-12, denom)

                ln_Gamma[k] = Q_k * (1.0 - np.log(max(1e-12, term1)) - term2)
            return ln_Gamma

        ln_Gamma_mix = calc_ln_Gamma(Theta_m, all_subgroups)

        # Pure component group activity coefficients ln(Gamma_k^(i))
        ln_gamma_r = {}
        for sp, grps in frag_map.items():
            sub_sp = sorted([k for k in grps.keys() if k in SUBGROUPS])
            tot_sp_grps = sum(grps[k] for k in sub_sp)
            X_pure = {k: grps[k] / max(1e-12, tot_sp_grps) for k in sub_sp}
            sum_XQ_pure = sum(X_pure[k] * SUBGROUPS[k]["Q"] for k in sub_sp)
            Theta_pure = {k: (X_pure[k] * SUBGROUPS[k]["Q"]) / max(1e-12, sum_XQ_pure) for k in sub_sp}
            ln_Gamma_pure = calc_ln_Gamma(Theta_pure, sub_sp)

            ln_gr = sum(grps[k] * (ln_Gamma_mix[k] - ln_Gamma_pure[k]) for k in sub_sp)
            ln_gamma_r[sp] = float(ln_gr)

        # Total activity coefficients gamma_i = exp(ln(gamma_i^C) + ln(gamma_i^R))
        gammas = {}
        for sp in x_norm:
            gammas[sp] = float(np.exp(ln_gamma_c[sp] + ln_gamma_r[sp]))

        return {
            "gammas": gammas,
            "ln_gamma_c": ln_gamma_c,
            "ln_gamma_r": ln_gamma_r,
            "molecular_r": r,
            "molecular_q": q,
            "subgroups_used": all_subgroups
        }

    @classmethod
    def generate_vle_diagram(cls, comp1: str, comp2: str, P_pa: float = 101325.0,
                             num_points: int = 41) -> Dict[str, Any]:
        """
        Generates isobaric T-x-y boiling point curve using UNIFAC activity coefficients.
        """
        # Boiling point approximations
        t_boil = {
            "ethanol": 351.5, "water": 373.15, "methanol": 337.8,
            "acetone": 329.4, "benzene": 353.25, "toluene": 383.75,
            "octane": 398.8, "hexane": 341.9, "acetic_acid": 391.2
        }
        tb1 = t_boil.get(comp1.lower(), 350.0)
        tb2 = t_boil.get(comp2.lower(), 370.0)

        x1_vals = np.linspace(0.001, 0.999, num_points)
        y1_vals = []
        t_vals = []
        gamma1_vals = []
        gamma2_vals = []

        # Antoine approximations for saturation pressure (Pa): log10(P_bar) = A - B/(T + C)
        antoine = {
            "ethanol": [5.24677, 1598.673, -46.424],
            "water": [5.20389, 1733.926, -39.485],
            "methanol": [5.20409, 1581.341, -33.650],
            "acetone": [4.42448, 1312.253, -32.445],
            "benzene": [4.72583, 1660.652, -1.461],
            "toluene": [4.07827, 1343.943, -53.773],
            "octane": [4.04867, 1355.126, -63.633]
        }
        ant1 = antoine.get(comp1.lower(), [5.0, 1500.0, -40.0])
        ant2 = antoine.get(comp2.lower(), [5.0, 1600.0, -40.0])

        def p_sat(ant, temp):
            p_bar = 10.0 ** (ant[0] - ant[1] / (temp + ant[2]))
            return max(1.0, p_bar * 1e5)

        azeotrope_found = False
        azeotrope_x = None
        azeotrope_t = None

        for x1 in x1_vals:
            x2 = 1.0 - x1
            # Iterative bubble point temperature
            t_guess = x1 * tb1 + x2 * tb2
            for _ in range(15):
                unifac_res = cls.calculate_gammas({comp1: x1, comp2: x2}, t_guess)
                g1 = unifac_res["gammas"][comp1]
                g2 = unifac_res["gammas"][comp2]
                ps1 = p_sat(ant1, t_guess)
                ps2 = p_sat(ant2, t_guess)
                p_calc = x1 * g1 * ps1 + x2 * g2 * ps2
                dp_dt = (p_sat(ant1, t_guess + 0.1) * x1 * g1 + p_sat(ant2, t_guess + 0.1) * x2 * g2 - p_calc) / 0.1
                diff = P_pa - p_calc
                t_guess += diff / max(100.0, dp_dt)

            g_res = cls.calculate_gammas({comp1: x1, comp2: x2}, t_guess)
            g1 = g_res["gammas"][comp1]
            g2 = g_res["gammas"][comp2]
            y1 = (x1 * g1 * p_sat(ant1, t_guess)) / P_pa
            y1 = max(0.0, min(1.0, float(y1)))

            x1_vals_list = list(x1_vals)
            y1_vals.append(y1)
            t_vals.append(round(float(t_guess), 2))
            gamma1_vals.append(round(float(g1), 3))
            gamma2_vals.append(round(float(g2), 3))

            # Check for azeotrope crossing
            if not azeotrope_found and len(y1_vals) > 1:
                idx = len(y1_vals) - 1
                prev_diff = x1_vals_list[idx - 1] - y1_vals[idx - 1]
                curr_diff = x1 - y1
                if prev_diff * curr_diff < 0:
                    azeotrope_found = True
                    azeotrope_x = round(float(x1), 3)
                    azeotrope_t = round(float(t_guess) - 273.15, 2)

        return {
            "comp1": comp1,
            "comp2": comp2,
            "x1": [round(float(x), 3) for x in x1_vals],
            "y1": [round(float(y), 3) for y in y1_vals],
            "T_K": t_vals,
            "T_C": [round(t - 273.15, 2) for t in t_vals],
            "gamma1": gamma1_vals,
            "gamma2": gamma2_vals,
            "azeotrope_found": azeotrope_found,
            "azeotrope_x": azeotrope_x,
            "azeotrope_t_c": azeotrope_t
        }
