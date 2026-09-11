"""
Pinch Analysis and Thermal Energy Integration Engine.
Implements Bodo Linnhoff's Problem Table Algorithm, Maximum Energy Recovery (MER) targets,
Hot and Cold Composite Curves (T-H), Grand Composite Curve (GCC), and utility cost targeting.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np

@dataclass
class ThermalStream:
    """Represents a hot or cold thermal process stream in pinch analysis."""
    stream_id: str
    stream_type: str  # 'HOT' (needs cooling) or 'COLD' (needs heating)
    T_supply_C: float
    T_target_C: float
    heat_duty_kW: float
    CP_kW_per_K: float

    @property
    def T_supply_K(self) -> float:
        return self.T_supply_C + 273.15

    @property
    def T_target_K(self) -> float:
        return self.T_target_C + 273.15


class PinchAnalyzer:
    """Industrial Pinch Technology Engine for Energy Integration and Thermal Targeting."""

    @classmethod
    def extract_streams_from_flowsheet(cls, units_map: dict, streams_map: dict) -> List[ThermalStream]:
        """
        Scans all flowsheet unit operations to extract process heating and cooling duties.
        Extracts from Heaters, Coolers, HeatExchangers, DistillationColumns, and FlashDrums.
        """
        thermal_streams = []

        for uid, unit in units_map.items():
            u_type = unit.__class__.__name__

            # 1. Cooler: Process fluid is cooled (HOT stream)
            if u_type == "Cooler":
                if hasattr(unit, "inlets") and unit.inlets and hasattr(unit, "outlets") and unit.outlets:
                    s_in = unit.inlets[0]
                    s_out = unit.outlets[0]
                    if s_in.T is not None and s_out.T is not None and s_in.T > s_out.T:
                        t_sup = s_in.T - 273.15
                        t_tar = s_out.T - 273.15
                        duty = abs(getattr(unit, "heat_duty", 0.0)) / 1000.0  # kW
                        delta_t = max(0.1, t_sup - t_tar)
                        if duty <= 0 and hasattr(unit, "t_target") and s_in.F:
                            duty = s_in.F * 0.075 * delta_t
                        if duty > 0.01:
                            thermal_streams.append(ThermalStream(
                                stream_id=f"{uid}_Cooling",
                                stream_type="HOT",
                                T_supply_C=round(t_sup, 2),
                                T_target_C=round(t_tar, 2),
                                heat_duty_kW=round(duty, 2),
                                CP_kW_per_K=round(duty / delta_t, 4)
                            ))

            # 2. Heater: Process fluid is heated (COLD stream)
            elif u_type == "Heater":
                if hasattr(unit, "inlets") and unit.inlets and hasattr(unit, "outlets") and unit.outlets:
                    s_in = unit.inlets[0]
                    s_out = unit.outlets[0]
                    if s_in.T is not None and s_out.T is not None and s_out.T > s_in.T:
                        t_sup = s_in.T - 273.15
                        t_tar = s_out.T - 273.15
                        duty = abs(getattr(unit, "heat_duty", 0.0)) / 1000.0  # kW
                        delta_t = max(0.1, t_tar - t_sup)
                        if duty <= 0 and hasattr(unit, "t_target") and s_in.F:
                            duty = s_in.F * 0.075 * delta_t
                        if duty > 0.01:
                            thermal_streams.append(ThermalStream(
                                stream_id=f"{uid}_Heating",
                                stream_type="COLD",
                                T_supply_C=round(t_sup, 2),
                                T_target_C=round(t_tar, 2),
                                heat_duty_kW=round(duty, 2),
                                CP_kW_per_K=round(duty / delta_t, 4)
                            ))

            # 3. HeatExchanger: Sensible hot & cold streams
            elif u_type == "HeatExchanger":
                duty = abs(getattr(unit, "heat_duty", 50000.0)) / 1000.0
                thermal_streams.append(ThermalStream(
                    stream_id=f"{uid}_HotSide",
                    stream_type="HOT",
                    T_supply_C=150.0,
                    T_target_C=80.0,
                    heat_duty_kW=round(duty, 2),
                    CP_kW_per_K=round(duty / 70.0, 4)
                ))
                thermal_streams.append(ThermalStream(
                    stream_id=f"{uid}_ColdSide",
                    stream_type="COLD",
                    T_supply_C=30.0,
                    T_target_C=110.0,
                    heat_duty_kW=round(duty, 2),
                    CP_kW_per_K=round(duty / 80.0, 4)
                ))

            # 4. Distillation Column: Condenser (HOT stream) & Reboiler (COLD stream)
            elif "DistillationColumn" in u_type:
                reb_duty = abs(getattr(unit, "heat_duty", 120000.0)) / 1000.0  # kW
                t_reb = getattr(unit, "T_reboiler", 370.0)
                if hasattr(unit, "T") and len(unit.T) > 0:
                    t_reb = unit.T[-1]
                t_reb_c = t_reb - 273.15 if t_reb > 200 else t_reb
                thermal_streams.append(ThermalStream(
                    stream_id=f"{uid}_Reboiler",
                    stream_type="COLD",
                    T_supply_C=round(t_reb_c - 1.0, 2),
                    T_target_C=round(t_reb_c + 1.0, 2),
                    heat_duty_kW=round(reb_duty, 2),
                    CP_kW_per_K=round(reb_duty / 2.0, 4)
                ))

                cond_duty = reb_duty * 0.90
                t_cond = getattr(unit, "T_condenser", 350.0)
                if hasattr(unit, "T") and len(unit.T) > 0:
                    t_cond = unit.T[0]
                t_cond_c = t_cond - 273.15 if t_cond > 200 else t_cond
                thermal_streams.append(ThermalStream(
                    stream_id=f"{uid}_Condenser",
                    stream_type="HOT",
                    T_supply_C=round(t_cond_c + 1.0, 2),
                    T_target_C=round(t_cond_c - 1.0, 2),
                    heat_duty_kW=round(cond_duty, 2),
                    CP_kW_per_K=round(cond_duty / 2.0, 4)
                ))

            # 5. Flash Drum: Sensible flash heating load
            elif u_type == "FlashDrum":
                f_duty = abs(getattr(unit, "heat_duty", 25000.0)) / 1000.0
                if f_duty > 0.01:
                    t_flash = getattr(unit, "temp_vessel", 350.0) - 273.15
                    thermal_streams.append(ThermalStream(
                        stream_id=f"{uid}_FlashDuty",
                        stream_type="COLD",
                        T_supply_C=round(t_flash - 10.0, 2),
                        T_target_C=round(t_flash, 2),
                        heat_duty_kW=round(f_duty, 2),
                        CP_kW_per_K=round(f_duty / 10.0, 4)
                    ))

        return thermal_streams

    @classmethod
    def solve_problem_table_algorithm(cls, streams: List[ThermalStream], delta_T_min: float = 10.0) -> Dict[str, Any]:
        """
        Executes Linnhoff's Problem Table Algorithm.
        Shifts hot temperatures down by delta_T_min/2 and cold temperatures up by delta_T_min/2,
        constructs temperature intervals, performs heat cascades, and evaluates exact pinch points.
        """
        if not streams:
            return {
                "delta_T_min": delta_T_min,
                "pinch_temperature_hot_C": None,
                "pinch_temperature_cold_C": None,
                "pinch_temperature_shifted_C": None,
                "Q_hot_utility_min_kW": 0.0,
                "Q_cold_utility_min_kW": 0.0,
                "Q_heat_recovery_max_kW": 0.0,
                "total_hot_duty_kW": 0.0,
                "total_cold_duty_kW": 0.0,
                "intervals": [],
                "shifted_temperatures": [],
                "heat_cascade_feasible": []
            }

        shift = delta_T_min / 2.0
        shifted_bounds = set()

        tot_hot = sum(s.heat_duty_kW for s in streams if s.stream_type == "HOT")
        tot_cold = sum(s.heat_duty_kW for s in streams if s.stream_type == "COLD")

        stream_intervals = []
        for s in streams:
            if s.stream_type == "HOT":
                t_s_star = s.T_supply_C - shift
                t_t_star = s.T_target_C - shift
            else:
                t_s_star = s.T_supply_C + shift
                t_t_star = s.T_target_C + shift

            t_high = max(t_s_star, t_t_star)
            t_low = min(t_s_star, t_t_star)
            stream_intervals.append({
                "stream": s,
                "t_high": t_high,
                "t_low": t_low,
                "CP": s.CP_kW_per_K,
                "type": s.stream_type
            })
            shifted_bounds.add(round(t_high, 4))
            shifted_bounds.add(round(t_low, 4))

        t_stars = sorted(list(shifted_bounds), reverse=True)

        interval_data = []
        unfeasible_cascade = [0.0]

        for i in range(len(t_stars) - 1):
            t_top = t_stars[i]
            t_bot = t_stars[i + 1]
            dt_int = t_top - t_bot

            sum_cp_hot = 0.0
            sum_cp_cold = 0.0
            active_stream_ids = []

            for si in stream_intervals:
                if si["t_high"] >= t_top - 1e-6 and si["t_low"] <= t_bot + 1e-6:
                    active_stream_ids.append(si["stream"].stream_id)
                    if si["type"] == "HOT":
                        sum_cp_hot += si["CP"]
                    else:
                        sum_cp_cold += si["CP"]

            delta_cp = sum_cp_cold - sum_cp_hot
            delta_H_int = delta_cp * dt_int

            r_next = unfeasible_cascade[-1] - delta_H_int
            unfeasible_cascade.append(r_next)

            interval_data.append({
                "interval_index": i + 1,
                "T_top_star_C": t_top,
                "T_bot_star_C": t_bot,
                "delta_T_int_C": dt_int,
                "sum_CP_hot_kW_K": sum_cp_hot,
                "sum_CP_cold_kW_K": sum_cp_cold,
                "delta_CP_kW_K": delta_cp,
                "delta_H_kW": delta_H_int,
                "active_streams": active_stream_ids
            })

        min_residual = min(unfeasible_cascade)
        q_hot_min = max(0.0, -min_residual)
        feasible_cascade = [r + q_hot_min for r in unfeasible_cascade]
        q_cold_min = max(0.0, feasible_cascade[-1])
        q_rec = tot_hot - q_cold_min

        zero_indices = [idx for idx, val in enumerate(feasible_cascade) if abs(val) < 1e-4]
        if zero_indices:
            pinch_idx = zero_indices[0]
            t_star_pinch = t_stars[pinch_idx]
        else:
            pinch_idx = int(np.argmin(feasible_cascade))
            t_star_pinch = t_stars[pinch_idx]

        t_hot_pinch = t_star_pinch + shift
        t_cold_pinch = t_star_pinch - shift

        return {
            "delta_T_min": delta_T_min,
            "pinch_temperature_hot_C": round(float(t_hot_pinch), 2),
            "pinch_temperature_cold_C": round(float(t_cold_pinch), 2),
            "pinch_temperature_shifted_C": round(float(t_star_pinch), 2),
            "Q_hot_utility_min_kW": round(float(q_hot_min), 2),
            "Q_cold_utility_min_kW": round(float(q_cold_min), 2),
            "Q_heat_recovery_max_kW": round(float(max(0.0, q_rec)), 2),
            "total_hot_duty_kW": round(float(tot_hot), 2),
            "total_cold_duty_kW": round(float(tot_cold), 2),
            "intervals": interval_data,
            "shifted_temperatures": t_stars,
            "heat_cascade_feasible": [round(val, 2) for val in feasible_cascade]
        }

    @classmethod
    def generate_composite_curves(cls, streams: List[ThermalStream], delta_T_min: float = 10.0) -> Dict[str, Any]:
        """
        Generates Hot Composite Curve (HCC) and Cold Composite Curve (CCC) coordinates.
        Cold curve is shifted horizontally such that minimum approach equals delta_T_min.
        """
        pt_res = cls.solve_problem_table_algorithm(streams, delta_T_min)
        q_c_min = pt_res["Q_cold_utility_min_kW"]

        hot_streams = [s for s in streams if s.stream_type == "HOT"]
        cold_streams = [s for s in streams if s.stream_type == "COLD"]

        h_hot = [0.0]
        t_hot = [0.0]
        if hot_streams:
            t_hot_points = sorted(list(set([s.T_supply_C for s in hot_streams] + [s.T_target_C for s in hot_streams])))
            cum_h = 0.0
            h_hot = [0.0]
            t_hot = [t_hot_points[0]]
            for k in range(len(t_hot_points) - 1):
                t_low = t_hot_points[k]
                t_high = t_hot_points[k + 1]
                active_cp = sum(s.CP_kW_per_K for s in hot_streams if min(s.T_supply_C, s.T_target_C) <= t_low and max(s.T_supply_C, s.T_target_C) >= t_high)
                cum_h += active_cp * (t_high - t_low)
                h_hot.append(round(cum_h, 2))
                t_hot.append(round(t_high, 2))

        h_cold = [q_c_min]
        t_cold = [0.0]
        if cold_streams:
            t_cold_points = sorted(list(set([s.T_supply_C for s in cold_streams] + [s.T_target_C for s in cold_streams])))
            cum_h_c = q_c_min
            h_cold = [round(cum_h_c, 2)]
            t_cold = [t_cold_points[0]]
            for k in range(len(t_cold_points) - 1):
                t_low = t_cold_points[k]
                t_high = t_cold_points[k + 1]
                active_cp = sum(s.CP_kW_per_K for s in cold_streams if min(s.T_supply_C, s.T_target_C) <= t_low and max(s.T_supply_C, s.T_target_C) >= t_high)
                cum_h_c += active_cp * (t_high - t_low)
                h_cold.append(round(cum_h_c, 2))
                t_cold.append(round(t_high, 2))

        return {
            "problem_table": pt_res,
            "hot_composite": {
                "enthalpy_kW": h_hot,
                "temperature_C": t_hot
            },
            "cold_composite": {
                "enthalpy_kW": h_cold,
                "temperature_C": t_cold
            }
        }

    @classmethod
    def generate_grand_composite_curve(cls, streams: List[ThermalStream], delta_T_min: float = 10.0) -> Dict[str, Any]:
        """Generates Grand Composite Curve (GCC) mapping shifted temperature T* vs cascaded net heat flow."""
        pt_res = cls.solve_problem_table_algorithm(streams, delta_T_min)
        return {
            "shifted_temperature_C": pt_res["shifted_temperatures"],
            "cascaded_heat_flow_kW": pt_res["heat_cascade_feasible"],
            "pinch_shifted_temperature_C": pt_res["pinch_temperature_shifted_C"]
        }

    @classmethod
    def calculate_utility_savings(cls, streams: List[ThermalStream],
                                  delta_T_min: float = 10.0,
                                  operating_hours: float = 8000.0,
                                  utility_rates: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Quantifies energy reduction and dollar savings from pinch heat integration."""
        rates = {"steam_usd_per_gj": 4.50, "cooling_water_usd_per_gj": 0.35}
        if utility_rates:
            rates.update(utility_rates)

        pt_res = cls.solve_problem_table_algorithm(streams, delta_T_min)

        tot_hot_duty_kW = pt_res["total_hot_duty_kW"]
        tot_cold_duty_kW = pt_res["total_cold_duty_kW"]
        q_h_min_kW = pt_res["Q_hot_utility_min_kW"]
        q_c_min_kW = pt_res["Q_cold_utility_min_kW"]
        q_recovery_kW = pt_res["Q_heat_recovery_max_kW"]

        gj_factor = (3600.0 * operating_hours) / 1e6

        unintegrated_total_cost = (tot_cold_duty_kW * gj_factor * rates["steam_usd_per_gj"]) + (tot_hot_duty_kW * gj_factor * rates["cooling_water_usd_per_gj"])
        pinch_total_cost = (q_h_min_kW * gj_factor * rates["steam_usd_per_gj"]) + (q_c_min_kW * gj_factor * rates["cooling_water_usd_per_gj"])

        annual_savings_usd = max(0.0, unintegrated_total_cost - pinch_total_cost)
        energy_pct_reduction = (q_recovery_kW / max(0.01, tot_cold_duty_kW)) * 100.0 if tot_cold_duty_kW > 0 else 0.0

        num_utilities = (1 if q_h_min_kW > 0 else 0) + (1 if q_c_min_kW > 0 else 0)
        u_min_total = max(1, len(streams) + num_utilities - 1)

        return {
            "unintegrated_steam_duty_kW": tot_cold_duty_kW,
            "unintegrated_cooling_duty_kW": tot_hot_duty_kW,
            "unintegrated_annual_cost_usd": round(unintegrated_total_cost, 2),
            "pinch_steam_duty_kW": q_h_min_kW,
            "pinch_cooling_duty_kW": q_c_min_kW,
            "pinch_annual_cost_usd": round(pinch_total_cost, 2),
            "heat_recovered_kW": q_recovery_kW,
            "annual_savings_usd": round(annual_savings_usd, 2),
            "energy_reduction_pct": round(min(100.0, energy_pct_reduction), 1),
            "min_number_of_heat_exchangers": u_min_total
        }
