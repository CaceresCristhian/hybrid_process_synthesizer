"""
Multi-Objective Pareto Frontier Generator & Trade-Off Analyzer.
Optimizes process configurations across competing objectives:
Objective 1: min CAPEX (Capital Expenditure, USD)
Objective 2: min Annual GHG Emissions (Scope 2 Carbon Footprint, tonnes CO2/yr)
Computes non-dominated sorting, marginal carbon abatement cost (MAC),
and trade-off curve fitting.
"""

from typing import Dict, List, Any, Optional
import numpy as np
from src.optimization.sequence_synthesizer import SequenceCandidate, SeparationSequencer


class ParetoOptimizer:
    """Computes Pareto-optimal design frontiers and marginal abatement metrics."""

    @classmethod
    def generate_pareto_frontier(cls, candidates: List[SequenceCandidate],
                                 synthesis_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extracts non-dominated solutions across CAPEX vs Annual Carbon Emissions.
        Optionally evaluates reflux ratio variations (R/R_min in [1.05, 1.10, 1.20, 1.30, 1.50, 1.80])
        to populate a dense trade-off surface.
        """
        all_designs = []

        if synthesis_params:
            feed_flow = synthesis_params.get("feed_flow_mol_s", 100.0)
            z = synthesis_params.get("feed_fractions", [0.35, 0.40, 0.25])
            alphas = synthesis_params.get("alphas", [7.5, 3.0, 1.0])
            st_price = synthesis_params.get("steam_price_usd_per_gj", 7.50)
            cl_price = synthesis_params.get("cooling_price_usd_per_gj", 0.354)
            c_tax = synthesis_params.get("carbon_tax_usd_per_tonne", 50.0)
            crf = synthesis_params.get("crf", 0.16275)

            for rf in [1.05, 1.10, 1.20, 1.30, 1.50, 1.80]:
                d_cand = SeparationSequencer.evaluate_direct_sequence(
                    feed_flow, z, alphas, steam_price_usd_per_gj=st_price,
                    cooling_price_usd_per_gj=cl_price, carbon_tax_usd_per_tonne=c_tax,
                    crf=crf, reflux_factor=rf
                )
                i_cand = SeparationSequencer.evaluate_indirect_sequence(
                    feed_flow, z, alphas, steam_price_usd_per_gj=st_price,
                    cooling_price_usd_per_gj=cl_price, carbon_tax_usd_per_tonne=c_tax,
                    crf=crf, reflux_factor=rf
                )
                dwc_cand = SeparationSequencer.evaluate_dividing_wall_column(
                    d_cand, i_cand, steam_price_usd_per_gj=st_price,
                    cooling_price_usd_per_gj=cl_price, carbon_tax_usd_per_tonne=c_tax,
                    crf=crf
                )
                dist_cand = SeparationSequencer.evaluate_distributed_sequence(
                    d_cand, i_cand, steam_price_usd_per_gj=st_price,
                    cooling_price_usd_per_gj=cl_price, carbon_tax_usd_per_tonne=c_tax,
                    crf=crf
                )
                all_designs.extend([
                    {"design_name": f"Direct (R={rf:.2f}*Rmin)", "cand": d_cand, "seq_type": "Direct"},
                    {"design_name": f"Indirect (R={rf:.2f}*Rmin)", "cand": i_cand, "seq_type": "Indirect"},
                    {"design_name": f"Distributed (R={rf:.2f}*Rmin)", "cand": dist_cand, "seq_type": "Distributed"},
                    {"design_name": f"DWC Petlyuk (R={rf:.2f}*Rmin)", "cand": dwc_cand, "seq_type": "DWC"}
                ])
        else:
            for c in candidates:
                all_designs.append({
                    "design_name": c.sequence_name,
                    "cand": c,
                    "seq_type": c.sequence_name
                })

        # Non-dominated sorting (Min CAPEX, Min Carbon Emissions)
        pareto_designs = []
        for i, d in enumerate(all_designs):
            cand = d["cand"]
            c_p = cand.capex_usd
            e_p = cand.annual_carbon_emissions_tonnes

            is_dominated = False
            for j, other in enumerate(all_designs):
                if i == j:
                    continue
                c_o = other["cand"].capex_usd
                e_o = other["cand"].annual_carbon_emissions_tonnes
                # Strictly dominates if <= in both and < in at least one
                if (c_o <= c_p and e_o <= e_p) and (c_o < c_p or e_o < e_p):
                    is_dominated = True
                    break
            if not is_dominated:
                pareto_designs.append(d)

        # Sort Pareto frontier by ascending CAPEX (descending carbon emissions)
        pareto_designs.sort(key=lambda x: x["cand"].capex_usd)

        # Calculate Marginal Abatement Cost (MAC) between adjacent points
        pareto_points = []
        for idx, d in enumerate(pareto_designs):
            cand = d["cand"]
            mac = 0.0
            if idx > 0:
                prev_cand = pareto_designs[idx - 1]["cand"]
                delta_capex = cand.capex_usd - prev_cand.capex_usd
                delta_emissions = prev_cand.annual_carbon_emissions_tonnes - cand.annual_carbon_emissions_tonnes
                if delta_emissions > 1e-3:
                    mac = round(delta_capex / delta_emissions, 2)
                else:
                    mac = 0.0

            pareto_points.append({
                "design_name": d["design_name"],
                "seq_type": d["seq_type"],
                "capex_usd": round(cand.capex_usd, 2),
                "annual_carbon_emissions_tonnes": round(cand.annual_carbon_emissions_tonnes, 2),
                "annual_utility_opex_usd": round(cand.annual_utility_opex_usd, 2),
                "total_annualized_cost_tac_usd": round(cand.total_annualized_cost_tac_usd, 2),
                "marginal_abatement_cost_usd_per_tonne": mac
            })

        all_points = [{
            "design_name": d["design_name"],
            "seq_type": d["seq_type"],
            "capex_usd": round(d["cand"].capex_usd, 2),
            "annual_carbon_emissions_tonnes": round(d["cand"].annual_carbon_emissions_tonnes, 2),
            "annual_utility_opex_usd": round(d["cand"].annual_utility_opex_usd, 2),
            "total_annualized_cost_tac_usd": round(d["cand"].total_annualized_cost_tac_usd, 2)
        } for d in all_designs]

        return {
            "pareto_points": pareto_points,
            "all_points": all_points,
            "pareto_count": len(pareto_points),
            "total_designs_evaluated": len(all_designs)
        }
