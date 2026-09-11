"""
Pressure Relief Device Sizing Engine.
Implements API Standard 520 (Parts I & II), API Standard 521, and API Standard 526.
Evaluates vapor relief, certified liquid relief, fire case pool engulfment,
blocked discharge, thermal expansion, and selects standard API letter orifices (D to T).
"""

from typing import Dict, List, Any, Optional
import numpy as np

# Standard API 526 Designated Letter Orifices (Orifices D through T)
API_ORIFICE_SIZES: Dict[str, Dict[str, Any]] = {
    "D": {"letter": "D", "area_in2": 0.110, "area_mm2": 71.0, "flange": "1.5D2 (1.5\"x2\")"},
    "E": {"letter": "E", "area_in2": 0.196, "area_mm2": 126.0, "flange": "1.5E2 (1.5\"x2\")"},
    "F": {"letter": "F", "area_in2": 0.307, "area_mm2": 198.0, "flange": "1.5F2 (1.5\"x2\")"},
    "G": {"letter": "G", "area_in2": 0.503, "area_mm2": 325.0, "flange": "2G3 (2\"x3\")"},
    "H": {"letter": "H", "area_in2": 0.785, "area_mm2": 506.0, "flange": "2H3 (2\"x3\")"},
    "J": {"letter": "J", "area_in2": 1.287, "area_mm2": 830.0, "flange": "2.5J4 (2.5\"x4\")"},
    "K": {"letter": "K", "area_in2": 1.838, "area_mm2": 1186.0, "flange": "3K4 (3\"x4\")"},
    "L": {"letter": "L", "area_in2": 2.853, "area_mm2": 1841.0, "flange": "4L6 (4\"x6\")"},
    "M": {"letter": "M", "area_in2": 3.600, "area_mm2": 2323.0, "flange": "4M6 (4\"x6\")"},
    "N": {"letter": "N", "area_in2": 4.340, "area_mm2": 2800.0, "flange": "4N6 (4\"x6\")"},
    "P": {"letter": "P", "area_in2": 6.380, "area_mm2": 4116.0, "flange": "4P6 (4\"x6\")"},
    "Q": {"letter": "Q", "area_in2": 11.050, "area_mm2": 7129.0, "flange": "6Q8 (6\"x8\")"},
    "R": {"letter": "R", "area_in2": 16.000, "area_mm2": 10323.0, "flange": "6R10 (6\"x10\")"},
    "T": {"letter": "T", "area_in2": 26.000, "area_mm2": 16774.0, "flange": "8T10 (8\"x10\")"}
}


class ReliefValveSizer:
    """Rigorous Relief Device Sizing Engine per API 520 / 521 / 526."""

    @classmethod
    def size_vapor_relief_api520(cls, W_kg_h: float, T_K: float, P_set_kPa_g: float,
                                  M_g_mol: float, k_ratio: float = 1.30, Z: float = 1.0,
                                  overpressure_pct: float = 10.0,
                                  backpressure_kPa_g: float = 0.0,
                                  Kd: float = 0.975, Kb: float = 1.0, Kc: float = 1.0) -> Dict[str, Any]:
        """
        Calculates required orifice area for gas/vapor critical flow per API 520 Part I Eq (3.2).
        A = (18.86 * W) / (Kd * P1 * Kb * Kc * C_factor) * sqrt(T * Z / M)
        where:
          - W_kg_h: Relieving flow rate in kg/h
          - T_K: Relieving temperature in Kelvin
          - P_set_kPa_g: Valve set pressure in kPa gauge
          - M_g_mol: Vapor molecular weight (g/mol)
          - k_ratio: Specific heat ratio Cp/Cv
          - overpressure_pct: Allowable overpressure (10% standard, 21% fire)
        """
        P_atm = 101.325  # kPa
        P_set_abs = P_set_kPa_g + P_atm
        P1_abs = (P_set_kPa_g * (1.0 + overpressure_pct / 100.0)) + P_atm
        P2_abs = backpressure_kPa_g + P_atm

        # Critical pressure ratio
        crit_ratio = (2.0 / (k_ratio + 1.0)) ** (k_ratio / (k_ratio - 1.0))
        is_critical = (P2_abs / P1_abs) <= crit_ratio

        # C-factor function of specific heat ratio
        term = (2.0 / (k_ratio + 1.0)) ** ((k_ratio + 1.0) / (k_ratio - 1.0))
        C_func = np.sqrt(k_ratio * term)

        if is_critical:
            # Critical vapor flow equation (API 520 SI metric formula)
            # Area in mm2
            A_req_mm2 = (18.86 * W_kg_h) / (Kd * P1_abs * Kb * Kc * C_func) * np.sqrt((T_K * Z) / M_g_mol)
        else:
            # Subcritical vapor flow equation
            r = P2_abs / P1_abs
            sub_factor = np.sqrt((2.0 * k_ratio / (k_ratio - 1.0)) * (r ** (2.0 / k_ratio)) * (1.0 - r ** ((k_ratio - 1.0) / k_ratio)))
            A_req_mm2 = (18.86 * W_kg_h) / (Kd * P1_abs * Kb * Kc * sub_factor) * np.sqrt((T_K * Z) / M_g_mol)

        A_req_in2 = A_req_mm2 / 645.16
        selected_orifice = cls.select_api_orifice(A_req_mm2)

        return {
            "service_type": "Vapor / Gas",
            "relieving_rate_kg_h": round(W_kg_h, 2),
            "set_pressure_kPa_g": round(P_set_kPa_g, 2),
            "relieving_pressure_P1_kPa_abs": round(P1_abs, 2),
            "overpressure_pct": overpressure_pct,
            "relieving_temperature_K": round(T_K, 2),
            "molecular_weight": round(M_g_mol, 2),
            "is_critical_flow": is_critical,
            "required_area_mm2": round(A_req_mm2, 2),
            "required_area_in2": round(A_req_in2, 4),
            "selected_orifice": selected_orifice
        }

    @classmethod
    def size_liquid_relief_api520(cls, Q_m3_h: float, P_set_kPa_g: float,
                                  specific_gravity: float = 1.0,
                                  overpressure_pct: float = 10.0,
                                  backpressure_kPa_g: float = 0.0,
                                  Kd: float = 0.65, Kw: float = 1.0, Kv: float = 1.0) -> Dict[str, Any]:
        """
        Calculates required orifice area for certified liquid relief valves per API 520 Part I Eq (3.11).
        A = (11.78 * Q) / (Kd * Kw * Kv) * sqrt(SG / (P1 - P2))
        """
        P1 = P_set_kPa_g * (1.0 + overpressure_pct / 100.0)
        P2 = backpressure_kPa_g
        delta_p = max(1.0, P1 - P2)

        A_req_mm2 = (11.78 * Q_m3_h) / (Kd * Kw * Kv) * np.sqrt(specific_gravity / delta_p)
        A_req_in2 = A_req_mm2 / 645.16
        selected_orifice = cls.select_api_orifice(A_req_mm2)

        return {
            "service_type": "Liquid Incompressible",
            "liquid_flow_m3_h": round(Q_m3_h, 2),
            "set_pressure_kPa_g": round(P_set_kPa_g, 2),
            "delta_P_kPa": round(delta_p, 2),
            "specific_gravity": round(specific_gravity, 3),
            "required_area_mm2": round(A_req_mm2, 2),
            "required_area_in2": round(A_req_in2, 4),
            "selected_orifice": selected_orifice
        }

    @classmethod
    def calculate_fire_relief_api521(cls, wetted_area_m2: float, latent_heat_kJ_kg: float,
                                     P_set_kPa_g: float = 500.0,
                                     T_relieving_K: float = 380.0,
                                     M_g_mol: float = 46.07,
                                     F_environment: float = 1.0) -> Dict[str, Any]:
        """
        Calculates external pool fire heat ingress and resulting vapor relief load per API 521 Eq (6).
        Q_fire = 43200 * F * A_wetted^0.82  (Watts)
        W_fire = (Q_fire * 3.6) / latent_heat_kJ_kg  (kg/h)
        Relief is evaluated at 21% allowable fire overpressure.
        """
        wetted_area_m2 = max(0.5, wetted_area_m2)
        latent_heat_kJ_kg = max(50.0, latent_heat_kJ_kg)

        # Heat absorption in Watts
        Q_fire_watts = 43200.0 * F_environment * (wetted_area_m2 ** 0.82)
        Q_fire_kW = Q_fire_watts / 1000.0

        # Relieving rate in kg/h: Q(kJ/s) * 3600 / delta_H_vap(kJ/kg)
        W_fire_kg_h = (Q_fire_kW * 3600.0) / latent_heat_kJ_kg

        # Size relief valve at 21% allowable overpressure per ASME / API 520
        sizing = cls.size_vapor_relief_api520(
            W_kg_h=W_fire_kg_h,
            T_K=T_relieving_K,
            P_set_kPa_g=P_set_kPa_g,
            M_g_mol=M_g_mol,
            overpressure_pct=21.0
        )

        sizing["scenario"] = "External Pool Fire Engulfment (API 521)"
        sizing["wetted_surface_area_m2"] = round(wetted_area_m2, 2)
        sizing["fire_heat_ingress_kW"] = round(Q_fire_kW, 2)
        sizing["latent_heat_kJ_kg"] = round(latent_heat_kJ_kg, 2)
        sizing["F_environment"] = F_environment
        return sizing

    @classmethod
    def calculate_thermal_expansion_api521(cls, heat_duty_kW: float, P_set_kPa_g: float = 600.0,
                                           liquid_density_kg_m3: float = 1000.0,
                                           cp_kJ_kg_K: float = 4.184,
                                           beta_cubic_expansion_1_K: float = 0.0008) -> Dict[str, Any]:
        """
        Calculates hydraulic thermal expansion relief rate for blocked-in liquid exchangers per API 521.
        Q_expansion = (beta * Q_heat) / (rho * Cp)  [m3/s]
        """
        # Q_heat in Watts: heat_duty_kW * 1000
        # Expansion in m3/s:
        q_exp_m3_s = (beta_cubic_expansion_1_K * (heat_duty_kW * 1000.0)) / (liquid_density_kg_m3 * (cp_kJ_kg_K * 1000.0))
        q_exp_m3_h = q_exp_m3_s * 3600.0

        sizing = cls.size_liquid_relief_api520(
            Q_m3_h=max(0.01, q_exp_m3_h),
            P_set_kPa_g=P_set_kPa_g,
            specific_gravity=liquid_density_kg_m3 / 1000.0,
            overpressure_pct=10.0
        )
        sizing["scenario"] = "Blocked-In Liquid Thermal Expansion (API 521)"
        sizing["expansion_flow_m3_h"] = round(q_exp_m3_h, 4)
        return sizing

    @classmethod
    def select_api_orifice(cls, required_area_mm2: float) -> Dict[str, Any]:
        """
        Selects the smallest standard API 526 letter orifice where A_API >= A_req.
        """
        for letter, data in API_ORIFICE_SIZES.items():
            if data["area_mm2"] >= required_area_mm2:
                margin_pct = ((data["area_mm2"] - required_area_mm2) / max(0.1, required_area_mm2)) * 100.0
                utilization_pct = (required_area_mm2 / data["area_mm2"]) * 100.0
                return {
                    "letter": letter,
                    "standard_area_mm2": data["area_mm2"],
                    "standard_area_in2": data["area_in2"],
                    "flange_designation": data["flange"],
                    "margin_pct": round(margin_pct, 1),
                    "capacity_utilization_pct": round(utilization_pct, 1)
                }

        # If exceeds largest orifice T (16,774 mm2), multiple valves required
        largest = API_ORIFICE_SIZES["T"]
        num_valves = int(np.ceil(required_area_mm2 / largest["area_mm2"]))
        return {
            "letter": f"{num_valves}x T",
            "standard_area_mm2": largest["area_mm2"] * num_valves,
            "standard_area_in2": largest["area_in2"] * num_valves,
            "flange_designation": f"{num_valves}x 8T10",
            "margin_pct": 0.0,
            "capacity_utilization_pct": 100.0
        }

    @classmethod
    def evaluate_equipment_relief_scenarios(cls, unit: Any, species_map: dict) -> Dict[str, Any]:
        """
        Evaluates credible overpressure scenarios for a given flowsheet unit operation
        and pinpoints the governing relief device sizing scenario.
        """
        u_id = getattr(unit, "unit_id", "V-101")
        u_type = unit.__class__.__name__

        # Sizing parameters based on equipment type
        p_set = 500.0  # default 500 kPa gauge
        t_rel = 380.0
        wetted_a = 25.0
        latent_h = 850.0  # kJ/kg
        mw = 46.0

        if "DistillationColumn" in u_type:
            p_set = 350.0
            wetted_a = 45.0
            t_rel = getattr(unit, "T_condenser", 351.0)
            latent_h = 840.0
        elif any(k in u_type for k in ["Reactor", "CSTR", "PFR"]):
            p_set = 1500.0
            wetted_a = 20.0
            t_rel = 420.0
            latent_h = 600.0
        elif "FlashDrum" in u_type:
            p_set = 400.0
            wetted_a = 15.0
            t_rel = 360.0
            latent_h = 850.0
        elif "HeatExchanger" in u_type or "Heater" in u_type:
            p_set = 600.0
            wetted_a = 10.0
            t_rel = 370.0
            latent_h = 900.0

        # Scenario 1: Pool Fire Case (API 521)
        fire_res = cls.calculate_fire_relief_api521(
            wetted_area_m2=wetted_a,
            latent_heat_kJ_kg=latent_h,
            P_set_kPa_g=p_set,
            T_relieving_K=t_rel,
            M_g_mol=mw
        )

        # Scenario 2: Blocked Vapor Outlet (Full feed vapor flow accumulation)
        norm_rate_kg_h = 3500.0
        if hasattr(unit, "inlets") and unit.inlets and getattr(unit.inlets[0], "F", 0):
            norm_rate_kg_h = unit.inlets[0].F * mw * 3.6

        blocked_res = cls.size_vapor_relief_api520(
            W_kg_h=norm_rate_kg_h,
            T_K=t_rel,
            P_set_kPa_g=p_set,
            M_g_mol=mw,
            overpressure_pct=10.0
        )
        blocked_res["scenario"] = "Blocked Vapor Outlet / Control Valve Failure"

        # Scenario 3: Utility Failure (Condenser cooling water failure)
        utility_res = cls.size_vapor_relief_api520(
            W_kg_h=norm_rate_kg_h * 1.25,
            T_K=t_rel + 15.0,
            P_set_kPa_g=p_set,
            M_g_mol=mw,
            overpressure_pct=10.0
        )
        utility_res["scenario"] = "Cooling Utility Failure (Overhead Condenser Trip)"

        # Determine Governing Scenario (largest required area)
        scenarios = [fire_res, blocked_res, utility_res]
        scenarios.sort(key=lambda s: s["required_area_mm2"], reverse=True)
        governing = scenarios[0]

        return {
            "unit_id": u_id,
            "unit_type": u_type,
            "design_set_pressure_kPa_g": p_set,
            "governing_scenario": governing["scenario"],
            "governing_required_area_mm2": governing["required_area_mm2"],
            "governing_selected_orifice": governing["selected_orifice"]["letter"],
            "governing_flange": governing["selected_orifice"]["flange_designation"],
            "governing_relieving_rate_kg_h": governing["relieving_rate_kg_h"],
            "scenarios_evaluated": scenarios
        }
