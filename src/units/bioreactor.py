import numpy as np
from scipy.integrate import solve_ivp
from src.units.base_unit import BaseUnit
from src.control.pid import PIDController
from src.mechanical_design.vessel_sizing import VesselSizing

class JacketedBioreactor(BaseUnit):
    """Dynamic model of a jacketed fed-batch bioreactor with integrated PID temperature control."""
    
    def __init__(self, unit_id: str, name: str, volume_init: float, s_in: float, 
                 u_coeff: float, area: float, temp_sp: float, pid_controller: PIDController):
        super().__init__(unit_id, name)
        self.volume_init = volume_init
        self.s_in = s_in
        self.u_coeff = u_coeff
        self.area = area
        self.temp_sp = temp_sp
        self.controller = pid_controller
        self.heat_duty = 0.0
        self.work_input = 0.0

    def odes(self, t: float, state: list, f_feed: float, f_jacket: float, t_jacket_in: float,
             kinetics_fn) -> list:
        """
        State variables:
        state = [X (biomass), S (substrate), P (product), V (volume), T (reactor temperature), Tj (jacket temperature)]
        """
        X, S, P, V, T, Tj = state
        
        # 1. Fetch kinetics from ML/Physics function
        # kinetics_fn returns (mu, qp, yield_xs, maintenance)
        mu, qp, yield_xs, maintenance = kinetics_fn(S, T)
        
        # 2. Conservation balances
        # Feed flow rate is clamped if volume reaches maximum (e.g. 5.0 m3)
        actual_feed = f_feed if V < 5.0 else 0.0
        
        dXdt = mu * X - (actual_feed / V) * X
        dSdt = -(mu / yield_xs) * X - maintenance * X + (actual_feed / V) * (self.s_in - S)
        dPdt = qp * X - (actual_feed / V) * P
        dVdt = actual_feed
        
        # 3. Energy balances (density = 1000 kg/m3, cp = 4184 J/kg K)
        rho, cp = 1000.0, 4184.0
        q_reaction = 0.0  # Optional biological reaction heat
        
        dTdt = ((actual_feed * rho * cp * (298.15 - T)) - (self.u_coeff * self.area * (T - Tj)) + q_reaction) / (rho * V * cp)
        
        # Jacket temperature change (Jacket Volume = 0.1 m3)
        v_jacket = 0.1
        dTjdt = (f_jacket / v_jacket) * (t_jacket_in - Tj) + (self.u_coeff * self.area * (T - Tj)) / (rho * v_jacket * cp)
        
        return [dXdt, dSdt, dPdt, dVdt, dTdt, dTjdt]

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        """
        Runs the dynamic simulation using solve_ivp, or propagates steady-state flowsheet stream.
        """
        if self.inlets and self.inlets[0].F is not None and self.inlets[0].F > 0:
            in_st = self.inlets[0]
            if self.outlets:
                out_st = self.outlets[0]
                out_st.T = self.temp_sp
                out_st.P = in_st.P
                out_st.F = in_st.F
                out_st.z = in_st.z.copy() if in_st.z else {}
                if "glucose" in out_st.z and "ethanol" in out_st.z:
                    conv = out_st.z["glucose"] * 0.40
                    out_st.z["glucose"] -= conv
                    out_st.z["ethanol"] += conv * 0.60
                    if "co2" in out_st.z:
                        out_st.z["co2"] += conv * 0.40

        kinetics_fn = kwargs.get("kinetics_fn")
        if kinetics_fn is None or not initial_state:
            return {"status": "steady_state_propagated"}
        f_feed = kwargs.get("f_feed", 0.05)
        t_jacket_in = kwargs.get("t_jacket_in", 280.0)
        
        # The PID controller dynamically adjusts the jacket flow rate (f_jacket)
        # to control reactor temperature T (state[4]) to temp_sp
        def closed_loop_odes(t, state):
            # Compute cooling water flow rate using PID
            T = state[4]
            # controller computes output f_jacket
            f_jacket = self.controller.compute(self.temp_sp, T)
            return self.odes(t, state, f_feed, f_jacket, t_jacket_in, kinetics_fn)

        t_eval = np.linspace(time_span[0], time_span[1], 100)
        sol = solve_ivp(closed_loop_odes, time_span, initial_state, t_eval=t_eval, method="RK45")
        
        return {
            "t": sol.t,
            "X": sol.y[0],
            "S": sol.y[1],
            "P": sol.y[2],
            "V": sol.y[3],
            "T": sol.y[4],
            "Tj": sol.y[5]
        }

    def size_equipment(self) -> dict:
        """Sizes mechanical vessel requirements (diameter, height, wall thickness)."""
        # Assume design pressure of 3.0 bar (300,000 Pa) and radius of 0.8 meters
        design_pressure = 300000.0
        radius = 0.8
        
        thickness = VesselSizing.calculate_shell_thickness(
            internal_pressure=design_pressure,
            internal_radius=radius,
            material="stainless_steel_316"
        )
        
        self.sizing_results = {
            "vessel_diameter_m": radius * 2.0,
            "asme_wall_thickness_mm": thickness * 1000.0,
            "max_volume_m3": 5.0
        }
        return self.sizing_results
