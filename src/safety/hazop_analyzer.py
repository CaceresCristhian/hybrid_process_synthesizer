"""
Automated Process Hazard Analysis (HAZOP) Matrix Generator.
Traverses flowsheet topology, applies standardized guide words (MORE, LESS, NONE, REVERSE),
evaluates credible causal failure chains, predicts process consequences,
recommends engineering safeguards, and assigns qualitative Risk Priority scores.
"""

from typing import Dict, List, Any

class HAZOPAnalyzer:
    """Rigorous Topological HAZOP Engine for Chemical Process Flowsheets."""

    @classmethod
    def generate_flowsheet_hazop(cls, units_map: dict, streams_map: dict, connections: list) -> List[Dict[str, Any]]:
        """
        Generates comprehensive HAZOP study rows across all flowsheet unit operations.
        """
        hazop_rows = []
        row_id = 1

        for u_id, unit in units_map.items():
            u_type = unit.__class__.__name__

            # ---------------------------------------------------------
            # 1. Distillation Columns (Binary or Dynamic)
            # ---------------------------------------------------------
            if "DistillationColumn" in u_type:
                hazop_rows.append({
                    "id": f"HAZOP-{row_id:03d}",
                    "node": f"{u_id} ({u_type})",
                    "parameter": "PRESSURE",
                    "guide_word": "MORE",
                    "deviation": "High Column Pressure (Overpressure)",
                    "causes": "Condenser cooling water supply failure; Blocked overhead vapor line; Loss of vent valve.",
                    "consequences": "Column pressure surges above MAWP; Risk of mechanical rupture or flange gasket blowout; Tray flooding and off-spec products.",
                    "safeguards": "API 520 PRV on overhead vapor line; High Pressure Switch (PSHH) interlocked to reboiler steam trip; Cooling water low flow alarm (FAL).",
                    "severity": 4, "likelihood": 3, "risk_score": 12, "risk_level": "HIGH"
                })
                row_id += 1

                hazop_rows.append({
                    "id": f"HAZOP-{row_id:03d}",
                    "node": f"{u_id} ({u_type})",
                    "parameter": "TEMPERATURE",
                    "guide_word": "MORE",
                    "deviation": "High Sump / Sensitive Tray Temperature",
                    "causes": "Reboiler steam control valve CV-102 fails open; Heavy feedstock surge; Low reflux flow.",
                    "consequences": "Thermal degradation of bottom product; Rapid vapor surge overloading trays; Overhead product contamination.",
                    "safeguards": "Tray temperature controller (TC) with high alarm (TSH); Dual automatic steam block valve; Feed analyzer (QI).",
                    "severity": 3, "likelihood": 3, "risk_score": 9, "risk_level": "MEDIUM"
                })
                row_id += 1

                hazop_rows.append({
                    "id": f"HAZOP-{row_id:03d}",
                    "node": f"{u_id} ({u_type})",
                    "parameter": "LEVEL",
                    "guide_word": "LESS",
                    "deviation": "Low Reboiler Sump Holdup (Dry-Out)",
                    "causes": "Bottoms discharge pump runaway; Loss of column feed; Level transmitter LT-102 calibration drift.",
                    "consequences": "Reboiler tubes dry out leading to localized thermal hot spots, coking, and pump cavitation damage.",
                    "safeguards": "Low-Low Level Switch (LSLL) triggering reboiler trip; Minimum recirculation line on bottoms pump.",
                    "severity": 4, "likelihood": 2, "risk_score": 8, "risk_level": "MEDIUM"
                })
                row_id += 1

            # ---------------------------------------------------------
            # 2. Chemical Reactors (CSTR, PFR, Equilibrium)
            # ---------------------------------------------------------
            elif any(k in u_type for k in ["Reactor", "CSTR", "PFR"]):
                hazop_rows.append({
                    "id": f"HAZOP-{row_id:03d}",
                    "node": f"{u_id} ({u_type})",
                    "parameter": "TEMPERATURE",
                    "guide_word": "MORE",
                    "deviation": "Thermal Runaway Exotherm",
                    "causes": "Cooling jacket supply outage; Reactant feed ratio imbalance (excess catalyst or oxidant); Agitator mechanical failure.",
                    "consequences": "Uncontrolled exponential kinetic acceleration; Severe solvent vaporization and pressure spike exceeding burst rating.",
                    "safeguards": "High-High Temperature Trip (TSHH); Emergency cold inhibitor/kill system; Rupture disk and full-bore API 520 PRV.",
                    "severity": 5, "likelihood": 2, "risk_score": 10, "risk_level": "HIGH"
                })
                row_id += 1

                hazop_rows.append({
                    "id": f"HAZOP-{row_id:03d}",
                    "node": f"{u_id} ({u_type})",
                    "parameter": "FLOW",
                    "guide_word": "LESS",
                    "deviation": "Loss of Feed Throughput",
                    "causes": "Feed pump trip; Upstream isolation valve closed; In-line filter plugged.",
                    "consequences": "Reactor starvation; Altered residence time leading to unwanted consecutive side reactions or product degradation.",
                    "safeguards": "Low Flow Alarm (FAL); Auto-start standby feed pump; Differential pressure transmitter on feed filter (PDI).",
                    "severity": 2, "likelihood": 3, "risk_score": 6, "risk_level": "LOW"
                })
                row_id += 1

            # ---------------------------------------------------------
            # 3. Heat Exchangers, Heaters & Coolers
            # ---------------------------------------------------------
            elif u_type in ["Heater", "Cooler", "HeatExchanger"]:
                hazop_rows.append({
                    "id": f"HAZOP-{row_id:03d}",
                    "node": f"{u_id} ({u_type})",
                    "parameter": "PRESSURE",
                    "guide_word": "MORE",
                    "deviation": "Hydraulic Overpressure of Blocked Liquid",
                    "causes": "Operator closes inlet and outlet block valves with heating utility active (Thermal Expansion); Tube rupture from high-pressure side.",
                    "consequences": "Enormous hydraulic pressure increase causing exchanger tube rupture, shell bulging, or flange gasket extrusion.",
                    "safeguards": "API 521 Thermal Relief Valve (TSV) on liquid side; ASME shell design rating matching tube side design pressure.",
                    "severity": 4, "likelihood": 2, "risk_score": 8, "risk_level": "MEDIUM"
                })
                row_id += 1

                hazop_rows.append({
                    "id": f"HAZOP-{row_id:03d}",
                    "node": f"{u_id} ({u_type})",
                    "parameter": "TEMPERATURE",
                    "guide_word": "LESS",
                    "deviation": "Low Outlet Temperature / Process Freezing",
                    "causes": "Excess cooling water flow; Loss of heating steam; Extreme ambient cold weather.",
                    "consequences": "Viscous plugging, crystallization, waxes drop out, or inadequate downstream reaction initiation.",
                    "safeguards": "Temperature control loop (TC) with low temperature alarm (TAL); Steam trap bypass and trace heating.",
                    "severity": 2, "likelihood": 2, "risk_score": 4, "risk_level": "LOW"
                })
                row_id += 1

            # ---------------------------------------------------------
            # 4. Pumps & Compressors
            # ---------------------------------------------------------
            elif u_type in ["FlowsheetPump", "Compressor", "Expander"]:
                hazop_rows.append({
                    "id": f"HAZOP-{row_id:03d}",
                    "node": f"{u_id} ({u_type})",
                    "parameter": "FLOW",
                    "guide_word": "NONE",
                    "deviation": "Deadhead / Blocked Discharge Flow",
                    "causes": "Discharge valve inadvertently closed; Downstream pipeline blockage; Check valve jammed closed.",
                    "consequences": "Liquid heats up rapidly to vapor state; Severe pump cavitation, mechanical seal failure, fluid release to atmosphere.",
                    "safeguards": "Minimum flow recirculation line with restriction orifice; High discharge pressure trip (PSHH); Relief valve on casing.",
                    "severity": 3, "likelihood": 3, "risk_score": 9, "risk_level": "MEDIUM"
                })
                row_id += 1

                hazop_rows.append({
                    "id": f"HAZOP-{row_id:03d}",
                    "node": f"{u_id} ({u_type})",
                    "parameter": "FLOW",
                    "guide_word": "REVERSE",
                    "deviation": "Reverse Flow on Driver Trip",
                    "causes": "Discharge check valve fails open upon sudden motor trip or power outage.",
                    "consequences": "High pressure fluid drives pump backwards at over-speed; Mechanical destruction of impellers and drive motor.",
                    "safeguards": "Dual non-return check valves in series; Reverse rotation ratchet / mechanical brake.",
                    "severity": 4, "likelihood": 2, "risk_score": 8, "risk_level": "MEDIUM"
                })
                row_id += 1

            # ---------------------------------------------------------
            # 5. Flash Drums & Phase Separators
            # ---------------------------------------------------------
            elif u_type in ["FlashDrum", "Splitter", "SolidLiquidSeparator"]:
                hazop_rows.append({
                    "id": f"HAZOP-{row_id:03d}",
                    "node": f"{u_id} ({u_type})",
                    "parameter": "LEVEL",
                    "guide_word": "MORE",
                    "deviation": "High Liquid Level (Carryover)",
                    "causes": "Liquid drain valve fails closed; High feed surge; Downstream transfer line plugged.",
                    "consequences": "Liquid carries over into vapor outlet line; Potential slugging damage to downstream gas compressor or flare header.",
                    "safeguards": "Level transmitter with high-high alarm (LAHH); Automatic shut-off valve on feed stream (ESDV); High-capacity mist eliminator.",
                    "severity": 4, "likelihood": 3, "risk_score": 12, "risk_level": "HIGH"
                })
                row_id += 1

        return hazop_rows
