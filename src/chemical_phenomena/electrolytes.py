import numpy as np
from scipy.optimize import fsolve

class ElectrolyteModel:
    """
    Electrolyte modeling engine containing both:
    1. Activity coefficient corrections (e-NRTL model approximation)
    2. Full chemical equilibrium solver (pH, dissociation, salt precipitation)
    """
    
    @staticmethod
    def calculate_debye_huckel(ionic_strength: float, temperature: float, charge: int) -> float:
        """
        Calculates the Debye-Huckel long-range activity coefficient term.
        ln(gamma_LR) = -A * z^2 * sqrt(I) / (1 + B * a * sqrt(I))
        """
        if ionic_strength <= 0:
            return 0.0
        
        # A parameter at 298.15K ~ 0.51 (mol/kg)^-0.5
        # Temperature dependence approximation
        A = 0.509 * (298.15 / temperature) ** 1.5
        B = 0.328  # dm^-1 kg^0.5 mol^-0.5
        a = 4.0    # Ion size parameter in Angstroms
        
        ln_gamma_lr = -A * (charge ** 2) * np.sqrt(ionic_strength) / (1.0 + B * a * np.sqrt(ionic_strength))
        return ln_gamma_lr

    @classmethod
    def calculate_enrtl(cls, species_charges: dict, molalities: dict, temperature: float) -> dict:
        """
        e-NRTL approximation for activity coefficients of mixed solvent-electrolyte systems.
        Combines Debye-Huckel (long-range) and local composition NRTL (short-range).
        species_charges: dict of {species_id: charge_integer} (e.g., {'Na+': 1, 'Cl-': -1, 'water': 0})
        molalities: dict of {species_id: molality_mol_kg}
        """
        # Calculate ionic strength: I = 0.5 * sum(m_i * z_i^2)
        ionic_strength = 0.5 * sum(m * (species_charges.get(sp, 0) ** 2) for sp, m in molalities.items())
        
        activity_coeffs = {}
        for sp, m in molalities.items():
            charge = species_charges.get(sp, 0)
            if charge == 0:
                # Neutral solvent: short-range NRTL effect (simplified as function of ionic strength)
                # ln(gamma_solvent) ~ -C * I^1.5
                activity_coeffs[sp] = np.exp(-0.1 * (ionic_strength ** 1.5))
            else:
                # Ions: Debye-Huckel + short-range correction
                ln_gamma_lr = cls.calculate_debye_huckel(ionic_strength, temperature, charge)
                # Short-range NRTL local attraction approximation
                ln_gamma_sr = 0.1 * ionic_strength
                activity_coeffs[sp] = np.exp(ln_gamma_lr + ln_gamma_sr)
                
        return activity_coeffs

    @staticmethod
    def solve_chemical_equilibrium(total_acid: float, total_base: float, total_salt: float, 
                                   temperature: float = 298.15) -> dict:
        """
        Solves full chemical equilibrium in water:
        - Water ionization: H+ + OH- <-> H2O  (Kw = 1e-14)
        - Weak acid dissociation: HA <-> H+ + A-  (Ka = 1.75e-5 for acetic acid)
        - Salt precipitation: MX(s) <-> M+ + X-  (Ksp = 1e-5 for generic salt)
        
        Returns concentrations of all species, pH, and amount of salt precipitated.
        """
        # Equilibrium constants at temperature
        # Kw = 10^-14 at 298.15 K
        Kw = 1.008e-14 * np.exp(-56000 / 8.314 * (1/temperature - 1/298.15))
        Ka = 1.75e-5   # Acetic acid Ka
        Ksp = 1.0e-3   # Solubility product of generic salt MX
        
        # State variables to solve for: [H+, OH-, HA, A-, M+, X-, precipitated_MX]
        # We can reduce variables using conservation equations:
        # Total Acid = [HA] + [A-]
        # Total Base = [B+] (assumed strong base like NaOH, fully dissociated)
        # Total Salt = [M+] + precipitated_MX = [X-] + precipitated_MX
        # Electroneutrallity: [H+] + [B+] + [M+] = [OH-] + [A-] + [X-]
        
        # Let's solve the system:
        # 1. Acid equilibrium: [H+][A-] / [HA] = Ka  => [A-] = Ka * Total_Acid / ([H+] + Ka)
        # 2. Water equilibrium: [OH-] = Kw / [H+]
        # 3. Salt precipitation logic:
        #    If no precipitation: [M+] = Total_Salt, [X-] = Total_Salt
        #    If precipitation occurs: [M+] * [X-] = Ksp => since equimolar, [M+] = [X-] = sqrt(Ksp)
        #    precipitated_MX = max(0, Total_Salt - sqrt(Ksp))
        
        # Check if precipitation occurs
        if total_salt ** 2 > Ksp:
            m_plus = np.sqrt(Ksp)
            x_minus = np.sqrt(Ksp)
            precipitated = total_salt - m_plus
        else:
            m_plus = total_salt
            x_minus = total_salt
            precipitated = 0.0
            
        # B+ is strong base concentration (total_base)
        b_plus = total_base
        
        # Now solve electroneutrallity for [H+]
        # f(H+) = [H+] + [B+] + [M+] - Kw/[H+] - [A-](H+) - [X-] = 0
        def charge_balance(h_val):
            h = h_val[0]
            if h <= 0:
                return 1e5 * (1.0 - h)  # penalize negative values
            a_minus = Ka * total_acid / (h + Ka)
            oh_minus = Kw / h
            return [h + b_plus + m_plus - oh_minus - a_minus - x_minus]
            
        # Initial guess: neutral pH (1e-7)
        h_sol, info, ier, msg = fsolve(charge_balance, [1.0e-7], full_output=True)
        h = max(1e-14, h_sol[0])
        
        # Calculate final concentrations
        oh = Kw / h
        ha = h * total_acid / (h + Ka)
        a_minus = total_acid - ha
        pH = -np.log10(h)
        
        return {
            "pH": pH,
            "H+": h,
            "OH-": oh,
            "HA": ha,
            "A-": a_minus,
            "M+": m_plus,
            "X-": x_minus,
            "precipitated_MX_mol_L": precipitated
        }
