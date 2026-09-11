"""
Distillation Separation Superstructure & Sequence Synthesis Engine.
Provides algorithmic multi-component distillation sequencing (Direct, Indirect,
Distributed Prefractionator, and Dividing-Wall Column / Petlyuk DWC),
Fenske-Underwood-Gilliland shortcut sizing, Turton bare module CAPEX,
utility OPEX, carbon emissions, and Total Annualized Cost (TAC) optimization.
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional

from src.economics.cost_correlations import CostCorrelations, DEFAULT_CEPCI, BASE_CEPCI


@dataclass
class SequenceCandidate:
    """Represents a synthesized distillation sequence candidate."""
    sequence_name: str
    columns_count: int
    total_stages: int
    total_reboiler_duty_kW: float
    total_condenser_duty_kW: float
    column_diameters_m: List[float]
    column_heights_m: List[float]
    reboiler_duties_kW: List[float]
    condenser_duties_kW: List[float]
    reflux_ratios: List[float]
    capex_usd: float
    annual_utility_opex_usd: float
    annual_carbon_emissions_tonnes: float
    annual_carbon_tax_usd: float
    total_annualized_cost_tac_usd: float
    steam_consumption_gj_yr: float
    cooling_water_gj_yr: float
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes candidate metrics to a standard dictionary."""
        return {
            "sequence_name": self.sequence_name,
            "columns_count": self.columns_count,
            "total_stages": self.total_stages,
            "total_reboiler_duty_kW": round(self.total_reboiler_duty_kW, 2),
            "total_condenser_duty_kW": round(self.total_condenser_duty_kW, 2),
            "column_diameters_m": [round(d, 2) for d in self.column_diameters_m],
            "column_heights_m": [round(h, 2) for h in self.column_heights_m],
            "reboiler_duties_kW": [round(q, 2) for q in self.reboiler_duties_kW],
            "condenser_duties_kW": [round(q, 2) for q in self.condenser_duties_kW],
            "reflux_ratios": [round(r, 2) for r in self.reflux_ratios],
            "capex_usd": round(self.capex_usd, 2),
            "annual_utility_opex_usd": round(self.annual_utility_opex_usd, 2),
            "annual_carbon_emissions_tonnes": round(self.annual_carbon_emissions_tonnes, 2),
            "annual_carbon_tax_usd": round(self.annual_carbon_tax_usd, 2),
            "total_annualized_cost_tac_usd": round(self.total_annualized_cost_tac_usd, 2),
            "steam_consumption_gj_yr": round(self.steam_consumption_gj_yr, 2),
            "cooling_water_gj_yr": round(self.cooling_water_gj_yr, 2),
            "description": self.description,
            "details": self.details
        }


class SeparationSequencer:
    """Algorithmic multi-component distillation sequencing and shortcut design synthesizer."""

    @classmethod
    def calculate_relative_volatilities(cls, components: List[str],
                                        species_map: Dict[str, Any],
                                        P_pa: float = 101325.0) -> Tuple[List[str], List[float], Dict[str, float]]:
        """
        Orders components by decreasing volatility (A, B, C) and computes relative volatilities
        relative to the heaviest component (alpha_C = 1.0).
        """
        temp_data = []
        for comp in components:
            sp = species_map.get(comp)
            if sp and hasattr(sp, "macro") and sp.macro.boiling_point:
                tb = sp.macro.boiling_point
            else:
                defaults = {
                    "benzene": 353.25,
                    "toluene": 383.75,
                    "octane": 398.8,
                    "pxylene": 411.5,
                    "methanol": 337.8,
                    "ethanol": 351.5,
                    "water": 373.15,
                    "propane": 231.1,
                    "butane": 272.7,
                    "pentane": 309.2,
                    "hexane": 341.9,
                    "acetone": 329.4
                }
                tb = defaults.get(comp.lower(), 360.0)
            temp_data.append((comp, tb))

        # Sort ascending by boiling point (lowest Tb is most volatile light key A)
        temp_data.sort(key=lambda x: x[1])
        sorted_comps = [x[0] for x in temp_data]
        sorted_tbs = [x[1] for x in temp_data]

        t_ref = float(np.mean(sorted_tbs))
        p_sats = []
        for comp, tb in temp_data:
            sp = species_map.get(comp)
            if sp and hasattr(sp, "system") and hasattr(sp.system, "antoine_coefficients") and sp.system.antoine_coefficients:
                a, b, c = sp.system.antoine_coefficients[:3]
                try:
                    p_bar = 10.0 ** (a - b / (t_ref + c))
                    p_sats.append(max(1e-4, p_bar * 1e5))
                except Exception:
                    p_sats.append(P_pa * np.exp((38000.0 / 8.314) * (1.0 / tb - 1.0 / t_ref)))
            else:
                p_sats.append(P_pa * np.exp((38000.0 / 8.314) * (1.0 / tb - 1.0 / t_ref)))

        p_ref = p_sats[-1]
        alphas = [max(1.0, float(p / p_ref)) for p in p_sats]
        alphas[-1] = 1.0

        alpha_dict = {comp: round(alpha, 3) for comp, alpha in zip(sorted_comps, alphas)}
        return sorted_comps, alphas, alpha_dict

    @classmethod
    def solve_underwood(cls, alphas: List[float], z: List[float], q: float = 1.0,
                         lk_idx: int = 0, hk_idx: int = 1) -> Tuple[float, float]:
        """
        Solves the Underwood equation for minimum reflux ratio R_min.
        """
        alpha_lk = alphas[lk_idx]
        alpha_hk = alphas[hk_idx]

        def f(th):
            return sum(a * zi / (a - th) for a, zi in zip(alphas, z) if abs(a - th) > 1e-9) - (1.0 - q)

        lo = alpha_hk + 1e-5
        hi = alpha_lk - 1e-5

        for _ in range(70):
            mid = 0.5 * (lo + hi)
            val = f(mid)
            if val > 0:
                hi = mid
            else:
                lo = mid
        theta = 0.5 * (lo + hi)

        xD = [0.0] * len(alphas)
        if lk_idx == 0 and hk_idx == 1:
            d_lk = 0.99 * z[0]
            d_hk = 0.01 * z[1]
            d_tot = max(1e-6, d_lk + d_hk)
            xD[0] = d_lk / d_tot
            xD[1] = d_hk / d_tot
        elif lk_idx == 1 and hk_idx == 2:
            d_lk = 0.99 * z[1]
            d_hk = 0.01 * z[2]
            d_tot = max(1e-6, d_lk + d_hk)
            xD[1] = d_lk / d_tot
            xD[2] = d_hk / d_tot
        else:
            d_tot = max(1e-6, sum(z[:hk_idx]))
            for i in range(hk_idx):
                xD[i] = z[i] / d_tot

        sum_terms = sum(a * xDi / (a - theta) for a, xDi in zip(alphas, xD) if abs(a - theta) > 1e-9)
        r_min = max(0.2, sum_terms - 1.0)
        return float(theta), float(r_min)

    @classmethod
    def calculate_gilliland_stages(cls, N_min: float, R: float, R_min: float) -> int:
        """
        Evaluates theoretical equilibrium stages using Gilliland correlation (Molokanov form).
        """
        if R <= R_min * 1.001:
            return int(round(4.0 * N_min))
        X = (R - R_min) / (R + 1.0)
        X = max(1e-4, min(0.999, X))
        Y = 0.75 * (1.0 - (X ** 0.5668))
        Y = max(0.01, min(0.85, Y))
        N = (N_min + Y) / (1.0 - Y)
        return max(6, int(round(N)))

    @classmethod
    def size_shortcut_column(cls, D_mol_s: float, R: float, N_stages: int,
                             delta_h_vap_kj_mol: float = 38.0,
                             MW_avg: float = 0.085,
                             P_pa: float = 101325.0,
                             T_k: float = 360.0,
                             material: str = "Carbon Steel",
                             cepci: float = DEFAULT_CEPCI) -> Dict[str, Any]:
        """
        Calculates column geometry (diameter, height), thermal duties, and Turton bare module CAPEX.
        """
        V_mol_s = (R + 1.0) * D_mol_s
        q_reb_kw = max(10.0, V_mol_s * delta_h_vap_kj_mol)
        q_cond_kw = q_reb_kw

        R_g = 8.314
        rho_v = max(0.1, (P_pa * MW_avg) / (R_g * T_k))
        rho_l = 800.0
        u_flood = 0.06 * np.sqrt(max(0.1, (rho_l - rho_v) / rho_v))
        u_design = max(0.2, 0.75 * u_flood)

        q_vap_m3_s = (V_mol_s * R_g * T_k) / P_pa
        a_col = max(0.15, q_vap_m3_s / u_design)
        d_col = max(0.5, np.sqrt(4.0 * a_col / np.pi))
        h_col = max(3.0, N_stages * 0.6 + 3.0)
        v_shell = (np.pi / 4.0) * (d_col ** 2) * h_col

        res_shell = CostCorrelations.calculate_bare_module_cost(
            "vessel_vertical", v_shell, design_pressure_pa=P_pa, material=material, cepci=cepci, diameter_m=d_col
        )
        c_bm_shell = res_shell["C_BM"]

        tray_area = (np.pi / 4.0) * (d_col ** 2)
        cp0_tray = CostCorrelations.calculate_cp0("tray_sieve", tray_area)
        cp_tray = cp0_tray * (cepci / BASE_CEPCI)
        f_m_tray = CostCorrelations.get_material_factor("tray_sieve", material)
        c_bm_trays = cp_tray * N_stages * f_m_tray

        a_cond = max(5.0, q_cond_kw / (0.8 * 25.0))
        res_cond = CostCorrelations.calculate_bare_module_cost(
            "heat_exchanger_floating_head", a_cond, design_pressure_pa=P_pa, material=material, cepci=cepci
        )
        c_bm_cond = res_cond["C_BM"]

        a_reb = max(5.0, q_reb_kw / (1.0 * 30.0))
        res_reb = CostCorrelations.calculate_bare_module_cost(
            "heat_exchanger_fixed_tubesheet", a_reb, design_pressure_pa=P_pa, material=material, cepci=cepci
        )
        c_bm_reb = res_reb["C_BM"]

        total_c_bm = c_bm_shell + c_bm_trays + c_bm_cond + c_bm_reb

        return {
            "D_col_m": float(d_col),
            "H_col_m": float(h_col),
            "V_shell_m3": float(v_shell),
            "N_stages": int(N_stages),
            "R": float(R),
            "Q_reb_kW": float(q_reb_kw),
            "Q_cond_kW": float(q_cond_kw),
            "C_BM_shell": float(c_bm_shell),
            "C_BM_trays": float(c_bm_trays),
            "C_BM_cond": float(c_bm_cond),
            "C_BM_reb": float(c_bm_reb),
            "total_C_BM": float(total_c_bm)
        }

    @classmethod
    def evaluate_direct_sequence(cls, F_mol_s: float, z: List[float], alphas: List[float],
                                 steam_price_usd_per_gj: float = 7.50,
                                 cooling_price_usd_per_gj: float = 0.354,
                                 electricity_price_usd_per_kwh: float = 0.085,
                                 carbon_tax_usd_per_tonne: float = 50.0,
                                 crf: float = 0.16275,
                                 operating_hours: float = 8000.0,
                                 delta_h_vap_kj_mol: float = 38.0,
                                 reflux_factor: float = 1.30) -> SequenceCandidate:
        """
        Evaluates Direct Sequence:
        Column 1: Splits A (distillate) from B+C (bottoms). LK = A, HK = B.
        Column 2: Splits B (distillate) from C (bottoms). LK = B, HK = C.
        """
        # Column 1
        _, r_min_1 = cls.solve_underwood(alphas, z, q=1.0, lk_idx=0, hk_idx=1)
        r_1 = max(0.5, reflux_factor * r_min_1)
        alpha_ab = max(1.05, alphas[0] / alphas[1])
        n_min_1 = np.log((0.99 * 0.99) / (0.01 * 0.01)) / np.log(alpha_ab)
        n_stages_1 = cls.calculate_gilliland_stages(n_min_1, r_1, r_min_1)
        d_mol_s_1 = max(1.0, F_mol_s * z[0])

        col1 = cls.size_shortcut_column(d_mol_s_1, r_1, n_stages_1, delta_h_vap_kj_mol=delta_h_vap_kj_mol)

        # Column 2
        z_2 = [0.0, z[1] / (z[1] + z[2]), z[2] / (z[1] + z[2])]
        _, r_min_2 = cls.solve_underwood(alphas, z_2, q=1.0, lk_idx=1, hk_idx=2)
        r_2 = max(0.5, reflux_factor * r_min_2)
        alpha_bc = max(1.05, alphas[1] / alphas[2])
        n_min_2 = np.log((0.99 * 0.99) / (0.01 * 0.01)) / np.log(alpha_bc)
        n_stages_2 = cls.calculate_gilliland_stages(n_min_2, r_2, r_min_2)
        d_mol_s_2 = max(1.0, F_mol_s * z[1])

        col2 = cls.size_shortcut_column(d_mol_s_2, r_2, n_stages_2, delta_h_vap_kj_mol=delta_h_vap_kj_mol)

        tot_q_reb = col1["Q_reb_kW"] + col2["Q_reb_kW"]
        tot_q_cond = col1["Q_cond_kW"] + col2["Q_cond_kW"]
        tot_capex = col1["total_C_BM"] + col2["total_C_BM"]

        steam_gj_yr = tot_q_reb * 3600.0 * operating_hours / 1.0e6
        cooling_gj_yr = tot_q_cond * 3600.0 * operating_hours / 1.0e6
        annual_steam_cost = steam_gj_yr * steam_price_usd_per_gj
        annual_cooling_cost = cooling_gj_yr * cooling_price_usd_per_gj
        annual_opex = annual_steam_cost + annual_cooling_cost

        annual_carbon = steam_gj_yr * 0.055 + cooling_gj_yr * 0.005
        annual_tax = annual_carbon * carbon_tax_usd_per_tonne

        tac = tot_capex * crf + annual_opex + annual_tax

        return SequenceCandidate(
            sequence_name="Direct Sequence (A/BC → B/C)",
            columns_count=2,
            total_stages=n_stages_1 + n_stages_2,
            total_reboiler_duty_kW=tot_q_reb,
            total_condenser_duty_kW=tot_q_cond,
            column_diameters_m=[col1["D_col_m"], col2["D_col_m"]],
            column_heights_m=[col1["H_col_m"], col2["H_col_m"]],
            reboiler_duties_kW=[col1["Q_reb_kW"], col2["Q_reb_kW"]],
            condenser_duties_kW=[col1["Q_cond_kW"], col2["Q_cond_kW"]],
            reflux_ratios=[r_1, r_2],
            capex_usd=tot_capex,
            annual_utility_opex_usd=annual_opex,
            annual_carbon_emissions_tonnes=annual_carbon,
            annual_carbon_tax_usd=annual_tax,
            total_annualized_cost_tac_usd=tac,
            steam_consumption_gj_yr=steam_gj_yr,
            cooling_water_gj_yr=cooling_gj_yr,
            description="Conventional direct sequence taking lightest component A overhead first, followed by separation of B and C in Column 2.",
            details={"col1": col1, "col2": col2}
        )

    @classmethod
    def evaluate_indirect_sequence(cls, F_mol_s: float, z: List[float], alphas: List[float],
                                   steam_price_usd_per_gj: float = 7.50,
                                   cooling_price_usd_per_gj: float = 0.354,
                                   electricity_price_usd_per_kwh: float = 0.085,
                                   carbon_tax_usd_per_tonne: float = 50.0,
                                   crf: float = 0.16275,
                                   operating_hours: float = 8000.0,
                                   delta_h_vap_kj_mol: float = 38.0,
                                   reflux_factor: float = 1.30) -> SequenceCandidate:
        """
        Evaluates Indirect Sequence:
        Column 1: Splits A+B (distillate) from C (bottoms). LK = B, HK = C.
        Column 2: Splits A (distillate) from B (bottoms). LK = A, HK = B.
        """
        _, r_min_1 = cls.solve_underwood(alphas, z, q=1.0, lk_idx=1, hk_idx=2)
        r_1 = max(0.5, reflux_factor * r_min_1)
        alpha_bc = max(1.05, alphas[1] / alphas[2])
        n_min_1 = np.log((0.99 * 0.99) / (0.01 * 0.01)) / np.log(alpha_bc)
        n_stages_1 = cls.calculate_gilliland_stages(n_min_1, r_1, r_min_1)
        d_mol_s_1 = max(1.0, F_mol_s * (z[0] + z[1]))

        col1 = cls.size_shortcut_column(d_mol_s_1, r_1, n_stages_1, delta_h_vap_kj_mol=delta_h_vap_kj_mol)

        z_2 = [z[0] / (z[0] + z[1]), z[1] / (z[0] + z[1]), 0.0]
        _, r_min_2 = cls.solve_underwood(alphas, z_2, q=1.0, lk_idx=0, hk_idx=1)
        r_2 = max(0.5, reflux_factor * r_min_2)
        alpha_ab = max(1.05, alphas[0] / alphas[1])
        n_min_2 = np.log((0.99 * 0.99) / (0.01 * 0.01)) / np.log(alpha_ab)
        n_stages_2 = cls.calculate_gilliland_stages(n_min_2, r_2, r_min_2)
        d_mol_s_2 = max(1.0, F_mol_s * z[0])

        col2 = cls.size_shortcut_column(d_mol_s_2, r_2, n_stages_2, delta_h_vap_kj_mol=delta_h_vap_kj_mol)

        tot_q_reb = col1["Q_reb_kW"] + col2["Q_reb_kW"]
        tot_q_cond = col1["Q_cond_kW"] + col2["Q_cond_kW"]
        tot_capex = col1["total_C_BM"] + col2["total_C_BM"]

        steam_gj_yr = tot_q_reb * 3600.0 * operating_hours / 1.0e6
        cooling_gj_yr = tot_q_cond * 3600.0 * operating_hours / 1.0e6
        annual_steam_cost = steam_gj_yr * steam_price_usd_per_gj
        annual_cooling_cost = cooling_gj_yr * cooling_price_usd_per_gj
        annual_opex = annual_steam_cost + annual_cooling_cost

        annual_carbon = steam_gj_yr * 0.055 + cooling_gj_yr * 0.005
        annual_tax = annual_carbon * carbon_tax_usd_per_tonne

        tac = tot_capex * crf + annual_opex + annual_tax

        return SequenceCandidate(
            sequence_name="Indirect Sequence (AB/C → A/B)",
            columns_count=2,
            total_stages=n_stages_1 + n_stages_2,
            total_reboiler_duty_kW=tot_q_reb,
            total_condenser_duty_kW=tot_q_cond,
            column_diameters_m=[col1["D_col_m"], col2["D_col_m"]],
            column_heights_m=[col1["H_col_m"], col2["H_col_m"]],
            reboiler_duties_kW=[col1["Q_reb_kW"], col2["Q_reb_kW"]],
            condenser_duties_kW=[col1["Q_cond_kW"], col2["Q_cond_kW"]],
            reflux_ratios=[r_1, r_2],
            capex_usd=tot_capex,
            annual_utility_opex_usd=annual_opex,
            annual_carbon_emissions_tonnes=annual_carbon,
            annual_carbon_tax_usd=annual_tax,
            total_annualized_cost_tac_usd=tac,
            steam_consumption_gj_yr=steam_gj_yr,
            cooling_water_gj_yr=cooling_gj_yr,
            description="Conventional indirect sequence separating heaviest component C first, followed by separation of A and B in Column 2.",
            details={"col1": col1, "col2": col2}
        )

    @classmethod
    def evaluate_distributed_sequence(cls, direct_cand: SequenceCandidate,
                                      indirect_cand: SequenceCandidate,
                                      steam_price_usd_per_gj: float = 7.50,
                                      cooling_price_usd_per_gj: float = 0.354,
                                      carbon_tax_usd_per_tonne: float = 50.0,
                                      crf: float = 0.16275,
                                      operating_hours: float = 8000.0) -> SequenceCandidate:
        """
        Evaluates Distributed / Prefractionator Sequence.
        Benchmark: 12% utility reduction vs best conventional sequence, with 5% higher CAPEX.
        """
        best_conv = direct_cand if direct_cand.total_reboiler_duty_kW < indirect_cand.total_reboiler_duty_kW else indirect_cand
        tot_q_reb = best_conv.total_reboiler_duty_kW * 0.88
        tot_q_cond = best_conv.total_condenser_duty_kW * 0.88
        tot_capex = best_conv.capex_usd * 1.05
        tot_stages = int(round(best_conv.total_stages * 1.10))

        steam_gj_yr = tot_q_reb * 3600.0 * operating_hours / 1.0e6
        cooling_gj_yr = tot_q_cond * 3600.0 * operating_hours / 1.0e6
        annual_steam_cost = steam_gj_yr * steam_price_usd_per_gj
        annual_cooling_cost = cooling_gj_yr * cooling_price_usd_per_gj
        annual_opex = annual_steam_cost + annual_cooling_cost

        annual_carbon = steam_gj_yr * 0.055 + cooling_gj_yr * 0.005
        annual_tax = annual_carbon * carbon_tax_usd_per_tonne

        tac = tot_capex * crf + annual_opex + annual_tax

        return SequenceCandidate(
            sequence_name="Distributed Prefractionator Sequence",
            columns_count=2,
            total_stages=tot_stages,
            total_reboiler_duty_kW=tot_q_reb,
            total_condenser_duty_kW=tot_q_cond,
            column_diameters_m=best_conv.column_diameters_m,
            column_heights_m=[h * 1.05 for h in best_conv.column_heights_m],
            reboiler_duties_kW=[q * 0.88 for q in best_conv.reboiler_duties_kW],
            condenser_duties_kW=[q * 0.88 for q in best_conv.condenser_duties_kW],
            reflux_ratios=best_conv.reflux_ratios,
            capex_usd=tot_capex,
            annual_utility_opex_usd=annual_opex,
            annual_carbon_emissions_tonnes=annual_carbon,
            annual_carbon_tax_usd=annual_tax,
            total_annualized_cost_tac_usd=tac,
            steam_consumption_gj_yr=steam_gj_yr,
            cooling_water_gj_yr=cooling_gj_yr,
            description="Distributed sequence utilizing a preliminary prefractionator column to avoid intermediate component remixing.",
            details={"benchmark_baseline": best_conv.sequence_name, "energy_savings_pct": 12.0}
        )

    @classmethod
    def evaluate_dividing_wall_column(cls, direct_cand: SequenceCandidate,
                                      indirect_cand: SequenceCandidate,
                                      steam_price_usd_per_gj: float = 7.50,
                                      cooling_price_usd_per_gj: float = 0.354,
                                      carbon_tax_usd_per_tonne: float = 50.0,
                                      crf: float = 0.16275,
                                      operating_hours: float = 8000.0) -> SequenceCandidate:
        """
        Evaluates Dividing-Wall Column (DWC / Petlyuk):
        Thermodynamic benchmark: 30% reduction in thermal duties and 30% reduction in capital cost.
        """
        best_conv = direct_cand if direct_cand.total_reboiler_duty_kW < indirect_cand.total_reboiler_duty_kW else indirect_cand
        tot_q_reb = best_conv.total_reboiler_duty_kW * 0.70
        tot_q_cond = best_conv.total_condenser_duty_kW * 0.70
        tot_capex = best_conv.capex_usd * 0.70

        max_stages_single = max(best_conv.total_stages // 2, 10)
        tot_stages = int(round(max_stages_single * 1.35))
        d_dwc = max(best_conv.column_diameters_m) * 1.15
        h_dwc = tot_stages * 0.6 + 4.0

        steam_gj_yr = tot_q_reb * 3600.0 * operating_hours / 1.0e6
        cooling_gj_yr = tot_q_cond * 3600.0 * operating_hours / 1.0e6
        annual_steam_cost = steam_gj_yr * steam_price_usd_per_gj
        annual_cooling_cost = cooling_gj_yr * cooling_price_usd_per_gj
        annual_opex = annual_steam_cost + annual_cooling_cost

        annual_carbon = steam_gj_yr * 0.055 + cooling_gj_yr * 0.005
        annual_tax = annual_carbon * carbon_tax_usd_per_tonne

        tac = tot_capex * crf + annual_opex + annual_tax

        return SequenceCandidate(
            sequence_name="Dividing-Wall Column (DWC Petlyuk)",
            columns_count=1,
            total_stages=tot_stages,
            total_reboiler_duty_kW=tot_q_reb,
            total_condenser_duty_kW=tot_q_cond,
            column_diameters_m=[d_dwc],
            column_heights_m=[h_dwc],
            reboiler_duties_kW=[tot_q_reb],
            condenser_duties_kW=[tot_q_cond],
            reflux_ratios=[1.25],
            capex_usd=tot_capex,
            annual_utility_opex_usd=annual_opex,
            annual_carbon_emissions_tonnes=annual_carbon,
            annual_carbon_tax_usd=annual_tax,
            total_annualized_cost_tac_usd=tac,
            steam_consumption_gj_yr=steam_gj_yr,
            cooling_water_gj_yr=cooling_gj_yr,
            description="Intensified Dividing-Wall Column (Petlyuk configuration) with internal vertical partition, eliminating remixing in a single shell.",
            details={
                "benchmark_baseline": best_conv.sequence_name,
                "energy_savings_pct": 30.0,
                "capex_savings_pct": 30.0,
                "reboiler_duty_saved_kW": best_conv.total_reboiler_duty_kW - tot_q_reb,
                "capex_saved_usd": best_conv.capex_usd - tot_capex
            }
        )

    @classmethod
    def synthesize_all_sequences(cls, feed_flow_mol_s: float,
                                 feed_fractions: List[float],
                                 components: List[str],
                                 species_map: Dict[str, Any],
                                 steam_price_usd_per_gj: float = 7.50,
                                 cooling_price_usd_per_gj: float = 0.354,
                                 electricity_price_usd_per_kwh: float = 0.085,
                                 carbon_tax_usd_per_tonne: float = 50.0,
                                 crf: float = 0.16275,
                                 operating_hours: float = 8000.0,
                                 delta_h_vap_kj_mol: float = 38.0) -> Dict[str, Any]:
        """
        Synthesizes, sizes, and ranks all 4 separation sequences for a ternary mixture.
        """
        tot_z = sum(feed_fractions[:3])
        z_norm = [f / tot_z for f in feed_fractions[:3]]

        sorted_comps, alphas, alpha_dict = cls.calculate_relative_volatilities(components[:3], species_map)

        direct_cand = cls.evaluate_direct_sequence(
            feed_flow_mol_s, z_norm, alphas,
            steam_price_usd_per_gj=steam_price_usd_per_gj,
            cooling_price_usd_per_gj=cooling_price_usd_per_gj,
            electricity_price_usd_per_kwh=electricity_price_usd_per_kwh,
            carbon_tax_usd_per_tonne=carbon_tax_usd_per_tonne,
            crf=crf, operating_hours=operating_hours,
            delta_h_vap_kj_mol=delta_h_vap_kj_mol
        )

        indirect_cand = cls.evaluate_indirect_sequence(
            feed_flow_mol_s, z_norm, alphas,
            steam_price_usd_per_gj=steam_price_usd_per_gj,
            cooling_price_usd_per_gj=cooling_price_usd_per_gj,
            electricity_price_usd_per_kwh=electricity_price_usd_per_kwh,
            carbon_tax_usd_per_tonne=carbon_tax_usd_per_tonne,
            crf=crf, operating_hours=operating_hours,
            delta_h_vap_kj_mol=delta_h_vap_kj_mol
        )

        distributed_cand = cls.evaluate_distributed_sequence(
            direct_cand, indirect_cand,
            steam_price_usd_per_gj=steam_price_usd_per_gj,
            cooling_price_usd_per_gj=cooling_price_usd_per_gj,
            carbon_tax_usd_per_tonne=carbon_tax_usd_per_tonne,
            crf=crf, operating_hours=operating_hours
        )

        dwc_cand = cls.evaluate_dividing_wall_column(
            direct_cand, indirect_cand,
            steam_price_usd_per_gj=steam_price_usd_per_gj,
            cooling_price_usd_per_gj=cooling_price_usd_per_gj,
            carbon_tax_usd_per_tonne=carbon_tax_usd_per_tonne,
            crf=crf, operating_hours=operating_hours
        )

        candidates = [direct_cand, indirect_cand, distributed_cand, dwc_cand]
        candidates_sorted_tac = sorted(candidates, key=lambda c: c.total_annualized_cost_tac_usd)
        optimal_sequence = candidates_sorted_tac[0]

        baseline_conv = direct_cand if direct_cand.total_annualized_cost_tac_usd < indirect_cand.total_annualized_cost_tac_usd else indirect_cand

        dwc_energy_savings_kw = baseline_conv.total_reboiler_duty_kW - dwc_cand.total_reboiler_duty_kW
        dwc_energy_savings_pct = (dwc_energy_savings_kw / baseline_conv.total_reboiler_duty_kW) * 100.0
        dwc_capex_savings_usd = baseline_conv.capex_usd - dwc_cand.capex_usd
        dwc_capex_savings_pct = (dwc_capex_savings_usd / baseline_conv.capex_usd) * 100.0
        dwc_carbon_abatement_tonnes = baseline_conv.annual_carbon_emissions_tonnes - dwc_cand.annual_carbon_emissions_tonnes

        return {
            "candidates": [c.to_dict() for c in candidates],
            "candidate_objects": candidates,
            "optimal_sequence": optimal_sequence.to_dict(),
            "optimal_candidate_name": optimal_sequence.sequence_name,
            "sorted_by_tac": [c.sequence_name for c in candidates_sorted_tac],
            "mixture_info": {
                "components": sorted_comps,
                "feed_fractions": z_norm,
                "relative_volatilities": alpha_dict,
                "feed_flow_mol_s": feed_flow_mol_s
            },
            "dwc_benchmarks": {
                "baseline_conventional_name": baseline_conv.sequence_name,
                "energy_savings_kW": round(dwc_energy_savings_kw, 2),
                "energy_savings_pct": round(dwc_energy_savings_pct, 1),
                "capex_savings_usd": round(dwc_capex_savings_usd, 2),
                "capex_savings_pct": round(dwc_capex_savings_pct, 1),
                "carbon_abatement_tonnes_yr": round(dwc_carbon_abatement_tonnes, 2)
            }
        }
