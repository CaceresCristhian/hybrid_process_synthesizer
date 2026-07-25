from abc import ABC, abstractmethod

class BaseUnit(ABC):
    """
    Abstract Base Class representing a general process equipment unit.
    Includes stream connections and mass/energy balance properties.
    """
    
    def __init__(self, unit_id: str, name: str):
        self.unit_id = unit_id
        self.name = name
        self.sizing_results = {}
        
        # Connections
        self.inlets = []
        self.outlets = []
        
        # Energy balances: Heat duty (Q) and mechanical work input (W) in Watts
        self.heat_duty = 0.0
        self.work_input = 0.0
        
        # Individual thermodynamic base option
        self.thermo_base = "Ideal"

    def connect_inlet(self, stream):
        self.inlets.append(stream)
        stream.downstream_units.append(self)

    def connect_outlet(self, stream):
        self.outlets.append(stream)
        stream.upstream_unit = self

    def propagate_forward(self, stream):
        """Called when an inlet stream updates. Override in subclasses."""
        pass

    def propagate_backward(self, stream):
        """Called when an outlet stream updates. Override in subclasses."""
        pass

    @abstractmethod
    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        """Runs dynamic simulation over specified time span."""
        pass

    @abstractmethod
    def size_equipment(self) -> dict:
        """Sizes mechanical structural properties of unit."""
        pass
