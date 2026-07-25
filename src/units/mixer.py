import numpy as np
from src.units.base_unit import BaseUnit

class FlowsheetMixer(BaseUnit):
    """
    Mixer unit operation (HYSYS-style).
    Combines up to 10 inlet streams into a single outlet stream.
    Calculates molar flow conservation, mass fractions, adiabatic mixing temperature,
    and sets the outlet pressure to the minimum of all inlet pressures.
    """
    
    def __init__(self, unit_id: str, name: str):
        super().__init__(unit_id, name)
        self.heat_duty = 0.0  # adiabatic mixing
        self.work_input = 0.0
        
    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        species_map = kwargs.get("species_map", {})
        
        # Check active inlets
        active_inlets = [i for i in self.inlets if i.F is not None and i.F > 0]
        out_stream = self.outlets[0] if self.outlets else None
        
        if not active_inlets or not out_stream:
            if out_stream:
                out_stream.F = 0.0
            return {"outlet_flow_mol_s": 0.0}
            
        # 1. Total outlet molar flow (F_out = sum(F_in))
        f_out = sum(in_st.F for in_st in active_inlets)
        
        # 2. Minimum of inlet pressures is the outlet pressure
        p_out = min(in_st.P for in_st in active_inlets)
        
        # 3. Mixed composition (z_out_i = sum(F_in_j * z_in_j_i) / F_out)
        z_out = {}
        all_species_ids = set()
        for in_st in active_inlets:
            all_species_ids.update(in_st.z.keys())
            
        for sp_id in all_species_ids:
            total_moles_sp = sum(in_st.F * in_st.z.get(sp_id, 0.0) for in_st in active_inlets)
            z_out[sp_id] = total_moles_sp / f_out
            
        # 4. Adiabatic enthalpy mixing (H_out = sum(F_in_j * H_in_j) / F_out)
        total_energy_flow = sum(in_st.F * in_st.get_enthalpy(species_map) for in_st in active_inlets)
        h_out = total_energy_flow / f_out
        
        # 5. Back-calculate mixed temperature from enthalpy:
        # H = sum( z_i * Cp_i * (T - 298.15) ) => T = 298.15 + H / sum( z_i * Cp_i )
        t_ref = 298.15
        weighted_cp = 0.0
        for sp_id, z_val in z_out.items():
            sp = species_map.get(sp_id)
            cp = sp.macro.cp_constants[0] if sp and sp.macro.cp_constants else 75.3
            weighted_cp += z_val * cp
            
        if weighted_cp > 0:
            t_out = t_ref + h_out / weighted_cp
        else:
            t_out = t_ref
            
        # Set values on outlet stream
        out_stream.T = t_out
        out_stream.P = p_out
        out_stream.F = f_out
        out_stream.z = z_out
        out_stream.H = h_out
        
        return {
            "outlet_flow_mol_s": f_out,
            "outlet_temp_K": t_out,
            "outlet_press_Pa": p_out,
            "mixed_enthalpy_J_mol": h_out
        }

    def size_equipment(self) -> dict:
        # Mixer nozzle sizing: select sizing diameter based on inlets
        inlet_count = len(self.inlets)
        self.sizing_results = {
            "nozzle_inlet_ports": inlet_count,
            "mixer_body_diameter_m": 0.15 + 0.02 * min(10, inlet_count),
            "max_working_pressure_bar": 20.0
        }
        return self.sizing_results
