import numpy as np
from src.units.base_unit import BaseUnit

class AbsorptionColumn(BaseUnit):
    """
    Gas-Liquid Packed / Tray Absorption Column / Stripper.
    Used for Carbon Capture, Natural Gas Sweetening (Amine treating), and Scrubbers.
    Inlets: [0] Gas Feed (bottom inlet), [1] Lean Solvent (top inlet).
    Outlets: [0] Clean Treated Gas (top outlet), [1] Rich Solvent (bottom outlet).
    """
    def __init__(self, unit_id: str, name: str, target_solute: str = "co2", removal_efficiency: float = 0.92):
        super().__init__(unit_id, name)
        self.target_solute = target_solute
        self.removal_efficiency = removal_efficiency
        self.heat_duty = 0.0
        self.work_input = 0.0

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        if len(self.inlets) >= 2 and len(self.outlets) >= 2:
            gas_in = self.inlets[0]
            solv_in = self.inlets[1]
            gas_out = self.outlets[0]
            solv_out = self.outlets[1]
            
            if gas_in.F is not None and solv_in.F is not None and gas_in.F > 0 and solv_in.F > 0:
                # Flow of solute in gas
                solute_frac = gas_in.z.get(self.target_solute, 0.0) if gas_in.z else 0.0
                solute_moles = gas_in.F * solute_frac
                absorbed_moles = solute_moles * self.removal_efficiency
                
                # Clean Gas outlet
                gas_out.T = gas_in.T
                gas_out.P = gas_in.P - 5000.0  # bed pressure drop
                gas_out.F = max(0.01, gas_in.F - absorbed_moles)
                gas_out.z = gas_in.z.copy() if gas_in.z else {}
                if self.target_solute in gas_out.z:
                    rem_solute = solute_moles - absorbed_moles
                    gas_out.z[self.target_solute] = rem_solute / gas_out.F
                    # renormalize other species
                    non_solute_sum = sum(v for k, v in gas_in.z.items() if k != self.target_solute)
                    for k in gas_out.z:
                        if k != self.target_solute:
                            gas_out.z[k] = (gas_in.z[k] * (gas_in.F - solute_moles)) / gas_out.F
                            
                # Rich Solvent outlet
                solv_out.T = solv_in.T + 4.0  # slight exotherm from absorption
                solv_out.P = solv_in.P
                solv_out.F = solv_in.F + absorbed_moles
                solv_out.z = solv_in.z.copy() if solv_in.z else {}
                solv_out.z[self.target_solute] = absorbed_moles / solv_out.F
                for k in solv_in.z:
                    if k != self.target_solute:
                        solv_out.z[k] = (solv_in.z[k] * solv_in.F) / solv_out.F
                        
        elif len(self.inlets) >= 1 and len(self.outlets) >= 1:
            in_s = self.inlets[0]
            out_s = self.outlets[0]
            if in_s.F is not None:
                out_s.T = in_s.T
                out_s.P = in_s.P - 5000.0
                out_s.F = in_s.F
                out_s.z = in_s.z.copy() if in_s.z else {}
                
        return {"absorption_efficiency": self.removal_efficiency}

    def size_equipment(self) -> dict:
        self.sizing_results = {
            "column_diameter_m": 1.2,
            "packing_height_m": 8.5,
            "packing_type": "Mellapak 250Y Structured Packing",
            "removal_efficiency_pct": self.removal_efficiency * 100.0
        }
        return self.sizing_results
