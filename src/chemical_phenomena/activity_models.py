"""
Activity coefficient models for non-ideal liquid mixtures (NRTL and Wilson).
Includes pre-loaded binary interaction parameters for industrial systems,
multi-component gamma calculations, and VLE phase diagram (T-x-y) generation.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from config.settings import GAS_CONSTANT_R

# Standard binary interaction parameters: (species_1, species_2) -> dict
# tau_ij = a_ij + b_ij / T (Kelvin)
# G_ij = exp(-alpha_ij * tau_ij)
NRTL_PARAMETERS = {
    ("ethanol", "water"): {"a_12": 0.0, "b_12": 697.98, "a_21": 0.0, "b_21": 175.76, "alpha": 0.3},
    ("water", "ethanol"): {"a_12": 0.0, "b_12": 175.76, "a_21": 0.0, "b_21": 697.98, "alpha": 0.3},
    
    ("methanol", "water"): {"a_12": 0.0, "b_12": 273.2, "a_21": 0.0, "b_21": -84.3, "alpha": 0.3},
    ("water", "methanol"): {"a_12": 0.0, "b_12": -84.3, "a_21": 0.0, "b_21": 273.2, "alpha": 0.3},
    
    ("acetone", "water"): {"a_12": 0.0, "b_12": 631.0, "a_21": 0.0, "b_21": 1195.0, "alpha": 0.3},
    ("water", "acetone"): {"a_12": 0.0, "b_12": 1195.0, "a_21": 0.0, "b_21": 631.0, "alpha": 0.3},
    
    ("acetic_acid", "water"): {"a_12": 0.0, "b_12": -210.0, "a_21": 0.0, "b_21": 480.0, "alpha": 0.3},
    ("water", "acetic_acid"): {"a_12": 0.0, "b_12": 480.0, "a_21": 0.0, "b_21": -210.0, "alpha": 0.3},
    
    ("benzene", "toluene"): {"a_12": 0.0, "b_12": 12.0, "a_21": 0.0, "b_21": -10.0, "alpha": 0.3},
    ("toluene", "benzene"): {"a_12": 0.0, "b_12": -10.0, "a_21": 0.0, "b_21": 12.0, "alpha": 0.3},
    
    ("pentane", "octane"): {"a_12": 0.0, "b_12": 45.0, "a_21": 0.0, "b_21": 38.0, "alpha": 0.3},
    ("octane", "pentane"): {"a_12": 0.0, "b_12": 38.0, "a_21": 0.0, "b_21": 45.0, "alpha": 0.3}
}

# Wilson energy parameters (J/mol) and molar liquid volumes (m3/mol)
WILSON_PARAMETERS = {
    ("ethanol", "water"): {"lambda_12": 1820.0, "lambda_21": 3980.0, "v1": 58.68e-6, "v2": 18.07e-6},
    ("water", "ethanol"): {"lambda_12": 3980.0, "lambda_21": 1820.0, "v1": 18.07e-6, "v2": 58.68e-6},
    ("methanol", "water"): {"lambda_12": 850.0, "lambda_21": 2150.0, "v1": 40.73e-6, "v2": 18.07e-6},
    ("water", "methanol"): {"lambda_12": 2150.0, "lambda_21": 850.0, "v1": 18.07e-6, "v2": 40.73e-6},
    ("acetone", "water"): {"lambda_12": 2450.0, "lambda_21": 6120.0, "v1": 74.05e-6, "v2": 18.07e-6},
    ("water", "acetone"): {"lambda_12": 6120.0, "lambda_21": 2450.0, "v1": 18.07e-6, "v2": 74.05e-6}
}

class NRTLModel:
    """Multi-component Non-Random Two-Liquid (NRTL) activity coefficient model."""

    @staticmethod
    def get_binary_params(sp1: str, sp2: str) -> dict:
        key = (sp1.lower(), sp2.lower())
        if key in NRTL_PARAMETERS:
            return NRTL_PARAMETERS[key]
        return {"a_12": 0.0, "b_12": 0.0, "a_21": 0.0, "b_21": 0.0, "alpha": 0.3}

    @classmethod
    def calculate_gammas(cls, composition: Dict[str, float], temperature: float) -> Dict[str, float]:
        """
        Calculates activity coefficients gamma_i for each species in the mixture using NRTL.
        ln(gamma_i) = sum_j(x_j*tau_ji*G_ji) / sum_k(x_k*G_ki) +
                      sum_j [ (x_j*G_ij / sum_k(x_k*G_kj)) * (tau_ij - sum_m(x_m*tau_mj*G_mj)/sum_k(x_k*G_kj)) ]
        """
        species = list(composition.keys())
        n = len(species)
        if n <= 1:
            return {s: 1.0 for s in species}

        x_raw = np.array([max(1e-12, composition[s]) for s in species])
        x = x_raw / np.sum(x_raw)
        T = max(100.0, temperature)

        tau = np.zeros((n, n))
        G = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if i == j:
                    tau[i, j] = 0.0
                    G[i, j] = 1.0
                else:
                    params = cls.get_binary_params(species[i], species[j])
                    tau[i, j] = params["a_12"] + params["b_12"] / T
                    alpha = params["alpha"]
                    G[i, j] = np.exp(-alpha * tau[i, j])

        ln_gamma = np.zeros(n)
        for i in range(n):
            # Term 1: sum_j(x_j * tau_ji * G_ji) / sum_k(x_k * G_ki)
            num1 = sum(x[j] * tau[j, i] * G[j, i] for j in range(n))
            den1 = sum(x[k] * G[k, i] for k in range(n))
            term1 = num1 / max(1e-15, den1)

            # Term 2
            term2 = 0.0
            for j in range(n):
                den_j = sum(x[k] * G[k, j] for k in range(n))
                if den_j > 1e-15:
                    sub_num = sum(x[m] * tau[m, j] * G[m, j] for m in range(n))
                    term2 += (x[j] * G[i, j] / den_j) * (tau[i, j] - sub_num / den_j)

            ln_gamma[i] = term1 + term2

        # Clamp activity coefficients to prevent numerical overflow
        gammas = np.exp(np.clip(ln_gamma, -10.0, 15.0))
        return {species[i]: float(gammas[i]) for i in range(n)}


class WilsonModel:
    """Multi-component Wilson activity coefficient model."""

    @staticmethod
    def get_binary_params(sp1: str, sp2: str) -> dict:
        key = (sp1.lower(), sp2.lower())
        if key in WILSON_PARAMETERS:
            return WILSON_PARAMETERS[key]
        return {"lambda_12": 0.0, "lambda_21": 0.0, "v1": 50e-6, "v2": 50e-6}

    @classmethod
    def calculate_gammas(cls, composition: Dict[str, float], temperature: float) -> Dict[str, float]:
        """
        Calculates activity coefficients gamma_i using Wilson model.
        ln(gamma_i) = 1 - ln(sum_j(x_j*Lambda_ij)) - sum_k(x_k*Lambda_ki / sum_j(x_j*Lambda_kj))
        """
        species = list(composition.keys())
        n = len(species)
        if n <= 1:
            return {s: 1.0 for s in species}

        x_raw = np.array([max(1e-12, composition[s]) for s in species])
        x = x_raw / np.sum(x_raw)
        T = max(100.0, temperature)
        R = GAS_CONSTANT_R

        Lambda = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i == j:
                    Lambda[i, j] = 1.0
                else:
                    params = cls.get_binary_params(species[i], species[j])
                    v_ratio = params["v2"] / max(1e-15, params["v1"])
                    energy = params["lambda_12"]
                    Lambda[i, j] = v_ratio * np.exp(-energy / (R * T))

        ln_gamma = np.zeros(n)
        for i in range(n):
            sum_j_L = sum(x[j] * Lambda[i, j] for j in range(n))
            term1 = 1.0 - np.log(max(1e-15, sum_j_L))

            term2 = 0.0
            for k in range(n):
                sum_j_Lk = sum(x[j] * Lambda[k, j] for j in range(n))
                term2 += x[k] * Lambda[k, i] / max(1e-15, sum_j_Lk)

            ln_gamma[i] = term1 - term2

        gammas = np.exp(np.clip(ln_gamma, -10.0, 15.0))
        return {species[i]: float(gammas[i]) for i in range(n)}


class VLEPhaseDiagramGenerator:
    """Generates binary T-x-y and x-y VLE diagrams, detecting azeotropes."""

    @classmethod
    def generate_diagram(cls, sp1_obj, sp2_obj, total_pressure: float = 101325.0, 
                         model: str = "nrtl", num_points: int = 50) -> dict:
        from src.chemical_phenomena.thermodynamics import Thermodynamics

        x1_vals = np.linspace(0.001, 0.999, num_points)
        y1_vals = []
        t_bubble_vals = []
        gamma1_vals = []
        gamma2_vals = []

        current_t_guess = 0.5 * (sp1_obj.macro.boiling_point + sp2_obj.macro.boiling_point)

        for x1 in x1_vals:
            x2 = 1.0 - x1
            comp = {sp1_obj.id: x1, sp2_obj.id: x2}

            # Bubble point temperature iteration
            t = current_t_guess
            for _ in range(30):
                if model.lower() == "wilson":
                    gammas = WilsonModel.calculate_gammas(comp, t)
                else:
                    gammas = NRTLModel.calculate_gammas(comp, t)

                p1_sat = Thermodynamics.calculate_vapor_pressure(sp1_obj, t)
                p2_sat = Thermodynamics.calculate_vapor_pressure(sp2_obj, t)

                f_val = x1 * gammas[sp1_obj.id] * p1_sat + x2 * gammas[sp2_obj.id] * p2_sat - total_pressure

                dt = 0.05
                p1_sat_dt = Thermodynamics.calculate_vapor_pressure(sp1_obj, t + dt)
                p2_sat_dt = Thermodynamics.calculate_vapor_pressure(sp2_obj, t + dt)
                df_dt = (x1 * gammas[sp1_obj.id] * (p1_sat_dt - p1_sat) + 
                         x2 * gammas[sp2_obj.id] * (p2_sat_dt - p2_sat)) / dt

                if abs(f_val) < 1.0 or abs(df_dt) < 1e-6:
                    break
                t -= f_val / df_dt
                t = max(150.0, min(650.0, t))

            current_t_guess = t
            t_bubble_vals.append(t)
            gamma1_vals.append(gammas[sp1_obj.id])
            gamma2_vals.append(gammas[sp2_obj.id])

            p1_sat = Thermodynamics.calculate_vapor_pressure(sp1_obj, t)
            y1 = (x1 * gammas[sp1_obj.id] * p1_sat) / total_pressure
            y1 = max(0.0, min(1.0, y1))
            y1_vals.append(y1)

        diff = np.array(y1_vals) - np.array(x1_vals)
        has_azeotrope = False
        az_x = None
        az_T = None

        for idx in range(1, len(diff) - 1):
            if diff[idx] * diff[idx + 1] <= 0:
                if 0.02 < x1_vals[idx] < 0.98:
                    has_azeotrope = True
                    az_x = float(0.5 * (x1_vals[idx] + x1_vals[idx + 1]))
                    az_T = float(0.5 * (t_bubble_vals[idx] + t_bubble_vals[idx + 1]))
                    break

        return {
            "x1": x1_vals.tolist(),
            "y1": y1_vals,
            "T_bubble": t_bubble_vals,
            "gamma1": gamma1_vals,
            "gamma2": gamma2_vals,
            "has_azeotrope": has_azeotrope,
            "azeotrope_x1": az_x,
            "azeotrope_T_K": az_T,
            "pressure_kPa": total_pressure / 1000.0,
            "model": model.upper()
        }
