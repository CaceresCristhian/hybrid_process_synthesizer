"""
Project Profitability and Financial Analysis Engine.
Computes Cost of Manufacturing (COM), EBITDA, Net Cash Flow,
Payback Period, Return on Investment (ROI), and Net Present Value (NPV).
"""

from typing import Dict, List, Any, Optional
import numpy as np

# Typical benchmark market prices (USD per kg)
DEFAULT_CHEMICAL_PRICES_USD_KG = {
    "ethanol": 0.95,
    "ammonia": 0.65,
    "water": 0.002,
    "octane": 1.15,
    "methanol": 0.45,
    "acetone": 1.10,
    "hydrogen": 4.50,
    "co2": 0.05,
    "glucose": 0.50,
    "general": 0.80
}

class EconomicAnalyzer:
    """Calculates project profitability metrics, DCF, and multi-year investment returns."""

    @classmethod
    def analyze_profitability(cls, capex_dict: Dict[str, Any],
                              utility_opex_dict: Dict[str, Any],
                              streams_list: list,
                              species_map: dict,
                              project_lifetime_years: int = 15,
                              discount_rate: float = 0.10,
                              tax_rate: float = 0.25,
                              raw_materials_cost_annual: float = 0.0,
                              product_revenue_annual: Optional[float] = None) -> Dict[str, Any]:
        """
        Runs comprehensive financial profitability analysis.
        """
        fci = capex_dict.get("fixed_capital_investment_FCI", 1000000.0)
        tci = capex_dict.get("total_capital_investment_TCI", 1150000.0)
        utility_opex = utility_opex_dict.get("total_annual_utility_opex_usd", 50000.0)
        op_hours = utility_opex_dict.get("operating_hours_per_year", 8000.0)

        # 1. Estimate Product Revenue if not directly provided
        if product_revenue_annual is None:
            revenue = 0.0
            for st in streams_list:
                if not st.downstream_units and st.F is not None and st.F > 0:
                    m_flow_kg_h = st.get_mass_flow(species_map)
                    for sp_id, mole_frac in (st.z or {}).items():
                        if mole_frac > 0.05:
                            unit_price = DEFAULT_CHEMICAL_PRICES_USD_KG.get(sp_id.lower(), DEFAULT_CHEMICAL_PRICES_USD_KG["general"])
                            sp_kg_h = m_flow_kg_h * mole_frac
                            revenue += sp_kg_h * unit_price * op_hours
            annual_revenue = max(revenue, utility_opex * 2.5 + fci * 0.25)
        else:
            annual_revenue = product_revenue_annual

        # 2. Estimate Raw Materials Cost if not directly provided
        if raw_materials_cost_annual <= 0.0:
            raw_mat_cost = 0.0
            for st in streams_list:
                if st.upstream_unit is None and st.F is not None and st.F > 0:
                    m_flow_kg_h = st.get_mass_flow(species_map)
                    for sp_id, mole_frac in (st.z or {}).items():
                        if mole_frac > 0.05:
                            unit_price = DEFAULT_CHEMICAL_PRICES_USD_KG.get(sp_id.lower(), 0.30) * 0.5
                            sp_kg_h = m_flow_kg_h * mole_frac
                            raw_mat_cost += sp_kg_h * unit_price * op_hours
            raw_materials_cost_annual = max(raw_mat_cost, utility_opex * 0.8)

        # 3. Cost of Manufacturing (COM) without depreciation (Turton Eq)
        # COM_d = 0.18*FCI + 1.23*(Utility_OPEX + Raw_Materials)
        # 0.18*FCI includes maintenance (6%), operating labor (4%), supervision (2%), plant overhead (3%), insurance/taxes (3%)
        com_d = 0.18 * fci + 1.23 * (utility_opex + raw_materials_cost_annual)

        # 4. Straight-line Depreciation
        depreciation_annual = fci / project_lifetime_years

        # 5. Earnings & Cash Flow
        gross_profit = annual_revenue - com_d
        ebit = gross_profit - depreciation_annual
        taxes = max(0.0, ebit * tax_rate)
        net_profit = ebit - taxes
        net_cash_flow = gross_profit - taxes  # Net profit + depreciation

        # 6. Profitability Metrics
        payback_years = round(fci / max(net_cash_flow, 1.0), 2) if net_cash_flow > 0 else 99.0
        roi_pct = round((net_profit / max(fci, 1.0)) * 100.0, 2)

        # 7. Multi-Year Discounted Cash Flow (DCF) & NPV
        years = list(range(0, project_lifetime_years + 1))
        dcf_profile = []
        cum_dcf = -tci
        cum_cash_flow_profile = [cum_dcf]

        for yr in range(1, project_lifetime_years + 1):
            discount_factor = 1.0 / ((1.0 + discount_rate) ** yr)
            # In final year, recover working capital
            year_cash_flow = net_cash_flow + (capex_dict.get("working_capital_WC", 0.0) if yr == project_lifetime_years else 0.0)
            dcf = year_cash_flow * discount_factor
            dcf_profile.append(round(dcf, 2))
            cum_dcf += dcf
            cum_cash_flow_profile.append(round(cum_dcf, 2))

        npv = round(cum_dcf, 2)

        return {
            "annual_revenue_usd": round(annual_revenue, 2),
            "raw_materials_cost_annual_usd": round(raw_materials_cost_annual, 2),
            "cost_of_manufacturing_COM_usd": round(com_d, 2),
            "gross_profit_usd": round(gross_profit, 2),
            "depreciation_annual_usd": round(depreciation_annual, 2),
            "taxes_annual_usd": round(taxes, 2),
            "net_profit_annual_usd": round(net_profit, 2),
            "net_annual_cash_flow_usd": round(net_cash_flow, 2),
            "payback_period_years": payback_years,
            "return_on_investment_ROI_pct": roi_pct,
            "project_lifetime_years": project_lifetime_years,
            "discount_rate_pct": discount_rate * 100.0,
            "net_present_value_NPV_usd": npv,
            "cash_flow_years": years,
            "cumulative_cash_flow": cum_cash_flow_profile
        }
