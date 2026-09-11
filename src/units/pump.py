from src.units.base_unit import BaseUnit

class FlowsheetPump(BaseUnit):
    """
    Standard centrifugal/positive displacement pump model.
    Increases pressure, adds small frictional/compression heat, and computes shaft power work input.
    """
    def __init__(self, unit_id: str, name: str, p_boost: float = 150000.0, efficiency: float = 0.75):
        super().__init__(unit_id, name)
        self.p_boost = p_boost
        self.efficiency = efficiency
        self.work_input = 0.0
        self.heat_duty = 0.0
        
    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_stream = self.inlets[0] if self.inlets else None
        out_stream = self.outlets[0] if self.outlets else None
        
        if in_stream and out_stream and in_stream.F is not None and in_stream.F > 0:
            out_stream.T = in_stream.T + 0.4  # pump heat compression
            out_stream.P = in_stream.P + self.p_boost
            out_stream.F = in_stream.F
            out_stream.z = in_stream.z.copy() if in_stream.z else {}
            
            species_map = kwargs.get("species_map", {})
            mw = in_stream.get_mixture_mw(species_map) if species_map else 30.0
            vol_flow = (in_stream.F * mw * 1e-3 / 1000.0)  # m3/s approx
            self.work_input = (vol_flow * self.p_boost) / self.efficiency
        return {"work_input_W": self.work_input}
        
    def size_equipment(self) -> dict:
        self.sizing_results = {"hydraulic_power_W": getattr(self, "work_input", 0.0)}
        return self.sizing_results
