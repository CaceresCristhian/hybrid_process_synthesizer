import numpy as np

class HeatTransfer:
    """Solves heat transfer coefficients, jackets, and heat exchangers."""
    
    @staticmethod
    def calculate_lmtd(t_hot_in: float, t_hot_out: float, t_cold_in: float, t_cold_out: float) -> float:
        """Calculate Log-Mean Temperature Difference (LMTD)."""
        dt1 = t_hot_in - t_cold_out
        dt2 = t_hot_out - t_cold_in
        
        if dt1 <= 0 or dt2 <= 0:
            raise ValueError("Temperature crossovers detected or driving force is zero.")
            
        if np.abs(dt1 - dt2) < 1e-5:
            return dt1
            
        return (dt1 - dt2) / np.log(dt1 / dt2)

    @staticmethod
    def jacket_energy_derivative(t_jacket: float, t_process: float, f_jacket: float, 
                                 t_jacket_in: float, volume: float, density: float, 
                                 cp: float, u_coeff: float, area: float) -> float:
        """
        Calculates dT_jacket/dt for cooling/heating jacket.
        Governed by: dT_j/dt = (F_j/V_j)*(T_in - T_j) - (U*A/(rho*V_j*Cp))*(T_j - T_p)
        """
        residence_term = (f_jacket / volume) * (t_jacket_in - t_jacket)
        heat_transfer_term = (u_coeff * area * (t_jacket - t_process)) / (density * volume * cp)
        return residence_term - heat_transfer_term
