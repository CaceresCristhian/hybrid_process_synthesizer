import numpy as np
from scipy.optimize import fsolve

class FlowsheetSolver:
    """
    Flowsheet-wide calculation engine containing:
    1. Sequential Modular (SM) Solver with Wegstein recycle loop convergence.
    2. Equation-Oriented (EO) simultaneous Newton-Raphson solver.
    """
    
    @staticmethod
    def wegstein_update(x_k: float, x_k_prev: float, g_k: float, g_k_prev: float) -> float:
        """
        Calculates accelerated Wegstein guess for recycle streams:
        x_new = q * x_k + (1 - q) * g_k
        where s = (g_k - g_k_prev)/(x_k - x_k_prev), and q = s / (s - 1)
        """
        denom = x_k - x_k_prev
        if np.abs(denom) < 1e-9:
            return g_k
            
        s = (g_k - g_k_prev) / denom
        # Bounding the acceleration factor to avoid instability
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
        Runs Sequential Modular solver on the flowsheet.
        If a recycle loop is detected, uses the Wegstein method to converge variables of the tear_stream.
        recycle_loop_fn: function representing the loop calculations: g_k = loop(x_k)
        """
        # initial state vector: [T, P, F] of the tear stream
        x_k = np.array([tear_stream.T if tear_stream.T else 298.15,
                        tear_stream.P if tear_stream.P else 101325.0,
                        tear_stream.F if tear_stream.F else 10.0])
        
        # Run first iteration
        # loop function runs all units sequentially and returns the calculated feedback stream state
        x_next = np.array(recycle_loop_fn(x_k))
        
        # Save history for Wegstein
        x_prev = x_k.copy()
        x_k = x_next.copy()
        
        converged = False
        history = [x_prev.tolist(), x_k.tolist()]
        
        for i in range(max_iter):
            # Run simulation loop
            g_k = np.array(recycle_loop_fn(x_k))
            
            # Check convergence
            error = np.linalg.norm(g_k - x_k) / (np.linalg.norm(x_k) + 1e-5)
            if error < tolerance:
                converged = True
                break
                
            # Wegstein update for each state variable
            x_next = np.zeros_like(x_k)
            for j in range(len(x_k)):
                x_next[j] = cls.wegstein_update(x_k[j], x_prev[j], g_k[j], history[-2][j])
                
            # Shift states
            x_prev = x_k.copy()
            x_k = x_next.copy()
            history.append(x_k.tolist())
            
        # Update final tear stream values
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
        Runs Equation-Oriented (EO) solver.
        Solves flowsheet equations simultaneously using a Newton-Raphson solver (via scipy fsolve).
        flowsheet_equations_fn: function mapping state vector X -> list of residuals (F(X) = 0)
        """
        sol, info, ier, msg = fsolve(flowsheet_equations_fn, initial_guess, full_output=True)
        converged = ier == 1
        
        # Calculate residuals at solution
        residuals = flowsheet_equations_fn(sol)
        max_residual = np.max(np.abs(residuals))
        
        return {
            "converged": converged,
            "solution": sol,
            "max_residual": max_residual,
            "message": msg,
            "iterations": info.get("nfev", 0)
        }
