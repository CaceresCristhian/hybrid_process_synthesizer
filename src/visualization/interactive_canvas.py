import json
from typing import Dict, List, Optional
from src.visualization.ports import PortRegistry, PortDefinition

class InteractiveCanvasStudio:
    """
    Generates an interactive HTML5/SVG drag-and-drop Flowsheet Design Studio.
    Features:
    1. Draggable equipment nodes on an engineering grid canvas.
    2. Interactive corner resize handles for scaling equipment images/cards.
    3. Port-to-port click-and-drag wiring from outlet nozzles to inlet nozzles.
    4. Support for multiple distinct inlets and outlets (distillate, bottoms, shell, tube, etc.).
    5. Live hover tooltips displaying thermodynamic and sizing data.
    6. Two-way synchronization bridge with Streamlit session state.
    """

    @classmethod
    def render_studio_html(cls, units_dict: Dict[str, dict], 
                            connections_list: List[dict],
                            stream_states: Optional[dict] = None,
                            units_states: Optional[dict] = None,
                            species_map: Optional[dict] = None,
                            canvas_height: int = 700) -> str:
        stream_states = stream_states or {}
        units_states = units_states or {}
        species_map = species_map or {}

        nodes_data = {}
        for idx, (uid, udata) in enumerate(units_dict.items()):
            utype = udata.get("type", "Pump")
            default_dim = PortRegistry.get_default_dimensions(utype)
            w = udata.get("width", default_dim["width"])
            h = udata.get("height", default_dim["height"])
            
            x = udata.get("x", 80 + (idx % 5) * 190)
            y = udata.get("y", 70 + (idx // 5) * 190)
            
            ports_raw = PortRegistry.get_ports(utype)
            ports_json = [
                {
                    "id": p.id,
                    "label": p.label,
                    "type": p.type,
                    "x_rel": p.x_rel,
                    "y_rel": p.y_rel,
                    "fluid_hint": p.fluid_hint
                }
                for p in ports_raw
            ]
            
            u_obj = units_states.get(uid)
            sizing_data = getattr(u_obj, "sizing_results", {}) if u_obj else {}
            heat_duty = getattr(u_obj, "heat_duty", 0.0) if u_obj else 0.0
            work_input = getattr(u_obj, "work_input", 0.0) if u_obj else 0.0

            nodes_data[uid] = {
                "id": uid,
                "type": utype,
                "thermo": udata.get("thermo", "Ideal"),
                "variation": udata.get("variation", "Standard"),
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "ports": ports_json,
                "sizing": sizing_data,
                "heat_duty_kW": round(heat_duty / 1000.0, 2),
                "work_input_kW": round(work_input / 1000.0, 2)
            }

        connections_data = []
        for conn in connections_list:
            src = conn.get("from", "")
            dst = conn.get("to", "")
            s_id = conn.get("stream", "S-101")
            
            src_type = units_dict.get(src, {}).get("type", "Pump") if src in units_dict else "Feed Boundary"
            dst_type = units_dict.get(dst, {}).get("type", "Pump") if dst in units_dict else "Product Boundary"
            
            from_port = conn.get("from_port") or PortRegistry.get_default_port_id(src_type, "outlet")
            to_port = conn.get("to_port") or PortRegistry.get_default_port_id(dst_type, "inlet")
            
            s_obj = stream_states.get(s_id)
            flow_val = getattr(s_obj, "F", None) if s_obj else None
            temp_val = getattr(s_obj, "T", None) if s_obj else None
            press_val = getattr(s_obj, "P", None) if s_obj else None
            z_dict = getattr(s_obj, "z", {}) if s_obj else {}
            
            connections_data.append({
                "stream": s_id,
                "from": src,
                "from_port": from_port,
                "to": dst,
                "to_port": to_port,
                "flow_mol_s": round(flow_val, 2) if flow_val is not None else None,
                "temp_K": round(temp_val, 1) if temp_val is not None else None,
                "press_kPa": round(press_val / 1000.0, 1) if press_val is not None else None,
                "compositions": {k: round(v, 3) for k, v in z_dict.items()} if z_dict else {}
            })

        nodes_json_str = json.dumps(nodes_data)
        conns_json_str = json.dumps(connections_data)

        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    user-select: none;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  body {
    background-color: #0b1329;
    color: #e2e8f0;
    overflow: hidden;
    height: __CANVAS_HEIGHT__px;
  }
  .studio-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    border: 1px solid #1e293b;
    border-radius: 8px;
    background: radial-gradient(circle at 50% 50%, #0f172a 0%, #080d1a 100%);
    position: relative;
  }
  .studio-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 16px;
    background-color: #0f172a;
    border-bottom: 1px solid #1e293b;
    z-index: 20;
  }
  .toolbar-left, .toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .tool-btn {
    background-color: #1e293b;
    border: 1px solid #334155;
    color: #cbd5e1;
    padding: 5px 10px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.15s ease;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .tool-btn:hover {
    background-color: #334155;
    color: #ffffff;
    border-color: #0ea5e9;
  }
  .tool-btn.active {
    background-color: #0369a1;
    color: #ffffff;
    border-color: #38bdf8;
  }
  .status-pill {
    font-size: 11px;
    background-color: #1e293b;
    padding: 4px 10px;
    border-radius: 12px;
    color: #94a3b8;
    border: 1px solid #334155;
  }
  .viewport {
    flex: 1;
    width: 100%;
    height: 100%;
    overflow: hidden;
    position: relative;
    cursor: grab;
  }
  .viewport:active {
    cursor: grabbing;
  }
  svg.flowsheet-canvas {
    width: 100%;
    height: 100%;
    transform-origin: 0 0;
  }
  .grid-pattern {
    stroke: rgba(51, 65, 85, 0.4);
    stroke-width: 0.75;
  }
  .grid-pattern-major {
    stroke: rgba(51, 65, 85, 0.7);
    stroke-width: 1.2;
  }
  .node-group {
    cursor: move;
  }
  .node-card {
    fill: #131d35;
    stroke: #334155;
    stroke-width: 1.5;
    rx: 8;
    ry: 8;
    filter: drop-shadow(0 4px 8px rgba(0,0,0,0.5));
    transition: stroke 0.15s ease, fill 0.15s ease;
  }
  .node-group:hover .node-card, .node-group.selected .node-card {
    stroke: #38bdf8;
    stroke-width: 2.2;
    fill: #162444;
  }
  .node-header {
    font-size: 11px;
    font-weight: 700;
    fill: #38bdf8;
    text-anchor: middle;
  }
  .node-subtext {
    font-size: 9px;
    font-weight: 500;
    fill: #94a3b8;
    text-anchor: middle;
  }
  .port-circle {
    r: 5.5;
    stroke-width: 2;
    cursor: crosshair;
    transition: r 0.15s ease, filter 0.15s ease;
  }
  .port-inlet {
    fill: #064e3b;
    stroke: #10b981;
  }
  .port-outlet {
    fill: #7c2d12;
    stroke: #f97316;
  }
  .port-circle:hover, .port-circle.highlight {
    r: 8.5;
    filter: drop-shadow(0 0 8px #38bdf8);
    stroke-width: 2.5;
  }
  .resize-handle {
    fill: #38bdf8;
    cursor: nwse-resize;
    opacity: 0.4;
    transition: opacity 0.15s ease;
  }
  .node-group:hover .resize-handle, .node-group.selected .resize-handle {
    opacity: 1.0;
  }
  .stream-wire {
    fill: none;
    stroke: #0284c7;
    stroke-width: 2.5;
    stroke-linecap: round;
    cursor: pointer;
    transition: stroke 0.15s ease, stroke-width 0.15s ease;
  }
  .stream-wire:hover, .stream-wire.selected {
    stroke: #38bdf8;
    stroke-width: 4.0;
    filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.6));
  }
  .stream-wire-active {
    fill: none;
    stroke: #f59e0b;
    stroke-width: 2.5;
    stroke-dasharray: 6 3;
    pointer-events: none;
  }
  .stream-badge {
    fill: #0f172a;
    stroke: #0284c7;
    stroke-width: 1.2;
    rx: 4;
    cursor: pointer;
  }
  .stream-badge-text {
    font-size: 9.5px;
    font-weight: 700;
    fill: #7dd3fc;
    text-anchor: middle;
    pointer-events: none;
  }
  .hud-tooltip {
    position: absolute;
    display: none;
    background: rgba(15, 23, 42, 0.94);
    border: 1px solid #0284c7;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 11px;
    color: #f8fafc;
    box-shadow: 0 8px 24px rgba(0,0,0,0.6);
    pointer-events: none;
    z-index: 50;
    max-width: 280px;
    backdrop-filter: blur(4px);
  }
  .hud-title {
    font-weight: 700;
    color: #38bdf8;
    margin-bottom: 4px;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 2px;
  }
  .hud-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 2px;
  }
  .hud-label {
    color: #94a3b8;
  }
  .hud-val {
    font-weight: 600;
  }
  .modal-backdrop {
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,0.7);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }
  .modal-box {
    background: #0f172a;
    border: 1px solid #38bdf8;
    border-radius: 8px;
    padding: 16px 20px;
    width: 320px;
    box-shadow: 0 12px 32px rgba(0,0,0,0.8);
  }
  .modal-input {
    width: 100%;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 4px;
    color: #ffffff;
    padding: 6px 10px;
    margin: 10px 0 16px 0;
    font-size: 13px;
  }
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
</style>
</head>
<body>

<div class="studio-container">
  <div class="studio-toolbar">
    <div class="toolbar-left">
      <span style="font-weight: 700; color: #38bdf8; font-size: 13px;">[Interactive Flowsheet Studio]</span>
      <span class="status-pill" id="status-text">Drag nodes to position | Drag orange port to green port to link</span>
    </div>
    <div class="toolbar-right">
      <button class="tool-btn" id="btn-zoom-in">Zoom In (+)</button>
      <button class="tool-btn" id="btn-zoom-out">Zoom Out (-)</button>
      <button class="tool-btn" id="btn-zoom-reset">Reset View</button>
      <button class="tool-btn" id="btn-export-sync">Copy / Sync Config</button>
    </div>
  </div>

  <div class="viewport" id="viewport">
    <svg class="flowsheet-canvas" id="canvas">
      <defs>
        <pattern id="smallGrid" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M 20 0 L 0 0 0 20" fill="none" class="grid-pattern" />
        </pattern>
        <pattern id="grid" width="100" height="100" patternUnits="userSpaceOnUse">
          <rect width="100" height="100" fill="url(#smallGrid)" />
          <path d="M 100 0 L 0 0 0 100" fill="none" class="grid-pattern-major" />
        </pattern>
        <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#0284c7" />
        </marker>
        <marker id="arrow-active" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#f59e0b" />
        </marker>
      </defs>

      <rect x="-2000" y="-2000" width="6000" height="6000" fill="url(#grid)" />
      <g id="wires-layer"></g>
      <path id="active-wire" class="stream-wire-active" d="" marker-end="url(#arrow-active)" style="display: none;" />
      <g id="nodes-layer"></g>
    </svg>
  </div>

  <div class="hud-tooltip" id="hud-tooltip"></div>

  <div class="modal-backdrop" id="stream-modal">
    <div class="modal-box">
      <h3 style="color:#38bdf8; font-size:14px; margin-bottom:4px;">Connect New Stream</h3>
      <p id="modal-desc" style="font-size:11px; color:#94a3b8;"></p>
      <input type="text" id="modal-stream-id" class="modal-input" value="S-101" />
      <div class="modal-actions">
        <button class="tool-btn" id="modal-cancel">Cancel</button>
        <button class="tool-btn active" id="modal-confirm">Confirm Connection</button>
      </div>
    </div>
  </div>
</div>

<script>
  const nodes = __NODES_DATA__;
  let connections = __CONNS_DATA__;

  const canvas = document.getElementById("canvas");
  const viewport = document.getElementById("viewport");
  const nodesLayer = document.getElementById("nodes-layer");
  const wiresLayer = document.getElementById("wires-layer");
  const activeWire = document.getElementById("active-wire");
  const hudTooltip = document.getElementById("hud-tooltip");
  const statusText = document.getElementById("status-text");

  let scale = 1.0;
  let panX = 0;
  let panY = 0;
  let isPanning = false;
  let panStartX = 0;
  let panStartY = 0;

  let isDraggingNode = false;
  let draggedNodeId = null;
  let dragOffset = { x: 0, y: 0 };

  let isResizing = false;
  let resizingNodeId = null;
  let resizeStartDim = { w: 0, h: 0, mouseX: 0, mouseY: 0 };

  let isConnecting = false;
  let wireStart = null;
  let pendingConnection = null;

  function updateTransform() {
    canvas.style.transform = "translate(" + panX + "px, " + panY + "px) scale(" + scale + ")";
  }

  function screenToCanvas(screenX, screenY) {
    const rect = viewport.getBoundingClientRect();
    return {
      x: (screenX - rect.left - panX) / scale,
      y: (screenY - rect.top - panY) / scale
    };
  }

  function getPortCoords(nodeId, portId) {
    const node = nodes[nodeId];
    if (!node) return { x: 0, y: 0 };
    const port = node.ports.find(p => p.id === portId) || node.ports[0];
    return {
      x: node.x + port.x_rel * node.width,
      y: node.y + port.y_rel * node.height
    };
  }

  function makeBezierPath(x1, y1, x2, y2) {
    const dx = Math.max(40, Math.abs(x2 - x1) * 0.5);
    return "M " + x1 + " " + y1 + " C " + (x1 + dx) + " " + y1 + ", " + (x2 - dx) + " " + y2 + ", " + x2 + " " + y2;
  }

  function renderAll() {
    renderWires();
    renderNodes();
  }

  function renderNodes() {
    nodesLayer.innerHTML = "";
    Object.values(nodes).forEach(node => {
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("class", "node-group");
      g.setAttribute("data-id", node.id);
      g.setAttribute("transform", "translate(" + node.x + ", " + node.y + ")");

      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("class", "node-card");
      rect.setAttribute("width", node.width);
      rect.setAttribute("height", node.height);
      g.appendChild(rect);

      const title = document.createElementNS("http://www.w3.org/2000/svg", "text");
      title.setAttribute("class", "node-header");
      title.setAttribute("x", node.width / 2);
      title.setAttribute("y", 18);
      title.textContent = node.id;
      g.appendChild(title);

      const sub = document.createElementNS("http://www.w3.org/2000/svg", "text");
      sub.setAttribute("class", "node-subtext");
      sub.setAttribute("x", node.width / 2);
      sub.setAttribute("y", 30);
      sub.textContent = node.type;
      g.appendChild(sub);

      if (node.heat_duty_kW !== 0 || node.work_input_kW !== 0) {
        const dutyText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        dutyText.setAttribute("class", "node-subtext");
        dutyText.setAttribute("x", node.width / 2);
        dutyText.setAttribute("y", node.height - 12);
        dutyText.setAttribute("fill", "#38bdf8");
        const val = node.heat_duty_kW !== 0 ? ("Q: " + node.heat_duty_kW + " kW") : ("W: " + node.work_input_kW + " kW");
        dutyText.textContent = val;
        g.appendChild(dutyText);
      }

      node.ports.forEach(port => {
        const px = port.x_rel * node.width;
        const py = port.y_rel * node.height;

        const portCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        portCircle.setAttribute("cx", px);
        portCircle.setAttribute("cy", py);
        portCircle.setAttribute("class", "port-circle port-" + port.type);
        portCircle.setAttribute("data-node", node.id);
        portCircle.setAttribute("data-port", port.id);
        portCircle.setAttribute("data-type", port.type);
        g.appendChild(portCircle);
      });

      const resizeHandle = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
      resizeHandle.setAttribute("class", "resize-handle");
      const rw = node.width;
      const rh = node.height;
      resizeHandle.setAttribute("points", rw + "," + (rh - 12) + " " + rw + "," + rh + " " + (rw - 12) + "," + rh);
      resizeHandle.setAttribute("data-node", node.id);
      g.appendChild(resizeHandle);

      nodesLayer.appendChild(g);
    });
  }

  function renderWires() {
    wiresLayer.innerHTML = "";
    connections.forEach((conn, idx) => {
      const p1 = getPortCoords(conn.from, conn.from_port);
      const p2 = getPortCoords(conn.to, conn.to_port);
      if (!p1.x && !p1.y) return;

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("class", "stream-wire");
      path.setAttribute("d", makeBezierPath(p1.x, p1.y, p2.x, p2.y));
      path.setAttribute("marker-end", "url(#arrow)");
      path.setAttribute("data-idx", idx);
      wiresLayer.appendChild(path);

      const midX = (p1.x + p2.x) / 2;
      const midY = (p1.y + p2.y) / 2;
      const badgeW = 46;
      const badgeH = 18;

      const badgeRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      badgeRect.setAttribute("class", "stream-badge");
      badgeRect.setAttribute("x", midX - badgeW/2);
      badgeRect.setAttribute("y", midY - badgeH/2);
      badgeRect.setAttribute("width", badgeW);
      badgeRect.setAttribute("height", badgeH);
      badgeRect.setAttribute("data-idx", idx);
      wiresLayer.appendChild(badgeRect);

      const badgeText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      badgeText.setAttribute("class", "stream-badge-text");
      badgeText.setAttribute("x", midX);
      badgeText.setAttribute("y", midY + 3.5);
      badgeText.textContent = conn.stream;
      wiresLayer.appendChild(badgeText);
    });
  }

  viewport.addEventListener("mousedown", (e) => {
    const target = e.target;
    const pt = screenToCanvas(e.clientX, e.clientY);

    if (target.classList.contains("port-circle")) {
      const ptype = target.getAttribute("data-type");
      if (ptype === "outlet") {
        const nid = target.getAttribute("data-node");
        const pid = target.getAttribute("data-port");
        const pcoords = getPortCoords(nid, pid);
        isConnecting = true;
        wireStart = { nodeId: nid, portId: pid, x: pcoords.x, y: pcoords.y };
        activeWire.style.display = "block";
        activeWire.setAttribute("d", makeBezierPath(pcoords.x, pcoords.y, pt.x, pt.y));
        statusText.textContent = "Connecting from " + nid + " [" + pid + "]... Drop on an inlet nozzle.";
        e.stopPropagation();
        return;
      }
    }

    if (target.classList.contains("resize-handle")) {
      const nid = target.getAttribute("data-node");
      isResizing = true;
      resizingNodeId = nid;
      resizeStartDim = {
        w: nodes[nid].width,
        h: nodes[nid].height,
        mouseX: e.clientX,
        mouseY: e.clientY
      };
      e.stopPropagation();
      return;
    }

    const nodeGroup = target.closest(".node-group");
    if (nodeGroup) {
      const nid = nodeGroup.getAttribute("data-id");
      isDraggingNode = true;
      draggedNodeId = nid;
      dragOffset = {
        x: pt.x - nodes[nid].x,
        y: pt.y - nodes[nid].y
      };
      e.stopPropagation();
      return;
    }

    isPanning = true;
    panStartX = e.clientX - panX;
    panStartY = e.clientY - panY;
  });

  window.addEventListener("mousemove", (e) => {
    const pt = screenToCanvas(e.clientX, e.clientY);

    if (isConnecting && wireStart) {
      activeWire.setAttribute("d", makeBezierPath(wireStart.x, wireStart.y, pt.x, pt.y));
      return;
    }

    if (isResizing && resizingNodeId) {
      const dw = (e.clientX - resizeStartDim.mouseX) / scale;
      const dh = (e.clientY - resizeStartDim.mouseY) / scale;
      nodes[resizingNodeId].width = Math.max(60, Math.min(260, resizeStartDim.w + dw));
      nodes[resizingNodeId].height = Math.max(50, Math.min(280, resizeStartDim.h + dh));
      renderAll();
      return;
    }

    if (isDraggingNode && draggedNodeId) {
      nodes[draggedNodeId].x = pt.x - dragOffset.x;
      nodes[draggedNodeId].y = pt.y - dragOffset.y;
      renderAll();
      return;
    }

    if (isPanning) {
      panX = e.clientX - panStartX;
      panY = e.clientY - panStartY;
      updateTransform();
    }
  });

  window.addEventListener("mouseup", (e) => {
    if (isConnecting) {
      isConnecting = false;
      activeWire.style.display = "none";
      const target = document.elementFromPoint(e.clientX, e.clientY);
      if (target && target.classList.contains("port-circle")) {
        const targetType = target.getAttribute("data-type");
        const targetNode = target.getAttribute("data-node");
        const targetPort = target.getAttribute("data-port");

        if (targetType === "inlet" && targetNode !== wireStart.nodeId) {
          const autoStreamId = "S-" + (connections.length + 101);
          pendingConnection = {
            from: wireStart.nodeId,
            from_port: wireStart.portId,
            to: targetNode,
            to_port: targetPort,
            stream: autoStreamId
          };
          document.getElementById("modal-desc").textContent = 
            "Connect " + wireStart.nodeId + " (" + wireStart.portId + ") -> " + targetNode + " (" + targetPort + ")";
          document.getElementById("modal-stream-id").value = autoStreamId;
          document.getElementById("stream-modal").style.display = "flex";
        }
      }
      statusText.textContent = "Flowsheet Studio Ready";
    }

    isDraggingNode = false;
    draggedNodeId = null;
    isResizing = false;
    resizingNodeId = null;
    isPanning = false;
  });

  document.getElementById("modal-confirm").addEventListener("click", () => {
    if (pendingConnection) {
      const customId = document.getElementById("modal-stream-id").value.trim() || pendingConnection.stream;
      pendingConnection.stream = customId;
      connections.push(pendingConnection);
      pendingConnection = null;
      renderAll();
      syncStateToStorage();
    }
    document.getElementById("stream-modal").style.display = "none";
  });

  document.getElementById("modal-cancel").addEventListener("click", () => {
    pendingConnection = null;
    document.getElementById("stream-modal").style.display = "none";
  });

  document.getElementById("btn-zoom-in").addEventListener("click", () => {
    scale = Math.min(2.5, scale * 1.2);
    updateTransform();
  });
  document.getElementById("btn-zoom-out").addEventListener("click", () => {
    scale = Math.max(0.4, scale / 1.2);
    updateTransform();
  });
  document.getElementById("btn-zoom-reset").addEventListener("click", () => {
    scale = 1.0;
    panX = 0;
    panY = 0;
    updateTransform();
  });

  function syncStateToStorage() {
    const exportState = {
      units: Object.fromEntries(Object.entries(nodes).map(([k, v]) => [k, {
        type: v.type,
        thermo: v.thermo,
        variation: v.variation,
        x: Math.round(v.x),
        y: Math.round(v.y),
        width: Math.round(v.width),
        height: Math.round(v.height)
      }])),
      connections: connections.map(c => ({
        stream: c.stream,
        from: c.from,
        from_port: c.from_port,
        to: c.to,
        to_port: c.to_port
      }))
    };
    const jsonString = JSON.stringify(exportState);
    try {
      localStorage.setItem("hps_canvas_sync", jsonString);
    } catch(e) {}
    return jsonString;
  }

  document.getElementById("btn-export-sync").addEventListener("click", () => {
    const jsonString = syncStateToStorage();
    navigator.clipboard.writeText(jsonString).then(() => {
      statusText.textContent = "[OK] Flowsheet layout copied to clipboard & synced!";
    }).catch(() => {
      statusText.textContent = "[OK] Flowsheet layout saved locally.";
    });
  });

  viewport.addEventListener("mousemove", (e) => {
    const target = e.target;
    const nodeGroup = target.closest(".node-group");
    if (nodeGroup && !isDraggingNode && !isConnecting && !isResizing) {
      const nid = nodeGroup.getAttribute("data-id");
      const node = nodes[nid];
      if (node) {
        let rows = "<div class='hud-title'>" + node.id + " (" + node.type + ")</div>";
        rows += "<div class='hud-row'><span class='hud-label'>Fluid Base:</span><span class='hud-val'>" + node.thermo + "</span></div>";
        rows += "<div class='hud-row'><span class='hud-label'>Dimensions:</span><span class='hud-val'>" + Math.round(node.width) + " x " + Math.round(node.height) + " px</span></div>";
        if (node.heat_duty_kW) rows += "<div class='hud-row'><span class='hud-label'>Heat Duty:</span><span class='hud-val'>" + node.heat_duty_kW + " kW</span></div>";
        if (node.work_input_kW) rows += "<div class='hud-row'><span class='hud-label'>Work Input:</span><span class='hud-val'>" + node.work_input_kW + " kW</span></div>";
        Object.entries(node.sizing || {}).slice(0, 4).forEach(([k, v]) => {
          const val = typeof v === "number" ? v.toFixed(2) : v;
          rows += "<div class='hud-row'><span class='hud-label'>" + k + ":</span><span class='hud-val'>" + val + "</span></div>";
        });
        hudTooltip.innerHTML = rows;
        hudTooltip.style.left = (e.clientX + 14) + "px";
        hudTooltip.style.top = (e.clientY + 14) + "px";
        hudTooltip.style.display = "block";
        return;
      }
    }

    if (target.classList.contains("stream-wire") || target.classList.contains("stream-badge")) {
      const idx = target.getAttribute("data-idx");
      const conn = connections[idx];
      if (conn) {
        let rows = "<div class='hud-title'>Stream: " + conn.stream + "</div>";
        rows += "<div class='hud-row'><span class='hud-label'>Route:</span><span class='hud-val'>" + conn.from + " (" + conn.from_port + ") -> " + conn.to + " (" + conn.to_port + ")</span></div>";
        if (conn.flow_mol_s !== null) rows += "<div class='hud-row'><span class='hud-label'>Molar Flow:</span><span class='hud-val'>" + conn.flow_mol_s + " mol/s</span></div>";
        if (conn.temp_K !== null) rows += "<div class='hud-row'><span class='hud-label'>Temperature:</span><span class='hud-val'>" + conn.temp_K + " K</span></div>";
        if (conn.press_kPa !== null) rows += "<div class='hud-row'><span class='hud-label'>Pressure:</span><span class='hud-val'>" + conn.press_kPa + " kPa</span></div>";
        hudTooltip.innerHTML = rows;
        hudTooltip.style.left = (e.clientX + 14) + "px";
        hudTooltip.style.top = (e.clientY + 14) + "px";
        hudTooltip.style.display = "block";
        return;
      }
    }

    hudTooltip.style.display = "none";
  });

  renderAll();
</script>
</body>
</html>
"""
        html_code = html_template.replace("__CANVAS_HEIGHT__", str(canvas_height))
        html_code = html_code.replace("__NODES_DATA__", nodes_json_str)
        html_code = html_code.replace("__CONNS_DATA__", conns_json_str)
        return html_code
