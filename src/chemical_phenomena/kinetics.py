import numpy as np
from config.settings import GAS_CONSTANT_R

class Kinetics:
    """Calculates chemical reaction rates and kinetic parameters."""
    
    @staticmethod
    def calculate_arrhenius_rate(pre_exponential_factor: float, activation_energy: float, 
                                 temperature: float) -> float:
        """
        Calculates reaction rate constant k(T) using the Arrhenius equation.
        k = A * exp( -Ea / (R * T) )
        where:
          - Pre-exponential factor A (same units as k)
          - Activation energy Ea in J/mol
          - Temperature T in Kelvin
        """
        if temperature <= 0:
            raise ValueError("Temperature must be greater than zero Kelvin.")
        
        exponent = -activation_energy / (GAS_CONSTANT_R * temperature)
        return pre_exponential_factor * np.exp(exponent)
