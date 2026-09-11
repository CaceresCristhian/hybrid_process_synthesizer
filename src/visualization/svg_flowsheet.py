class SVGFlowsheet:
    """
    Dynamic Process Flow Diagram (PFD) generator that outputs clean vector-based SVGs.
    Integrates separate stream boundary nodes, Mixer rendering, and hover tooltips.
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
    def get_symbol_svg(cls, eq_id: str, eq_type: str, x: float, y: float, 
                       variation: str = "Tray Column", tooltip: str = "") -> str:
        """Returns SVG code representing the equipment symbol with hover tooltip."""
        svg = [f'<g id="node_{eq_id}">']
        if tooltip:
            svg.append(f'  <title>{tooltip}</title>')
            
        fill_color = "#e2e8f0"
        stroke_color = "#1e293b"
        
        if eq_type == "DistillationColumn":
            w, h = 60, 140
            # Shell
            svg.append(cls.draw_capsule(x, y, w, h, fill=fill_color, stroke=stroke_color))
            
            if "Packed" in variation:
                # Draw cross-hatched packing bed sections
                svg.append(f'<rect x="{x+6}" y="{y+25}" width="48" height="35" fill="none" stroke="{stroke_color}" stroke-dasharray="3 3"/>')
                svg.append(f'<line x1="{x+6}" y1="{y+25}" x2="{x+54}" y2="{y+60}" stroke="{stroke_color}" stroke-width="1"/>')
                svg.append(f'<line x1="{x+6}" y1="{y+60}" x2="{x+54}" y2="{y+25}" stroke="{stroke_color}" stroke-width="1"/>')
                
                svg.append(f'<rect x="{x+6}" y="{y+80}" width="48" height="35" fill="none" stroke="{stroke_color}" stroke-dasharray="3 3"/>')
                svg.append(f'<line x1="{x+6}" y1="{y+80}" x2="{x+54}" y2="{y+115}" stroke="{stroke_color}" stroke-width="1"/>')
                svg.append(f'<line x1="{x+6}" y1="{y+115}" x2="{x+54}" y2="{y+80}" stroke="{stroke_color}" stroke-width="1"/>')
            else:
                # Sieve Trays
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
            
        elif eq_type == "Mixer":
            r = 20
            svg.append(f'<circle cx="{x+r}" cy="{y+r}" r="{r}" fill="#e0f2fe" stroke="#0ea5e9" stroke-width="2" />')
            svg.append(f'<line x1="{x+5}" y1="{y+5}" x2="{x+r}" y2="{y+r}" stroke="#0ea5e9" stroke-width="1.5" />')
            svg.append(f'<line x1="{x+5}" y1="{y+r*2-5}" x2="{x+r}" y2="{y+r}" stroke="#0ea5e9" stroke-width="1.5" />')
            svg.append(f'<line x1="{x+r}" y1="{y+r}" x2="{x+r*2-5}" y2="{y+r}" stroke="#0ea5e9" stroke-width="2" />')
            svg.append(f'<text x="{x+r}" y="{y+r+4}" font-family="Inter, sans-serif" font-size="10" font-weight="bold" fill="#0f172a" text-anchor="middle">{eq_id}</text>')

        elif eq_type in ["Heater", "Furnace", "Boiler"]:
            w, h = 50, 50
            # Cylindrical/rectangular body
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#ffedd5" stroke="#ea580c" stroke-width="2" />')
            # Internal heating coil
            svg.append(f'<path d="M {x+8} {y+15} Q {x+25} {y+5} {x+42} {y+15} T {x+42} {y+35} T {x+8} {y+35}" fill="none" stroke="#ea580c" stroke-width="2" stroke-linecap="round"/>')
            svg.append(f'<text x="{x + w/2}" y="{y + h/2 + 4}" font-family="Inter, sans-serif" font-size="9" font-weight="bold" fill="#7c2d12" text-anchor="middle">{eq_id}</text>')

        elif eq_type in ["Cooler", "Condenser", "Chiller"]:
            w, h = 50, 50
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#e0f2fe" stroke="#0284c7" stroke-width="2" />')
            # Cooling snowflake/cross icon
            svg.append(f'<line x1="{x+12}" y1="{y+12}" x2="{x+38}" y2="{y+38}" stroke="#0284c7" stroke-width="2" stroke-dasharray="3 2" />')
            svg.append(f'<line x1="{x+38}" y1="{y+12}" x2="{x+12}" y2="{y+38}" stroke="#0284c7" stroke-width="2" stroke-dasharray="3 2" />')
            svg.append(f'<text x="{x + w/2}" y="{y + h/2 + 4}" font-family="Inter, sans-serif" font-size="9" font-weight="bold" fill="#0c4a6e" text-anchor="middle">{eq_id}</text>')

        elif eq_type == "HeatExchanger":
            r = 25
            svg.append(f'<circle cx="{x+r}" cy="{y+r}" r="{r}" fill="#cffafe" stroke="#0891b2" stroke-width="2" />')
            # Cross tube bundle lines
            svg.append(f'<line x1="{x+5}" y1="{y+r}" x2="{x+r*2-5}" y2="{y+r}" stroke="#0891b2" stroke-width="2" />')
            svg.append(f'<path d="M {x+10} {y+10} Q {x+r} {y+r+10} {x+r*2-10} {y+r*2-10}" fill="none" stroke="#0891b2" stroke-width="2"/>')
            svg.append(f'<text x="{x+r}" y="{y+r-8}" font-family="Inter, sans-serif" font-size="9" font-weight="bold" fill="#164e63" text-anchor="middle">{eq_id}</text>')

        elif eq_type in ["FlashDrum", "Separator", "KnockoutDrum"]:
            w, h = 45, 90
            svg.append(cls.draw_capsule(x, y, w, h, fill="#f8fafc", stroke="#475569", stroke_width=2))
            # Demister pad
            svg.append(f'<rect x="{x+4}" y="{y+20}" width="{w-8}" height="10" fill="#cbd5e1" stroke="#475569" stroke-width="1" stroke-dasharray="2 2" />')
            # Liquid level
            svg.append(f'<line x1="{x+4}" y1="{y+h-25}" x2="{x+w-4}" y2="{y+h-25}" stroke="#38bdf8" stroke-width="2" stroke-dasharray="3 2" />')
            svg.append(f'<text x="{x + w/2}" y="{y + h/2 + 5}" font-family="Inter, sans-serif" font-size="9" font-weight="bold" fill="#1e293b" text-anchor="middle">{eq_id}</text>')

        elif eq_type == "Splitter":
            r = 18
            svg.append(f'<polygon points="{x+r} {y}, {x+r*2} {y+r}, {x+r} {y+r*2}, {x} {y+r}" fill="#ede9fe" stroke="#7c3aed" stroke-width="2" />')
            svg.append(f'<text x="{x+r}" y="{y+r+4}" font-family="Inter, sans-serif" font-size="9" font-weight="bold" fill="#4c1d95" text-anchor="middle">{eq_id}</text>')

        elif eq_type == "Compressor":
            w, h = 45, 45
            # Tapered trapezoid (narrowing in flow direction for compression)
            points = f"{x} {y}, {x+w} {y+10}, {x+w} {y+h-10}, {x} {y+h}"
            svg.append(f'<polygon points="{points}" fill="#fef08a" stroke="#ca8a04" stroke-width="2" />')
            svg.append(f'<text x="{x + w/2 - 2}" y="{y + h/2 + 4}" font-family="Inter, sans-serif" font-size="9" font-weight="bold" fill="#713f12" text-anchor="middle">{eq_id}</text>')

        elif eq_type == "Expander":
            w, h = 45, 45
            # Inverted trapezoid (widening in flow direction)
            points = f"{x} {y+10}, {x+w} {y}, {x+w} {y+h}, {x} {y+h-10}"
            svg.append(f'<polygon points="{points}" fill="#dbeafe" stroke="#2563eb" stroke-width="2" />')
            svg.append(f'<text x="{x + w/2 + 2}" y="{y + h/2 + 4}" font-family="Inter, sans-serif" font-size="9" font-weight="bold" fill="#1e3a8a" text-anchor="middle">{eq_id}</text>')

        elif eq_type == "AbsorptionColumn":
            w, h = 55, 130
            svg.append(cls.draw_capsule(x, y, w, h, fill="#f1f5f9", stroke="#334155", stroke_width=2))
            # Packing sections
            svg.append(f'<rect x="{x+5}" y="{y+25}" width="{w-10}" height="75" fill="none" stroke="#334155" stroke-dasharray="3 3"/>')
            svg.append(f'<line x1="{x+5}" y1="{y+25}" x2="{x+w-5}" y2="{y+100}" stroke="#334155" stroke-width="1"/>')
            svg.append(f'<line x1="{x+5}" y1="{y+100}" x2="{x+w-5}" y2="{y+25}" stroke="#334155" stroke-width="1"/>')
            svg.append(f'<text x="{x + w/2}" y="{y + h/2 + 5}" font-family="Inter, sans-serif" font-size="10" font-weight="bold" fill="#0f172a" text-anchor="middle">{eq_id}</text>')

        elif eq_type in ["SolidLiquidSeparator", "Centrifuge", "Filter", "LauterTun"]:
            w, h = 50, 60
            points = f"{x} {y}, {x+w} {y}, {x+w*0.8} {y+h*0.7}, {x+w*0.5} {y+h}, {x+w*0.2} {y+h*0.7}"
            svg.append(f'<polygon points="{points}" fill="#fef3c7" stroke="#d97706" stroke-width="2" />')
            svg.append(f'<line x1="{x+8}" y1="{y+20}" x2="{x+w-8}" y2="{y+20}" stroke="#d97706" stroke-dasharray="2 2" stroke-width="1.5" />')
            svg.append(f'<text x="{x + w/2}" y="{y + 15}" font-family="Inter, sans-serif" font-size="9" font-weight="bold" fill="#78350f" text-anchor="middle">{eq_id}</text>')

        elif eq_type == "MembraneUnit":
            w, h = 70, 40
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#e0e7ff" stroke="#4338ca" stroke-width="2" />')
            # Diagonal membrane separator
            svg.append(f'<line x1="{x+10}" y1="{y+h-5}" x2="{x+w-10}" y2="{y+5}" stroke="#4338ca" stroke-dasharray="4 2" stroke-width="2" />')
            svg.append(f'<text x="{x + w/2}" y="{y + h/2 + 4}" font-family="Inter, sans-serif" font-size="9" font-weight="bold" fill="#312e81" text-anchor="middle">{eq_id}</text>')

        elif eq_type in ["EquilibriumReactor", "REquil"]:
            w, h = 60, 75
            # Catalyst fixed-bed reactor with equilibrium symbol (<=>)
            svg.append(cls.draw_capsule(x, y, w, h, fill="#fdf4ff", stroke="#9333ea", stroke_width=2))
            svg.append(f'<rect x="{x+6}" y="{y+20}" width="{w-12}" height="35" fill="#f3e8ff" stroke="#9333ea" stroke-dasharray="2 2" stroke-width="1"/>')
            svg.append(f'<text x="{x + w/2}" y="{y + 42}" font-family="Inter, sans-serif" font-size="12" font-weight="bold" fill="#7e22ce" text-anchor="middle">⇌</text>')
            svg.append(f'<text x="{x + w/2}" y="{y + h/2 + 25}" font-family="Inter, sans-serif" font-size="9" font-weight="bold" fill="#581c87" text-anchor="middle">{eq_id}</text>')

        elif eq_type in ["CSTR", "Reactor", "IdealCSTR", "IdealPFR", "PFR"]:
            w, h = 60, 70
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#fdf4ff" stroke="#c026d3" stroke-width="2" />')
            svg.append(f'<line x1="{x+w/2}" y1="{y-5}" x2="{x+w/2}" y2="{y+h-15}" stroke="#c026d3" stroke-width="2" />')
            svg.append(f'<line x1="{x+15}" y1="{y+h-20}" x2="{x+w-15}" y2="{y+h-20}" stroke="#c026d3" stroke-width="3" />')
            svg.append(f'<text x="{x + w/2}" y="{y + h/2 - 5}" font-family="Inter, sans-serif" font-size="9" font-weight="bold" fill="#701a75" text-anchor="middle">{eq_id}</text>')

        elif eq_type in ["ContinuousCrystallizer", "Crystallizer", "MSMPR"]:
            w, h = 60, 90
            points = f"{x} {y}, {x+w} {y}, {x+w} {y+h*0.7}, {x+w*0.5} {y+h}, {x} {y+h*0.7}"
            svg.append(f'<polygon points="{points}" fill="#eff6ff" stroke="#2563eb" stroke-width="2" />')
            svg.append(f'<rect x="{x+w*0.3}" y="{y+15}" width="{w*0.4}" height="{h*0.45}" fill="none" stroke="#2563eb" stroke-dasharray="2 2" stroke-width="1.5" />')
            svg.append(f'<line x1="{x+w*0.5}" y1="{y-5}" x2="{x+w*0.5}" y2="{y+h*0.65}" stroke="#1d4ed8" stroke-width="2" />')
            svg.append(f'<text x="{x + w/2}" y="{y + h*0.35}" font-family="Inter, sans-serif" font-size="8" font-weight="bold" fill="#1e40af" text-anchor="middle">❄️ {eq_id}</text>')

        elif eq_type in ["SprayDryer", "Dryer"]:
            w, h = 65, 100
            points = f"{x} {y+15}, {x+w} {y+15}, {x+w} {y+h*0.65}, {x+w*0.5} {y+h}, {x} {y+h*0.65}"
            svg.append(f'<polygon points="{points}" fill="#fffbeb" stroke="#b45309" stroke-width="2" />')
            svg.append(f'<polygon points="{x+w*0.5-8} {y}, {x+w*0.5+8} {y}, {x+w*0.5} {y+15}" fill="#f59e0b" stroke="#b45309" stroke-width="1" />')
            svg.append(f'<text x="{x + w/2}" y="{y + h*0.40}" font-family="Inter, sans-serif" font-size="8" font-weight="bold" fill="#92400e" text-anchor="middle">💨 {eq_id}</text>')

        else:  # Feed / Product Boundaries
            w, h = 100, 40
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="#f8fafc" stroke="#64748b" stroke-width="1.5" stroke-dasharray="3 3" />')
            svg.append(f'<text x="{x+w/2}" y="{y+h/2+4}" font-family="Inter, sans-serif" font-size="10" fill="#475569" text-anchor="middle">{eq_id}</text>')
            
        svg.append('</g>')
        return "\n".join(svg)

    @classmethod
    def generate_flowsheet_svg(cls, units_dict: dict, connections_list: list, 
                               variations_dict: dict = None, 
                               stream_states: dict = None, 
                               units_states: dict = None,
                               species_map: dict = None) -> str:
        """
        Generates compiled SVG code representing the whole Flowsheet diagram.
        Separates boundary feeds and products, groups them in labeled boxes,
        and uses dynamic topological layered graph layout for arbitrary plants.
        """
        if variations_dict is None:
            variations_dict = {}
        if stream_states is None:
            stream_states = {}
        if units_states is None:
            units_states = {}
        if species_map is None:
            species_map = {}

        # 1. Translate boundary connection points to unique node IDs
        mapped_connections = []
        feed_nodes = set()
        product_nodes = set()
        
        for c in connections_list:
            src = c.get("from", "Feed Boundary")
            dst = c.get("to", "Product Boundary")
            conn_s_id = c.get("stream", "S-101")
            
            # Separate Feed Boundaries
            if src == "Feed Boundary":
                src_id = f"Feed_{conn_s_id}"
                feed_nodes.add(src_id)
            else:
                src_id = src
                
            # Separate Product Boundaries
            if dst == "Product Boundary":
                dst_id = f"Product_{conn_s_id}"
                product_nodes.add(dst_id)
            else:
                dst_id = dst
                
            mapped_connections.append({
                "from": src_id,
                "to": dst_id,
                "stream": conn_s_id,
                "from_port": c.get("from_port"),
                "to_port": c.get("to_port")
            })

        # 2. Dynamic Topological Rank (Layered Graph Layout)
        node_rank = {f: 0 for f in feed_nodes}
        adj = {}
        for conn in mapped_connections:
            u = conn["from"]
            v = conn["to"]
            adj.setdefault(u, []).append(v)
            
        # Relax ranks along edges
        changed = True
        passes = 0
        while changed and passes < 25:
            changed = False
            passes += 1
            for u in list(node_rank.keys()):
                curr_r = node_rank[u]
                for v in adj.get(u, []):
                    if v not in product_nodes:
                        if v not in node_rank or node_rank[v] < curr_r + 1:
                            node_rank[v] = curr_r + 1
                            changed = True

        for u in units_dict.keys():
            if u not in node_rank:
                node_rank[u] = 1
                
        max_unit_rank = max([r for n, r in node_rank.items() if n not in product_nodes], default=1)
        for p in product_nodes:
            node_rank[p] = max_unit_rank + 1
            
        # Group nodes by rank
        rank_groups = {}
        for n, r in node_rank.items():
            rank_groups.setdefault(r, []).append(n)
            
        # Compute dynamic coordinates
        node_coords = {}
        max_rank = max(node_rank.values(), default=1)
        
        dx = 175
        x_start = 70
        y_start = 140
        dy = 130
        
        max_group_len = 1
        for r, nodes in rank_groups.items():
            nodes.sort()
            max_group_len = max(max_group_len, len(nodes))
            for idx, n in enumerate(nodes):
                x = x_start + r * dx
                y = y_start + idx * dy
                node_coords[n] = (x, y)
                
        svg_w = max(980, x_start + (max_rank + 1) * dx + 120)
        svg_h = max(560, y_start + max_group_len * dy + 100)
        
        # Compile SVG markup
        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="100%" height="100%">',
            '  <style>',
            '    .stream-path:hover { stroke: #0f766e; stroke-width: 3.5px; cursor: pointer; }',
            '  </style>',
            '  <defs>',
            '    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
            '      <path d="M 0 1 L 10 5 L 0 9 z" fill="#475569" />',
            '    </marker>',
            '  </defs>',
            '  <!-- Background Canvas Grid -->',
            f'  <rect width="{svg_w}" height="{svg_h}" fill="#fafafa" stroke="#e2e8f0" stroke-width="1"/>'
        ]

        # 3. Draw Demarcated Bounding Boxes (subgraph boxes)
        if feed_nodes:
            min_x_f = min(node_coords[f][0] for f in feed_nodes) - 30
            max_y = max(node_coords[f][1] for f in feed_nodes) + 60
            svg.append(f'  <rect x="{min_x_f}" y="80" width="160" height="{max_y - 60}" rx="8" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4 4" />')
            svg.append(f'  <text x="{min_x_f + 80}" y="72" font-family="Inter, sans-serif" font-size="11" font-weight="bold" fill="#64748b" text-anchor="middle">Feed Boundaries</text>')
            
        if product_nodes:
            min_x_p = min(node_coords[pr][0] for pr in product_nodes) - 30
            max_y = max(node_coords[pr][1] for pr in product_nodes) + 60
            svg.append(f'  <rect x="{min_x_p}" y="60" width="160" height="{max_y - 20}" rx="8" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4 4" />')
            svg.append(f'  <text x="{min_x_p + 80}" y="52" font-family="Inter, sans-serif" font-size="11" font-weight="bold" fill="#64748b" text-anchor="middle">Product Boundaries</text>')

        # 4. Draw Connection Streams (Lines with hover tooltips)
        for conn in mapped_connections:
            src = conn["from"]
            dst = conn["to"]
            s_id = conn["stream"]
            
            if src in node_coords and dst in node_coords:
                x1, y1 = node_coords[src]
                x2, y2 = node_coords[dst]
                
                # Offsets based on node types and specific port IDs
                src_type = units_dict.get(src, {}).get("type", "Boundary")
                src_port = conn.get("from_port", "outlet")
                
                if src.startswith("Feed_"):
                    x1_offset = x1 + 100
                    y1_offset = y1 + 20
                elif src_type in ["DistillationColumn", "BinaryDistillationColumn"]:
                    if src_port == "distillate":
                        x1_offset = x1 + 30
                        y1_offset = y1
                    elif src_port == "bottoms":
                        x1_offset = x1 + 30
                        y1_offset = y1 + 140
                    elif src_port == "side_draw":
                        x1_offset = x1 + 60
                        y1_offset = y1 + 90
                    else:
                        x1_offset = x1 + 60
                        y1_offset = y1 + 70
                elif src_type == "AbsorptionColumn":
                    if src_port == "clean_gas":
                        x1_offset = x1 + 27
                        y1_offset = y1
                    elif src_port == "rich_solvent":
                        x1_offset = x1 + 27
                        y1_offset = y1 + 130
                    else:
                        x1_offset = x1 + 55
                        y1_offset = y1 + 65
                elif src_type == "HeatExchanger":
                    if src_port == "shell_out":
                        x1_offset = x1 + 25
                        y1_offset = y1 + 50
                    else:
                        x1_offset = x1 + 50
                        y1_offset = y1 + 35
                elif src_type in ["FlashDrum", "Separator"]:
                    if src_port == "vapor":
                        x1_offset = x1 + 22
                        y1_offset = y1
                    elif src_port == "liquid":
                        x1_offset = x1 + 22
                        y1_offset = y1 + 90
                    else:
                        x1_offset = x1 + 45
                        y1_offset = y1 + 45
                elif src_type == "MembraneUnit":
                    if src_port == "permeate_out":
                        x1_offset = x1 + 50
                        y1_offset = y1 + 15
                    else:
                        x1_offset = x1 + 50
                        y1_offset = y1 + 45
                elif src_type in ["SolidLiquidSeparator", "LauterTun"]:
                    if src_port == "solids_out":
                        x1_offset = x1 + 25
                        y1_offset = y1 + 60
                    else:
                        x1_offset = x1 + 50
                        y1_offset = y1 + 25
                elif src_type == "Bioreactor":
                    x1_offset = x1 + 80
                    y1_offset = y1 + 50
                elif src_type == "Pump":
                    x1_offset = x1 + 45
                    y1_offset = y1 + 20
                elif src_type == "ControlValve":
                    x1_offset = x1 + 40
                    y1_offset = y1 + 35
                elif src_type == "Mixer":
                    x1_offset = x1 + 40
                    y1_offset = y1 + 20
                else:
                    x1_offset = x1 + 45
                    y1_offset = y1 + 25
                    
                # Destination adjustments
                dst_type = units_dict.get(dst, {}).get("type", "Boundary")
                dst_port = conn.get("to_port", "inlet")
                
                if dst.startswith("Product_"):
                    x2_offset = x2
                    y2_offset = y2 + 20
                elif dst_type in ["DistillationColumn", "BinaryDistillationColumn"]:
                    x2_offset = x2
                    y2_offset = y2 + 70
                elif dst_type == "AbsorptionColumn":
                    if dst_port == "solvent_in":
                        x2_offset = x2
                        y2_offset = y2 + 25
                    else:
                        x2_offset = x2
                        y2_offset = y2 + 105
                elif dst_type == "HeatExchanger":
                    if dst_port == "shell_in":
                        x2_offset = x2 + 25
                        y2_offset = y2
                    else:
                        x2_offset = x2
                        y2_offset = y2 + 25
                elif dst_type == "Bioreactor":
                    x2_offset = x2
                    y2_offset = y2 + 50
                elif dst_type == "Pump":
                    x2_offset = x2
                    y2_offset = y2 + 20
                elif dst_type == "ControlValve":
                    x2_offset = x2
                    y2_offset = y2 + 35
                elif dst_type == "Mixer":
                    x2_offset = x2
                    y2_offset = y2 + 20
                else:
                    x2_offset = x2
                    y2_offset = y2 + 25
                
                # Compile stream tooltip text
                st_data = stream_states.get(s_id)
                if st_data and st_data.F is not None:
                    # Mass flow
                    mass_flow = st_data.get_mass_flow(species_map)
                    # Compositions string
                    comp_parts = []
                    for sp_id, x_frac in st_data.z.items():
                        sp = species_map.get(sp_id)
                        name_sp = sp.name if sp else sp_id
                        comp_parts.append(f"  - {name_sp}: {x_frac*100:.1f} mol%")
                    comp_str = "\n".join(comp_parts)
                    
                    st_tooltip = f"Stream: {s_id}\n" \
                                 f"Flow Rate: {st_data.F:.2f} mol/s ({mass_flow:.2f} kg/h)\n" \
                                 f"Temperature: {st_data.T:.2f} K\n" \
                                 f"Pressure: {st_data.P/1000:.1f} kPa\n" \
                                 f"Composition:\n{comp_str}"
                else:
                    st_tooltip = f"Stream: {s_id} (Unsolved)"

                # Ortho Connector line path
                x_mid = x1_offset + (x2_offset - x1_offset) * 0.45
                path_str = f"M {x1_offset} {y1_offset} L {x_mid} {y1_offset} L {x_mid} {y2_offset} L {x2_offset} {y2_offset}"
                
                svg.append(f'  <g>')
                svg.append(f'    <title>{st_tooltip}</title>')
                svg.append(f'    <path class="stream-path" d="{path_str}" fill="none" stroke="#475569" stroke-width="2" marker-end="url(#arrow)" />')
                svg.append(f'    <text x="{x_mid}" y="{(y1_offset + y2_offset)/2 - 5}" font-family="Inter, sans-serif" font-size="9" fill="#0f766e" font-weight="bold" text-anchor="middle">{s_id}</text>')
                svg.append(f'  </g>')

        # 5. Draw Equipment and Boundary Nodes on top
        # Equipment Nodes
        for node, udata in units_dict.items():
            if node in node_coords:
                x, y = node_coords[node]
                utype = udata["type"]
                var_val = udata.get("variation", "Sieve Tray Column")
                
                # Compile equipment tooltip
                u_obj = units_states.get(node)
                if u_obj:
                    sizing_str = ", ".join(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}" for k, v in u_obj.sizing_results.items())
                    u_tooltip = f"Equipment: {node}\n" \
                                f"Type: {utype}\n" \
                                f"Fluid Package: {u_obj.thermo_base}\n" \
                                f"Heat Duty (Q): {u_obj.heat_duty/1000:.3f} kW\n" \
                                f"Work Input (W): {u_obj.work_input/1000:.3f} kW\n" \
                                f"Sizing Metrics:\n  {sizing_str}"
                else:
                    u_tooltip = f"Equipment: {node}\nType: {utype}\nFluid Package: {udata['thermo']}"
                    
                svg.append(cls.get_symbol_svg(node, utype, x, y, var_val, u_tooltip))
                
        # Split Boundary Nodes
        for feed in feed_nodes:
            if feed in node_coords:
                x, y = node_coords[feed]
                # Label feed based on stream name
                stream_ref = feed.replace("Feed_", "")
                lbl = f"Feed ({stream_ref})"
                
                st_data = stream_states.get(stream_ref)
                if st_data and st_data.F is not None:
                    mass_flow = st_data.get_mass_flow(species_map)
                    b_tooltip = f"Feed Stream Boundary: {stream_ref}\n" \
                                f"Flow: {st_data.F:.2f} mol/s ({mass_flow:.2f} kg/h)\n" \
                                f"Temp: {st_data.T:.1f} K | Press: {st_data.P/1000:.1f} kPa"
                else:
                    b_tooltip = f"Feed Stream Boundary: {stream_ref}"
                    
                svg.append(cls.get_symbol_svg(lbl, "Boundary", x, y, tooltip=b_tooltip))
                
        for prod in product_nodes:
            if prod in node_coords:
                x, y = node_coords[prod]
                stream_ref = prod.replace("Product_", "")
                lbl = f"Product ({stream_ref})"
                
                st_data = stream_states.get(stream_ref)
                if st_data and st_data.F is not None:
                    mass_flow = st_data.get_mass_flow(species_map)
                    b_tooltip = f"Product Outlet Boundary: {stream_ref}\n" \
                                f"Flow: {st_data.F:.2f} mol/s ({mass_flow:.2f} kg/h)\n" \
                                f"Temp: {st_data.T:.1f} K | Press: {st_data.P/1000:.1f} kPa"
                else:
                    b_tooltip = f"Product Outlet Boundary: {stream_ref}"
                    
                svg.append(cls.get_symbol_svg(lbl, "Boundary", x, y, tooltip=b_tooltip))

        svg.append('</svg>')
        return "\n".join(svg)

    @staticmethod
    def draw_bioreactor_figure_svg(max_vol: float, t_shell: float) -> str:
        """
        Draws a detailed vector schematic of a Jacketed Bioreactor
        with interactive hovers on all parts (vessel, jacket, impeller, motor).
        """
        svg = [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">',
            '  <rect width="400" height="300" fill="#fafafa" stroke="#e2e8f0" stroke-width="1"/>',
            '  <!-- 1. Cooling Jacket (Back Layer) -->',
            '  <g>',
            f'    <title>Cooling Jacket\nASME Material: SS-316\nU-Coefficient: 600 W/m²·K\nExchange Area: 5.0 m²\nDesign Pressure: 3.5 bar</title>',
            '    <path d="M 105 90 L 105 220 A 95 95 0 0 0 295 220 L 295 90" fill="none" stroke="#2dd4bf" stroke-width="12" stroke-linecap="round" />',
            '  </g>',
            '  <!-- 2. Vessel Body (Middle Layer) -->',
            '  <g>',
            f'    <title>Vessel Shell\nMax Volume: {max_vol:.2f} m³\nCalculated Wall Thickness: {t_shell:.2f} mm\nASME Material: SS-316\nHeight-to-Diameter Ratio: 3:1</title>',
            '    <rect x="120" y="50" width="160" height="180" rx="20" ry="20" fill="#f1f5f9" stroke="#334155" stroke-width="3" />',
            '    <line x1="120" y1="90" x2="280" y2="90" stroke="#cbd5e1" stroke-dasharray="4 4" />',
            '    <text x="200" y="80" font-family="Inter, sans-serif" font-size="10" fill="#64748b" text-anchor="middle">Liquid Level</text>',
            '  </g>',
            '  <!-- 3. Impeller Agitator -->',
            '  <g>',
            '    <title>Agitator Agitation System\nType: Rushton Turbine (Double Blade)\nDrive Motor: 1.5 kW AC\nPID Speed Control: 0 - 250 rpm</title>',
            '    <!-- Motor block -->',
            '    <rect x="180" y="10" width="40" height="40" rx="3" fill="#ef4444" stroke="#dc2626" stroke-width="2" />',
            '    <text x="200" y="32" font-family="Inter, sans-serif" font-size="10" font-weight="bold" fill="#ffffff" text-anchor="middle">M</text>',
            '    <!-- Shaft -->',
            '    <line x1="200" y1="50" x2="200" y2="210" stroke="#475569" stroke-width="4" />',
            '    <!-- Blade 1 -->',
            '    <line x1="150" y1="150" x2="250" y2="150" stroke="#475569" stroke-width="6" stroke-linecap="round" />',
            '    <rect x="150" y="142" width="12" height="16" fill="#334155" />',
            '    <rect x="238" y="142" width="12" height="16" fill="#334155" />',
            '    <!-- Blade 2 -->',
            '    <line x1="150" y1="190" x2="250" y2="190" stroke="#475569" stroke-width="6" stroke-linecap="round" />',
            '    <rect x="150" y="182" width="12" height="16" fill="#334155" />',
            '    <rect x="238" y="182" width="12" height="16" fill="#334155" />',
            '  </g>',
            '  <!-- Labeling text overlay -->',
            '  <text x="200" y="260" font-family="Inter, sans-serif" font-size="12" font-weight="bold" fill="#334155" text-anchor="middle">Jacketed Bioreactor Vessel (Stirred-Tank)</text>',
            '  <text x="200" y="275" font-family="Inter, sans-serif" font-size="10" fill="#64748b" text-anchor="middle">Hover over parts to inspect calculated dimensions</text>',
            '</svg>'
        ]
        return "\n".join(svg)

    @staticmethod
    def draw_distillation_figure_svg(sizing: dict, result: dict) -> str:
        """
        Draws a detailed vector schematic of a Distillation Column
        with interactive hovers on all parts (shell, trays, condenser, reboiler).
        """
        dia = sizing.get("column_diameter_m", 0.50)
        h = sizing.get("column_height_m", 10.20)
        dp = sizing.get("dp_per_tray_Pa", 800.0)
        total_dp = sizing.get("total_dp_kPa", 9.6)
        dc_backup = sizing.get("downcomer_backup_m", 0.16)
        
        cond_temp = result.get("T", [351.5])[0] if "T" in result else 351.5
        reboiler_temp = result.get("T", [373.15])[-1] if "T" in result else 373.15
        purity = result.get("distillate_x", 0.80)
        
        svg = [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 480" width="100%" height="100%">',
            '  <rect width="400" height="480" fill="#fafafa" stroke="#e2e8f0" stroke-width="1"/>',
            '  <!-- 1. Column Shell -->',
            '  <g>',
            f'    <title>Column Tower Shell\nSized Diameter: {dia:.2f} m\nTotal Height: {h:.2f} m\nASME Material: SS-316\nNumber of Sieve Trays: 12\nTotal Pressure Drop: {total_dp:.2f} kPa</title>',
            '    <rect x="150" y="80" width="100" height="310" rx="15" ry="15" fill="#f1f5f9" stroke="#334155" stroke-width="3" />',
            '  </g>',
            '  <!-- 2. Sieve Trays inside -->',
            '  <g>',
            f'    <title>Sieve Trays Hydraulics\nTray Spacing: 0.60 m\nPressure Drop per Tray: {dp:.1f} Pa\nDowncomer Backup: {dc_backup*1000:.1f} mm\nFlooding Limit Margin: 80%</title>'
        ]
        
        for i in range(1, 10):
            tray_y = 80 + i * 31
            svg.append(f'    <line x1="154" y1="{tray_y}" x2="246" y2="{tray_y}" stroke="#475569" stroke-width="1.5" stroke-dasharray="5 2" />')
            if i % 2 == 0:
                svg.append(f'    <line x1="154" y1="{tray_y}" x2="154" y2="{tray_y+15}" stroke="#475569" stroke-width="2" />')
            else:
                svg.append(f'    <line x1="246" y1="{tray_y}" x2="246" y2="{tray_y+15}" stroke="#475569" stroke-width="2" />')
                
        svg.append('  </g>')
        
        svg.extend([
            '  <!-- 3. Condenser Loop -->',
            '  <g>',
            f'    <title>Overhead Condenser\nCondenser Temp: {cond_temp:.2f} K\nDistillate Purity: {purity*100:.2f} mol%\nReflux Ratio (R/D): 2.5</title>',
            '    <path d="M 200 80 L 200 40 L 300 40 L 300 100 L 250 100" fill="none" stroke="#475569" stroke-width="2" />',
            '    <rect x="275" y="50" width="50" height="30" rx="3" fill="#fee2e2" stroke="#ef4444" stroke-width="2" />',
            '    <text x="300" y="68" font-family="Inter, sans-serif" font-size="9" fill="#991b1b" font-weight="bold" text-anchor="middle">COND</text>',
            '  </g>',
            '  <!-- 4. Reboiler Loop -->',
            '  <g>',
            f'    <title>Bottom Reboiler\nReboiler Temp: {reboiler_temp:.2f} K\nBoilup Ratio: 3.5</title>',
            '    <path d="M 200 390 L 200 430 L 300 430 L 300 370 L 250 370" fill="none" stroke="#475569" stroke-width="2" />',
            '    <rect x="275" y="385" width="50" height="30" rx="3" fill="#fee2e2" stroke="#ef4444" stroke-width="2" />',
            '    <text x="300" y="403" font-family="Inter, sans-serif" font-size="9" fill="#991b1b" font-weight="bold" text-anchor="middle">REB</text>',
            '  </g>',
            '  <!-- Labeling text overlay -->',
            '  <text x="200" y="445" font-family="Inter, sans-serif" font-size="12" font-weight="bold" fill="#334155" text-anchor="middle">Multi-Stage Distillation Column</text>',
            '  <text x="200" y="460" font-family="Inter, sans-serif" font-size="10" fill="#64748b" text-anchor="middle">Hover over shell, condenser, reboiler, or trays to inspect sizing</text>',
            '</svg>'
        ])
        
        return "\n".join(svg)
