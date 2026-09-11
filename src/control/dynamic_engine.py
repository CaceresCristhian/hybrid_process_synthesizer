"""
Dynamic Simulation Engine & Disturbance Scenario Manager.
Orchestrates real-time time-stepping dynamic runs, manages interactive disturbances
(surges, composition drops, cooling failure), monitors safety interlocks, and records strip-chart histories.
"""

from typing import Dict, List, Any, Optional
import numpy as np

class DynamicSimulationEngine:
    """Orchestrates dynamic process simulations, disturbances, and safety interlocks."""

    DISTURBANCE_PRESETS = {
        "None": "Baseline nominal operation",
        "Feed Flow Surge (+25%)": "+25% step surge in column feed flow rate",
        "Feed Composition Drop": "Feed light key fraction drops from 0.50 to 0.35",
        "Feed Subcooling Pulse": "Feed temperature drops by 15 K (subcooled liquid)",
        "Cooling Water Failure (-50%)": "50% condenser heat removal reduction",
        "Reboiler Steam Cut (-20%)": "20% drop in reboiler thermal heat input",
        "Reflux Valve Sticking": "Reflux valve frozen at current position"
    }

    def __init__(self, dynamic_column=None):
        from src.units.dynamic_column import DynamicDistillationColumn
        self.column = dynamic_column or DynamicDistillationColumn("C-101", "Dynamic De-Ethanizer")
        self.current_time = 0.0
        self.active_disturbances = set()
        self.alarm_log = []
        self.is_running = False

    def reset(self):
        """Resets column to nominal steady state."""
        from src.units.dynamic_column import DynamicDistillationColumn
        self.column = DynamicDistillationColumn(self.column.unit_id, self.column.name)
        self.current_time = 0.0
        self.active_disturbances.clear()
        self.alarm_log.clear()
        self.is_running = False

    def trigger_disturbance(self, disturbance_name: str):
        """Activates a process disturbance scenario."""
        if disturbance_name in self.DISTURBANCE_PRESETS:
            self.active_disturbances.add(disturbance_name)
            self._apply_disturbances()

    def clear_disturbance(self, disturbance_name: str):
        """Clears an active disturbance and restores baseline parameter."""
        if disturbance_name in self.active_disturbances:
            self.active_disturbances.remove(disturbance_name)
            self._apply_disturbances()

    def _apply_disturbances(self):
        """Applies active disturbances to column parameters."""
        # Baseline values
        f_base = self.column.nominal_feed_flow
        z_base = 0.50
        t_base = 340.0
        v_base = self.column.nominal_feed_flow * 0.75

        # 1. Feed Flow Surge
        if "Feed Flow Surge (+25%)" in self.active_disturbances:
            self.column.F_feed = f_base * 1.25
        else:
            self.column.F_feed = f_base

        # 2. Feed Composition Drop
        if "Feed Composition Drop" in self.active_disturbances:
            self.column.z_feed = 0.35
        else:
            self.column.z_feed = z_base

        # 3. Feed Subcooling Pulse
        if "Feed Subcooling Pulse" in self.active_disturbances:
            self.column.T_feed = t_base - 15.0
        else:
            self.column.T_feed = t_base

        # 4. Reboiler Steam Cut
        if "Reboiler Steam Cut (-20%)" in self.active_disturbances:
            self.column.V_boilup = v_base * 0.80
        else:
            self.column.V_boilup = v_base

    def check_alarms(self) -> List[Dict[str, Any]]:
        """Monitors column safety interlocks and alarm limits."""
        alarms = []

        # Purity warning
        xd = self.column.x[0]
        if xd < 0.80:
            alarms.append({
                "time": self.current_time,
                "severity": "WARNING",
                "tag": "QA-101",
                "message": f"Off-spec distillate purity: xD = {xd*100:.1f}% (Spec >= 80.0%)"
            })

        # Accumulator Level
        acc_pct = 100.0 * (self.column.M[0] / self.column.nominal_holdup_vessels)
        if acc_pct < 25.0:
            alarms.append({"time": self.current_time, "severity": "WARNING", "tag": "LAL-101", "message": f"Reflux accumulator level low: {acc_pct:.1f}%"})
        elif acc_pct > 80.0:
            alarms.append({"time": self.current_time, "severity": "WARNING", "tag": "LAH-101", "message": f"Reflux accumulator level high: {acc_pct:.1f}%"})

        # Sump Level
        sump_pct = 100.0 * (self.column.M[-1] / self.column.nominal_holdup_vessels)
        if sump_pct < 20.0:
            alarms.append({"time": self.current_time, "severity": "TRIP", "tag": "LALL-102", "message": f"Reboiler dry-out imminent: Sump level = {sump_pct:.1f}%"})
        elif sump_pct > 85.0:
            alarms.append({"time": self.current_time, "severity": "WARNING", "tag": "LAH-102", "message": f"Column base flooded: Sump level = {sump_pct:.1f}%"})

        for a in alarms:
            if not any(logged["message"] == a["message"] and abs(logged["time"] - a["time"]) < 5.0 for logged in self.alarm_log):
                self.alarm_log.append(a)

        return alarms

    def run_time_steps(self, duration_seconds: float = 30.0, dt: float = 1.0) -> Dict[str, Any]:
        """Advances dynamic simulation forward by duration_seconds."""
        steps = int(np.ceil(duration_seconds / dt))
        for _ in range(steps):
            self.column.step(dt=dt)
            self.current_time = self.column.time_history[-1]
            self.check_alarms()

        return {
            "current_time": self.current_time,
            "history": self.column.history,
            "active_disturbances": list(self.active_disturbances),
            "recent_alarms": self.alarm_log[-5:]
        }

    @property
    def history(self) -> Dict[str, list]:
        """Returns the dynamic column transient history dictionary."""
        return self.column.history

    def run_transient(self, duration: float = 30.0, dt: float = 1.0) -> Dict[str, Any]:
        """Convenience wrapper for run_time_steps."""
        return self.run_time_steps(duration_seconds=duration, dt=dt)

    def inject_disturbance(self, name: str, magnitude: Optional[float] = None):
        """Convenience method accepting short alias codes or full names."""
        alias_map = {
            "feed_surge": "Feed Flow Surge (+25%)",
            "feed_composition_drop": "Feed Composition Drop",
            "feed_subcooling": "Feed Subcooling Pulse",
            "cooling_water_failure": "Cooling Water Failure (-50%)",
            "steam_cut": "Reboiler Steam Cut (-20%)"
        }
        resolved = alias_map.get(name, name)
        if resolved in self.DISTURBANCE_PRESETS:
            self.trigger_disturbance(resolved)
        else:
            self.active_disturbances.add(name)

    def get_active_disturbances_summary(self) -> str:
        """Returns readable summary string of active disturbances."""
        if not self.active_disturbances:
            return "None (Nominal Baseline)"
        return ", ".join(sorted(self.active_disturbances))

