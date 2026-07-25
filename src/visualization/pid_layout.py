class PIDLayout:
    """Programmatic P&ID Topology model that generates clean Mermaid representations."""
    
    def __init__(self, name: str):
        self.name = name
        self.nodes = []
        self.edges = []

    def add_equipment(self, element_id: str, label: str):
        self.nodes.append((element_id, f'"{label}"', "equipment"))

    def add_valve(self, element_id: str, label: str):
        self.nodes.append((element_id, f'"{label}"', "valve"))

    def add_instrument(self, element_id: str, label: str):
        self.nodes.append((element_id, f'(("{label}"))', "instrument"))

    def add_process_stream(self, from_id: str, to_id: str, label: str = ""):
        self.edges.append((from_id, to_id, f"|{label}|" if label else ""))

    def add_control_signal(self, from_id: str, to_id: str, label: str = ""):
        self.edges.append((from_id, to_id, f"-.->|{label}|" if label else "-.->"))

    def to_mermaid(self) -> str:
        """Generates compiled Mermaid syntax block."""
        lines = ["graph TD", "    %% Equipment and Instruments %%"]
        
        for elem_id, symbol, cls in self.nodes:
            lines.append(f"    {elem_id}{symbol}")
            
        lines.append("\n    %% Stream and Signals %%")
        for f, t, label in self.edges:
            if "-->" in label or "-.->" in label or label.startswith("-.->"):
                lines.append(f"    {f} {label} {t}")
            elif label:
                lines.append(f"    {f} -->{label} {t}")
            else:
                lines.append(f"    {f} --> {t}")
                
        # Inject standard style CSS classes
        lines.extend([
            "\n    %% CSS Styles %%",
            "    classDef equipment fill:#d4ebf2,stroke:#333,stroke-width:2px;",
            "    classDef valve fill:#fcd5d9,stroke:#333,stroke-width:1px;",
            "    classDef instrument fill:#fff,stroke:#333,stroke-dasharray: 5 5;"
        ])
        
        # Apply styles by node class type
        equip_nodes = [n[0] for n in self.nodes if n[2] == "equipment"]
        valve_nodes = [n[0] for n in self.nodes if n[2] == "valve"]
        instr_nodes = [n[0] for n in self.nodes if n[2] == "instrument"]
        
        if equip_nodes:
            lines.append(f"    class {','.join(equip_nodes)} equipment;")
        if valve_nodes:
            lines.append(f"    class {','.join(valve_nodes)} valve;")
        if instr_nodes:
            lines.append(f"    class {','.join(instr_nodes)} instrument;")
            
        return "\n".join(lines)
