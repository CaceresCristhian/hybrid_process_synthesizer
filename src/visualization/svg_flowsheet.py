import xml.etree.ElementTree as ET

class SVGFlowsheet:
    """
    Dynamic Process Flow Diagram (PFD) generator that outputs clean vector-based SVGs.
    Replaces generic blocks with recognizable chemical engineering symbols and groups boundaries.
    """
    
    @staticmethod
    def draw_capsule(x, y, w, h, fill="#f1f5f9", stroke="#334155", stroke_width=2):
        """Draws a capsule (cylinder with round head/bottom) using SVG path."""
        r = w / 2
        path_data = f"M {x} {y + r} " \
                    f"A {r} {r} 0 0 1 {x + w} {y + r} " \
                    f"L {x + w} {y + h - r} " \
                    f"A {r} {r} 0 0 1 {x} {y + h - r} " \
                    f"Z"
        return f'<path d="{path_data}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" />'

    @classmethod
    def get_symbol_svg(cls, eq_id: str, eq_type: str, x: float, y: float, variation: str = "Tray Column") -> str:
        """Returns SVG code representing the equipment symbol."""
        svg = []
        fill_color = "#e2e8f0"
        stroke_color = "#1e293b"
        
        if eq_type == "DistillationColumn":
            w, h = 60, 140
            # Shell
            svg.append(cls.draw_capsule(x, y, w, h, fill=fill_color, stroke=stroke_color))
            
            if "Packed" in variation:
                # Draw cross-hatched packing bed sections
                # Section 1 (top packing)
                svg.append(f'<rect x="{x+6}" y="{y+25}" width="48" height="35" fill="none" stroke="{stroke_color}" stroke-dasharray="3 3"/>')
                svg.append(f'<line x1="{x+6}" y1="{y+25}" x2="{x+54}" y2="{y+60}" stroke="{stroke_color}" stroke-width="1"/>')
                svg.append(f'<line x1="{x+6}" y1="{y+60}" x2="{x+54}" y2="{y+25}" stroke="{stroke_color}" stroke-width="1"/>')
                
                # Section 2 (bottom packing)
                svg.append(f'<rect x="{x+6}" y="{y+80}" width="48" height="35" fill="none" stroke="{stroke_color}" stroke-dasharray="3 3"/>')
                svg.append(f'<line x1="{x+6}" y1="{y+80}" x2="{x+54}" y2="{y+115}" stroke="{stroke_color}" stroke-width="1"/>')
                svg.append(f'<line x1="{x+6}" y1="{y+115}" x2="{x+54}" y2="{y+80}" stroke="{stroke_color}" stroke-width="1"/>')
            else:
                # Sieve Trays (sieve tray lines)
                for i in range(1, 8):
                    tray_y = y + 15 + i * 14
                    svg.append(f'<line x1="{x+4}" y1="{tray_y}" x2="{x+w-4}" y2="{tray_y}" stroke="{stroke_color}" stroke-width="1.5" stroke-dasharray="4 2" />')
            
            # Text label overlay
            svg.append(f'<text x="{x + w/2}" y="{y + h/2 + 5}" font-family="Inter, sans-serif" font-size="11" font-weight="bold" fill="#0f172a" text-anchor="middle">{eq_id}</text>')
            
        elif eq_type == "Bioreactor":
            w, h = 80, 100
            # Reactor outer jacket
            svg.append(f'<rect x="{x-5}" y="{y+10}" width="{w+10}" height="{h-20}" rx="10" fill="#ccfbf1" stroke="#0d9488" stroke-width="2" />')
            # Reactor vessel inner
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="15" fill="{fill_color}" stroke="{stroke_color}" stroke-width="2" />')
            # Impeller Shaft
            svg.append(f'<line x1="{x + w/2}" y1="{y-10}" x2="{x + w/2}" y2="{y + h - 25}" stroke="{stroke_color}" stroke-width="3" />')
            # Impeller blades
            svg.append(f'<line x1="{x + w/2 - 15}" y1="{y + h - 35}" x2="{x + w/2 + 15}" y2="{y + h - 35}" stroke="{stroke_color}" stroke-width="4" />')
            svg.append(f'<line x1="{x + w/2 - 15}" y1="{y + h - 55}" x2="{x + w/2 + 15}" y2="{y + h - 55}" stroke="{stroke_color}" stroke-width="4" />')
            # Text label
            svg.append(f'<text x="{x + w/2}" y="{y + h/2 - 5}" font-family="Inter, sans-serif" font-size="11" font-weight="bold" fill="#0f172a" text-anchor="middle">{eq_id}</text>')
            
        elif eq_type == "Pump":
            r = 20
            # Circular casing
            svg.append(f'<circle cx="{x+r}" cy="{y+r}" r="{r}" fill="#fee2e2" stroke="#ef4444" stroke-width="2" />')
            # Tangential discharge nozzle (triangle)
            points = f"{x+r*2} {y+r-5}, {x+r*2+10} {y}, {x+r*2} {y+r+5}"
            svg.append(f'<polygon points="{points}" fill="#ef4444" stroke="{stroke_color}" stroke-width="1" />')
            # Text label
            svg.append(f'<text x="{x+r}" y="{y+r+4}" font-family="Inter, sans-serif" font-size="10" font-weight="bold" fill="#0f172a" text-anchor="middle">{eq_id}</text>')
            
        elif eq_type == "ControlValve":
            w, h = 40, 50
            # Actuator diaphragm (ellipse)
            svg.append(f'<ellipse cx="{x + w/2}" cy="{y + 10}" rx="15" ry="6" fill="#ffedd5" stroke="#f97316" stroke-width="1.5" />')
            # Stem line
            svg.append(f'<line x1="{x + w/2}" y1="{y + 16}" x2="{x + w/2}" y2="{y + 35}" stroke="{stroke_color}" stroke-width="2" />')
            # Valve body (double triangles / bow-tie)
            points = f"{x} {y+25}, {x+w} {y+45}, {x+w} {y+25}, {x} {y+45}"
            svg.append(f'<polygon points="{points}" fill="#ffedd5" stroke="#f97316" stroke-width="2" />')
            # Text label
            svg.append(f'<text x="{x + w/2}" y="{y + h - 2}" font-family="Inter, sans-serif" font-size="9" font-weight="bold" fill="#0f172a" text-anchor="middle">{eq_id}</text>')
            
        else:  # Feed / Product Boundaries
            w, h = 100, 40
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="#f8fafc" stroke="#64748b" stroke-width="1.5" stroke-dasharray="3 3" />')
            svg.append(f'<text x="{x+w/2}" y="{y+h/2+4}" font-family="Inter, sans-serif" font-size="10" fill="#475569" text-anchor="middle">{eq_id}</text>')
            
        return "\n".join(svg)

    @classmethod
    def generate_flowsheet_svg(cls, units_dict: dict, connections_list: list, variations_dict: dict = None) -> str:
        """
        Generates compiled SVG code representing the whole Flowshet diagram.
        Groups boundary nodes in labeled boxes.
        """
        if variations_dict is None:
            variations_dict = {}
            
        # Classify nodes for auto-coordinate mapping
        feeds = []
        products = []
        pumps = []
        valves = []
        reactors = []
        columns = []
        
        # Get all nodes involved
        all_nodes = set(c["from"] for c in connections_list) | set(c["to"] for c in connections_list)
        
        for n in all_nodes:
            if n == "Feed Boundary":
                feeds.append(n)
            elif n == "Product Boundary":
                products.append(n)
            elif n in units_dict:
                utype = units_dict[n]["type"]
                if utype == "Pump":
                    pumps.append(n)
                elif utype == "ControlValve":
                    valves.append(n)
                elif utype == "Bioreactor":
                    reactors.append(n)
                elif utype == "DistillationColumn":
                    columns.append(n)
                    
        # Coordinates mapping (left-to-right columns)
        node_coords = {}
        
        # 1. Feeds
        for idx, f in enumerate(feeds):
            node_coords[f] = (80, 180 + idx * 120)
            
        # 2. Pumps
        for idx, p in enumerate(pumps):
            node_coords[p] = (240, 180 + idx * 120)
            
        # 3. Valves
        for idx, v in enumerate(valves):
            node_coords[v] = (380, 175 + idx * 120)
            
        # 4. Reactors & Columns
        for idx, r in enumerate(reactors):
            node_coords[r] = (540, 150 + idx * 150)
        for idx, c in enumerate(columns):
            node_coords[c] = (550, 120 + idx * 200)
            
        # 5. Products
        for idx, pr in enumerate(products):
            node_coords[pr] = (780, 100 + idx * 160)

        # SVG Dimensions
        svg_w = 980
        svg_h = 500
        
        # Compile SVG markup
        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="100%" height="100%">',
            '  <defs>',
            '    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
            '      <path d="M 0 1 L 10 5 L 0 9 z" fill="#475569" />',
            '    </marker>',
            '  </defs>',
            '  <!-- Background Canvas Grid -->',
            f'  <rect width="{svg_w}" height="{svg_h}" fill="#fafafa" stroke="#e2e8f0" stroke-width="1"/>'
        ]

        # Draw Demarcated Bounding Boxes (subgraph boxes)
        # Bounding box for Feeds (left)
        if feeds:
            max_y = max(node_coords[f][1] for f in feeds) + 60
            svg.append(f'  <rect x="50" y="80" width="160" height="{max_y - 60}" rx="8" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4 4" />')
            svg.append('  <text x="130" y="72" font-family="Inter, sans-serif" font-size="11" font-weight="bold" fill="#64748b" text-anchor="middle">Feed boundaries</text>')
            
        # Bounding box for Products (right)
        if products:
            max_y = max(node_coords[pr][1] for pr in products) + 60
            svg.append(f'  <rect x="750" y="60" width="160" height="{max_y - 20}" rx="8" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4 4" />')
            svg.append('  <text x="830" y="52" font-family="Inter, sans-serif" font-size="11" font-weight="bold" fill="#64748b" text-anchor="middle">Product boundaries</text>')

        # Draw Connection Streams (Lines with arrows)
        for conn in connections_list:
            src = conn["from"]
            dst = conn["to"]
            s_id = conn["stream"]
            
            if src in node_coords and dst in node_coords:
                x1, y1 = node_coords[src]
                x2, y2 = node_coords[dst]
                
                # Adjust port contact offsets based on equipment width/height
                # Source adjustments
                src_type = units_dict.get(src, {}).get("type", "Boundary")
                if src == "Feed Boundary":
                    x1_offset = x1 + 100
                    y1_offset = y1 + 20
                elif src_type == "DistillationColumn":
                    x1_offset = x1 + 60
                    y1_offset = y1 + 70
                elif src_type == "Bioreactor":
                    x1_offset = x1 + 80
                    y1_offset = y1 + 50
                elif src_type == "Pump":
                    x1_offset = x1 + 45
                    y1_offset = y1 + 20
                elif src_type == "ControlValve":
                    x1_offset = x1 + 40
                    y1_offset = y1 + 35
                else:
                    x1_offset = x1
                    y1_offset = y1
                    
                # Destination adjustments
                dst_type = units_dict.get(dst, {}).get("type", "Boundary")
                if dst == "Product Boundary":
                    x2_offset = x2
                    y2_offset = y2 + 20
                elif dst_type == "DistillationColumn":
                    x2_offset = x2
                    y2_offset = y2 + 70
                elif dst_type == "Bioreactor":
                    x2_offset = x2
                    y2_offset = y2 + 50
                elif dst_type == "Pump":
                    x2_offset = x2
                    y2_offset = y2 + 20
                elif dst_type == "ControlValve":
                    x2_offset = x2
                    y2_offset = y2 + 35
                else:
                    x2_offset = x2
                    y2_offset = y2
                
                # Draw right-angled ortho line connectors for neat CAD rendering
                x_mid = x1_offset + (x2_offset - x1_offset) * 0.4
                path_str = f"M {x1_offset} {y1_offset} L {x_mid} {y1_offset} L {x_mid} {y2_offset} L {x2_offset} {y2_offset}"
                
                svg.append(f'  <path d="{path_str}" fill="none" stroke="#475569" stroke-width="2" marker-end="url(#arrow)" />')
                # Add text label above the horizontal mid line
                svg.append(f'  <text x="{x_mid}" y="{(y1_offset + y2_offset)/2 - 5}" font-family="Inter, sans-serif" font-size="9" fill="#0f766e" font-weight="bold" text-anchor="middle">{s_id}</text>')

        # Draw Equipment and Boundary Nodes on top of streams
        for node in all_nodes:
            if node in node_coords:
                x, y = node_coords[node]
                if node in units_dict:
                    utype = units_dict[node]["type"]
                    # Get symbol variation (e.g. Sieve Tray vs Packed Bed)
                    var_val = variations_dict.get(node, "Sieve Tray Column")
                    svg.append(cls.get_symbol_svg(node, utype, x, y, var_val))
                else:
                    # boundary node
                    svg.append(cls.get_symbol_svg(node, "Boundary", x, y))

        svg.append('</svg>')
        return "\n".join(svg)
