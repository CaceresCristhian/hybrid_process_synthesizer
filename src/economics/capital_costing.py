"""
Plant-wide Capital Expenditure (CAPEX) Aggregator.
Computes Total Bare Module Cost (C_BM), Total Module Cost (C_TM),
Grassroots Capital Cost (C_GR), Fixed Capital Investment (FCI),
Working Capital (WC), and Total Capital Investment (TCI).
"""

from typing import Dict, List, Any
from src.economics.cost_correlations import DEFAULT_CEPCI

class CapitalCosting:
    """Aggregates flowsheet equipment costs into plant-level capital expenditure structure."""

    @classmethod
    def calculate_capex(cls, equipment_cost_list: List[Dict[str, Any]],
                        plant_mode: str = "Grassroots Plant",
                        contingency_factor: float = 0.15,
                        contractor_fee_factor: float = 0.03,
                        working_capital_fraction: float = 0.15) -> Dict[str, Any]:
        """
        Aggregates individual equipment costs into full CAPEX breakdown.
        
        Args:
            equipment_cost_list: List of dicts returned by EquipmentCosting.cost_unit
            plant_mode: 'Grassroots Plant' (greenfield) or 'Battery-Limits Expansion'
            contingency_factor: Project contingency fraction (default: 0.15 = 15%)
            contractor_fee_factor: Contractor engineering fee fraction (default: 0.03 = 3%)
            working_capital_fraction: Working capital fraction of FCI (default: 0.15 = 15%)
        """
        total_cp0 = sum(item.get("Cp0", 0.0) for item in equipment_cost_list)
        total_cp = sum(item.get("Cp", 0.0) for item in equipment_cost_list)
        total_c_bm = sum(item.get("C_BM", 0.0) for item in equipment_cost_list)

        # 1. Total Module Cost (C_TM) = C_BM * (1 + contingency + contractor_fee)
        module_multiplier = 1.0 + contingency_factor + contractor_fee_factor
        c_tm = total_c_bm * module_multiplier

        # 2. Grassroots Capital Cost (C_GR) = C_TM + 0.50 * sum(Cp0_inflated)
        # 50% of purchased equipment cost covers site development, civil infrastructure, and auxiliary buildings
        site_development_cost = 0.50 * total_cp
        c_gr = c_tm + site_development_cost

        # 3. Fixed Capital Investment (FCI)
        if plant_mode == "Grassroots Plant":
            fci = c_gr
        else: # Battery-Limits Expansion
            fci = c_tm

        # 4. Working Capital (WC) and Total Capital Investment (TCI)
        working_capital = fci * working_capital_fraction
        tci = fci + working_capital

        return {
            "total_purchased_cost_base_Cp0": round(total_cp0, 2),
            "total_purchased_cost_Cp": round(total_cp, 2),
            "total_bare_module_cost_C_BM": round(total_c_bm, 2),
            "contingency_fee": round(total_c_bm * contingency_factor, 2),
            "contractor_fee": round(total_c_bm * contractor_fee_factor, 2),
            "total_module_cost_C_TM": round(c_tm, 2),
            "site_development_cost": round(site_development_cost, 2),
            "grassroots_capital_cost_C_GR": round(c_gr, 2),
            "plant_mode": plant_mode,
            "fixed_capital_investment_FCI": round(fci, 2),
            "working_capital_WC": round(working_capital, 2),
            "total_capital_investment_TCI": round(tci, 2)
        }
