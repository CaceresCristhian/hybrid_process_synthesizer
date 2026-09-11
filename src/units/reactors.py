import numpy as np
from scipy.integrate import solve_ivp
from src.units.base_unit import BaseUnit

class IdealCSTR(BaseUnit):
    """Steady-state and dynamic model of a Continuous Stirred Tank Reactor (CSTR)."""
    
    def __init__(self, unit_id: str, name: str, volume: float):
        super().__init__(unit_id, name)
        self.volume = volume

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        """
        Runs dynamic simulation of a CSTR with feed flow.
        state = [C_A (concentration of reactant A)]
        kwargs must supply:
          - 'c_a0': inlet concentration of A (mol/m3)
          - 'v0': volumetric flow rate (m3/h)
          - 'reaction_rate_fn': function mapping (C_A) -> reaction rate (mol/m3/h)
        """
        in_stream = self.inlets[0] if self.inlets else None
        out_stream = self.outlets[0] if self.outlets else None
        
        # Flowsheet stream propagation mode
        if in_stream and out_stream and in_stream.F is not None and in_stream.F > 0:
            conversion = kwargs.get("conversion", 0.70)
            delta_h_rxn = kwargs.get("delta_h_rxn", -45000.0)  # J/mol (exothermic)
            
            out_stream.T = in_stream.T + 12.0  # temperature rise from reaction
            out_stream.P = in_stream.P - 10000.0  # bed/tank pressure drop
            out_stream.F = in_stream.F
            out_stream.z = in_stream.z.copy() if in_stream.z else {}
            
            # Convert first component to second component if available
            keys = list(out_stream.z.keys())
            if len(keys) >= 2:
                r_amount = out_stream.z[keys[0]] * conversion
                out_stream.z[keys[0]] -= r_amount
                out_stream.z[keys[1]] += r_amount
                
            self.heat_duty = in_stream.F * conversion * delta_h_rxn
            return {"conversion": conversion, "reaction_heat_kW": self.heat_duty / 1000.0}

        c_a0 = kwargs.get("c_a0", 10.0)
        v0 = kwargs.get("v0", 1.0)
        reaction_rate_fn = kwargs.get("reaction_rate_fn", lambda ca: -0.5 * ca)
        
        tau = self.volume / max(0.01, v0)
        
        def odes(t, state):
            c_a = state[0]
            r_a = reaction_rate_fn(c_a)
            dc_a_dt = (c_a0 - c_a) / tau + r_a
            return [dc_a_dt]

        t_eval = np.linspace(time_span[0], time_span[1] if time_span[1] > time_span[0] else 1.0, 100)
        init_st = initial_state if initial_state else [c_a0]
        sol = solve_ivp(odes, (time_span[0], max(time_span[1], 1.0)), init_st, t_eval=t_eval)
        
        return {
            "t": sol.t,
            "C_A": sol.y[0]
        }

    def size_equipment(self) -> dict:
        """Sizes mechanical vessel requirements."""
        # Design CSTR volume sizing
        self.sizing_results = {
            "vessel_volume_m3": self.volume,
            "design_flow_m3_h": 2.0
        }
        return self.sizing_results


class IdealPFR(BaseUnit):
    """Steady-state concentration profile solver for a Plug Flow Reactor (PFR)."""
    
    def __init__(self, unit_id: str, name: str, volume: float):
        super().__init__(unit_id, name)
        self.volume = volume

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        """
        PFR represents spatial profiles rather than temporal ones at steady-state.
        This simulates the profile along the reactor volume coordinate.
        state = [C_A] (concentration profile along volume coordinate V)
        kwargs must supply:
          - 'c_a0': inlet concentration of A (mol/m3)
          - 'v0': volumetric flow rate (m3/h)
          - 'reaction_rate_fn': function mapping (C_A) -> reaction rate (mol/m3/h)
        """
        in_stream = self.inlets[0] if self.inlets else None
        out_stream = self.outlets[0] if self.outlets else None
        
        # Flowsheet stream propagation mode
        if in_stream and out_stream and in_stream.F is not None and in_stream.F > 0:
            conversion = kwargs.get("conversion", 0.85)
            delta_h_rxn = kwargs.get("delta_h_rxn", -60000.0)  # J/mol
            
            out_stream.T = in_stream.T + 25.0  # adiabatic tubular temperature rise
            out_stream.P = in_stream.P - 25000.0  # catalyst bed pressure drop
            out_stream.F = in_stream.F
            out_stream.z = in_stream.z.copy() if in_stream.z else {}
            
            keys = list(out_stream.z.keys())
            if len(keys) >= 2:
                r_amount = out_stream.z[keys[0]] * conversion
                out_stream.z[keys[0]] -= r_amount
                out_stream.z[keys[1]] += r_amount
                
            self.heat_duty = in_stream.F * conversion * delta_h_rxn
            return {"conversion": conversion, "reaction_heat_kW": self.heat_duty / 1000.0}

        c_a0 = kwargs.get("c_a0", 10.0)
        v0 = kwargs.get("v0", 1.0)
        reaction_rate_fn = kwargs.get("reaction_rate_fn", lambda ca: -0.8 * ca)
        
        # dF_A/dV = r_A  ==>  dC_A/dV = r_A / v0
        def odes(V, state):
            c_a = state[0]
            r_a = reaction_rate_fn(c_a)
            dc_a_dv = r_a / max(0.01, v0)
            return [dc_a_dv]

        # Integrate along the volume coordinate (from V=0 to V=self.volume)
        v_eval = np.linspace(0.0, self.volume, 100)
        sol = solve_ivp(odes, (0.0, self.volume), [c_a0], t_eval=v_eval)
        
        return {
            "V": sol.t,      # Volume coordinate (independent variable)
            "C_A": sol.y[0]  # Concentration profile
        }

    def size_equipment(self) -> dict:
        self.sizing_results = {
            "vessel_volume_m3": self.volume,
            "design_length_m": 5.0,
            "design_diameter_m": 2.0 * np.sqrt(self.volume / (5.0 * np.pi))
        }
        return self.sizing_results
