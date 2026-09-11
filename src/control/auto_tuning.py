"""
Industrial Auto-Tuning Engine for Process Controllers.
Implements First-Order Plus Dead Time (FOPDT) system identification from process step response tests,
and calculates optimal PID parameters via Ziegler-Nichols, Cohen-Coon, and Internal Model Control (IMC/SIMC).
"""

import numpy as np
from typing import Dict, List, Any, Optional

class AutoTuner:
    """Industrial Process Control Auto-Tuning Engine."""

    @classmethod
    def perform_step_test(cls, column, step_input: str = "reflux_flow", step_amplitude: float = 0.5, step_time: float = 5.0, total_time: float = 80.0, dt: float = 1.0) -> Dict[str, Any]:
        """
        Executes an in-situ open-loop step test on a distillation column to collect (t, u, y) response.
        step_input: 'reflux_flow' (L) or 'boilup' (V)
        """
        base_u = column.L_reflux if step_input == "reflux_flow" else column.V_boilup
        
        t_hist = []
        u_hist = []
        y_hist = []

        steps = int(np.ceil(total_time / dt))
        current_u = base_u

        orig_manual = getattr(column, "manual_reflux", False)
        column.manual_reflux = True
        try:
            for k in range(steps):
                t_now = k * dt
                if t_now >= step_time:
                    current_u = base_u + step_amplitude
                else:
                    current_u = base_u

                if step_input == "reflux_flow":
                    column.L_reflux = current_u
                else:
                    column.V_boilup = current_u

                column.step(dt=dt)
                y_val = float(column.T[column.sensitive_tray])

                t_hist.append(t_now)
                u_hist.append(float(current_u))
                y_hist.append(y_val)
        finally:
            column.manual_reflux = orig_manual

        return {
            "time": t_hist,
            "input": u_hist,
            "output": y_hist
        }

    @classmethod
    def fit_fopdt(cls, t: List[float], u: List[float], y: List[float], dt: float = 1.0) -> Dict[str, Any]:
        """
        Identifies First-Order Plus Dead Time (FOPDT) model from step test data:
        G(s) = (K_p * exp(-theta * s)) / (tau * s + 1)
        Uses the standard two-point method (28.3% and 63.2% response points).
        """
        t_arr = np.array(t, dtype=float)
        u_arr = np.array(u, dtype=float)
        y_arr = np.array(y, dtype=float)

        if len(t_arr) < 5:
            raise ValueError("Insufficient data points for FOPDT parameter identification.")

        # Baseline and final values
        u0 = u_arr[0]
        u_final = u_arr[-1]
        delta_u = u_final - u0

        if abs(delta_u) < 1e-6:
            raise ValueError("No step change detected in manipulated variable u(t).")

        y0 = y_arr[0]
        y_final = y_arr[-1]
        delta_y = y_final - y0

        # Process gain
        kp = delta_y / delta_u

        # Two-point method:
        # y(t1) = y0 + 0.283 * delta_y
        # y(t2) = y0 + 0.632 * delta_y
        y_283 = y0 + 0.283 * delta_y
        y_632 = y0 + 0.632 * delta_y

        # Detect time of step start
        step_idx = np.where(np.abs(u_arr - u0) > 0.05 * np.abs(delta_u))[0]
        t_step = t_arr[step_idx[0]] if len(step_idx) > 0 else t_arr[0]

        # Interpolate t_283 and t_632
        # Use normalized response for monotonic search
        norm_y = (y_arr - y0) / (delta_y + 1e-12)
        norm_y = np.clip(norm_y, 0.0, 1.0)

        idx_283 = np.searchsorted(norm_y, 0.283)
        idx_632 = np.searchsorted(norm_y, 0.632)

        idx_283 = min(len(t_arr) - 1, max(0, idx_283))
        idx_632 = min(len(t_arr) - 1, max(idx_283 + 1, idx_632))

        t1 = t_arr[idx_283] - t_step
        t2 = t_arr[idx_632] - t_step

        tau = max(0.1, 1.5 * (t2 - t1))
        theta = max(0.01, t2 - tau)

        # Theoretical FOPDT response
        y_model = []
        for ti in t_arr:
            dt = ti - t_step
            if dt <= theta:
                y_model.append(y0)
            else:
                y_model.append(y0 + delta_y * (1.0 - np.exp(-(dt - theta) / tau)))
        
        # R2 fit metric
        ss_res = np.sum((y_arr - np.array(y_model)) ** 2)
        ss_tot = np.sum((y_arr - np.mean(y_arr)) ** 2)
        r2 = max(0.0, 1.0 - (ss_res / (ss_tot + 1e-12)))

        return {
            "K_p": round(float(kp), 4),
            "Kp": round(float(kp), 4),
            "tau": round(float(tau), 2),
            "tau_p": round(float(tau), 2),
            "theta": round(float(theta), 2),
            "R2": round(float(r2), 4),
            "r_squared": round(float(r2), 4),
            "delta_u": round(float(delta_u), 3),
            "delta_y": round(float(delta_y), 3),
            "t_step": round(float(t_step), 2),
            "t_model": t_arr.tolist(),
            "y_model": [round(val, 4) for val in y_model],
            "simulated_output": [round(val, 4) for val in y_model]
        }

    @classmethod
    def calculate_ziegler_nichols(cls, fopdt: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates Ziegler-Nichols open-loop reaction curve PID/PI parameters."""
        kp = fopdt.get("K_p", fopdt.get("Kp", 1.0))
        tau = fopdt.get("tau", fopdt.get("tau_p", 10.0))
        theta = max(0.01, fopdt.get("theta", 1.0))

        # PID
        kc_pid = (1.2 * tau) / (abs(kp) * theta)
        tau_i_pid = 2.0 * theta
        tau_d_pid = 0.5 * theta

        # PI
        kc_pi = (0.9 * tau) / (abs(kp) * theta)
        tau_i_pi = 3.33 * theta

        return {
            "PID": {
                "Kc": round(float(kc_pid), 4),
                "tau_I": round(float(tau_i_pid), 2),
                "tau_D": round(float(tau_d_pid), 2),
                "Ki": round(float(kc_pid / tau_i_pid), 4),
                "Kd": round(float(kc_pid * tau_d_pid), 4)
            },
            "PI": {
                "Kc": round(float(kc_pi), 4),
                "tau_I": round(float(tau_i_pi), 2),
                "tau_D": 0.0,
                "Ki": round(float(kc_pi / tau_i_pi), 4),
                "Kd": 0.0
            }
        }

    @classmethod
    def calculate_cohen_coon(cls, fopdt: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates Cohen-Coon PID/PI parameters (better for systems with significant dead time)."""
        kp = fopdt.get("K_p", fopdt.get("Kp", 1.0))
        tau = fopdt.get("tau", fopdt.get("tau_p", 10.0))
        theta = max(0.01, fopdt.get("theta", 1.0))
        r = theta / tau

        # PID
        kc_pid = (1.0 / (abs(kp) * r)) * (4.0 / 3.0 + r / 4.0)
        tau_i_pid = theta * (32.0 + 6.0 * r) / (13.0 + 8.0 * r)
        tau_d_pid = theta * 4.0 / (11.0 + 2.0 * r)

        # PI
        kc_pi = (1.0 / (abs(kp) * r)) * (0.9 + r / 12.0)
        tau_i_pi = theta * (30.0 + 3.0 * r) / (9.0 + 20.0 * r)

        return {
            "PID": {
                "Kc": round(float(kc_pid), 4),
                "tau_I": round(float(tau_i_pid), 2),
                "tau_D": round(float(tau_d_pid), 2),
                "Ki": round(float(kc_pid / tau_i_pid), 4),
                "Kd": round(float(kc_pid * tau_d_pid), 4)
            },
            "PI": {
                "Kc": round(float(kc_pi), 4),
                "tau_I": round(float(tau_i_pi), 2),
                "tau_D": 0.0,
                "Ki": round(float(kc_pi / tau_i_pi), 4),
                "Kd": 0.0
            }
        }

    @classmethod
    def calculate_imc(cls, fopdt: Dict[str, Any], tuning_style: str = "moderate") -> Dict[str, Any]:
        """
        Calculates Internal Model Control (SIMC / Skogestad) parameters.
        tuning_style: 'aggressive' (tau_c = 0.5*theta), 'moderate' (tau_c = theta), 'robust' (tau_c = 2*theta).
        """
        kp = fopdt.get("K_p", fopdt.get("Kp", 1.0))
        tau = fopdt.get("tau", fopdt.get("tau_p", 10.0))
        theta = max(0.01, fopdt.get("theta", 1.0))

        mult = {"aggressive": 0.5, "moderate": 1.0, "robust": 2.0}.get(tuning_style.lower(), 1.0)
        tau_c = max(0.05, mult * theta)

        kc = (1.0 / abs(kp)) * (tau / (tau_c + theta))
        tau_i = min(tau, 4.0 * (tau_c + theta))
        tau_d = 0.5 * theta

        return {
            "style": tuning_style,
            "tau_c": round(float(tau_c), 2),
            "Kc": round(float(kc), 4),
            "tau_I": round(float(tau_i), 2),
            "tau_D": round(float(tau_d), 2),
            "Ki": round(float(kc / tau_i), 4),
            "Kd": round(float(kc * tau_d), 4)
        }

    @classmethod
    def get_full_tuning_comparison(cls, fopdt_or_kp: Any, theta: Optional[float] = None, tau_p: Optional[float] = None) -> Dict[str, Any]:
        """Generates unified comparison table of all tuning rules, supporting both dict and positional inputs."""
        if isinstance(fopdt_or_kp, dict):
            fopdt = fopdt_or_kp
        else:
            fopdt = {
                "K_p": float(fopdt_or_kp), "Kp": float(fopdt_or_kp),
                "theta": float(theta) if theta is not None else 1.0,
                "tau": float(tau_p) if tau_p is not None else 10.0,
                "tau_p": float(tau_p) if tau_p is not None else 10.0
            }

        zn = cls.calculate_ziegler_nichols(fopdt)
        cc = cls.calculate_cohen_coon(fopdt)
        imc_mod = cls.calculate_imc(fopdt, "moderate")
        imc_rob = cls.calculate_imc(fopdt, "robust")

        return {
            "FOPDT": fopdt,
            "methods": [
                {"Method": "Ziegler-Nichols (PID)", "Kc": zn["PID"]["Kc"], "tau_I": zn["PID"]["tau_I"], "tau_D": zn["PID"]["tau_D"], "Ki": zn["PID"]["Ki"], "Kd": zn["PID"]["Kd"], "Philosophy": "Quarter decay ratio, fast & oscillatory"},
                {"Method": "Cohen-Coon (PID)", "Kc": cc["PID"]["Kc"], "tau_I": cc["PID"]["tau_I"], "tau_D": cc["PID"]["tau_D"], "Ki": cc["PID"]["Ki"], "Kd": cc["PID"]["Kd"], "Philosophy": "Optimized for dead-time dominant loops"},
                {"Method": "IMC / SIMC (Moderate)", "Kc": imc_mod["Kc"], "tau_I": imc_mod["tau_I"], "tau_D": imc_mod["tau_D"], "Ki": imc_mod["Ki"], "Kd": imc_mod["Kd"], "Philosophy": "Robust, non-oscillatory, smooth control"},
                {"Method": "IMC / SIMC (Robust)", "Kc": imc_rob["Kc"], "tau_I": imc_rob["tau_I"], "tau_D": imc_rob["tau_D"], "Ki": imc_rob["Ki"], "Kd": imc_rob["Kd"], "Philosophy": "High gain margin, maximum plant stability"}
            ],
            "Ziegler_Nichols_PID": zn["PID"],
            "Ziegler_Nichols_PI": zn["PI"],
            "Cohen_Coon_PID": cc["PID"],
            "Cohen_Coon_PI": cc["PI"],
            "IMC_Moderate": imc_mod,
            "IMC_Robust": imc_rob
        }
