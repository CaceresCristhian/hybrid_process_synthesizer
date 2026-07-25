from src.units.base_unit import BaseUnit
import numpy as np

class ControlValve(BaseUnit):
    """
    Control Valve Unit Operation (HYSYS-style).
    Flow is governed by pressure-flow relationship:
    F = Cv * open_fraction * sqrt(delta_P / SG)
    """
    
    def __init__(self, unit_id: str, name: str, cv: float = 0.5):
        super().__init__(unit_id, name)
        self.cv = cv
        self.open_fraction = 1.0  # 100% open by default
        self.sg = 1.0            # Specific gravity (water = 1.0)
        self.delta_p = 0.0

    def calculate_flow(self, p_in: float, p_out: float) -> float:
        """Calculates flow rate through the valve based on pressure difference (in mol/s)."""
        self.delta_p = max(0.0, p_in - p_out)
        # Flow rate: F = Cv * open_fraction * sqrt(delta_p)
        # Converting Pa to bar for standard Cv units (approximate scaling)
        # Cv is typically defined for gpm / psi^0.5, but we use a scaled molar flow rate here.
        # Let's say: molar flow (mol/s) = Cv * open_fraction * sqrt(delta_p_Pa) * constant
        # Let constant = 0.01 for physical realism
        flow = self.cv * self.open_fraction * np.sqrt(self.delta_p) * 0.02
        return flow

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        """Solves transient valve behavior."""
        p_in = kwargs.get("p_in", 101325.0)
        p_out = kwargs.get("p_out", 101325.0)
        self.open_fraction = kwargs.get("open_fraction", self.open_fraction)
        
        flow = self.calculate_flow(p_in, p_out)
        return {
            "flow_rate_mol_s": flow,
            "pressure_drop_Pa": self.delta_p,
            "open_fraction": self.open_fraction
        }

    def size_equipment(self) -> dict:
        """Sizes required Cv based on design conditions."""
        # Design conditions: flow = 10 mol/s, delta_p = 20 kPa (20000 Pa)
        design_flow = 10.0
        design_dp = 20000.0
        # Cv = flow / (open_fraction * sqrt(dp))
        required_cv = design_flow / (1.0 * np.sqrt(design_dp) * 0.02)
        self.sizing_results = {
            "installed_cv": required_cv,
            "design_pressure_drop_kPa": design_dp / 1000.0,
            "design_flow_mol_s": design_flow
        }
        return self.sizing_results
