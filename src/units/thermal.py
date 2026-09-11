import numpy as np
from src.units.base_unit import BaseUnit
from src.units.stream import MaterialStream

class Heater(BaseUnit):
    """
    Thermal heater / furnace / boiler unit operation.
    Adds heat duty Q > 0 to an inlet process stream.
    """
    def __init__(self, unit_id: str, name: str, t_target: float = 373.15, delta_p: float = 5000.0):
        super().__init__(unit_id, name)
        self.t_target = t_target
        self.delta_p = delta_p
        self.heat_duty = 0.0  # Watts
        self.work_input = 0.0
        
    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_stream = self.inlets[0] if self.inlets else None
        out_stream = self.outlets[0] if self.outlets else None
        
        if in_stream and out_stream and in_stream.F is not None and in_stream.F > 0:
            species_map = kwargs.get("species_map", {})
            # Estimate mean heat capacity (J/mol*K)
            cp_mix = 0.0
            for sp_id, frac in (in_stream.z or {}).items():
                sp = species_map.get(sp_id)
                if sp and sp.macro.cp_constants:
                    cp_mix += frac * sp.macro.cp_constants[0]
                else:
                    cp_mix += frac * 75.0  # default generic Cp
            if cp_mix <= 0.0:
                cp_mix = 75.0
                
            out_stream.T = max(self.t_target, in_stream.T)
            out_stream.P = max(1000.0, in_stream.P - self.delta_p)
            out_stream.F = in_stream.F
            out_stream.z = in_stream.z.copy() if in_stream.z else {}
            
            # Heat duty Q = F (mol/s) * Cp (J/mol*K) * Delta_T (K) in Watts
            delta_t = out_stream.T - in_stream.T
            self.heat_duty = in_stream.F * cp_mix * delta_t
            
        return {"heat_duty_kW": self.heat_duty / 1000.0}

    def size_equipment(self) -> dict:
        u_coeff = 450.0  # W/m2*K
        lmtd = 40.0      # K
        area = max(0.5, abs(self.heat_duty) / (u_coeff * lmtd)) if self.heat_duty > 0 else 2.0
        self.sizing_results = {
            "thermal_duty_kW": self.heat_duty / 1000.0,
            "heat_transfer_area_m2": round(area, 2),
            "tube_passes": 2,
            "shell_diameter_m": round(0.2 * np.sqrt(area), 2)
        }
        return self.sizing_results


class Cooler(BaseUnit):
    """
    Thermal cooler / chiller / condenser unit operation.
    Removes heat duty Q < 0 from an inlet process stream.
    """
    def __init__(self, unit_id: str, name: str, t_target: float = 298.15, delta_p: float = 5000.0):
        super().__init__(unit_id, name)
        self.t_target = t_target
        self.delta_p = delta_p
        self.heat_duty = 0.0  # Watts (negative)
        self.work_input = 0.0
        
    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_stream = self.inlets[0] if self.inlets else None
        out_stream = self.outlets[0] if self.outlets else None
        
        if in_stream and out_stream and in_stream.F is not None and in_stream.F > 0:
            species_map = kwargs.get("species_map", {})
            cp_mix = 0.0
            for sp_id, frac in (in_stream.z or {}).items():
                sp = species_map.get(sp_id)
                if sp and sp.macro.cp_constants:
                    cp_mix += frac * sp.macro.cp_constants[0]
                else:
                    cp_mix += frac * 75.0
            if cp_mix <= 0.0:
                cp_mix = 75.0
                
            out_stream.T = min(self.t_target, in_stream.T)
            out_stream.P = max(1000.0, in_stream.P - self.delta_p)
            out_stream.F = in_stream.F
            out_stream.z = in_stream.z.copy() if in_stream.z else {}
            
            delta_t = out_stream.T - in_stream.T
            self.heat_duty = in_stream.F * cp_mix * delta_t  # negative
            
        return {"heat_duty_kW": self.heat_duty / 1000.0}

    def size_equipment(self) -> dict:
        u_coeff = 500.0
        lmtd = 25.0
        area = max(0.5, abs(self.heat_duty) / (u_coeff * lmtd)) if self.heat_duty != 0 else 1.5
        self.sizing_results = {
            "cooling_duty_kW": self.heat_duty / 1000.0,
            "heat_transfer_area_m2": round(area, 2),
            "cooling_water_flow_kg_h": round(abs(self.heat_duty) * 3600.0 / (4184.0 * 10.0), 1)
        }
        return self.sizing_results


class HeatExchanger(BaseUnit):
    """
    Two-stream countercurrent heat exchanger.
    Inlets: [0] Hot Stream In, [1] Cold Stream In.
    Outlets: [0] Hot Stream Out, [1] Cold Stream Out.
    Conserves enthalpy internally (Q_hot = -Q_cold, net external Q = 0).
    """
    def __init__(self, unit_id: str, name: str, u_area: float = 2000.0, delta_p: float = 10000.0):
        super().__init__(unit_id, name)
        self.u_area = u_area  # U * A in W/K
        self.delta_p = delta_p
        self.heat_duty = 0.0  # net heat added to flowsheet is 0
        self.internal_duty = 0.0  # exchanged duty in Watts
        self.work_input = 0.0

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        if len(self.inlets) >= 2 and len(self.outlets) >= 2:
            h_in = self.inlets[0]
            c_in = self.inlets[1]
            h_out = self.outlets[0]
            c_out = self.outlets[1]
            
            if h_in.F is not None and c_in.F is not None and h_in.F > 0 and c_in.F > 0:
                species_map = kwargs.get("species_map", {})
                
                # Capacities (W/K)
                cp_h = 75.0
                cp_c = 75.0
                c_dot_h = h_in.F * cp_h
                c_dot_c = c_in.F * cp_c
                
                c_min = min(c_dot_h, c_dot_c)
                c_max = max(c_dot_h, c_dot_c)
                cr = c_min / max(c_max, 1e-6)
                
                # Number of transfer units (NTU)
                ntu = self.u_area / max(c_min, 1e-6)
                # Effectiveness for countercurrent
                if abs(cr - 1.0) < 1e-4:
                    eff = ntu / (1.0 + ntu)
                else:
                    eff = (1.0 - np.exp(-ntu * (1.0 - cr))) / (1.0 - cr * np.exp(-ntu * (1.0 - cr)))
                eff = max(0.05, min(0.95, eff))
                
                delta_t_max = max(0.0, h_in.T - c_in.T)
                q_exchanged = eff * c_min * delta_t_max
                self.internal_duty = q_exchanged
                
                # Update Hot Out
                h_out.T = h_in.T - q_exchanged / max(c_dot_h, 1e-6)
                h_out.P = max(1000.0, h_in.P - self.delta_p)
                h_out.F = h_in.F
                h_out.z = h_in.z.copy() if h_in.z else {}
                
                # Update Cold Out
                c_out.T = c_in.T + q_exchanged / max(c_dot_c, 1e-6)
                c_out.P = max(1000.0, c_in.P - self.delta_p)
                c_out.F = c_in.F
                c_out.z = c_in.z.copy() if c_in.z else {}
                
        elif len(self.inlets) >= 1 and len(self.outlets) >= 1:
            # Fallback for single stream pass
            in_s = self.inlets[0]
            out_s = self.outlets[0]
            if in_s.F is not None:
                out_s.T = in_s.T - 15.0
                out_s.P = max(1000.0, in_s.P - self.delta_p)
                out_s.F = in_s.F
                out_s.z = in_s.z.copy() if in_s.z else {}
                
        return {"exchanged_duty_kW": self.internal_duty / 1000.0}

    def size_equipment(self) -> dict:
        u_assumed = 600.0  # W/m2*K
        area = max(1.0, self.u_area / u_assumed)
        self.sizing_results = {
            "exchanged_duty_kW": round(self.internal_duty / 1000.0, 2),
            "heat_transfer_area_m2": round(area, 2),
            "overall_U_W_m2K": u_assumed,
            "ntu_metric": round(self.u_area / 500.0, 2)
        }
        return self.sizing_results
