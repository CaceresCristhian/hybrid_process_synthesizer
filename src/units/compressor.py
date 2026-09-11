import numpy as np
from src.units.base_unit import BaseUnit

class Compressor(BaseUnit):
    """
    Gas Compressor (Centrifugal / Reciprocating / Blower).
    Increases gas pressure via isentropic compression with polytropic/mechanical efficiency.
    Calculates power requirement W_comp (Watts) and temperature rise.
    """
    def __init__(self, unit_id: str, name: str, pressure_ratio: float = 3.0, isentropic_eff: float = 0.78):
        super().__init__(unit_id, name)
        self.pressure_ratio = pressure_ratio
        self.isentropic_eff = isentropic_eff
        self.work_input = 0.0  # Watts
        self.heat_duty = 0.0

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_st = self.inlets[0] if self.inlets else None
        out_st = self.outlets[0] if self.outlets else None
        
        if in_st and out_st and in_st.F is not None and in_st.F > 0:
            gamma = 1.30  # typical gas ratio of heat capacities Cp/Cv
            p_out = in_st.P * self.pressure_ratio
            
            # Isentropic temperature rise: T_out,is = T_in * (P_out/P_in)^((gamma-1)/gamma)
            t_is = in_st.T * (self.pressure_ratio ** ((gamma - 1.0) / gamma))
            t_out = in_st.T + (t_is - in_st.T) / max(0.2, self.isentropic_eff)
            
            out_st.T = t_out
            out_st.P = p_out
            out_st.F = in_st.F
            out_st.z = in_st.z.copy() if in_st.z else {}
            
            # Work input = F (mol/s) * Cp (J/mol*K) * (T_out - T_in)
            cp = 35.0  # J/mol*K
            self.work_input = in_st.F * cp * (t_out - in_st.T)
            
        return {"work_input_kW": self.work_input / 1000.0}

    def size_equipment(self) -> dict:
        self.sizing_results = {
            "driver_power_kW": round(self.work_input / 1000.0 * 1.15, 2),  # 15% motor margin
            "pressure_ratio": self.pressure_ratio,
            "impeller_stages": max(1, int(np.ceil(np.log(self.pressure_ratio) / np.log(2.5)))),
            "casing_design_p_bar": round((self.pressure_ratio * 1.5), 1)
        }
        return self.sizing_results


class Expander(BaseUnit):
    """
    Cryogenic Turbo-Expander / Pressure Letdown Turbine.
    Extracts mechanical work W_out < 0 and drops temperature.
    """
    def __init__(self, unit_id: str, name: str, pressure_ratio: float = 0.33, isentropic_eff: float = 0.82):
        super().__init__(unit_id, name)
        self.pressure_ratio = pressure_ratio  # P_out / P_in < 1
        self.isentropic_eff = isentropic_eff
        self.work_input = 0.0  # negative (work produced)
        self.heat_duty = 0.0

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_st = self.inlets[0] if self.inlets else None
        out_st = self.outlets[0] if self.outlets else None
        
        if in_st and out_st and in_st.F is not None and in_st.F > 0:
            gamma = 1.30
            p_out = in_st.P * self.pressure_ratio
            t_is = in_st.T * (self.pressure_ratio ** ((gamma - 1.0) / gamma))
            t_out = in_st.T - (in_st.T - t_is) * self.isentropic_eff
            
            out_st.T = max(50.0, t_out)
            out_st.P = max(1000.0, p_out)
            out_st.F = in_st.F
            out_st.z = in_st.z.copy() if in_st.z else {}
            
            cp = 35.0
            self.work_input = -in_st.F * cp * (in_st.T - out_st.T)  # negative
            
        return {"power_generated_kW": abs(self.work_input) / 1000.0}

    def size_equipment(self) -> dict:
        self.sizing_results = {
            "power_recovery_kW": round(abs(self.work_input) / 1000.0, 2),
            "expansion_ratio": round(1.0 / max(0.01, self.pressure_ratio), 2)
        }
        return self.sizing_results
