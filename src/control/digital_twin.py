"""
Industrial Digital Twin & SCADA/OPC-UA Engine.
Implements:
1. IEC 62541 compliant OPC-UA Tag Node Architecture and Tag Registry.
2. Virtual DCS Operator Faceplate Console (Auto/Manual/Cascade loops with 4-tier HH/H/L/LL alarms).
3. Equipment Health & Predictive Maintenance Diagnostics (Exchanger Fouling, Pump Cavitation, Column Flooding).
4. XML NodeSet & CSV SCADA Historian Exporter.
"""

import time
import math
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union


@dataclass
class OPCUANode:
    """Standard IEC 62541 OPC-UA Variable Node Representation."""
    node_id: str                      # e.g. "ns=2;s=Plant.T-101.PV_TopTemp"
    browse_name: str                  # e.g. "PV_TopTemp"
    data_type: str = "Double"         # "Double", "Int32", "Boolean", "String"
    eng_units: str = ""               # "°C", "kPa", "bar", "mol/s", "kg/h", "kW", "%", "m"
    access_level: str = "CurrentRead" # "CurrentRead", "CurrentWrite", "ReadWrite"
    value: Any = 0.0
    status: str = "Good"              # "Good", "Bad_SensorFailure", "Uncertain"
    timestamp: str = ""
    description: str = ""
    unit_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def update_value(self, new_val: Any, status: str = "Good"):
        self.value = new_val
        self.status = status
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "browse_name": self.browse_name,
            "unit_id": self.unit_id,
            "data_type": self.data_type,
            "eng_units": self.eng_units,
            "access_level": self.access_level,
            "value": self.value,
            "status": self.status,
            "timestamp": self.timestamp,
            "description": self.description
        }


class OPCUATagRegistry:
    """In-memory OPC-UA Tag Registry and SCADA Server simulation."""

    def __init__(self, namespace_uri: str = "urn:hybrid:process:synthesizer"):
        self.namespace_uri = namespace_uri
        self.namespace_index = 2
        self.tags: Dict[str, OPCUANode] = {}

    def register_tag(self, node: OPCUANode) -> OPCUANode:
        self.tags[node.node_id] = node
        return node

    def get_tag(self, node_id: str) -> Optional[OPCUANode]:
        return self.tags.get(node_id)

    def write_tag(self, node_id: str, value: Any) -> bool:
        if node_id in self.tags:
            node = self.tags[node_id]
            if "Write" in node.access_level or node.access_level == "ReadWrite":
                node.update_value(value)
                return True
        return False

    def browse_tags(self, unit_id_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for node in self.tags.values():
            if unit_id_filter is None or node.unit_id == unit_id_filter:
                results.append(node.to_dict())
        return results

    def export_nodeset_xml(self) -> str:
        """Exports the registered address space into standard IEC 62541-6 UANodeSet XML."""
        xml_lines = [
            '<?xml version="1.0" encoding="utf-8"?>',
            '<UANodeSet xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
            f'  <NamespaceUris>',
            f'    <Uri>{self.namespace_uri}</Uri>',
            f'  </NamespaceUris>',
            '  <Models/>',
            '  <Aliases>',
            '    <Alias Alias="Boolean">i=1</Alias>',
            '    <Alias Alias="Double">i=11</Alias>',
            '    <Alias Alias="String">i=12</Alias>',
            '  </Aliases>'
        ]

        for node in self.tags.values():
            dt_alias = "Double" if node.data_type == "Double" else ("Boolean" if node.data_type == "Boolean" else "String")
            xml_lines.append(f'  <UAVariable NodeId="{node.node_id}" BrowseName="{self.namespace_index}:{node.browse_name}" DataType="{dt_alias}" AccessLevel="3">')
            xml_lines.append(f'    <DisplayName>{node.browse_name}</DisplayName>')
            xml_lines.append(f'    <Description>{node.description}</Description>')
            xml_lines.append(f'    <Value>')
            xml_lines.append(f'      <{dt_alias}>{node.value}</{dt_alias}>')
            xml_lines.append(f'    </Value>')
            xml_lines.append(f'  </UAVariable>')

        xml_lines.append('</UANodeSet>')
        return chr(10).join(xml_lines)

    def export_tag_csv(self) -> str:
        """Exports the tag database formatted for industrial SCADA historians."""
        csv_lines = ["NodeId,BrowseName,UnitID,DataType,EngUnits,Value,Status,Timestamp,Description"]
        for node in self.tags.values():
            val_str = f"{node.value:.4f}" if isinstance(node.value, float) else str(node.value)
            csv_lines.append(f'"{node.node_id}","{node.browse_name}","{node.unit_id}","{node.data_type}","{node.eng_units}",{val_str},"{node.status}","{node.timestamp}","{node.description}"')
        return chr(10).join(csv_lines)


class DCSControllerFaceplate:
    """
    Virtual DCS Operator Faceplate Controller (Emerson DeltaV / Honeywell Experion).
    Supports Auto (closed-loop PID), Manual (operator MV override), and Cascade control.
    Four-tier safety limits: High-High (HH), High (H), Low (L), Low-Low (LL).
    """

    def __init__(self, loop_id: str, name: str, unit_id: str,
                 loop_type: str = "Temperature",
                 pv_init: float = 350.0,
                 sp_init: float = 350.0,
                 units: str = "°C",
                 pv_range: Optional[tuple] = None,
                 hh_limit: float = 430.0,
                 h_limit: float = 400.0,
                 l_limit: float = 280.0,
                 ll_limit: float = 260.0,
                 kp: float = 2.5,
                 ti: float = 60.0,
                 td: float = 5.0):
        self.loop_id = loop_id
        self.name = name
        self.unit_id = unit_id
        self.loop_type = loop_type
        self.units = units

        if pv_range is not None:
            self.pv_min, self.pv_max = pv_range
        else:
            self.pv_min = min(0.0, pv_init * 0.5)
            self.pv_max = max(100.0, pv_init * 1.8)

        self.pv = pv_init
        self.sp = sp_init
        self.mv = 50.0  # 0 to 100%

        self.mode = "AUTO"  # "AUTO", "MANUAL", "CASCADE"
        self.hh_limit = hh_limit
        self.h_limit = h_limit
        self.l_limit = l_limit
        self.ll_limit = ll_limit

        self.alarm_state = "NORMAL"  # "NORMAL", "UNACK_ALARM", "ACK_ALARM", "CLEARED_UNACK"
        self.active_alarm = None     # None, "HH", "H", "L", "LL"

        self.kp = kp
        self.ti = max(0.1, ti)
        self.td = td

        # Internal integrator state
        self._integral_err = 0.0
        self._prev_err = 0.0

    def set_mode(self, new_mode: str):
        if new_mode.upper() in ["AUTO", "MANUAL", "CASCADE"]:
            self.mode = new_mode.upper()

    def set_sp(self, new_sp: float):
        self.sp = max(self.pv_min, min(self.pv_max, float(new_sp)))

    def set_mv(self, new_mv: float):
        """Manual operator override of control valve / power output (0-100%)."""
        if self.mode == "MANUAL":
            self.mv = max(0.0, min(100.0, float(new_mv)))

    def update_pv(self, new_pv: float):
        self.pv = max(self.pv_min - 20.0, min(self.pv_max + 20.0, float(new_pv)))
        self._check_alarms()

    def acknowledge_alarm(self):
        if self.alarm_state == "UNACK_ALARM":
            self.alarm_state = "ACK_ALARM"
        elif self.alarm_state == "CLEARED_UNACK":
            self.alarm_state = "NORMAL"

    def _check_alarms(self):
        trip = None
        if self.pv >= self.hh_limit:
            trip = "HH"
        elif self.pv <= self.ll_limit:
            trip = "LL"
        elif self.pv >= self.h_limit:
            trip = "H"
        elif self.pv <= self.l_limit:
            trip = "L"

        if trip is not None:
            if self.active_alarm != trip:
                self.active_alarm = trip
                self.alarm_state = "UNACK_ALARM"
        else:
            if self.active_alarm is not None:
                self.active_alarm = None
                if self.alarm_state == "UNACK_ALARM":
                    self.alarm_state = "CLEARED_UNACK"
                else:
                    self.alarm_state = "NORMAL"

    def execute_pid_step(self, dt_sec: float = 1.0) -> float:
        """Computes PID control action if in AUTO or CASCADE mode."""
        if self.mode in ["AUTO", "CASCADE"]:
            err = self.sp - self.pv
            self._integral_err += err * dt_sec
            # Anti-windup clamping
            self._integral_err = max(-100.0, min(100.0, self._integral_err))

            deriv = (err - self._prev_err) / max(1e-3, dt_sec)
            self._prev_err = err

            p_term = self.kp * err
            i_term = (self.kp / self.ti) * self._integral_err
            d_term = self.kp * self.td * deriv

            calc_mv = 50.0 + p_term + i_term + d_term
            self.mv = max(0.0, min(100.0, calc_mv))

        return self.mv

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "name": self.name,
            "unit_id": self.unit_id,
            "loop_type": self.loop_type,
            "units": self.units,
            "mode": self.mode,
            "pv": round(self.pv, 2),
            "sp": round(self.sp, 2),
            "mv": round(self.mv, 1),
            "pv_min": self.pv_min,
            "pv_max": self.pv_max,
            "hh_limit": self.hh_limit,
            "h_limit": self.h_limit,
            "l_limit": self.l_limit,
            "ll_limit": self.ll_limit,
            "alarm_state": self.alarm_state,
            "active_alarm": self.active_alarm
        }


class EquipmentHealthMonitor:
    """
    Predictive Maintenance & Degradation Analytics for Digital Twins:
    1. Heat Exchanger Fouling (overall U degradation and chemical wash schedule).
    2. Centrifugal Pump Cavitation Risk (NPSHa vs NPSHr).
    3. Column Hydraulic Stability (Weeping and Flooding indices).
    """

    @classmethod
    def evaluate_heat_exchanger_fouling(cls, u_clean: float, duty_kw: float, area_m2: float,
                                         t_hot_in: float, t_hot_out: float,
                                         t_cold_in: float, t_cold_out: float,
                                         hours_operated: float = 2500.0) -> Dict[str, Any]:
        """Calculates fouling resistance Rf and projected wash interval."""
        dt1 = max(0.5, t_hot_in - t_cold_out)
        dt2 = max(0.5, t_hot_out - t_cold_in)

        if abs(dt1 - dt2) < 0.01:
            lmtd = dt1
        else:
            ratio = max(1e-4, dt1 / dt2)
            lmtd = (dt1 - dt2) / math.log(ratio)
        lmtd = max(0.5, lmtd)

        # Actual overall heat transfer coefficient (W / m2 K)
        u_actual = (abs(duty_kw) * 1000.0) / max(0.1, area_m2 * lmtd)
        u_actual = min(u_clean * 1.05, u_actual)

        # Fouling thermal resistance Rf (m2 K / W)
        rf = max(0.0, (1.0 / max(1.0, u_actual)) - (1.0 / max(1.0, u_clean)))

        # Thermal performance degradation %
        u_loss_pct = max(0.0, min(100.0, ((u_clean - u_actual) / max(1.0, u_clean)) * 100.0))

        # Projected hours remaining until critical fouling limit Rf_crit = 0.0005 m2 K / W
        rf_critical = 0.0005
        fouling_rate = rf / max(1.0, hours_operated)
        if fouling_rate > 1e-9:
            hours_to_clean = max(0.0, (rf_critical - rf) / fouling_rate)
        else:
            hours_to_clean = 10000.0

        health_status = "OPTIMAL"
        if u_loss_pct > 35.0 or rf >= rf_critical:
            health_status = "CRITICAL FOULING (WASH REQUIRED)"
        elif u_loss_pct > 15.0:
            health_status = "MODERATE FOULING"

        return {
            "u_clean_W_m2K": round(u_clean, 1),
            "u_actual_W_m2K": round(u_actual, 1),
            "lmtd_K": round(lmtd, 2),
            "fouling_resistance_Rf": round(rf, 6),
            "performance_loss_pct": round(u_loss_pct, 1),
            "hours_operated": round(hours_operated, 0),
            "hours_until_cleaning_wash": round(hours_to_clean, 0),
            "health_status": health_status
        }

    @classmethod
    def evaluate_pump_cavitation(cls, p_suction_kpa: float, p_vapor_kpa: float,
                                fluid_density_kg_m3: float = 1000.0,
                                suction_velocity_m_s: float = 1.5,
                                friction_head_loss_m: float = 0.4,
                                npsh_required_m: float = 2.5) -> Dict[str, Any]:
        """Evaluates available NPSH and cavitation risk index."""
        g = 9.81
        p_diff_pa = (p_suction_kpa - p_vapor_kpa) * 1000.0
        static_head = p_diff_pa / max(1.0, fluid_density_kg_m3 * g)
        velocity_head = (suction_velocity_m_s ** 2) / (2.0 * g)

        npsh_a = static_head + velocity_head - friction_head_loss_m
        margin = npsh_a - npsh_required_m

        if margin < 0.2:
            cav_risk = "CRITICAL CAVITATION DAMAGE"
        elif margin < 1.0:
            cav_risk = "INCIPIENT CAVITATION WARNING"
        else:
            cav_risk = "SAFE (ADEQUATE MARGIN)"

        return {
            "npsh_available_m": round(npsh_a, 2),
            "npsh_required_m": round(npsh_required_m, 2),
            "margin_m": round(margin, 2),
            "static_head_m": round(static_head, 2),
            "velocity_head_m": round(velocity_head, 2),
            "cavitation_risk": cav_risk
        }

    @classmethod
    def evaluate_column_hydraulic_stability(cls, vapor_velocity_m_s: float,
                                           flood_velocity_m_s: float,
                                           weep_velocity_m_s: float = 0.40) -> Dict[str, Any]:
        """Calculates weeping and flooding margins on distillation trays."""
        flood_pct = (vapor_velocity_m_s / max(0.1, flood_velocity_m_s)) * 100.0
        weep_margin_pct = ((vapor_velocity_m_s - weep_velocity_m_s) / max(0.1, weep_velocity_m_s)) * 100.0

        if flood_pct >= 90.0:
            status = "DANGEROUS FLOODING RISK"
        elif flood_pct >= 80.0:
            status = "HIGH JET ENTRAINMENT"
        elif vapor_velocity_m_s <= weep_velocity_m_s:
            status = "WEEPING / DUMPING TRAYS"
        else:
            status = "STABLE FROTH REGIME"

        return {
            "vapor_velocity_m_s": round(vapor_velocity_m_s, 2),
            "flood_velocity_m_s": round(flood_velocity_m_s, 2),
            "flooding_pct": round(flood_pct, 1),
            "weep_velocity_m_s": round(weep_velocity_m_s, 2),
            "weep_margin_pct": round(weep_margin_pct, 1),
            "operating_regime": status
        }
