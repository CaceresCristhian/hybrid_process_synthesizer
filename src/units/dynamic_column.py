"""
Rigorous Dynamic Distillation Column Unit Operation.
Simulates transient stage-by-stage material and component balances,
Francis weir tray hydraulics, bubble point temperature profiles,
and multi-loop PID controllers (accumulator level, sump level, tray temperature).
"""

import numpy as np
from typing import Dict, List, Any, Optional
from src.units.base_unit import BaseUnit
from src.control.pid import PIDController

class DynamicDistillationColumn(BaseUnit):
    """
    Transient stage-by-stage dynamic distillation column model.
    Stage 1: Reflux drum / accumulator.
    Stages 2..N-1: Distillation trays with hydraulic liquid holdups.
    Stage N: Column base sump / reboiler.
    """

    def __init__(self, unit_id: str, name: str, num_stages: int = 10, feed_stage: int = 5,
                 relative_volatility: float = 2.4, nominal_feed_flow: float = 10.0,
                 nominal_reflux_ratio: float = 2.5):
        super().__init__(unit_id, name)
        self.num_stages = max(4, num_stages)
        self.feed_stage = max(2, min(self.num_stages - 1, feed_stage))
        self.alpha = relative_volatility
        self.nominal_feed_flow = nominal_feed_flow
        self.reflux_ratio = nominal_reflux_ratio

        # Hydraulic and thermodynamic constants
        self.tau_liquid = 4.0      # Liquid hydraulic time constant (seconds)
        self.nominal_holdup_tray = 15.0  # Nominal tray liquid holdup (moles)
        self.nominal_holdup_vessels = 80.0 # Nominal drum and sump holdup (moles)
        self.delta_H_vap = 38000.0 # Heat of vaporization (J/mol)
        self.Tb_light = 351.44     # Boiling point of light key (Ethanol, K)
        self.Tb_heavy = 373.15     # Boiling point of heavy key (Water, K)

        # State vectors
        # Stages 0..N-1 (0-indexed internally: 0 = Condenser, N-1 = Reboiler)
        self.M = np.ones(self.num_stages) * self.nominal_holdup_tray
        self.M[0] = self.nominal_holdup_vessels       # Reflux drum
        self.M[-1] = self.nominal_holdup_vessels      # Reboiler sump

        # Initial composition profile (linear gradient light to heavy)
        self.x = np.linspace(0.85, 0.05, self.num_stages)
        self.y = np.zeros(self.num_stages)
        self.T = np.zeros(self.num_stages)
        self._update_vle_and_temperatures()

        # Operational flow rates (mol/s)
        self.F_feed = self.nominal_feed_flow
        self.z_feed = 0.50
        self.T_feed = 340.0

        self.V_boilup = self.nominal_feed_flow * 0.75
        self.L_reflux = self.reflux_ratio * (self.nominal_feed_flow * 0.4)
        self.D_distillate = self.nominal_feed_flow * 0.4
        self.B_bottoms = self.nominal_feed_flow * 0.6
        self.heat_duty = self.V_boilup * self.delta_H_vap # Reboiler duty (W)

        # Multi-loop PID Controllers
        # 1. Accumulator Level Controller (LC_D): controls Distillate flow D
        self.lc_d = PIDController(kp=0.08, ki=0.015, kd=0.005, dt=1.0, u_min=0.1, u_max=self.nominal_feed_flow * 2.0)
        self.lc_d.reset(initial_u=self.D_distillate)

        # 2. Sump Level Controller (LC_B): controls Bottoms flow B
        self.lc_b = PIDController(kp=0.08, ki=0.015, kd=0.005, dt=1.0, u_min=0.1, u_max=self.nominal_feed_flow * 2.0)
        self.lc_b.reset(initial_u=self.B_bottoms)

        # 3. Sensitive Tray Temperature Controller (TC): measures Tray 3 temperature, controls Reflux flow L
        self.tc = PIDController(kp=0.25, ki=0.03, kd=0.01, dt=1.0, u_min=0.2, u_max=self.nominal_feed_flow * 3.0)
        self.tc.reset(initial_u=self.L_reflux)
        self.sensitive_tray = max(1, min(self.num_stages - 2, 3))
        self.temp_setpoint = self.T[self.sensitive_tray]

        # History logger for strip charts
        self.time_history = [0.0]
        self.history = {
            "time": [0.0],
            "xD": [float(self.x[0])],
            "xB": [float(self.x[-1])],
            "x_feed_tray": [float(self.x[self.feed_stage - 1])],
            "T_condenser": [float(self.T[0])],
            "T_sensitive": [float(self.T[self.sensitive_tray])],
            "T_reboiler": [float(self.T[-1])],
            "level_accumulator_pct": [100.0 * float(self.M[0] / self.nominal_holdup_vessels)],
            "level_sump_pct": [100.0 * float(self.M[-1] / self.nominal_holdup_vessels)],
            "reflux_flow": [float(self.L_reflux)],
            "distillate_flow": [float(self.D_distillate)],
            "bottoms_flow": [float(self.B_bottoms)],
            "reboiler_duty_kW": [float(self.heat_duty / 1000.0)]
        }

    def _update_vle_and_temperatures(self):
        """Computes vapor compositions y_i and bubble point temperatures T_i."""
        for i in range(self.num_stages):
            xi = max(0.0001, min(0.9999, self.x[i]))
            yi = (self.alpha * xi) / (1.0 + (self.alpha - 1.0) * xi)
            self.y[i] = max(0.0, min(1.0, yi))
            self.T[i] = xi * self.Tb_light + (1.0 - xi) * self.Tb_heavy

    def get_tray_liquid_flows(self) -> np.ndarray:
        """Calculates liquid flow leaving each stage via hydraulic holdup relationship."""
        L = np.zeros(self.num_stages)
        # Stage 0 (Accumulator): L[0] is reflux back to Stage 1
        L[0] = max(0.0, self.L_reflux)
        
        # Intermediate trays 1..N-2: Francis weir linearized response
        for i in range(1, self.num_stages - 1):
            delta_m = self.M[i] - self.nominal_holdup_tray
            l_flow = (self.L_reflux + self.F_feed * 0.5) + (delta_m / self.tau_liquid)
            L[i] = max(0.01, l_flow)

        # Stage N-1 (Reboiler Sump): liquid leaves as bottoms discharge B
        L[-1] = max(0.0, self.B_bottoms)
        return L

    def get_stage_vapor_flows(self) -> np.ndarray:
        """Calculates vapor flow leaving each stage."""
        V = np.ones(self.num_stages) * self.V_boilup
        V[0] = 0.0 # Total condenser: no vapor leaves stage 0
        return V

    def step(self, dt: float = 1.0):
        """Advances dynamic column state by dt seconds using adaptive sub-stepping for stiff ODE stability."""
        # Sub-step to ensure explicit integration stability (dt_sub <= 0.02s)
        n_sub = max(1, int(np.ceil(dt / 0.02)))
        dt_sub = dt / n_sub

        for _ in range(n_sub):
            # 1. Evaluate current hydraulics and flows
            L = self.get_tray_liquid_flows()
            V = self.get_stage_vapor_flows()

            # 2. Compute time derivatives dM/dt and dx/dt
            dM_dt = np.zeros(self.num_stages)
            dx_dt = np.zeros(self.num_stages)

            feed_idx = self.feed_stage - 1

            # Stage 0: Total Condenser / Reflux Drum
            dM_dt[0] = V[1] - L[0] - self.D_distillate
            dx_dt[0] = (V[1] / max(1.0, self.M[0])) * (self.y[1] - self.x[0])

            # Intermediate trays 1..N-2
            for i in range(1, self.num_stages - 1):
                l_in = L[i - 1]
                l_out = L[i]
                v_in = V[i + 1] if i + 1 < self.num_stages else 0.0
                v_out = V[i]

                f_tray = self.F_feed if i == feed_idx else 0.0
                zf_tray = self.z_feed if i == feed_idx else 0.0

                dM_dt[i] = l_in - l_out + v_in - v_out + f_tray

                component_inflow = l_in * (self.x[i - 1] - self.x[i]) + v_in * (self.y[i + 1] - self.x[i]) - v_out * (self.y[i] - self.x[i]) + f_tray * (zf_tray - self.x[i])
                dx_dt[i] = component_inflow / max(0.5, self.M[i])

            # Stage N-1: Reboiler Sump
            l_in_sump = L[-2]
            dM_dt[-1] = l_in_sump - V[-1] - self.B_bottoms
            dx_dt[-1] = (l_in_sump / max(1.0, self.M[-1])) * (self.x[-2] - self.x[-1]) - (V[-1] / max(1.0, self.M[-1])) * (self.y[-1] - self.x[-1])

            # Integration sub-step
            self.M = np.maximum(0.5, self.M + dM_dt * dt_sub)
            self.x = np.clip(self.x + dx_dt * dt_sub, 0.001, 0.999)
            self._update_vle_and_temperatures()

        # 4. Multi-Loop PID Controller Evaluations (evaluated at primary time step)
        # Accumulator level loop (SP = nominal_holdup_vessels)
        acc_pv = self.M[0]
        self.D_distillate = self.lc_d.compute(setpoint=self.nominal_holdup_vessels, process_variable=acc_pv)

        # Sump level loop (SP = nominal_holdup_vessels)
        sump_pv = self.M[-1]
        self.B_bottoms = self.lc_b.compute(setpoint=self.nominal_holdup_vessels, process_variable=sump_pv)

        # Tray temperature loop (SP = temp_setpoint)
        t_pv = self.T[self.sensitive_tray]
        if not getattr(self, "manual_reflux", False):
            # Direct action: higher temperature requires more reflux cooling
            l_action = self.tc.compute(setpoint=self.temp_setpoint, process_variable=t_pv)
            self.L_reflux = max(0.1, l_action)
        self.reflux_ratio = self.L_reflux / max(0.01, self.D_distillate)

        # Update reboiler duty
        self.heat_duty = self.V_boilup * self.delta_H_vap

        # 5. Propagate stream outlets if connected
        if len(self.outlets) >= 2:
            self.outlets[0].F = self.D_distillate
            self.outlets[0].T = self.T[0]
            self.outlets[0].z = {"light": float(self.x[0]), "heavy": float(1.0 - self.x[0])}
            self.outlets[1].F = self.B_bottoms
            self.outlets[1].T = self.T[-1]
            self.outlets[1].z = {"light": float(self.x[-1]), "heavy": float(1.0 - self.x[-1])}

        # 6. Record history
        curr_time = self.time_history[-1] + dt
        self.time_history.append(curr_time)
        self.history["time"].append(curr_time)
        self.history["xD"].append(float(self.x[0]))
        self.history["xB"].append(float(self.x[-1]))
        self.history["x_feed_tray"].append(float(self.x[feed_idx]))
        self.history["T_condenser"].append(float(self.T[0]))
        self.history["T_sensitive"].append(float(self.T[self.sensitive_tray]))
        self.history["T_reboiler"].append(float(self.T[-1]))
        self.history["level_accumulator_pct"].append(100.0 * float(self.M[0] / self.nominal_holdup_vessels))
        self.history["level_sump_pct"].append(100.0 * float(self.M[-1] / self.nominal_holdup_vessels))
        self.history["reflux_flow"].append(float(self.L_reflux))
        self.history["distillate_flow"].append(float(self.D_distillate))
        self.history["bottoms_flow"].append(float(self.B_bottoms))
        self.history["reboiler_duty_kW"].append(float(self.heat_duty / 1000.0))

        return {
            "time": curr_time,
            "xD": float(self.x[0]),
            "xB": float(self.x[-1]),
            "T_sensitive": float(self.T[self.sensitive_tray]),
            "T_condenser": float(self.T[0]),
            "T_reboiler": float(self.T[-1]),
            "M_acc": float(self.M[0]),
            "M_sump": float(self.M[-1]),
            "L_reflux": float(self.L_reflux),
            "D_distillate": float(self.D_distillate),
            "B_bottoms": float(self.B_bottoms),
            "V_boilup": float(self.V_boilup)
        }

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        """Runs dynamic simulation over specified time span (t_start, t_end)."""
        t_start, t_end = time_span
        duration = max(1.0, t_end - t_start)
        dt = kwargs.get("dt", 0.5)
        steps = int(np.ceil(duration / dt))

        for _ in range(steps):
            self.step(dt=dt)

        self.size_equipment()
        return {
            "time": self.history["time"],
            "xD": self.history["xD"],
            "xB": self.history["xB"],
            "reflux_flow": self.history["reflux_flow"],
            "T_profile": self.T.tolist(),
            "x_profile": self.x.tolist()
        }

    def size_equipment(self) -> dict:
        """Sizes column diameter, height, and tray count."""
        rho_v = 1.8
        rho_l = 800.0
        c_sb = 0.08
        v_flood = c_sb * np.sqrt((rho_l - rho_v) / rho_v)
        v_design = 0.8 * v_flood

        max_v_mol = max(1.0, self.V_boilup)
        vol_vapor = (max_v_mol * 0.035) / rho_v
        area = max(0.2, vol_vapor / v_design)
        diam = max(0.5, 2.0 * np.sqrt(area / np.pi))
        height = self.num_stages * 0.6 + 3.0

        self.sizing_results = {
            "column_diameter_m": round(diam, 2),
            "column_height_m": round(height, 2),
            "num_stages": self.num_stages,
            "feed_stage": self.feed_stage,
            "tray_spacing_m": 0.6,
            "reboiler_duty_kW": round(self.heat_duty / 1000.0, 2)
        }
        return self.sizing_results
