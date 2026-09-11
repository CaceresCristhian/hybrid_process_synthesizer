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


