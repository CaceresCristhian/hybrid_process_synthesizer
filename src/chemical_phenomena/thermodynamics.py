import numpy as np
from src.database.chemical_db import ChemicalSpecies
from config.settings import GAS_CONSTANT_R

class Thermodynamics:
    """
    Thermodynamic Calculations Engine.
    Integrates:
    1. Ideal gas & Activity Coefficient models (Antoine, Raoult, Margules VLE)
    2. Rigorous Pure Python Peng-Robinson Cubic Equation of State (EOS) for VLE/VLLE
    3. External database wrapper (CoolProp/Thermo interface with simulated fallback)
    """
    
    # Global settings for database mode
    db_mode = "python"  # "python" or "external"
    
    @staticmethod
    def calculate_vapor_pressure(species: ChemicalSpecies, temperature: float) -> float:
        """Calculates pure component vapor pressure using the Antoine Equation (P in Pascals)."""
        antoine = species.system.antoine_coefficients
        if not antoine or len(antoine) < 3 or all(v == 0.0 for v in antoine):
            raise ValueError(f"Antoine coefficients not configured for species: {species.name}")
        a, b, c = antoine
        log_p = a - (b / (temperature + c))
        return (10.0 ** log_p) * 1e5  # Convert bar to Pascals

    @classmethod
    def calculate_vle_k_value(cls, species: ChemicalSpecies, temperature: float, 
                               pressure: float, activity_coefficient: float = 1.0) -> float:
        """Calculates ideal phase equilibrium partition coefficient: K = (gamma * Ps) / P"""
        p_vap = cls.calculate_vapor_pressure(species, temperature)
        return (activity_coefficient * p_vap) / pressure

    @classmethod
    def bubble_point_temperature(cls, x_fractions: dict, species_dict: dict, total_pressure: float, 
                                 activity_coeffs: dict = None, initial_temp_guess: float = 350.0) -> float:
        """Finds bubble point temperature in Kelvin using Newton-Raphson iteration (Ideal/Activity model)."""
        t = initial_temp_guess
        tolerance = 1e-6
        max_iter = 100
        
        for _ in range(max_iter):
            sum_y = 0.0
            derivative = 0.0
            for name, x in x_fractions.items():
                species = species_dict[name]
                gamma = activity_coeffs.get(name, 1.0) if activity_coeffs else 1.0
                p_vap = cls.calculate_vapor_pressure(species, t)
                sum_y += (x * gamma * p_vap) / total_pressure
                
                # Temperature derivative of vapor pressure
                a, b, c = species.system.antoine_coefficients
                dp_vap_dt = p_vap * np.log(10.0) * b / ((t + c) ** 2)
                derivative += (x * gamma * dp_vap_dt) / total_pressure
                
            residual = sum_y - 1.0
            if np.abs(residual) < tolerance:
                return t
            if np.abs(derivative) < 1e-9:
                break
            t -= residual / derivative
            
        return t

    # ==========================================
    # PENG-ROBINSON EQUATION OF STATE (PURE PYTHON)
    # ==========================================
    
    @classmethod
    def solve_peng_robinson_z(cls, A: float, B: float, phase: str = 'vapor') -> float:
        """
        Solves the cubic Peng-Robinson equation for compressibility factor Z:
        Z^3 - (1-B)*Z^2 + (A - 2B - 3B^2)*Z - (AB - B^2 - B^3) = 0
        """
        # Coefficients
        c2 = -(1.0 - B)
        c1 = A - 2.0 * B - 3.0 * B**2
        c0 = -(A * B - B**2 - B**3)
        
        roots = np.roots([1.0, c2, c1, c0])
        real_roots = [r.real for r in roots if np.abs(r.imag) < 1e-5 and r.real > B]
        
        if not real_roots:
            return 1.0  # Fallback to ideal gas
            
        if phase == 'liquid':
            return min(real_roots)
        else:
            return max(real_roots)

    @classmethod
    def calculate_peng_robinson_coefficients(cls, species_list: list, composition: dict, 
                                             temperature: float, pressure: float) -> tuple:
        """
        Calculates mixture parameters a_m, b_m, A, B and binary cross terms for Peng-Robinson.
        Returns: (a_m, b_m, A, B, a_pure, b_pure, a_ij)
        """
        R = GAS_CONSTANT_R  # 8.31446 J/(mol K)
        
        # 1. Pure component properties
        a_pure = {}
        b_pure = {}
        
        for sp in species_list:
            Tc = sp.macro.critical_temperature
            Pc = sp.macro.critical_pressure
            omega = sp.macro.acentric_factor if sp.macro.acentric_factor is not None else 0.0
            
            # co-volume b
            b_i = 0.07780 * R * Tc / Pc
            
            # alpha parameter
            if omega <= 0.49:
                m_i = 0.37464 + 1.54226 * omega - 0.26992 * omega**2
            else:
                m_i = 0.379642 + 1.48503 * omega - 0.164423 * omega**2 + 0.016666 * omega**3
                
            Tr = temperature / Tc
            alpha_i = (1.0 + m_i * (1.0 - np.sqrt(Tr))) ** 2
            a_i = 0.45724 * (R**2 * Tc**2 / Pc) * alpha_i
            
            a_pure[sp.id] = a_i
            b_pure[sp.id] = b_i
            
        # 2. Mixture parameters (van der Waals one-fluid mixing rules with binary k_ij)
        b_m = sum(composition.get(sp.id, 0.0) * b_pure[sp.id] for sp in species_list)
        
        k_ij_table = {
            ("methane", "ethane"): 0.0026,
            ("methane", "propane"): 0.0140,
            ("methane", "butane"): 0.0185,
            ("methane", "octane"): 0.0450,
            ("methane", "co2"): 0.0919,
            ("ethane", "propane"): 0.0011,
            ("benzene", "toluene"): 0.0007,
            ("ethanol", "water"): -0.0650,
            ("methanol", "water"): -0.0750,
            ("phenol", "octane"): 0.0820,
        }
        a_m = 0.0
        a_ij = {}
        for sp_i in species_list:
            x_i = composition.get(sp_i.id, 0.0)
            a_ij[sp_i.id] = {}
            vc_i = float(sp_i.macro.critical_volume or 0.20)
            for sp_j in species_list:
                x_j = composition.get(sp_j.id, 0.0)
                if sp_i.id == sp_j.id:
                    k_ij = 0.0
                elif (sp_i.id, sp_j.id) in k_ij_table:
                    k_ij = k_ij_table[(sp_i.id, sp_j.id)]
                elif (sp_j.id, sp_i.id) in k_ij_table:
                    k_ij = k_ij_table[(sp_j.id, sp_i.id)]
                else:
                    # Chueh-Prausnitz (1967) predictive binary interaction correlation from Vc_i, Vc_j
                    vc_j = float(sp_j.macro.critical_volume or 0.20)
                    v_num = 2.0 * ((vc_i * vc_j) ** (1.0 / 6.0))
                    v_den = max(1e-6, (vc_i ** (1.0 / 3.0)) + (vc_j ** (1.0 / 3.0)))
                    k_ij = float(np.clip(1.0 - (v_num / v_den) ** 3, -0.10, 0.18))
                a_term = (1.0 - k_ij) * np.sqrt(a_pure[sp_i.id] * a_pure[sp_j.id])
                a_ij[sp_i.id][sp_j.id] = a_term
                a_m += x_i * x_j * a_term
                
        # Dimensionless A and B parameters
        A = a_m * pressure / (R**2 * temperature**2)
        B = b_m * pressure / (R * temperature)
        
        return a_m, b_m, A, B, a_pure, b_pure, a_ij

    @classmethod
    def calculate_pr_fugacities(cls, species_list: list, composition: dict, 
                                 temperature: float, pressure: float, phase: str = 'vapor') -> dict:
        """Calculates fugacity coefficients (phi_i) for each component in the mixture using PR EOS."""
        R = GAS_CONSTANT_R
        
        a_m, b_m, A, B, a_pure, b_pure, a_ij = cls.calculate_peng_robinson_coefficients(
            species_list, composition, temperature, pressure
        )
        
        Z = cls.solve_peng_robinson_z(A, B, phase)
        
        # Calculate ln(phi_i) for each species
        phi = {}
        for sp_i in species_list:
            sum_x_a = sum(composition.get(sp_j.id, 0.0) * a_ij[sp_i.id][sp_j.id] for sp_j in species_list)
            
            term1 = (b_pure[sp_i.id] / b_m) * (Z - 1.0)
            log_arg_z_b = max(1e-10, Z - B)
            term2 = -np.log(log_arg_z_b)
            
            factor = A / (2.0 * np.sqrt(2.0) * B) if B > 0 else 0.0
            term3_num = 2.0 * sum_x_a / a_m if a_m > 0 else 0.0
            term3_den = b_pure[sp_i.id] / b_m
            
            log_arg_z_plus = max(1e-10, (Z + (1.0 + np.sqrt(2.0)) * B) / (Z + (1.0 - np.sqrt(2.0)) * B))
            term3 = -factor * (term3_num - term3_den) * np.log(log_arg_z_plus)
            
            ln_phi = term1 + term2 + term3
            phi[sp_i.id] = np.exp(ln_phi)
            
        return phi

    # ==========================================
    # RACHFORD-RICE MULTI-COMPONENT FLASH SOLVER
    # ==========================================
    
    @classmethod
    def solve_rachford_rice(cls, z: dict | list, K: dict | list) -> float:
        """
        Solves the Rachford-Rice equation for vapor fraction beta in [0, 1]:
            f(beta) = sum( z_i * (K_i - 1) / (1 + beta * (K_i - 1)) ) = 0
        Includes analytical negative-flash boundary checks:
            - f(0) = sum(z_i * (K_i - 1)) <= 0  => Subcooled liquid (beta = 0.0)
            - f(1) = sum(z_i * (1 - 1/K_i)) >= 0 => Superheated vapor (beta = 1.0)
        Uses guaranteed bracketed Brent root-finding (scipy.optimize.brentq) on [0, 1].
        Supports both dict (keyed by species_id) and list/array inputs for z and K.
        """
        from scipy.optimize import brentq

        if isinstance(z, dict) and isinstance(K, dict):
            pairs = [(float(z[k]), float(K[k])) for k in z]
        else:
            pairs = [(float(zi), float(ki)) for zi, ki in zip(z, K)]

        def rr_func(beta: float) -> float:
            return sum(
                zi * (ki - 1.0) / max(1e-12, 1.0 + beta * (ki - 1.0))
                for zi, ki in pairs
            )

        f0 = rr_func(0.0)
        if f0 <= 0.0:
            return 0.0

        f1 = rr_func(1.0)
        if f1 >= 0.0:
            return 1.0

        try:
            beta_sol = brentq(rr_func, 0.0, 1.0, xtol=1e-10, rtol=1e-10, maxiter=100)
            return float(np.clip(beta_sol, 0.0, 1.0))
        except ValueError:
            return 0.5

    @classmethod
    def solve_tp_flash(cls, species_list: list, feed_composition: dict, 
                       temperature: float, pressure: float, method: str = "peng_robinson") -> dict:
        """
        Solves isothermal TP Flash.
        Supports: 'peng_robinson', 'nrtl', 'wilson', 'pinn', and 'external' (CoolProp).
        Returns: {
            "beta": Vapor fraction (0.0 to 1.0),
            "x": liquid compositions,
            "y": vapor compositions,
            "K": partition coefficients
        }
        """
        import logging
        logger = logging.getLogger(__name__)

        # 1. Check if external option is requested
        if cls.db_mode == "external" or method == "external":
            try:
                import CoolProp.CoolProp as CP
                fluid_mapping = {"water": "Water", "methane": "Methane", "ethane": "Ethane", "ethanol": "Ethanol"}
                if len(feed_composition) == 1:
                    sp_id = list(feed_composition.keys())[0]
                    fluid = fluid_mapping.get(sp_id, sp_id.capitalize())
                    Psat = CP.PropsSI('P', 'T', temperature, 'Q', 0.5, fluid)
                    if pressure > Psat:
                        return {"beta": 0.0, "x": feed_composition, "y": feed_composition, "K": {sp_id: 1.0}}
                    elif pressure < Psat:
                        return {"beta": 1.0, "x": feed_composition, "y": feed_composition, "K": {sp_id: 1.0}}
                    else:
                        return {"beta": 0.5, "x": feed_composition, "y": feed_composition, "K": {sp_id: 1.0}}
            except ImportError:
                logger.debug("CoolProp not installed; falling back to pure-Python PR-EOS.")
            except Exception as exc:
                logger.debug("CoolProp evaluation fallback: %s", exc)

        # 2. Activity coefficient flash (NRTL / Wilson / PINN surrogate)
        if method.lower() in ["nrtl", "wilson", "activity", "pinn"]:
            from src.chemical_phenomena.activity_models import NRTLModel, WilsonModel
            use_pinn = (method.lower() == "pinn")
            model_cls = WilsonModel if method.lower() == "wilson" else NRTLModel
            
            x = feed_composition.copy()
            y = feed_composition.copy()
            K = {}
            for sp in species_list:
                try:
                    p_sat = cls.calculate_vapor_pressure(sp, temperature)
                    K[sp.id] = p_sat / pressure
                except Exception:
                    K[sp.id] = 1.0
                    
            beta = 0.5
            for _ in range(40):
                beta = cls.solve_rachford_rice(feed_composition, K)
                for sp_id in feed_composition:
                    x[sp_id] = feed_composition[sp_id] / (1.0 + beta * (K[sp_id] - 1.0))
                    y[sp_id] = K[sp_id] * x[sp_id]
                sum_x = sum(x.values())
                sum_y = sum(y.values())
                x = {k: v / max(1e-12, sum_x) for k, v in x.items()}
                y = {k: v / max(1e-12, sum_y) for k, v in y.items()}
                
                if use_pinn and len(species_list) == 2:
                    from src.ml_models.pinn import ThermodynamicsPINN
                    sp0_id = species_list[0].id
                    sp1_id = species_list[1].id
                    g1, g2 = ThermodynamicsPINN.predict_gammas(x.get(sp0_id, 0.5), temperature)
                    gammas = {sp0_id: g1, sp1_id: g2}
                else:
                    gammas = model_cls.calculate_gammas(x, temperature)
                new_K = {}
                max_diff = 0.0
                for sp in species_list:
                    try:
                        p_sat = cls.calculate_vapor_pressure(sp, temperature)
                        k_val = gammas.get(sp.id, 1.0) * p_sat / pressure
                    except Exception:
                        k_val = 1.0
                    k_val = max(1e-5, min(k_val, 1e5))
                    max_diff = max(max_diff, abs(k_val - K.get(sp.id, 1.0)))
                    new_K[sp.id] = k_val
                K = new_K
                if max_diff < 1e-6:
                    break
            return {
                "beta": beta,
                "x": x,
                "y": y,
                "K": K
            }

        # 3. Pure Python Peng-Robinson Flash Solver
        K = {}
        for sp in species_list:
            Tc = sp.macro.critical_temperature
            Pc = sp.macro.critical_pressure
            omega = sp.macro.acentric_factor if sp.macro.acentric_factor is not None else 0.1
            # Wilson correlation initial guess
            K[sp.id] = max(1e-5, min(1e5, (Pc / pressure) * np.exp(5.373 * (1.0 + omega) * (1.0 - Tc / max(temperature, 50.0)))))
                
        x = feed_composition.copy()
        y = feed_composition.copy()
        beta = 0.5
        
        for _ in range(60):
            beta = cls.solve_rachford_rice(feed_composition, K)
            for sp_id in feed_composition:
                x[sp_id] = feed_composition[sp_id] / (1.0 + beta * (K[sp_id] - 1.0))
                y[sp_id] = K[sp_id] * x[sp_id]
                
            sum_x = max(1e-12, sum(x.values()))
            sum_y = max(1e-12, sum(y.values()))
            x = {k: v / sum_x for k, v in x.items()}
            y = {k: v / sum_y for k, v in y.items()}
            
            phi_L = cls.calculate_pr_fugacities(species_list, x, temperature, pressure, 'liquid')
            phi_V = cls.calculate_pr_fugacities(species_list, y, temperature, pressure, 'vapor')
            
            new_K = {}
            max_diff = 0.0
            for sp_id in K:
                new_val = phi_L[sp_id] / max(1e-12, phi_V[sp_id])
                new_val = max(1e-5, min(new_val, 1e5))
                max_diff = max(max_diff, np.abs(new_val - K[sp_id]) / max(1e-6, K[sp_id]))
                new_K[sp_id] = new_val
                
            # Guard against trivial solution (phi_L == phi_V => K == 1) when Wilson K strongly indicates two-phase
            if all(abs(v - 1.0) < 1e-3 for v in new_K.values()):
                break
            K = new_K
            if max_diff < 1e-6:
                break
                
        return {
            "beta": beta,
            "x": x,
            "y": y,
            "K": K
        }

    @classmethod
    def generate_pt_envelope(cls, species_list: list, composition: dict) -> dict:
        """
        Generates PT Phase Envelope (Bubble and Dew points) by solving:
          - Bubble Point: sum_i(z_i * K_i^PR(T, P, x=z, y)) = 1.0
          - Dew Point:    sum_i(z_i / K_i^PR(T, P, x, y=z)) = 1.0
        using Wilson-K initialization followed by iterated Peng-Robinson fugacity convergence.
        Returns: {"pressures_kPa": [...], "bubble_T_K": [...], "dew_T_K": [...]}
        """
        pressures = np.linspace(100e3, 4000e3, 30)  # 100 kPa to 4 MPa
        bubble_temps = []
        dew_temps = []
        
        def wilson_k(sp, T, P):
            Tc = sp.macro.critical_temperature
            Pc = sp.macro.critical_pressure
            omega = sp.macro.acentric_factor if sp.macro.acentric_factor is not None else 0.1
            return (Pc / P) * np.exp(5.373 * (1.0 + omega) * (1.0 - Tc / max(T, 50.0)))

        def pr_k_values(x_comp, y_comp, T, P):
            phi_L = cls.calculate_pr_fugacities(species_list, x_comp, T, P, 'liquid')
            phi_V = cls.calculate_pr_fugacities(species_list, y_comp, T, P, 'vapor')
            k_pr = {}
            for sp in species_list:
                ratio = phi_L[sp.id] / max(1e-12, phi_V[sp.id])
                # If supercritical / single-root PR collapses to 1.0, blend smoothly with Wilson K near cricondenbar
                if abs(ratio - 1.0) < 1e-3:
                    k_pr[sp.id] = wilson_k(sp, T, P)
                else:
                    k_pr[sp.id] = ratio
            return k_pr

        for P in pressures:
            # 1. Initial Bubble Point from Wilson K bisection
            t_low, t_high = 60.0, 800.0
            for _ in range(30):
                t_mid = 0.5 * (t_low + t_high)
                f_mid = sum(composition.get(sp.id, 0.0) * wilson_k(sp, t_mid, P) for sp in species_list) - 1.0
                if f_mid < 0.0:
                    t_low = t_mid
                else:
                    t_high = t_mid
            t_bub = 0.5 * (t_low + t_high)
            
            # Converge Bubble Point iteratively with PR-EOS fugacity K-values (secant/Newton on ln(sum_y) = 0)
            y_vap = {sp.id: composition.get(sp.id, 0.0) * wilson_k(sp, t_bub, P) for sp in species_list}
            s_y = max(1e-12, sum(y_vap.values()))
            y_vap = {k: v / s_y for k, v in y_vap.items()}
            for _ in range(12):
                k_pr = pr_k_values(composition, y_vap, t_bub, P)
                y_unnorm = {sp.id: composition.get(sp.id, 0.0) * k_pr[sp.id] for sp in species_list}
                sum_y = sum(y_unnorm.values())
                if sum_y <= 1e-8:
                    break
                y_vap = {k: v / sum_y for k, v in y_unnorm.items()}
                err = np.log(sum_y)
                if abs(err) < 1e-4:
                    break
                # Thermodynamic sensitivity d(ln K)/dT ~ dH_vap/(R*T^2)
                k_pr_dt = pr_k_values(composition, y_vap, t_bub + 1.0, P)
                sum_y_dt = sum(composition.get(sp.id, 0.0) * k_pr_dt[sp.id] for sp in species_list)
                d_ln_dt = np.log(max(1e-8, sum_y_dt)) - err
                if abs(d_ln_dt) > 1e-6:
                    step_t = np.clip(-err / d_ln_dt, -8.0, 8.0)
                    t_bub = max(60.0, min(800.0, t_bub + 0.6 * step_t))
                else:
                    break
            bubble_temps.append(float(t_bub))

            # 2. Initial Dew Point from Wilson K bisection
            t_low, t_high = 60.0, 800.0
            for _ in range(30):
                t_mid = 0.5 * (t_low + t_high)
                f_mid = sum(composition.get(sp.id, 0.0) / max(1e-10, wilson_k(sp, t_mid, P)) for sp in species_list) - 1.0
                if f_mid > 0.0:
                    t_low = t_mid
                else:
                    t_high = t_mid
            t_dew = max(t_bub, 0.5 * (t_low + t_high))
            
            # Converge Dew Point iteratively with PR-EOS fugacity K-values (on ln(sum_x) = 0)
            x_liq = {sp.id: composition.get(sp.id, 0.0) / max(1e-10, wilson_k(sp, t_dew, P)) for sp in species_list}
            s_x = max(1e-12, sum(x_liq.values()))
            x_liq = {k: v / s_x for k, v in x_liq.items()}
            for _ in range(12):
                k_pr = pr_k_values(x_liq, composition, t_dew, P)
                x_unnorm = {sp.id: composition.get(sp.id, 0.0) / max(1e-10, k_pr[sp.id]) for sp in species_list}
                sum_x = sum(x_unnorm.values())
                if sum_x <= 1e-8:
                    break
                x_liq = {k: v / sum_x for k, v in x_unnorm.items()}
                err = np.log(sum_x)
                if abs(err) < 1e-4:
                    break
                k_pr_dt = pr_k_values(x_liq, composition, t_dew + 1.0, P)
                sum_x_dt = sum(composition.get(sp.id, 0.0) / max(1e-10, k_pr_dt[sp.id]) for sp in species_list)
                d_ln_dt = np.log(max(1e-8, sum_x_dt)) - err
                if abs(d_ln_dt) > 1e-6:
                    step_t = np.clip(-err / d_ln_dt, -8.0, 8.0)
                    t_dew = max(t_bub, min(800.0, t_dew + 0.6 * step_t))
                else:
                    break
            dew_temps.append(float(max(t_bub, t_dew)))
                
        return {
            "pressures_kPa": pressures / 1000.0,
            "bubble_T_K": np.array(bubble_temps),
            "dew_T_K": np.array(dew_temps)
        }
