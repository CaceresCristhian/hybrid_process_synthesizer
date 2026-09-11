from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class PortDefinition:
    id: str
    label: str
    type: str          # 'inlet' or 'outlet'
    x_rel: float       # 0.0 (left) to 1.0 (right)
    y_rel: float       # 0.0 (top) to 1.0 (bottom)
    fluid_hint: str = "any"  # 'vapor', 'liquid', 'gas', 'slurry', 'any'

# Registry of equipment connection nozzles/ports
EQUIPMENT_PORTS: Dict[str, List[PortDefinition]] = {
    "DistillationColumn": [
        PortDefinition("feed", "Feed Inlet", "inlet", 0.0, 0.5, "liquid"),
        PortDefinition("distillate", "Distillate (Overhead)", "outlet", 0.5, 0.0, "vapor"),
        PortDefinition("bottoms", "Bottoms Liquid", "outlet", 0.5, 1.0, "liquid"),
        PortDefinition("side_draw", "Side-Draw Liquid", "outlet", 1.0, 0.65, "liquid")
    ],
    "AbsorptionColumn": [
        PortDefinition("gas_in", "Sour Gas Feed", "inlet", 0.0, 0.85, "gas"),
        PortDefinition("solvent_in", "Lean Solvent Feed", "inlet", 0.0, 0.15, "liquid"),
        PortDefinition("clean_gas", "Treated Clean Gas", "outlet", 0.5, 0.0, "gas"),
        PortDefinition("rich_solvent", "Rich Solvent Bottoms", "outlet", 0.5, 1.0, "liquid")
    ],
    "HeatExchanger": [
        PortDefinition("tube_in", "Tube-Side Hot In", "inlet", 0.0, 0.35, "any"),
        PortDefinition("shell_in", "Shell-Side Cold In", "inlet", 0.5, 0.0, "any"),
        PortDefinition("tube_out", "Tube-Side Hot Out", "outlet", 1.0, 0.65, "any"),
        PortDefinition("shell_out", "Shell-Side Cold Out", "outlet", 0.5, 1.0, "any")
    ],
    "FlashDrum": [
        PortDefinition("feed", "Pressurized Feed", "inlet", 0.0, 0.5, "any"),
        PortDefinition("vapor", "Overhead Vapor", "outlet", 0.5, 0.0, "vapor"),
        PortDefinition("liquid", "Bottoms Liquid", "outlet", 0.5, 1.0, "liquid")
    ],
    "Splitter": [
        PortDefinition("inlet", "Main Feed", "inlet", 0.0, 0.5, "any"),
        PortDefinition("out_1", "Split Fraction 1", "outlet", 1.0, 0.25, "any"),
        PortDefinition("out_2", "Split Fraction 2", "outlet", 1.0, 0.75, "any"),
        PortDefinition("out_3", "Split Fraction 3", "outlet", 1.0, 0.50, "any")
    ],
    "Mixer": [
        PortDefinition("in_1", "Inlet Stream 1", "inlet", 0.0, 0.20, "any"),
        PortDefinition("in_2", "Inlet Stream 2", "inlet", 0.0, 0.50, "any"),
        PortDefinition("in_3", "Inlet Stream 3", "inlet", 0.0, 0.80, "any"),
        PortDefinition("mixed_out", "Combined Mixed Out", "outlet", 1.0, 0.50, "any")
    ],
    "SolidLiquidSeparator": [
        PortDefinition("slurry_in", "Slurry / Mash In", "inlet", 0.0, 0.35, "slurry"),
        PortDefinition("liquid_out", "Clarified Wort/Filtrate", "outlet", 1.0, 0.35, "liquid"),
        PortDefinition("solids_out", "Spent Grains / Cake Out", "outlet", 0.5, 1.0, "slurry")
    ],
    "MembraneUnit": [
        PortDefinition("feed_in", "High Pressure Feed", "inlet", 0.0, 0.5, "liquid"),
        PortDefinition("permeate_out", "Purified Permeate", "outlet", 1.0, 0.3, "liquid"),
        PortDefinition("retentate_out", "Concentrated Brine", "outlet", 1.0, 0.75, "liquid")
    ],
    "Pump": [
        PortDefinition("suction", "Suction Inlet", "inlet", 0.0, 0.5, "liquid"),
        PortDefinition("discharge", "Pressure Discharge", "outlet", 1.0, 0.5, "liquid")
    ],
    "Compressor": [
        PortDefinition("suction", "Gas Suction In", "inlet", 0.0, 0.5, "gas"),
        PortDefinition("discharge", "High-P Discharge", "outlet", 1.0, 0.5, "gas")
    ],
    "Expander": [
        PortDefinition("inlet", "High-P Gas In", "inlet", 0.0, 0.5, "gas"),
        PortDefinition("discharge", "Chilled Exhaust", "outlet", 1.0, 0.5, "gas")
    ],
    "Heater": [
        PortDefinition("inlet", "Cold Process In", "inlet", 0.0, 0.5, "any"),
        PortDefinition("outlet", "Heated Process Out", "outlet", 1.0, 0.5, "any")
    ],
    "Cooler": [
        PortDefinition("inlet", "Hot Process In", "inlet", 0.0, 0.5, "any"),
        PortDefinition("outlet", "Chilled Process Out", "outlet", 1.0, 0.5, "any")
    ],
    "Bioreactor": [
        PortDefinition("feed", "Nutrient Feed In", "inlet", 0.25, 0.0, "liquid"),
        PortDefinition("product", "Fermented Broth Out", "outlet", 0.75, 1.0, "liquid")
    ],
    "CSTR": [
        PortDefinition("feed", "Reactants In", "inlet", 0.25, 0.0, "liquid"),
        PortDefinition("product", "Effluent Out", "outlet", 0.75, 1.0, "liquid")
    ],
    "PFR": [
        PortDefinition("feed", "Tube Feed In", "inlet", 0.0, 0.5, "any"),
        PortDefinition("product", "Reactor Product Out", "outlet", 1.0, 0.5, "any")
    ],
    "EquilibriumReactor": [
        PortDefinition("feed", "Gas Feed In", "inlet", 0.0, 0.5, "gas"),
        PortDefinition("product", "Equilibrium Product", "outlet", 1.0, 0.5, "gas")
    ],
    "ControlValve": [
        PortDefinition("inlet", "Valve Inlet", "inlet", 0.0, 0.5, "any"),
        PortDefinition("outlet", "Throttled Outlet", "outlet", 1.0, 0.5, "any")
    ],
    "ContinuousCrystallizer": [
        PortDefinition("feed", "Saturated Solution Feed", "inlet", 0.0, 0.40, "liquid"),
        PortDefinition("overflow", "Mother Liquor Overflow", "outlet", 1.0, 0.25, "liquid"),
        PortDefinition("slurry", "Crystal Slurry Bottoms", "outlet", 0.5, 1.0, "slurry")
    ],
    "SprayDryer": [
        PortDefinition("feed", "Wet Feed / Slurry", "inlet", 0.5, 0.0, "liquid"),
        PortDefinition("gas_in", "Hot Drying Gas In", "inlet", 0.0, 0.25, "gas"),
        PortDefinition("exhaust", "Moist Exhaust Air Out", "outlet", 1.0, 0.35, "gas"),
        PortDefinition("powder", "Dry Powder Product", "outlet", 0.5, 1.0, "slurry")
    ],
    "Feed Boundary": [
        PortDefinition("out", "Boundary Feed Source", "outlet", 1.0, 0.5, "any")
    ],
    "Product Boundary": [
        PortDefinition("in", "Boundary Product Sink", "inlet", 0.0, 0.5, "any")
    ]
}

# Register DistillationColumn aliases
EQUIPMENT_PORTS["BinaryDistillationColumn"] = EQUIPMENT_PORTS["DistillationColumn"]
EQUIPMENT_PORTS["DynamicDistillationColumn"] = EQUIPMENT_PORTS["DistillationColumn"]
EQUIPMENT_PORTS["Crystallizer"] = EQUIPMENT_PORTS["ContinuousCrystallizer"]
EQUIPMENT_PORTS["Dryer"] = EQUIPMENT_PORTS["SprayDryer"]

# Standard default dimensions (pixels) for canvas nodes
DEFAULT_UNIT_DIMENSIONS: Dict[str, Dict[str, int]] = {
    "DistillationColumn": {"width": 80, "height": 170},
    "BinaryDistillationColumn": {"width": 80, "height": 170},
    "DynamicDistillationColumn": {"width": 80, "height": 170},
    "AbsorptionColumn": {"width": 80, "height": 160},
    "HeatExchanger": {"width": 95, "height": 70},
    "Bioreactor": {"width": 90, "height": 110},
    "CSTR": {"width": 85, "height": 100},
    "PFR": {"width": 110, "height": 55},
    "EquilibriumReactor": {"width": 85, "height": 95},
    "FlashDrum": {"width": 75, "height": 100},
    "SolidLiquidSeparator": {"width": 85, "height": 95},
    "ContinuousCrystallizer": {"width": 85, "height": 125},
    "Crystallizer": {"width": 85, "height": 125},
    "SprayDryer": {"width": 90, "height": 135},
    "Dryer": {"width": 90, "height": 135},
    "MembraneUnit": {"width": 100, "height": 60},
    "Splitter": {"width": 70, "height": 80},
    "Mixer": {"width": 70, "height": 80},
    "Heater": {"width": 80, "height": 65},
    "Cooler": {"width": 80, "height": 65},
    "Pump": {"width": 70, "height": 60},
    "Compressor": {"width": 75, "height": 60},
    "Expander": {"width": 75, "height": 60},
    "ControlValve": {"width": 60, "height": 50},
    "Feed Boundary": {"width": 95, "height": 45},
    "Product Boundary": {"width": 95, "height": 45}
}

class PortRegistry:
    @staticmethod
    def get_ports(unit_type: str) -> List[PortDefinition]:
        return EQUIPMENT_PORTS.get(unit_type, [
            PortDefinition("inlet", "Inlet", "inlet", 0.0, 0.5),
            PortDefinition("outlet", "Outlet", "outlet", 1.0, 0.5)
        ])

    @staticmethod
    def get_port(unit_type: str, port_id: str) -> Optional[PortDefinition]:
        ports = PortRegistry.get_ports(unit_type)
        for p in ports:
            if p.id == port_id:
                return p
        # Fallback to first matching direction if available
        if ports:
            return ports[0]
        return None

    @staticmethod
    def get_default_port_id(unit_type: str, direction: str = "inlet") -> str:
        ports = PortRegistry.get_ports(unit_type)
        for p in ports:
            if p.type == direction:
                return p.id
        return "inlet" if direction == "inlet" else "outlet"

    @staticmethod
    def get_default_dimensions(unit_type: str) -> Dict[str, int]:
        return DEFAULT_UNIT_DIMENSIONS.get(unit_type, {"width": 80, "height": 70})

    @staticmethod
    def calculate_port_absolute_xy(node_x: float, node_y: float, 
                                    node_w: float, node_h: float, 
                                    port_def: PortDefinition) -> tuple:
        px = node_x + port_def.x_rel * node_w
        py = node_y + port_def.y_rel * node_h
        return px, py

    @staticmethod
    def calculate_port_coordinates(unit_type: str, port_id: str, 
                                    node_x: float, node_y: float, 
                                    node_w: float, node_h: float) -> tuple:
        p = PortRegistry.get_port(unit_type, port_id)
        if not p:
            return node_x + node_w / 2.0, node_y + node_h / 2.0
        return PortRegistry.calculate_port_absolute_xy(node_x, node_y, node_w, node_h, p)
