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
            
        # 2. Mixture parameters (mixing rules)
        b_m = sum(composition.get(sp.id, 0.0) * b_pure[sp.id] for sp in species_list)
        
        a_m = 0.0
        a_ij = {}
        for sp_i in species_list:
            x_i = composition.get(sp_i.id, 0.0)
            a_ij[sp_i.id] = {}
            for sp_j in species_list:
                x_j = composition.get(sp_j.id, 0.0)
                # Binary interaction parameter k_ij assumed 0.0 for simplicity
                k_ij = 0.0
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
            # summation term in mixture: sum( x_j * a_ij )
            sum_x_a = sum(composition.get(sp_j.id, 0.0) * a_ij[sp_i.id][sp_j.id] for sp_j in species_list)
            
            term1 = (b_pure[sp_i.id] / b_m) * (Z - 1.0)
            # handle log argument clamping to avoid log(negative) during solver search
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
    def solve_rachford_rice(cls, z: dict, K: dict) -> float:
        """
        Solves the Rachford-Rice equation for vapor fraction beta:
        sum( z_i * (K_i - 1) / (1 + beta * (K_i - 1)) ) = 0
        """
        # Objective function
        def rr_func(beta):
            return sum(z[sp_id] * (K[sp_id] - 1.0) / (1.0 + beta * (K[sp_id] - 1.0)) for sp_id in z)
            
        # Derivative
        def rr_deriv(beta):
            return sum(-z[sp_id] * (K[sp_id] - 1.0)**2 / (1.0 + beta * (K[sp_id] - 1.0))**2 for sp_id in z)
            
        # Newton-Raphson solver
        # Roots must lie between 1/(1 - Kmax) and 1/(1 - Kmin)
        # We start at beta = 0.5
        beta = 0.5
        for _ in range(50):
            res = rr_func(beta)
            if np.abs(res) < 1e-7:
                return max(0.0, min(beta, 1.0))
            deriv = rr_deriv(beta)
            if np.abs(deriv) < 1e-9:
                break
            beta -= res / deriv
            
        return max(0.0, min(beta, 1.0))

    @classmethod
    def solve_tp_flash(cls, species_list: list, feed_composition: dict, 
                       temperature: float, pressure: float, method: str = "peng_robinson") -> dict:
        """
        Solves isothermal TP Flash.
        Returns: {
            "beta": Vapor fraction (0.0 to 1.0),
            "x": liquid compositions,
            "y": vapor compositions,
            "K": partition coefficients
        }
        """
        # 1. Check if external option is requested
        if cls.db_mode == "external" or method == "external":
            # Attempt to call CoolProp if available
            try:
                import CoolProp.CoolProp as CP
                # We fetch properties for a simulated or actual component (e.g. Methane/Ethane or Water)
                # Since CoolProp requires specific fluid names, let's map them:
                fluid_mapping = {"water": "Water", "methane": "Methane", "ethane": "Ethane", "ethanol": "Ethanol"}
                
                # Simple binary CoolProp flash approximation using HEOS
                # (For mixtures, CoolProp uses Refprop or specific mixing rules, which can be unstable.
                # So we show external values for water or pure components, and fallback for mixtures)
                if len(feed_composition) == 1:
                    sp_id = list(feed_composition.keys())[0]
                    fluid = fluid_mapping.get(sp_id, sp_id.capitalize())
                    # pure component flash
                    Psat = CP.PropsSI('P', 'T', temperature, 'Q', 0.5, fluid)
                    if pressure > Psat:
                        return {"beta": 0.0, "x": feed_composition, "y": feed_composition, "K": {sp_id: 1.0}}
                    elif pressure < Psat:
                        return {"beta": 1.0, "x": feed_composition, "y": feed_composition, "K": {sp_id: 1.0}}
                    else:
                        return {"beta": 0.5, "x": feed_composition, "y": feed_composition, "K": {sp_id: 1.0}}
            except Exception:
                # fall through to pure Python Peng-Robinson if CoolProp is not available or errors
                pass

        # 2. Pure Python Peng-Robinson Flash Solver
        # Initial guess of K-values using Antoine vapor pressures
        K = {}
        for sp in species_list:
            try:
                K[sp.id] = cls.calculate_vle_k_value(sp, temperature, pressure)
            except Exception:
                # Fallback guess for hydrocarbons
                Tc = sp.macro.critical_temperature
                Pc = sp.macro.critical_pressure
                # Wilson correlation: K = Pc/P * 10^(7/3 * (1 + omega) * (1 - Tc/T))
                omega = sp.macro.acentric_factor if sp.macro.acentric_factor else 0.1
                K[sp.id] = (Pc / pressure) * 10.0 ** (7.0/3.0 * (1.0 + omega) * (1.0 - Tc / temperature))
                
        # Outer loop to converge K-values via Peng-Robinson fugacities
        x = feed_composition.copy()
        y = feed_composition.copy()
        beta = 0.5
        
        for _ in range(50):
            # Solve Rachford-Rice
            beta = cls.solve_rachford_rice(feed_composition, K)
            
            # Update compositions
            for sp_id in feed_composition:
                x[sp_id] = feed_composition[sp_id] / (1.0 + beta * (K[sp_id] - 1.0))
                y[sp_id] = K[sp_id] * x[sp_id]
                
            # Normalize compositions
            sum_x = sum(x.values())
            sum_y = sum(y.values())
            x = {k: v / sum_x for k, v in x.items()}
            y = {k: v / sum_y for k, v in y.items()}
            
            # Compute fugacity coefficients for liquid and vapor
            phi_L = cls.calculate_pr_fugacities(species_list, x, temperature, pressure, 'liquid')
            phi_V = cls.calculate_pr_fugacities(species_list, y, temperature, pressure, 'vapor')
            
            # Calculate new K-values: K_i = phi_i^L / phi_i^V
            new_K = {}
            max_diff = 0.0
            for sp_id in K:
                new_val = phi_L[sp_id] / phi_V[sp_id]
                # clip K-values to prevent division by zero or infinities
                new_val = max(1e-5, min(new_val, 1e5))
                max_diff = max(max_diff, np.abs(new_val - K[sp_id]))
                new_K[sp_id] = new_val
                
            K = new_K
            if max_diff < 1e-5:
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
        Generates PT Phase Envelope (Bubble and Dew points) using Peng-Robinson EOS.
        Returns: {"pressures_kPa": [...], "bubble_T_K": [...], "dew_T_K": [...]}
        """
        pressures = np.linspace(100e3, 4000e3, 30)  # 100 kPa to 4 MPa
        bubble_temps = []
        dew_temps = []
        
        # We search temperature ranges to solve bubble and dew points
        for P in pressures:
            # Solve bubble point temperature: beta = 0.0 (onset of boiling)
            # Find temperature T where flash beta is close to 0.0
            def find_t_bubble(t_guess):
                res = cls.solve_tp_flash(species_list, composition, t_guess, P)
                return res["beta"] - 0.01  # target slightly above 0 for numerical ease
            
            # Solve dew point temperature: beta = 1.0 (onset of condensation)
            def find_t_dew(t_guess):
                res = cls.solve_tp_flash(species_list, composition, t_guess, P)
                return res["beta"] - 0.99
                
            # Quick scanning for roots (simple secant search)
            t_b = 300.0
            t_d = 350.0
            
            # Use critical temps to bracket
            Tc_mix = sum(composition.get(sp.id, 0.0) * sp.macro.critical_temperature for sp in species_list)
            
            # Secant updates
            for t_val, target_fn, results_list in [(250.0, find_t_bubble, bubble_temps), (320.0, find_t_dew, dew_temps)]:
                # simple secant solver
                t1 = t_val
                t2 = t_val + 5.0
                f1 = target_fn(t1)
                for _ in range(15):
                    f2 = target_fn(t2)
                    if np.abs(f2 - f1) < 1e-7:
                        break
                    t_next = t2 - f2 * (t2 - t1) / (f2 - f1)
                    t_next = max(100.0, min(t_next, Tc_mix + 50.0))  # limit
                    t1, t2 = t2, t_next
                    f1 = f2
                results_list.append(t2)
                
        return {
            "pressures_kPa": pressures / 1000.0,
            "bubble_T_K": np.array(bubble_temps),
            "dew_T_K": np.array(dew_temps)
        }
