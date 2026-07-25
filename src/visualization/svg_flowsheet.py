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
            # Circular body
            svg.append(f'<circle cx="{x+r}" cy="{y+r}" r="{r}" fill="#e0f2fe" stroke="#0ea5e9" stroke-width="2" />')
            # Converging flow lines inside
            svg.append(f'<line x1="{x+5}" y1="{y+5}" x2="{x+r}" y2="{y+r}" stroke="#0ea5e9" stroke-width="1.5" />')
            svg.append(f'<line x1="{x+5}" y1="{y+r*2-5}" x2="{x+r}" y2="{y+r}" stroke="#0ea5e9" stroke-width="1.5" />')
            svg.append(f'<line x1="{x+r}" y1="{y+r}" x2="{x+r*2-5}" y2="{y+r}" stroke="#0ea5e9" stroke-width="2" />')
            # Text label
            svg.append(f'<text x="{x+r}" y="{y+r+4}" font-family="Inter, sans-serif" font-size="10" font-weight="bold" fill="#0f172a" text-anchor="middle">{eq_id}</text>')
            
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
        Generates compiled SVG code representing the whole Flowshet diagram.
        Separates boundary feeds and products and groups them in labeled boxes.
        Includes hover tooltips for all elements.
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
            src = c["from"]
            dst = c["to"]
            s_id = conn_s_id = c["stream"]
            
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
                "stream": conn_s_id
            })
            
        # Classify equipment types
        pumps = []
        valves = []
        mixers = []
        reactors = []
        columns = []
        
        for n, udata in units_dict.items():
            utype = udata["type"]
            if utype == "Pump":
                pumps.append(n)
            elif utype == "ControlValve":
                valves.append(n)
            elif utype == "Mixer":
                mixers.append(n)
            elif utype == "Bioreactor":
                reactors.append(n)
            elif utype == "DistillationColumn":
                columns.append(n)

        # 2. Coordinates mapping (left-to-right columns)
        node_coords = {}
        
        # Column 1: Feeds (x = 80)
        for idx, f in enumerate(sorted(list(feed_nodes))):
            node_coords[f] = (80, 150 + idx * 100)
            
        # Column 2: Pumps (x = 240)
        for idx, p in enumerate(pumps):
            node_coords[p] = (240, 150 + idx * 100)
            
        # Column 3: Valves (x = 360)
        for idx, v in enumerate(valves):
            node_coords[v] = (360, 145 + idx * 100)
            
        # Column 4: Mixers (x = 460)
        for idx, m in enumerate(mixers):
            node_coords[m] = (460, 145 + idx * 100)
            
        # Column 5: Reactors & Columns (x = 600)
        for idx, r in enumerate(reactors):
            node_coords[r] = (600, 150 + idx * 150)
        for idx, c in enumerate(columns):
            node_coords[c] = (600, 120 + idx * 200)
            
        # Column 6: Products (x = 800)
        for idx, pr in enumerate(sorted(list(product_nodes))):
            node_coords[pr] = (800, 120 + idx * 120)

        # SVG Dimensions
        svg_w = 980
        svg_h = 550
        
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
            max_y = max(node_coords[f][1] for f in feed_nodes) + 60
            svg.append(f'  <rect x="50" y="80" width="160" height="{max_y - 60}" rx="8" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4 4" />')
            svg.append('  <text x="130" y="72" font-family="Inter, sans-serif" font-size="11" font-weight="bold" fill="#64748b" text-anchor="middle">Feed Boundaries</text>')
            
        if product_nodes:
            max_y = max(node_coords[pr][1] for pr in product_nodes) + 60
            svg.append(f'  <rect x="770" y="60" width="160" height="{max_y - 20}" rx="8" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4 4" />')
            svg.append('  <text x="850" y="52" font-family="Inter, sans-serif" font-size="11" font-weight="bold" fill="#64748b" text-anchor="middle">Product Boundaries</text>')

        # 4. Draw Connection Streams (Lines with hover tooltips)
        for conn in mapped_connections:
            src = conn["from"]
            dst = conn["to"]
            s_id = conn["stream"]
            
            if src in node_coords and dst in node_coords:
                x1, y1 = node_coords[src]
                x2, y2 = node_coords[dst]
                
                # Offsets based on node types
                # Source adjustments
                src_type = units_dict.get(src, {}).get("type", "Boundary")
                if src.startswith("Feed_"):
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
                elif src_type == "Mixer":
                    x1_offset = x1 + 40
                    y1_offset = y1 + 20
                else:
                    x1_offset = x1
                    y1_offset = y1
                    
                # Destination adjustments
                dst_type = units_dict.get(dst, {}).get("type", "Boundary")
                if dst.startswith("Product_"):
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
                elif dst_type == "Mixer":
                    x2_offset = x2
                    y2_offset = y2 + 20
                else:
                    x2_offset = x2
                    y2_offset = y2
                
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
