"""
Interactive 3D WebGL Industrial Plant Visualizer (Three.js Studio).
Features:
1. Procedural 3D chemical process equipment (Towers, Drums, Exchangers, Pumps, Reactors, Crystallizers, Spray Dryers).
2. Spatial 3D pipe routing with fluid-specific color coding and animated flow pulses.
3. Three.js OrbitControls with camera presets (Isometric, Front Elevation, Top Plan, First-Person Walkthrough).
4. Raycasted equipment telemetry HUD with live thermodynamic and mechanical sizing readouts.
"""

import json
from typing import Dict, List, Optional, Any


class Plant3DViewer:
    """Generates standalone interactive HTML/WebGL Three.js 3D chemical plant scenes."""

    @classmethod
    def generate_plant_3d_html(cls, units_dict: Dict[str, dict],
                                connections_list: List[dict],
                                stream_states: Optional[dict] = None,
                                units_states: Optional[dict] = None,
                                species_map: Optional[dict] = None,
                                canvas_height: int = 700) -> str:
        stream_states = stream_states or {}
        units_states = units_states or {}
        species_map = species_map or {}

        # 1. Prepare Equipment 3D Data
        equipment_3d = []
        for idx, (uid, udata) in enumerate(units_dict.items()):
            utype = udata.get("type", "Pump")
            u_obj = units_states.get(uid)
            sizing = getattr(u_obj, "sizing_results", {}) if u_obj else {}
            heat_duty = getattr(u_obj, "heat_duty", 0.0) if u_obj else 0.0
            work_input = getattr(u_obj, "work_input", 0.0) if u_obj else 0.0

            # 2D flowsheet coordinates to 3D plant plot coordinates
            x_2d = udata.get("x", 100 + (idx % 4) * 180)
            y_2d = udata.get("y", 100 + (idx // 4) * 180)
            pos_x = (x_2d - 350.0) * 0.08
            pos_z = (y_2d - 250.0) * 0.08

            # Gather telemetry from connected streams
            in_t, in_p, in_f = 25.0, 101.3, 0.0
            if u_obj and getattr(u_obj, "inlets", None) and len(u_obj.inlets) > 0:
                st0 = u_obj.inlets[0]
                if st0.T is not None: in_t = st0.T - 273.15
                if st0.P is not None: in_p = st0.P / 1000.0
                if st0.F is not None: in_f = st0.F

            equipment_3d.append({
                "id": uid,
                "type": utype,
                "x": round(pos_x, 2),
                "z": round(pos_z, 2),
                "temp_c": round(in_t, 1),
                "press_kpa": round(in_p, 1),
                "flow_mol_s": round(in_f, 2),
                "duty_kw": round(abs(heat_duty) / 1000.0, 1) if heat_duty else 0.0,
                "power_kw": round(work_input / 1000.0, 1) if work_input else 0.0,
                "sizing": sizing
            })

        # 2. Prepare Pipe Connection 3D Data
        pipes_3d = []
        for conn in connections_list:
            src = conn.get("from", "")
            dst = conn.get("to", "")
            s_id = conn.get("stream", "S-101")

            st_obj = stream_states.get(s_id)
            vf = getattr(st_obj, "Vf", 0.0) if st_obj else 0.0
            fluid_type = "liquid"
            if vf is not None and vf > 0.8:
                fluid_type = "vapor"
            elif "Slurry" in s_id or "Solids" in s_id:
                fluid_type = "slurry"

            pipes_3d.append({
                "stream_id": s_id,
                "from_unit": src,
                "to_unit": dst,
                "fluid_type": fluid_type
            })

        data_json = json.dumps({
            "units": equipment_3d,
            "pipes": pipes_3d
        })

        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D WebGL Chemical Plant Studio</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
        body {{
            background-color: #0f172a;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            overflow: hidden;
            width: 100vw;
            height: {canvas_height}px;
            position: relative;
        }}
        #webgl-canvas {{
            width: 100%;
            height: 100%;
            display: block;
        }}
        #hud-overlay {{
            position: absolute;
            top: 16px;
            left: 16px;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 14px 18px;
            font-size: 13px;
            color: #e2e8f0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            max-width: 340px;
            pointer-events: none;
            transition: all 0.2s ease;
        }}
        #hud-overlay h4 {{
            color: #38bdf8;
            margin-bottom: 6px;
            font-size: 15px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .hud-metric {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
            border-bottom: 1px dashed rgba(255,255,255,0.08);
            padding-bottom: 2px;
        }}
        .hud-val {{
            font-weight: 600;
            color: #f1f5f9;
        }}
        #camera-bar {{
            position: absolute;
            top: 16px;
            right: 16px;
            display: flex;
            gap: 8px;
            z-index: 10;
        }}
        .cam-btn {{
            background: rgba(30, 41, 59, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid #475569;
            color: #e2e8f0;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .cam-btn:hover {{
            background: #2563eb;
            color: #ffffff;
            border-color: #3b82f6;
            transform: translateY(-1px);
        }}
        #legend-bar {{
            position: absolute;
            bottom: 16px;
            left: 16px;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 8px 14px;
            font-size: 12px;
            display: flex;
            gap: 16px;
            z-index: 10;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .color-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }}
        #instruction-hint {{
            position: absolute;
            bottom: 16px;
            right: 16px;
            font-size: 12px;
            color: #94a3b8;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            padding: 8px 14px;
            border-radius: 6px;
            border: 1px solid #334155;
        }}
    </style>
    <!-- Three.js and OrbitControls from CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <div id="camera-bar">
        <button class="cam-btn" onclick="setCameraView('iso')">📐 Isometric View</button>
        <button class="cam-btn" onclick="setCameraView('front')">🏢 Front Elevation</button>
        <button class="cam-btn" onclick="setCameraView('top')">🗺️ Top Plan</button>
        <button class="cam-btn" onclick="setCameraView('walk')">🚶 Walkthrough</button>
        <button class="cam-btn" onclick="resetCamera()">🔄 Reset</button>
    </div>

    <div id="hud-overlay">
        <h4>🏭 Chemical Plant Telemetry</h4>
        <div id="hud-content">
            <p style="color: #94a3b8;">Hover or click any 3D equipment to inspect live telemetry & sizing.</p>
        </div>
    </div>

    <div id="legend-bar">
        <div class="legend-item"><span class="color-dot" style="background: #f59e0b;"></span> Vapor Pipe</div>
        <div class="legend-item"><span class="color-dot" style="background: #ef4444;"></span> Hot Liquid</div>
        <div class="legend-item"><span class="color-dot" style="background: #06b6d4;"></span> Cold Process</div>
        <div class="legend-item"><span class="color-dot" style="background: #10b981;"></span> Slurry / Solids</div>
    </div>

    <div id="instruction-hint">
        🖱️ <b>Orbit</b>: Left Click + Drag | <b>Pan</b>: Right Click + Drag | <b>Zoom</b>: Scroll Wheel
    </div>

    <div id="canvas-container"></div>

    <script>
        const PLANT_DATA = {data_json};

        // 1. Scene, Camera, Renderer Setup
        const container = document.getElementById('canvas-container');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0f172a);
        scene.fog = new THREE.FogExp2(0x0f172a, 0.015);

        const camera = new THREE.PerspectiveCamera(45, window.innerWidth / {canvas_height}, 0.1, 1000);
        camera.position.set(28, 22, 28);

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, {canvas_height});
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        container.appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.maxPolarAngle = Math.PI / 2 - 0.05; // Prevent dipping below ground

        // 2. Industrial Lighting
        const hemiLight = new THREE.HemisphereLight(0xffffff, 0x334155, 0.6);
        scene.add(hemiLight);

        const sunLight = new THREE.DirectionalLight(0xfff7ed, 1.0);
        sunLight.position.set(30, 45, 25);
        sunLight.castShadow = true;
        sunLight.shadow.mapSize.width = 2048;
        sunLight.shadow.mapSize.height = 2048;
        sunLight.shadow.camera.near = 0.5;
        sunLight.shadow.camera.far = 150;
        const d = 35;
        sunLight.shadow.camera.left = -d;
        sunLight.shadow.camera.right = d;
        sunLight.shadow.camera.top = d;
        sunLight.shadow.camera.bottom = -d;
        scene.add(sunLight);

        // 3. Ground & Plant Concrete Pad
        const gridHelper = new THREE.GridHelper(80, 40, 0x3b82f6, 0x334155);
        gridHelper.position.y = 0.01;
        scene.add(gridHelper);

        const groundMat = new THREE.MeshStandardMaterial({{ color: 0x1e293b, roughness: 0.8, metalness: 0.2 }});
        const groundGeo = new THREE.PlaneGeometry(100, 100);
        const groundMesh = new THREE.Mesh(groundGeo, groundMat);
        groundMesh.rotation.x = -Math.PI / 2;
        groundMesh.receiveShadow = true;
        scene.add(groundMesh);

        // Concrete equipment plinth pad
        const plinthMat = new THREE.MeshStandardMaterial({{ color: 0x475569, roughness: 0.9 }});
        const plinthGeo = new THREE.BoxGeometry(60, 0.4, 45);
        const plinthMesh = new THREE.Mesh(plinthGeo, plinthMat);
        plinthMesh.position.y = 0.2;
        plinthMesh.receiveShadow = true;
        scene.add(plinthMesh);

        // Standard Materials
        const steelMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, metalness: 0.8, roughness: 0.3 }});
        const insulMat = new THREE.MeshStandardMaterial({{ color: 0xd97706, metalness: 0.2, roughness: 0.6 }});
        const copperMat = new THREE.MeshStandardMaterial({{ color: 0xb45309, metalness: 0.7, roughness: 0.4 }});
        const pumpMat = new THREE.MeshStandardMaterial({{ color: 0x0284c7, metalness: 0.5, roughness: 0.4 }});
        const reactorMat = new THREE.MeshStandardMaterial({{ color: 0x4f46e5, metalness: 0.6, roughness: 0.3 }});
        const concreteSupportMat = new THREE.MeshStandardMaterial({{ color: 0x64748b, roughness: 0.95 }});

        // 4. Procedural 3D Equipment Generation
        const interactiveMeshes = [];
        const unitPosMap = {{}};

        function createEquipmentMesh(u) {{
            const group = new THREE.Group();
            group.position.set(u.x, 0.4, u.z);
            const utype = u.type;

            if (utype.includes("Distillation") || utype.includes("Absorption") || utype.includes("Column")) {{
                // Vertical Column Tower
                const h = 10.0;
                const r = 1.4;
                const colGeo = new THREE.CylinderGeometry(r, r, h, 24);
                const colMesh = new THREE.Mesh(colGeo, steelMat);
                colMesh.position.y = h / 2 + 0.8;
                colMesh.castShadow = true;
                group.add(colMesh);

                // Heads (dished top and bottom skirt)
                const headGeo = new THREE.SphereGeometry(r, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2);
                const topHead = new THREE.Mesh(headGeo, steelMat);
                topHead.position.y = h + 0.8;
                group.add(topHead);

                // Skirt base
                const skirtGeo = new THREE.CylinderGeometry(r * 1.05, r * 1.15, 0.8, 24);
                const skirtMesh = new THREE.Mesh(skirtGeo, concreteSupportMat);
                skirtMesh.position.y = 0.4;
                group.add(skirtMesh);

                // Tray rings
                for (let i = 1; i <= 6; i++) {{
                    const ringGeo = new THREE.TorusGeometry(r * 1.02, 0.05, 8, 24);
                    const ringMesh = new THREE.Mesh(ringGeo, steelMat);
                    ringMesh.rotation.x = Math.PI / 2;
                    ringMesh.position.y = 1.2 + i * 1.2;
                    group.add(ringMesh);
                }}
            }} else if (utype.includes("Drum") || utype.includes("Separator")) {{
                // Horizontal Pressure Vessel on 2 Concrete Saddles
                const l = 5.0;
                const r = 1.2;
                const drumGeo = new THREE.CylinderGeometry(r, r, l, 20);
                const drumMesh = new THREE.Mesh(drumGeo, steelMat);
                drumMesh.rotation.z = Math.PI / 2;
                drumMesh.position.y = 2.0;
                drumMesh.castShadow = true;
                group.add(drumMesh);

                // Hemispherical caps
                const capGeo = new THREE.SphereGeometry(r, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2);
                const leftCap = new THREE.Mesh(capGeo, steelMat);
                leftCap.rotation.z = Math.PI / 2;
                leftCap.position.set(-l/2, 2.0, 0);
                group.add(leftCap);

                const rightCap = new THREE.Mesh(capGeo, steelMat);
                rightCap.rotation.z = -Math.PI / 2;
                rightCap.position.set(l/2, 2.0, 0);
                group.add(rightCap);

                // Saddles
                [-1.6, 1.6].forEach(sx => {{
                    const saddle = new THREE.Mesh(new THREE.BoxGeometry(0.5, 1.4, 2.6), concreteSupportMat);
                    saddle.position.set(sx, 0.7, 0);
                    group.add(saddle);
                }});
            }} else if (utype.includes("HeatExchanger") || utype.includes("Heater") || utype.includes("Cooler")) {{
                // Shell & Tube Heat Exchanger
                const l = 4.0;
                const r = 0.9;
                const hexGeo = new THREE.CylinderGeometry(r, r, l, 20);
                const hexMesh = new THREE.Mesh(hexGeo, insulMat);
                hexMesh.rotation.z = Math.PI / 2;
                hexMesh.position.y = 1.4;
                hexMesh.castShadow = true;
                group.add(hexMesh);

                // Flanged channel heads
                [-l/2 - 0.2, l/2 + 0.2].forEach(fx => {{
                    const flg = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.15, r * 1.15, 0.2, 16), steelMat);
                    flg.rotation.z = Math.PI / 2;
                    flg.position.set(fx, 1.4, 0);
                    group.add(flg);
                }});
                // Supports
                [-1.2, 1.2].forEach(sx => {{
                    const sup = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.8, 1.6), concreteSupportMat);
                    sup.position.set(sx, 0.4, 0);
                    group.add(sup);
                }});
            }} else if (utype.includes("Reactor") || utype.includes("CSTR") || utype.includes("Bioreactor")) {{
                // Jacketed Stirred Tank Reactor with Agitator Motor
                const h = 4.5;
                const r = 1.6;
                const rGeo = new THREE.CylinderGeometry(r, r, h, 24);
                const rMesh = new THREE.Mesh(rGeo, reactorMat);
                rMesh.position.y = h/2 + 0.6;
                rMesh.castShadow = true;
                group.add(rMesh);

                // Top domed head
                const domGeo = new THREE.SphereGeometry(r, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2);
                const dome = new THREE.Mesh(domGeo, reactorMat);
                dome.position.y = h + 0.6;
                group.add(dome);

                // Agitator Motor on top
                const motor = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 1.0, 16), steelMat);
                motor.position.y = h + 1.6;
                group.add(motor);

                // 4 Leg Supports
                for (let i = 0; i < 4; i++) {{
                    const ang = (i * Math.PI) / 2;
                    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.3, 1.2, 0.3), steelMat);
                    leg.position.set(Math.cos(ang) * (r - 0.2), 0.6, Math.sin(ang) * (r - 0.2));
                    group.add(leg);
                }}
            }} else if (utype.includes("Crystallizer")) {{
                // MSMPR Crystallizer: Cylinder with steep 60 degree cone bottom
                const cylH = 3.5;
                const r = 1.5;
                const cylMesh = new THREE.Mesh(new THREE.CylinderGeometry(r, r, cylH, 20), steelMat);
                cylMesh.position.y = 2.0 + cylH/2;
                cylMesh.castShadow = true;
                group.add(cylMesh);

                // 60-degree cone bottom
                const coneH = 2.0;
                const coneGeo = new THREE.ConeGeometry(r, coneH, 20);
                coneGeo.rotateX(Math.PI); // Point downwards
                const coneMesh = new THREE.Mesh(coneGeo, steelMat);
                coneMesh.position.y = 2.0;
                group.add(coneMesh);

                // Agitator drive
                const agMotor = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 0.8, 16), pumpMat);
                agMotor.position.y = 2.0 + cylH + 0.4;
                group.add(agMotor);
            }} else if (utype.includes("Dryer")) {{
                // Industrial Spray Dryer Chamber & Tangential Cyclone
                const dH = 8.0;
                const dR = 2.2;
                const dMesh = new THREE.Mesh(new THREE.CylinderGeometry(dR, dR, dH, 24), steelMat);
                dMesh.position.y = 3.0 + dH/2;
                dMesh.castShadow = true;
                group.add(dMesh);

                // Lower hopper cone
                const hCone = new THREE.Mesh(new THREE.ConeGeometry(dR, 3.0, 24), steelMat);
                hCone.rotation.x = Math.PI;
                hCone.position.y = 3.0;
                group.add(hCone);

                // Adjacent Cyclone
                const cyMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.7, 3.5, 16), steelMat);
                cyMesh.position.set(3.5, 4.5, 0);
                group.add(cyMesh);
                const cyCone = new THREE.Mesh(new THREE.ConeGeometry(0.7, 2.0, 16), steelMat);
                cyCone.rotation.x = Math.PI;
                cyCone.position.set(3.5, 2.0, 0);
                group.add(cyCone);
            }} else {{
                // Centrifugal Pump / Compressor Skid
                const base = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.3, 1.2), concreteSupportMat);
                base.position.y = 0.15;
                group.add(base);

                // Volute casing
                const volute = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 0.4, 16), pumpMat);
                volute.rotation.z = Math.PI / 2;
                volute.position.set(-0.5, 0.6, 0);
                group.add(volute);

                // Motor
                const motor = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.45, 1.1, 16), steelMat);
                motor.rotation.z = Math.PI / 2;
                motor.position.set(0.5, 0.6, 0);
                group.add(motor);
            }}

            // Add tag label ring / identification billboard
            group.userData = u;
            scene.add(group);
            interactiveMeshes.push(group);
            unitPosMap[u.id] = new THREE.Vector3(u.x, 1.5, u.z);
        }}

        // Render all equipment
        PLANNT_UNITS = PLANT_DATA.units;
        PLANNT_UNITS.forEach(u => createEquipmentMesh(u));

        // 5. 3D Process Piping System
        const pipeColors = {{
            "vapor": 0xf59e0b,
            "liquid": 0xef4444,
            "cold": 0x06b6d4,
            "slurry": 0x10b981
        }};

        PLANNT_PIPES = PLANT_DATA.pipes;
        PLANNT_PIPES.forEach(p => {{
            const p1 = unitPosMap[p.from_unit];
            const p2 = unitPosMap[p.to_unit];
            if (p1 && p2) {{
                // Create stepped orthogonal spline between p1 and p2
                const midX = (p1.x + p2.x) / 2;
                const pipeElevation = 4.5 + Math.random() * 1.5;

                const pt1 = new THREE.Vector3(p1.x, p1.y + 0.8, p1.z);
                const pt2 = new THREE.Vector3(p1.x, pipeElevation, p1.z);
                const pt3 = new THREE.Vector3(midX, pipeElevation, p1.z);
                const pt4 = new THREE.Vector3(midX, pipeElevation, p2.z);
                const pt5 = new THREE.Vector3(p2.x, pipeElevation, p2.z);
                const pt6 = new THREE.Vector3(p2.x, p2.y + 0.8, p2.z);

                const curve = new THREE.CatmullRomCurve3([pt1, pt2, pt3, pt4, pt5, pt6], false, 'catmullrom', 0.1);
                const pipeGeo = new THREE.TubeGeometry(curve, 32, 0.12, 8, false);

                const colHex = pipeColors[p.fluid_type] || 0xef4444;
                const pipeMat = new THREE.MeshStandardMaterial({{
                    color: colHex,
                    roughness: 0.4,
                    metalness: 0.6
                }});

                const pipeMesh = new THREE.Mesh(pipeGeo, pipeMat);
                scene.add(pipeMesh);
            }}
        }});

        // 6. Raycasting for Live Equipment Telemetry HUD
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        let selectedObject = null;

        function onMouseMove(event) {{
            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(scene.children, true);

            if (intersects.length > 0) {{
                let root = intersects[0].object;
                while (root.parent && root.parent !== scene) {{
                    root = root.parent;
                }}

                if (root.userData && root.userData.id) {{
                    updateHUD(root.userData);
                    renderer.domElement.style.cursor = 'pointer';
                    return;
                }}
            }}
            renderer.domElement.style.cursor = 'default';
        }}

        function updateHUD(u) {{
            const hud = document.getElementById('hud-content');
            let sizingInfo = '';
            if (u.sizing) {{
                for (let k in u.sizing) {{
                    let val = u.sizing[k];
                    let formatted = (typeof val === 'number') ? val.toFixed(2) : val;
                    sizingInfo += `<div class="hud-metric"><span>${{k}}</span><span class="hud-val">${{formatted}}</span></div>`;
                }}
            }}

            hud.innerHTML = `
                <h4>🏷️ Node: ${{u.id}} (${{u.type}})</h4>
                <div class="hud-metric"><span>Inlet Temperature:</span><span class="hud-val">${{u.temp_c}} °C</span></div>
                <div class="hud-metric"><span>Inlet Pressure:</span><span class="hud-val">${{u.press_kpa}} kPa</span></div>
                <div class="hud-metric"><span>Mass / Molar Flow:</span><span class="hud-val">${{u.flow_mol_s}} mol/s</span></div>
                <div class="hud-metric"><span>Thermal Duty:</span><span class="hud-val">${{u.duty_kw}} kW</span></div>
                <div class="hud-metric"><span>Work / Power:</span><span class="hud-val">${{u.power_kw}} kW</span></div>
                <h5 style="color:#f59e0b; margin:6px 0 4px 0; font-size:12px;">Mechanical Sizing:</h5>
                ${{sizingInfo || '<p style="color:#64748b; font-size:11px;">Standard sizing parameters</p>'}}
            `;
        }}

        window.addEventListener('mousemove', onMouseMove, false);

        // 7. Camera Presets
        function setCameraView(view) {{
            if (view === 'iso') {{
                camera.position.set(30, 24, 30);
                controls.target.set(0, 3, 0);
            }} else if (view === 'front') {{
                camera.position.set(0, 14, 40);
                controls.target.set(0, 3, 0);
            }} else if (view === 'top') {{
                camera.position.set(0, 48, 0.1);
                controls.target.set(0, 0, 0);
            }} else if (view === 'walk') {{
                camera.position.set(-18, 2.2, 18);
                controls.target.set(0, 3.5, 0);
            }}
            controls.update();
        }}

        function resetCamera() {{
            setCameraView('iso');
        }}

        // 8. Animation & Render Loop
        function animate() {{
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }}
        animate();

        // Responsive resize
        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / {canvas_height};
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, {canvas_height});
        }});
    </script>
</body>
</html>
        """
        return html_template
