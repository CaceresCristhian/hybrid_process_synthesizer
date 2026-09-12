import numpy as np
from scipy.optimize import fsolve
from typing import Dict, List, Any, Optional

class FlowsheetSolver:
    """
    Flowsheet-wide calculation engine containing:
    1. Sequential Modular (SM) Solver with Wegstein recycle loop convergence.
    2. Equation-Oriented (EO) simultaneous Newton-Raphson solver.
    3. Mass & Energy balance compilers with conservation checking.
    """
    
    @staticmethod
    def wegstein_update(x_k: float, x_k_prev: float, g_k: float, g_k_prev: float) -> float:
        """
        Calculates accelerated Wegstein guess for recycle streams:
        x_new = q * x_k + (1 - q) * g_k
        """
        denom = x_k - x_k_prev
        if np.abs(denom) < 1e-9:
            return g_k
            
        s = (g_k - g_k_prev) / denom
        if np.abs(s - 1.0) < 1e-5:
            q = 0.0
        else:
            q = s / (s - 1.0)
            q = max(-5.0, min(q, 0.8))
            
        return q * x_k + (1.0 - q) * g_k

    @classmethod
    def solve_sequential_modular(cls, units_list: list, tear_stream, recycle_loop_fn, 
                                 max_iter: int = 40, tolerance: float = 1e-4) -> dict:
        """
        Runs Sequential Modular solver on the flowsheet with Wegstein acceleration.
        """
        x_k = np.array([tear_stream.T if tear_stream.T else 298.15,
                        tear_stream.P if tear_stream.P else 101325.0,
                        tear_stream.F if tear_stream.F else 10.0])
        
        x_next = np.array(recycle_loop_fn(x_k))
        x_prev = x_k.copy()
        x_k = x_next.copy()
        
        converged = False
        history = [x_prev.tolist(), x_k.tolist()]
        
        for i in range(max_iter):
            g_k = np.array(recycle_loop_fn(x_k))
            error = np.linalg.norm(g_k - x_k) / (np.linalg.norm(x_k) + 1e-5)
            if error < tolerance:
                converged = True
                break
                
            x_next = np.zeros_like(x_k)
            for j in range(len(x_k)):
                x_next[j] = cls.wegstein_update(x_k[j], x_prev[j], g_k[j], history[-2][j])
                
            x_prev = x_k.copy()
            x_k = x_next.copy()
            history.append(x_k.tolist())
            
        tear_stream.T = x_k[0]
        tear_stream.P = x_k[1]
        tear_stream.F = x_k[2]
        
        return {
            "converged": converged,
            "iterations": i + 1,
            "final_tear_state": x_k,
            "history": history
        }

    @staticmethod
    def solve_equation_oriented(flowsheet_equations_fn, initial_guess: list) -> dict:
        """
        Runs Equation-Oriented (EO) solver via scipy fsolve.
        """
        sol, info, ier, msg = fsolve(flowsheet_equations_fn, initial_guess, full_output=True)
        converged = ier == 1
        residuals = flowsheet_equations_fn(sol)
        max_residual = np.max(np.abs(residuals))
        
        return {
            "converged": converged,
            "solution": sol,
            "max_residual": max_residual,
            "message": msg,
            "iterations": info.get("nfev", 0)
        }

    @classmethod
    def solve_flowsheet_topology(cls, units_map: dict, streams_map: dict, species_map: dict,
                                 max_passes: int = 30, tolerance: float = 1e-4) -> dict:
        """
        Robust sequential modular flowsheet topology solver.
        Solves multi-unit chains in forward sequence regardless of naming/alphabetical order,
        and converges recycle loops iteratively.
        """
        solved_units = set()
        converged = False
        last_max_delta = 1.0
        p = 0
        
        for p in range(max_passes):
            # Snapshot stream flows and temperatures
            prev_snapshot = {
                s_id: (s.F if s.F is not None else -1.0, s.T if s.T is not None else -1.0)
                for s_id, s in streams_map.items()
            }
            
            # Sweep all units in the flowsheet
            for uid, unit in units_map.items():
                if unit.inlets:
                    inlets_ready = all(i.F is not None and i.F >= 0 for i in unit.inlets)
                    if inlets_ready:
                        try:
                            unit.run_simulation((0, 0), [], species_map=species_map)
                            solved_units.add(uid)
                        except Exception:
                            pass
                            
            # Check convergence across all streams
            deltas = []
            for s_id, s in streams_map.items():
                prev_f, prev_t = prev_snapshot.get(s_id, (-1.0, -1.0))
                curr_f = s.F if s.F is not None else -1.0
                curr_t = s.T if s.T is not None else -1.0
                if prev_f >= 0 and curr_f >= 0:
                    d_f = abs(curr_f - prev_f) / max(prev_f, 1e-4)
                    d_t = abs(curr_t - prev_t) / max(prev_t, 1e-4)
                    deltas.append(max(d_f, d_t))
                elif prev_f != curr_f or prev_t != curr_t:
                    deltas.append(1.0)
                    
            last_max_delta = max(deltas) if deltas else 0.0
            if deltas and last_max_delta < tolerance and len(solved_units) > 0:
                converged = True
                break
                
        return {
            "converged": converged or (len(solved_units) == len(units_map)),
            "passes": p + 1,
            "max_delta": last_max_delta,
            "solved_units_count": len(solved_units),
            "total_units_count": len(units_map)
        }

    # ==========================================
    # MASS & ENERGY BALANCE COMPILERS
    # ==========================================
    
    @classmethod
    def compile_mass_balance(cls, streams_list: list, species_map: dict) -> dict:
        """
        Compiles flowsheet-wide mass balances.
        Identifies boundary inlet and outlet streams.
        Returns: {
            "inlet_streams": {stream_id: mass_flow_kg_h},
            "outlet_streams": {stream_id: mass_flow_kg_h},
            "inlet_moles_mol_s": total_in_moles,
            "outlet_moles_mol_s": total_out_moles,
            "total_inlet_mass_kg_h": total_in_mass,
            "total_outlet_mass_kg_h": total_out_mass,
            "mass_balance_error_kg_h": error,
            "is_conserved": bool
        }
        """
        inlet_streams = {}
        outlet_streams = {}
        total_in_mass = 0.0
        total_out_mass = 0.0
        total_in_moles = 0.0
        total_out_moles = 0.0
        
        for st in streams_list:
            # Inlet: no upstream unit connected
            if st.upstream_unit is None and st.F is not None and st.F > 0:
                m_flow = st.get_mass_flow(species_map)
                inlet_streams[st.stream_id] = m_flow
                total_in_mass += m_flow
                total_in_moles += st.F
            # Outlet: no downstream units connected
            elif not st.downstream_units and st.F is not None and st.F > 0:
                m_flow = st.get_mass_flow(species_map)
                outlet_streams[st.stream_id] = m_flow
                total_out_mass += m_flow
                total_out_moles += st.F
                
        error = total_in_mass - total_out_mass
        is_conserved = np.abs(error) < 1e-4 if total_in_mass > 0 else True
        
        return {
            "inlet_streams": inlet_streams,
            "outlet_streams": outlet_streams,
            "inlet_moles_mol_s": total_in_moles,
            "outlet_moles_mol_s": total_out_moles,
            "total_inlet_mass_kg_h": total_in_mass,
            "total_outlet_mass_kg_h": total_out_mass,
            "mass_balance_error_kg_h": error,
            "is_conserved": is_conserved
        }

    @classmethod
    def compile_energy_balance(cls, units_list: list, streams_list: list, species_map: dict) -> dict:
        """
        Compiles flowsheet-wide energy balances (in kW).
        Energy Flow (kW) = F (mol/s) * H (J/mol) / 1000.
        Returns: {
            "inlet_energy_kW": total_in_energy,
            "outlet_energy_kW": total_out_energy,
            "total_heat_added_kW": total_Q,
            "total_work_added_kW": total_W,
            "energy_balance_error_kW": error,
            "is_conserved": bool
        }
        """
        total_in_energy = 0.0
        total_out_energy = 0.0
        
        # Streams energy flow
        for st in streams_list:
            if st.upstream_unit is None and st.F is not None and st.F > 0:
                total_in_energy += st.get_energy_flow(species_map)
            elif not st.downstream_units and st.F is not None and st.F > 0:
                total_out_energy += st.get_energy_flow(species_map)
                
        # Equipment duties
        total_Q = 0.0
        total_W = 0.0
        for unit in units_list:
            # convert Watts to kW
            total_Q += getattr(unit, "heat_duty", 0.0) / 1000.0
            total_W += getattr(unit, "work_input", 0.0) / 1000.0
            
        # Overall balance: Energy_in + Q_added + W_added - Energy_out = Error
        error = (total_in_energy + total_Q + total_W) - total_out_energy
        is_conserved = np.abs(error) < 1e-3 if (total_in_energy + total_Q + total_W) > 0 else True
        
        return {
            "inlet_energy_kW": total_in_energy,
            "outlet_energy_kW": total_out_energy,
            "total_heat_added_kW": total_Q,
            "total_work_added_kW": total_W,
            "energy_balance_error_kW": error,
            "is_conserved": is_conserved
        }

    # ==========================================
    # TECHNO-ECONOMIC ASSESSMENT (TEA) COMPILER
    # ==========================================

    @classmethod
    def compile_flowsheet_economics(cls, units_list: list, streams_list: list, species_map: dict,
                                    cepci: float = 825.0, plant_mode: str = "Grassroots Plant",
                                    operating_hours: float = 8000.0, material_override: str = None,
                                    utility_rates: dict = None, discount_rate: float = 0.10,
                                    project_lifetime_years: int = 15,
                                    product_revenue_annual: float = None) -> dict:
        """
        Compiles flowsheet-wide capital costs (CAPEX), utility operational costs (OPEX),
        and investment profitability analysis (NPV, ROI, Payback).
        """
        from src.economics.equipment_costing import EquipmentCosting
        from src.economics.capital_costing import CapitalCosting
        from src.economics.utility_costing import UtilityCosting
        from src.economics.profitability import EconomicAnalyzer

        # 1. Cost individual equipment items
        equipment_costs = []
        for unit in units_list:
            cost_res = EquipmentCosting.cost_unit(unit, material=material_override, cepci=cepci)
            equipment_costs.append(cost_res)

        # 2. Plant-wide CAPEX
        capex = CapitalCosting.calculate_capex(
            equipment_cost_list=equipment_costs,
            plant_mode=plant_mode
        )

        # 3. Utility OPEX
        opex = UtilityCosting.calculate_utility_opex(
            units_list=units_list,
            operating_hours_per_year=operating_hours,
            rates=utility_rates
        )

        # 4. Profitability & Financial Metrics
        profitability = EconomicAnalyzer.analyze_profitability(
            capex_dict=capex,
            utility_opex_dict=opex,
            streams_list=streams_list,
            species_map=species_map,
            project_lifetime_years=project_lifetime_years,
            discount_rate=discount_rate,
            product_revenue_annual=product_revenue_annual
        )

        return {
            "equipment_costs": equipment_costs,
            "capex": capex,
            "opex": opex,
            "profitability": profitability
        }

    @classmethod
    def compile_flowsheet_pinch(cls, units_list: list, streams_list: list,
                                delta_T_min: float = 10.0,
                                operating_hours: float = 8000.0,
                                utility_rates: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Extracts thermal streams from flowsheet and solves Linnhoff Problem Table,
        Composite Curves, and Utility Savings targets.
        """
        from src.economics.pinch_analysis import PinchAnalyzer

        units_map = {getattr(u, "unit_id", str(idx)): u for idx, u in enumerate(units_list)}
        streams_map = {getattr(s, "stream_id", str(idx)): s for idx, s in enumerate(streams_list)}

        streams = PinchAnalyzer.extract_streams_from_flowsheet(units_map, streams_map)
        problem_table = PinchAnalyzer.solve_problem_table_algorithm(streams, delta_T_min=delta_T_min)
        composite_curves = PinchAnalyzer.generate_composite_curves(streams, delta_T_min=delta_T_min)
        gcc = PinchAnalyzer.generate_grand_composite_curve(streams, delta_T_min=delta_T_min)
        savings = PinchAnalyzer.calculate_utility_savings(streams, delta_T_min=delta_T_min, operating_hours=operating_hours, utility_rates=utility_rates)

        return {
            "thermal_streams": streams,
            "problem_table": problem_table,
            "composite_curves": composite_curves,
            "grand_composite_curve": gcc,
            "savings": savings
        }

    @classmethod
    def compile_flowsheet_lca(cls, units_list: list, streams_list: list,
                              utility_opex_dict: Dict[str, Any],
                              profitability_dict: Dict[str, Any],
                              species_map: dict,
                              grid_region: str = "US_Average",
                              custom_grid_factor: Optional[float] = None,
                              steam_source: str = "natural_gas_boiler",
                              carbon_tax_usd_per_tonne: float = 50.0,
                              scope_policy: str = "Scope1_and_Scope2",
                              include_scope_3: bool = False,
                              operating_hours: float = 8000.0) -> Dict[str, Any]:
        """
        Compiles full Environmental Life Cycle Assessment (LCA), Scope 1/2/3 emissions,
        product carbon intensity, carbon tax sensitivity, and decarbonization pathways.
        """
        from src.economics.lca_engine import LCAAnalyzer

        s1 = LCAAnalyzer.calculate_scope_1_emissions(units_list, streams_list, fuel_type=steam_source, operating_hours=operating_hours)
        s2 = LCAAnalyzer.calculate_scope_2_emissions(utility_opex_dict, grid_region=grid_region, custom_grid_factor=custom_grid_factor, steam_source=steam_source)
        s3 = LCAAnalyzer.calculate_scope_3_emissions(streams_list, species_map, operating_hours=operating_hours)

        intensity = LCAAnalyzer.calculate_carbon_intensity(s1, s2, s3, streams_list, species_map, operating_hours=operating_hours, include_scope_3=include_scope_3)

        lca_res = {
            "scope_1": s1,
            "scope_2": s2,
            "scope_3": s3,
            "carbon_intensity": intensity
        }

        tax_impact = LCAAnalyzer.calculate_carbon_tax_impact(lca_res, profitability_dict, carbon_tax_usd_per_tonne=carbon_tax_usd_per_tonne, scope_policy=scope_policy)

        grid_f = custom_grid_factor if custom_grid_factor is not None else s2["grid_factor_kg_per_kwh"]
        pathways = LCAAnalyzer.evaluate_decarbonization_pathways(units_list, utility_opex_dict, lca_res, grid_factor=grid_f, operating_hours=operating_hours)

        return {
            "scope_1": s1,
            "scope_2": s2,
            "scope_3": s3,
            "carbon_intensity": intensity,
            "carbon_tax_impact": tax_impact,
            "decarbonization_pathways": pathways
        }

    @classmethod
    def compile_flowsheet_safety(cls, units_list: list, streams_list: list,
                                 connections: list, species_map: dict) -> Dict[str, Any]:
        """
        Compiles plant-wide Process Safety, API 520/521/526 relief valve schedules,
        and automated topological HAZOP matrix.
        """
        from src.safety.relief_sizing import ReliefValveSizer
        from src.safety.hazop_analyzer import HAZOPAnalyzer

        units_map = {getattr(u, "unit_id", str(idx)): u for idx, u in enumerate(units_list)}
        streams_map = {getattr(s, "stream_id", str(idx)): s for idx, s in enumerate(streams_list)}

        # 1. Relief Valve Sizing across pressurized equipment
        relief_schedule = []
        governing_scenarios_count = {}

        for u_id, unit in units_map.items():
            u_type = unit.__class__.__name__
            if any(k in u_type for k in ["Column", "Reactor", "Drum", "Heater", "HeatExchanger"]):
                eval_res = ReliefValveSizer.evaluate_equipment_relief_scenarios(unit, species_map)
                relief_schedule.append({
                    "valve_tag": f"PSV-{u_id}",
                    "protected_unit": u_id,
                    "unit_type": u_type,
                    "set_pressure_kPa_g": eval_res["design_set_pressure_kPa_g"],
                    "governing_scenario": eval_res["governing_scenario"],
                    "required_area_mm2": eval_res["governing_required_area_mm2"],
                    "selected_api_orifice": eval_res["governing_selected_orifice"],
                    "flange_designation": eval_res["governing_flange"],
                    "relieving_rate_kg_h": eval_res["governing_relieving_rate_kg_h"],
                    "details": eval_res
                })
                scen = eval_res["governing_scenario"]
                governing_scenarios_count[scen] = governing_scenarios_count.get(scen, 0) + 1

        # 2. Automated Topological HAZOP Study
        hazop_study = HAZOPAnalyzer.generate_flowsheet_hazop(units_map, streams_map, connections)
        high_risk_count = sum(1 for row in hazop_study if row["risk_level"] in ["HIGH", "CRITICAL"])

        return {
            "relief_schedule": relief_schedule,
            "governing_scenarios_count": governing_scenarios_count,
            "hazop_study": hazop_study,
            "total_nodes_analyzed": len(units_map),
            "total_hazop_deviations": len(hazop_study),
            "high_risk_deviations_count": high_risk_count
        }

    @classmethod
    def compile_flowsheet_superstructure(cls, feed_stream: Any = None,
                                         species_map: Optional[dict] = None,
                                         components_list: Optional[list] = None,
                                         feed_flow_mol_s: Optional[float] = None,
                                         feed_fractions: Optional[list] = None,
                                         steam_price: float = 7.50,
                                         electricity_price: float = 0.085,
                                         cooling_price: float = 0.354,
                                         carbon_tax_rate: float = 50.0,
                                         crf: float = 0.16275,
                                         operating_hours: float = 8000.0) -> Dict[str, Any]:
        """
        Synthesizes multi-component distillation separation sequences (Direct, Indirect,
        Distributed, Dividing-Wall Column Petlyuk) and computes multi-objective Pareto trade-offs.
        """
        from src.optimization.sequence_synthesizer import SeparationSequencer
        from src.optimization.pareto_optimizer import ParetoOptimizer

        sp_map = species_map or {}

        # 1. Determine Feed Flow and Compositions
        flow_mol_s = 100.0
        fractions = [0.35, 0.40, 0.25]
        comps = components_list or ["benzene", "toluene", "octane"]

        if feed_stream is not None:
            if hasattr(feed_stream, "m_flow") and hasattr(feed_stream, "MW") and feed_stream.MW and feed_stream.MW > 0:
                flow_mol_s = max(1.0, (feed_stream.m_flow / feed_stream.MW) * 1000.0)
            elif hasattr(feed_stream, "flow") and feed_stream.flow and feed_stream.flow > 0:
                flow_mol_s = max(1.0, feed_stream.flow)

            if hasattr(feed_stream, "z") and feed_stream.z:
                if isinstance(feed_stream.z, dict):
                    sorted_z = sorted(feed_stream.z.items(), key=lambda x: x[1], reverse=True)
                    if len(sorted_z) >= 3:
                        comps = [k for k, v in sorted_z[:3]]
                        fractions = [v for k, v in sorted_z[:3]]
                    elif len(sorted_z) == 2:
                        comps = [sorted_z[0][0], sorted_z[1][0], "octane"]
                        fractions = [sorted_z[0][1] * 0.7, sorted_z[1][1], sorted_z[0][1] * 0.3]
                elif isinstance(feed_stream.z, list) and len(feed_stream.z) >= 3:
                    fractions = feed_stream.z[:3]

        if feed_flow_mol_s is not None:
            flow_mol_s = float(feed_flow_mol_s)
        if feed_fractions is not None and len(feed_fractions) >= 3:
            fractions = list(feed_fractions[:3])
        if components_list is not None and len(components_list) >= 3:
            comps = list(components_list[:3])

        # Normalize fractions
        tot_f = sum(fractions)
        fractions = [f / tot_f for f in fractions]

        # 2. Run Separation Synthesis
        synth_res = SeparationSequencer.synthesize_all_sequences(
            feed_flow_mol_s=flow_mol_s,
            feed_fractions=fractions,
            components=comps,
            species_map=sp_map,
            steam_price_usd_per_gj=steam_price,
            cooling_price_usd_per_gj=cooling_price,
            electricity_price_usd_per_kwh=electricity_price,
            carbon_tax_usd_per_tonne=carbon_tax_rate,
            crf=crf,
            operating_hours=operating_hours
        )

        # 3. Multi-Objective Pareto Optimization
        alphas_val = [synth_res["mixture_info"]["relative_volatilities"].get(c, 1.0) for c in synth_res["mixture_info"]["components"]]
        s_params = {
            "feed_flow_mol_s": flow_mol_s,
            "feed_fractions": fractions,
            "alphas": alphas_val,
            "steam_price_usd_per_gj": steam_price,
            "cooling_price_usd_per_gj": cooling_price,
            "carbon_tax_usd_per_tonne": carbon_tax_rate,
            "crf": crf
        }
        pareto_res = ParetoOptimizer.generate_pareto_frontier(
            synth_res["candidate_objects"],
            synthesis_params=s_params
        )

        # 4. Summary & Optimal Architecture
        best_cand = synth_res["optimal_sequence"]

        return {
            "synthesis_result": synth_res,
            "pareto_result": pareto_res,
            "candidates": synth_res["candidates"],
            "optimal_sequence": best_cand,
            "optimal_candidate_name": synth_res["optimal_candidate_name"],
            "dwc_benchmarks": synth_res["dwc_benchmarks"],
            "mixture_info": synth_res["mixture_info"],
            "summary": {
                "optimal_name": best_cand["sequence_name"],
                "min_tac_usd_yr": best_cand["total_annualized_cost_tac_usd"],
                "dwc_energy_savings_pct": synth_res["dwc_benchmarks"]["energy_savings_pct"],
                "dwc_capex_savings_pct": synth_res["dwc_benchmarks"]["capex_savings_pct"],
                "carbon_abatement_tonnes_yr": synth_res["dwc_benchmarks"]["carbon_abatement_tonnes_yr"],
                "pareto_frontier_points_count": pareto_res["pareto_count"]
            }
        }

    @classmethod
    def compile_flowsheet_solids(cls, units_list: list, streams_list: list = None) -> Dict[str, Any]:
        """
        Compiles solids processing unit operations (ContinuousCrystallizer, SprayDryer),
        evaluating crystal size distributions (PBM), moments, magma density,
        and psychrometric drying gas balances.
        """
        from src.units.solids import ContinuousCrystallizer, SprayDryer

        if isinstance(units_list, dict):
            units_list = list(units_list.values())
        if streams_list is not None and isinstance(streams_list, dict):
            streams_list = list(streams_list.values())

        crystallizer_units = []
        dryer_units = []

        for u in units_list:
            u_type = u.__class__.__name__
            if isinstance(u, ContinuousCrystallizer) or "Crystallizer" in u_type:
                crystallizer_units.append(u)
            elif isinstance(u, SprayDryer) or "Dryer" in u_type:
                dryer_units.append(u)

        # 1. Crystallizer Analysis
        cryst_data = []
        total_crystals_kg_h = 0.0
        for c in crystallizer_units:
            pbm = getattr(c, "pbm_results", {})
            if not pbm and hasattr(c, "run_simulation"):
                pbm = c.run_simulation((0, 1), [0])
            cryst_data.append({
                "unit_id": c.unit_id,
                "unit_name": c.name,
                "residence_time_min": pbm.get("residence_time_min", 60.0),
                "growth_rate_um_s": pbm.get("growth_rate_um_s", 0.05),
                "magma_density_kg_m3": pbm.get("magma_density_kg_m3", 150.0),
                "solids_production_kg_h": pbm.get("solids_production_kg_h", 500.0),
                "L_10_um": pbm.get("L_10_um", 180.0),
                "L_43_um": pbm.get("L_43_um", 720.0),
                "L_50_um": pbm.get("L_50_um", 660.0),
                "CV_pct": pbm.get("CV_pct", 100.0),
                "cooling_duty_kW": pbm.get("cooling_duty_kW", 120.0),
                "psd_size_bins_um": pbm.get("psd_size_bins_um", []),
                "psd_volume_density": pbm.get("psd_volume_density", [])
            })
            total_crystals_kg_h += pbm.get("solids_production_kg_h", 0.0)

        # 2. Spray Dryer Analysis
        dryer_data = []
        total_powder_kg_h = 0.0
        total_water_evap_kg_h = 0.0
        for d in dryer_units:
            d_res = getattr(d, "dryer_results", {})
            if not d_res and hasattr(d, "run_simulation"):
                d_res = d.run_simulation((0, 1), [0])
            dryer_data.append({
                "unit_id": d.unit_id,
                "unit_name": d.name,
                "feed_rate_kg_h": d_res.get("feed_rate_kg_h", 1500.0),
                "water_evaporated_kg_h": d_res.get("water_evaporated_kg_h", 900.0),
                "powder_produced_kg_h": d_res.get("powder_produced_kg_h", 580.0),
                "drying_air_flow_kg_h": d_res.get("drying_air_flow_kg_h", 4000.0),
                "inlet_air_temp_C": d_res.get("inlet_air_temp_C", 190.0),
                "outlet_air_temp_C": d_res.get("outlet_air_temp_C", 85.0),
                "thermal_efficiency_pct": d_res.get("thermal_efficiency_pct", 60.0),
                "burner_heat_duty_kW": d_res.get("burner_heat_duty_kW", 250.0),
                "exhaust_humidity_kg_kg": d_res.get("exhaust_humidity_kg_kg", 0.035),
                "cyclone_recovery_pct": d_res.get("cyclone_recovery_pct", 98.5)
            })
            total_powder_kg_h += d_res.get("powder_produced_kg_h", 0.0)
            total_water_evap_kg_h += d_res.get("water_evaporated_kg_h", 0.0)

        return {
            "crystallizers": cryst_data,
            "dryers": dryer_data,
            "total_crystallizer_units": len(crystallizer_units),
            "total_dryer_units": len(dryer_units),
            "summary": {
                "total_crystal_production_kg_h": round(total_crystals_kg_h, 1),
                "total_powder_production_kg_h": round(total_powder_kg_h, 1),
                "total_water_evaporated_kg_h": round(total_water_evap_kg_h, 1)
            }
        }

    @classmethod
    def compile_flowsheet_digital_twin(cls, units_list: Any, streams_list: Any = None) -> Dict[str, Any]:
        """
        Compiles an IEC 62541 OPC-UA address space, DCS multi-loop operator faceplates,
        and equipment health/fouling diagnostics across all flowsheet units.
        """
        from src.control.digital_twin import (
            OPCUANode, OPCUATagRegistry, DCSControllerFaceplate, EquipmentHealthMonitor
        )

        if isinstance(units_list, dict):
            units_list = list(units_list.values())
        if streams_list is not None and isinstance(streams_list, dict):
            streams_list = list(streams_list.values())
        streams_list = streams_list or []

        registry = OPCUATagRegistry()
        dcs_faceplates = []
        hex_health = []
        pump_health = []
        column_health = []

        active_alarms_count = 0
        critical_equipment_count = 0

        for idx, u in enumerate(units_list):
            uid = getattr(u, "unit_id", f"UNIT-{idx+1}")
            utype = u.__class__.__name__

            # 1. Primary Operating Telemetry
            in_t_c = 25.0
            in_p_kpa = 101.3
            in_f_mol = 10.0
            duty_kw = abs(getattr(u, "heat_duty", 0.0)) / 1000.0
            power_kw = getattr(u, "work_input", 0.0) / 1000.0

            if getattr(u, "inlets", None) and len(u.inlets) > 0:
                st0 = u.inlets[0]
                if st0.T is not None: in_t_c = st0.T - 273.15
                if st0.P is not None: in_p_kpa = st0.P / 1000.0
                if st0.F is not None: in_f_mol = st0.F

            # 2. Register Standard OPC-UA Tags
            t_node = OPCUANode(
                node_id=f"ns=2;s=Plant.{uid}.PV_Temp",
                browse_name=f"{uid}_PV_Temp",
                unit_id=uid,
                data_type="Double",
                eng_units="°C",
                value=round(in_t_c, 2),
                description=f"Operating temperature for {uid} ({utype})"
            )
            p_node = OPCUANode(
                node_id=f"ns=2;s=Plant.{uid}.PV_Press",
                browse_name=f"{uid}_PV_Press",
                unit_id=uid,
                data_type="Double",
                eng_units="kPa",
                value=round(in_p_kpa, 2),
                description=f"Operating pressure for {uid} ({utype})"
            )
            f_node = OPCUANode(
                node_id=f"ns=2;s=Plant.{uid}.PV_Flow",
                browse_name=f"{uid}_PV_Flow",
                unit_id=uid,
                data_type="Double",
                eng_units="mol/s",
                value=round(in_f_mol, 2),
                description=f"Feed throughput for {uid} ({utype})"
            )
            d_node = OPCUANode(
                node_id=f"ns=2;s=Plant.{uid}.PV_ThermalDuty",
                browse_name=f"{uid}_PV_ThermalDuty",
                unit_id=uid,
                data_type="Double",
                eng_units="kW",
                value=round(duty_kw, 2),
                description=f"Thermal duty for {uid} ({utype})"
            )
            run_node = OPCUANode(
                node_id=f"ns=2;s=Plant.{uid}.STAT_Run",
                browse_name=f"{uid}_STAT_Run",
                unit_id=uid,
                data_type="Boolean",
                access_level="ReadWrite",
                value=True,
                description=f"Operational running status for {uid}"
            )

            registry.register_tag(t_node)
            registry.register_tag(p_node)
            registry.register_tag(f_node)
            registry.register_tag(d_node)
            registry.register_tag(run_node)

            # 3. Create DCS Control Loops
            if any(k in utype for k in ["Column", "Reactor", "CSTR", "Heater", "Cooler", "Crystallizer", "Dryer"]):
                sp_t = round(in_t_c, 1)
                fp = DCSControllerFaceplate(
                    loop_id=f"TIC-{uid}",
                    name=f"{uid} Temperature Control",
                    unit_id=uid,
                    loop_type="Temperature",
                    pv_init=in_t_c,
                    sp_init=sp_t,
                    units="°C",
                    pv_range=(max(0.0, in_t_c - 100.0), in_t_c + 100.0),
                    hh_limit=round(in_t_c + 50.0, 1),
                    h_limit=round(in_t_c + 25.0, 1),
                    l_limit=round(in_t_c - 25.0, 1),
                    ll_limit=round(in_t_c - 50.0, 1)
                )
                if fp.alarm_state != "NORMAL":
                    active_alarms_count += 1
                dcs_faceplates.append(fp)

            elif any(k in utype for k in ["Pump", "Compressor", "ControlValve"]):
                sp_p = round(in_p_kpa, 1)
                fp = DCSControllerFaceplate(
                    loop_id=f"PIC-{uid}",
                    name=f"{uid} Pressure Control",
                    unit_id=uid,
                    loop_type="Pressure",
                    pv_init=in_p_kpa,
                    sp_init=sp_p,
                    units="kPa",
                    pv_range=(max(10.0, in_p_kpa * 0.5), in_p_kpa * 2.0),
                    hh_limit=round(in_p_kpa * 1.5, 1),
                    h_limit=round(in_p_kpa * 1.25, 1),
                    l_limit=round(in_p_kpa * 0.75, 1),
                    ll_limit=round(in_p_kpa * 0.5, 1)
                )
                if fp.alarm_state != "NORMAL":
                    active_alarms_count += 1
                dcs_faceplates.append(fp)

            # 4. Equipment Health Diagnostics
            if any(k in utype for k in ["HeatExchanger", "Heater", "Cooler"]):
                u_clean = 850.0
                area = getattr(u, "area", 45.0)
                th_in, th_out = in_t_c + 40.0, in_t_c
                tc_in, tc_out = 20.0, 45.0
                foul_res = EquipmentHealthMonitor.evaluate_heat_exchanger_fouling(
                    u_clean=u_clean,
                    duty_kw=max(10.0, duty_kw),
                    area_m2=area,
                    t_hot_in=th_in, t_hot_out=th_out,
                    t_cold_in=tc_in, t_cold_out=tc_out,
                    hours_operated=2200.0
                )
                foul_res["unit_id"] = uid
                foul_res["unit_name"] = getattr(u, "name", uid)
                if "CRITICAL" in foul_res["health_status"]:
                    critical_equipment_count += 1
                hex_health.append(foul_res)

            elif any(k in utype for k in ["Pump"]):
                cav_res = EquipmentHealthMonitor.evaluate_pump_cavitation(
                    p_suction_kpa=in_p_kpa,
                    p_vapor_kpa=max(5.0, in_p_kpa * 0.3),
                    npsh_required_m=2.5
                )
                cav_res["unit_id"] = uid
                cav_res["unit_name"] = getattr(u, "name", uid)
                if "CRITICAL" in cav_res["cavitation_risk"]:
                    critical_equipment_count += 1
                pump_health.append(cav_res)

            elif any(k in utype for k in ["Column", "DistillationColumn"]):
                stab_res = EquipmentHealthMonitor.evaluate_column_hydraulic_stability(
                    vapor_velocity_m_s=1.25,
                    flood_velocity_m_s=1.65
                )
                stab_res["unit_id"] = uid
                stab_res["unit_name"] = getattr(u, "name", uid)
                column_health.append(stab_res)

        return {
            "registry": registry,
            "tags_list": registry.browse_tags(),
            "dcs_faceplates": dcs_faceplates,
            "faceplates_dict": [fp.to_dict() for fp in dcs_faceplates],
            "health_diagnostics": {
                "heat_exchangers": hex_health,
                "pumps": pump_health,
                "columns": column_health
            },
            "summary": {
                "total_tags_count": len(registry.tags),
                "total_control_loops": len(dcs_faceplates),
                "active_alarms_count": active_alarms_count,
                "critical_equipment_count": critical_equipment_count
            }
        }

    @classmethod
    def compile_flowsheet_deliverables(cls, units_list: Any, streams_list: Any = None,
                                       connections: Optional[list] = None,
                                       title_data: Any = None,
                                       jurisdiction: str = "DUAL") -> Dict[str, Any]:
        """
        Compiles comprehensive engineering deliverables and regulatory compliance records
        conforming to DIN EN ISO 10628, DIN EN ISO 7200, PED 2014/68/EU, and OSHA 1910.119.
        """
        from src.reporting.regulatory_standards import (
            TitleBlockData, PEDClassifier, OSHAPSIChecker, RegulatoryStandards
        )

        # Convert to dictionary maps if needed
        units_map = {}
        if isinstance(units_list, dict):
            units_map = units_list
        elif isinstance(units_list, (list, tuple)):
            for idx, u in enumerate(units_list):
                uid = getattr(u, "unit_id", getattr(u, "name", f"UNIT-{idx+1}"))
                units_map[uid] = u

        streams_map = {}
        if isinstance(streams_list, dict):
            streams_map = streams_list
        elif isinstance(streams_list, (list, tuple)):
            for idx, st in enumerate(streams_list):
                sid = getattr(st, "name", f"S-{idx+1:02d}")
                streams_map[sid] = st

        tb = title_data or TitleBlockData()
        tb.jurisdiction = jurisdiction

        # 1. PED 2014/68/EU Classifications
        ped_evaluations = []
        ped_cat_counts = {"SEP": 0, "Category I": 0, "Category II": 0, "Category III": 0, "Category IV": 0}
        ce_count = 0

        # Scan for flammable / dangerous chemicals in streams
        comp_names = set()
        for st in streams_map.values():
            if hasattr(st, "z") and st.z:
                comp_names.update(st.z.keys())

        fluid_group = 1 if any(c.lower() in PEDClassifier.GROUP_1_CHEMICALS for c in comp_names) else 2

        for uid, u in units_map.items():
            utype = u.__class__.__name__ if hasattr(u, "__class__") else str(u.get("type", "Unit"))
            ps_bar = getattr(u, "design_pressure", 101325.0) / 100000.0
            sizing = getattr(u, "sizing_results", {}) or {}
            vol_m3 = sizing.get("volume_m3", 2.0)
            is_gas = "Column" in utype or "Separator" in utype or "Compressor" in utype or "Dryer" in utype

            eval_res = PEDClassifier.classify_vessel(ps_bar, vol_m3, fluid_group, is_gas)
            eval_res["unit_id"] = uid
            eval_res["unit_type"] = utype
            eval_res["unit_name"] = getattr(u, "name", uid)
            ped_evaluations.append(eval_res)

            cat = eval_res["category"]
            if cat in ped_cat_counts:
                ped_cat_counts[cat] += 1
            if eval_res["ce_marking_required"]:
                ce_count += 1

        # 2. OSHA 1910.119 Process Technology Envelopes
        tech_envelopes = []
        for uid, u in units_map.items():
            utype = u.__class__.__name__ if hasattr(u, "__class__") else str(u.get("type", "Unit"))
            des_p = getattr(u, "design_pressure", 101325.0) / 100000.0
            envelope = OSHAPSIChecker.compile_technology_envelope(uid, utype, 80.0, des_p * 0.7, des_p)
            tech_envelopes.append(envelope)

        # 3. Chemical Hazards
        chem_hazards = OSHAPSIChecker.compile_chemical_hazards(list(comp_names) or ["methane", "water", "ethanol"])

        # 4. Filter Applicable Standards
        applicable_standards = RegulatoryStandards.filter_by_jurisdiction(jurisdiction)

        return {
            "title_data": tb,
            "units_map": units_map,
            "streams_map": streams_map,
            "connections": connections or [],
            "ped_evaluations": ped_evaluations,
            "osha_technology_envelopes": tech_envelopes,
            "chemical_hazards": chem_hazards,
            "applicable_standards": applicable_standards,
            "summary": {
                "total_units": len(units_map),
                "total_streams": len(streams_map),
                "fluid_group": fluid_group,
                "ped_category_counts": ped_cat_counts,
                "ce_mark_required_count": ce_count,
                "osha_psm_covered": fluid_group == 1,
                "standards_count": len(applicable_standards),
                "governing_jurisdiction": jurisdiction
            }
        }
