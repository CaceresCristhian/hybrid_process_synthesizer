import numpy as np

class PressureFlowSolver:
    """
    Pressure-Flow Network Solver (HYSYS-style).
    Determines flowsheet-wide flows and pressures based on equipment flow conductances (Cv)
    and boundary pressure conditions.
    """
    
    @staticmethod
    def solve_series_valves(p_inlet: float, p_outlet: float, cv1: float, open1: float, 
                            cv2: float, open2: float) -> tuple:
        """
        Solves pressures and flows for two valves in series:
        Inlet (P_inlet) -> Valve 1 (Cv1, open1) -> MidNode (P_mid) -> Valve 2 (Cv2, open2) -> Outlet (P_outlet)
        Returns: (p_mid, flow_rate)
        """
        # Conductances squared
        # Let's add a small offset to prevent division by zero if both are closed
        K1 = (cv1 * max(open1, 1e-4)) ** 2
        K2 = (cv2 * max(open2, 1e-4)) ** 2
        
        # P_mid = (K1*P_inlet + K2*P_outlet) / (K1 + K2)
        p_mid = (K1 * p_inlet + K2 * p_outlet) / (K1 + K2)
        
        # Calculate flow rate (mol/s)
        # Using same scaling constant 0.02 as in ControlValve class
        dp = max(0.0, p_inlet - p_mid)
        flow = cv1 * open1 * np.sqrt(dp) * 0.02
        
        return p_mid, flow

    @classmethod
    def solve_general_network(cls, boundary_pressures: dict, nodes_connections: list, 
                               valves_conductances: dict, valves_openings: dict) -> dict:
        """
        Solves pressure-flow for a general network using fsolve.
        boundary_pressures: dict of node_id: pressure (e.g. {'feed': 300000, 'vent': 101325})
        nodes_connections: list of connections: (from_node, to_node, valve_id)
        valves_conductances: dict of valve_id: Cv
        valves_openings: dict of valve_id: open_fraction (0.0 to 1.0)
        """
        # Get list of all intermediate nodes (not boundaries)
        all_nodes = set()
        for from_n, to_n, _ in nodes_connections:
            all_nodes.add(from_n)
            all_nodes.add(to_n)
            
        intermediate_nodes = sorted(list(all_nodes - set(boundary_pressures.keys())))
        
        if not intermediate_nodes:
            # Simple boundary connection
            results = {}
            for from_n, to_n, valve_id in nodes_connections:
                p_in = boundary_pressures.get(from_n, 101325.0)
                p_out = boundary_pressures.get(to_n, 101325.0)
                cv = valves_conductances.get(valve_id, 0.5)
                op = valves_openings.get(valve_id, 1.0)
                dp = max(0.0, p_in - p_out)
                flow = cv * op * np.sqrt(dp) * 0.02
                results[valve_id] = flow
            return {"pressures": boundary_pressures, "flows": results}

        # Solve system of equations: mass balance at each intermediate node
        # Sum(flow_in) = Sum(flow_out)
        def network_residuals(p_guesses):
            pressures = boundary_pressures.copy()
            for idx, node in enumerate(intermediate_nodes):
                pressures[node] = p_guesses[idx]
                
            residuals = []
            for node in intermediate_nodes:
                flow_in = 0.0
                flow_out = 0.0
                
                # Check connections
                for from_n, to_n, valve_id in nodes_connections:
                    cv = valves_conductances.get(valve_id, 0.5)
                    op = valves_openings.get(valve_id, 1.0)
                    
                    if to_n == node:
                        # Flow entering this node
                        p_from = pressures.get(from_n, 101325.0)
                        p_to = pressures.get(to_n, 101325.0)
                        dp = p_from - p_to
                        sgn = np.sign(dp)
                        flow = cv * op * np.sqrt(np.abs(dp)) * 0.02 * sgn
                        flow_in += flow
                    elif from_n == node:
                        # Flow leaving this node
                        p_from = pressures.get(from_n, 101325.0)
                        p_to = pressures.get(to_n, 101325.0)
                        dp = p_from - p_to
                        sgn = np.sign(dp)
                        flow = cv * op * np.sqrt(np.abs(dp)) * 0.02 * sgn
                        flow_out += flow
                        
                residuals.append(flow_in - flow_out)
            return residuals

        from scipy.optimize import fsolve
        initial_pressures = [np.mean(list(boundary_pressures.values()))] * len(intermediate_nodes)
        solved_pressures_list = fsolve(network_residuals, initial_pressures)
        
        # Compile results
        solved_pressures = boundary_pressures.copy()
        for idx, node in enumerate(intermediate_nodes):
            solved_pressures[node] = max(0.0, solved_pressures_list[idx])
            
        solved_flows = {}
        for from_n, to_n, valve_id in nodes_connections:
            p_from = solved_pressures.get(from_n, 101325.0)
            p_to = solved_pressures.get(to_n, 101325.0)
            cv = valves_conductances.get(valve_id, 0.5)
            op = valves_openings.get(valve_id, 1.0)
            dp = p_from - p_to
            sgn = np.sign(dp)
            flow = cv * op * np.sqrt(np.abs(dp)) * 0.02 * sgn
            solved_flows[valve_id] = flow
            
        return {
            "pressures": solved_pressures,
            "flows": solved_flows
        }
