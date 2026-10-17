import html


class PIDLayout:
    """Programmatic P&ID Topology model that generates clean Mermaid representations."""
    
    def __init__(self, name: str):
        self.name = html.escape(str(name), quote=True)
        self.nodes = []
        self.edges = []
        self.subgraphs = {} # maps group_name -> list of (node_id, label)

    def add_equipment(self, element_id: str, label: str):
        safe_id = html.escape(str(element_id), quote=True)
        safe_lbl = html.escape(str(label), quote=True)
        self.nodes.append((safe_id, f'["{safe_lbl}"]', "equipment"))

    def add_valve(self, element_id: str, label: str):
        safe_id = html.escape(str(element_id), quote=True)
        safe_lbl = html.escape(str(label), quote=True)
        self.nodes.append((safe_id, f'["{safe_lbl}"]', "valve"))

    def add_instrument(self, element_id: str, label: str):
        safe_id = html.escape(str(element_id), quote=True)
        safe_lbl = html.escape(str(label), quote=True)
        self.nodes.append((safe_id, f'(("{safe_lbl}"))', "instrument"))

    def add_subgraph(self, group_name: str, nodes_list: list):
        """Adds a labeled subgraph grouping in the Mermaid diagram."""
        safe_group = html.escape(str(group_name), quote=True)
        safe_nodes = [(html.escape(str(nid), quote=True), html.escape(str(nlbl), quote=True)) for nid, nlbl in nodes_list]
        self.subgraphs[safe_group] = safe_nodes

    def add_process_stream(self, from_id: str, to_id: str, label: str = ""):
        safe_from = html.escape(str(from_id), quote=True)
        safe_to = html.escape(str(to_id), quote=True)
        safe_lbl = html.escape(str(label), quote=True) if label else ""
        self.edges.append((safe_from, safe_to, f"|{safe_lbl}|" if safe_lbl else ""))

    def add_control_signal(self, from_id: str, to_id: str, label: str = ""):
        safe_from = html.escape(str(from_id), quote=True)
        safe_to = html.escape(str(to_id), quote=True)
        safe_lbl = html.escape(str(label), quote=True) if label else ""
        self.edges.append((safe_from, safe_to, f"-.->|{safe_lbl}|" if safe_lbl else "-.->"))

    def to_mermaid(self) -> str:
        """Generates compiled Mermaid syntax block with subgraphs."""
        lines = ["graph TD"]
        
        # 1. Render Subgraphs first
        if self.subgraphs:
            lines.append("    %% Subgraphs %%")
            for group, nodes_list in self.subgraphs.items():
                group_id = group.replace(" ", "_")
                lines.append(f"    subgraph {group_id} [\"{group}\"]")
                for nid, nlbl in nodes_list:
                    lines.append(f"        {nid}[\"{nlbl}\"]")
                lines.append("    end")
                
        # Set of nodes rendered in subgraphs to avoid double-definition
        subg_nodes = set(nid for nodes_list in self.subgraphs.values() for nid, _ in nodes_list)
        
        # 2. Render normal nodes
        lines.append("\n    %% Equipment and Instruments %%")
        for elem_id, symbol, cls in self.nodes:
            if elem_id not in subg_nodes:
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
