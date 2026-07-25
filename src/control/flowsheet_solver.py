import numpy as np
from scipy.optimize import fsolve

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
