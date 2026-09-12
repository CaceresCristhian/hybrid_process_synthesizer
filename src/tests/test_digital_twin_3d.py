"""
Unit Tests for Phase K: Industrial Digital Twin (OPC-UA / SCADA DCS) & 3D WebGL Spatial Plant.
Covers:
1. IEC 62541 OPC-UA node tags, tag registry, read/write, and namespace browsing.
2. OPC-UA XML NodeSet & CSV SCADA Historian export.
3. Virtual DCS operator faceplate controller (Auto/Manual/Cascade and PID steps).
4. Four-tier alarm annunciator state machine (HH, H, L, LL trips and acknowledgment).
5. Predictive equipment maintenance: heat exchanger fouling & cleaning wash prediction.
6. Centrifugal pump NPSHa and cavitation diagnostics.
7. Column hydraulic tray weeping and flooding stability evaluation.
8. Three.js WebGL 3D plant HTML generation & flowsheet digital twin compiler integration.
"""

import unittest
from src.control.digital_twin import (
    OPCUANode,
    OPCUATagRegistry,
    DCSControllerFaceplate,
    EquipmentHealthMonitor
)
from src.visualization.plant_3d_viewer import Plant3DViewer
from src.control.flowsheet_solver import FlowsheetSolver
from src.units.thermal import Heater
from src.units.pump import FlowsheetPump
from src.units.distillation import BinaryDistillationColumn
from src.units.stream import MaterialStream


class TestDigitalTwin3D(unittest.TestCase):
    """Test suite for Digital Twin OPC-UA, DCS Faceplates, and 3D WebGL Viewer."""

    def test_opcua_node_and_registry(self):
        """Test 1: OPC-UA Node creation, registration, and read/write operations."""
        registry = OPCUATagRegistry()
        node = OPCUANode(
            node_id="ns=2;s=Plant.T101.PV_Temp",
            browse_name="PV_Temp",
            unit_id="T-101",
            data_type="Double",
            eng_units="°C",
            access_level="ReadWrite",
            value=78.3,
            description="Tower top temperature"
        )
        registry.register_tag(node)

        # Retrieval
        fetched = registry.get_tag("ns=2;s=Plant.T101.PV_Temp")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.value, 78.3)
        self.assertEqual(fetched.eng_units, "°C")

        # Write operation
        success = registry.write_tag("ns=2;s=Plant.T101.PV_Temp", 81.5)
        self.assertTrue(success)
        self.assertEqual(registry.get_tag("ns=2;s=Plant.T101.PV_Temp").value, 81.5)

        # Browse tags
        tags = registry.browse_tags()
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0]["unit_id"], "T-101")

    def test_opcua_export_xml_and_csv(self):
        """Test 2: Export of standard IEC 62541-6 XML NodeSet and CSV tag list."""
        registry = OPCUATagRegistry()
        node1 = OPCUANode("ns=2;s=Plant.P101.PV_Press", "PV_Press", data_type="Double", eng_units="kPa", value=350.0)
        node2 = OPCUANode("ns=2;s=Plant.P101.STAT_Run", "STAT_Run", data_type="Boolean", value=True)
        registry.register_tag(node1)
        registry.register_tag(node2)

        xml = registry.export_nodeset_xml()
        self.assertIn("<UANodeSet", xml)
        self.assertIn("ns=2;s=Plant.P101.PV_Press", xml)
        self.assertIn("ns=2;s=Plant.P101.STAT_Run", xml)

        csv = registry.export_tag_csv()
        self.assertIn("NodeId,BrowseName", csv)
        self.assertIn("350.0000", csv)

    def test_dcs_faceplate_modes_and_pid(self):
        """Test 3: DCS Controller Faceplate in Auto, Manual, and Cascade modes."""
        fp = DCSControllerFaceplate(
            loop_id="TIC-101",
            name="Column Temp Loop",
            unit_id="T-101",
            pv_init=350.0,
            sp_init=350.0,
            pv_range=(250.0, 450.0),
            kp=2.0, ti=30.0, td=2.0
        )

        # Auto mode execution
        self.assertEqual(fp.mode, "AUTO")
        fp.update_pv(355.0)  # PV above SP -> PID should reduce heating MV
        mv_auto = fp.execute_pid_step(dt_sec=1.0)
        self.assertLess(mv_auto, 50.0)

        # Manual mode override
        fp.set_mode("MANUAL")
        self.assertEqual(fp.mode, "MANUAL")
        fp.set_mv(75.0)
        self.assertEqual(fp.mv, 75.0)
        # Clamping test
        fp.set_mv(150.0)
        self.assertEqual(fp.mv, 100.0)

        # Cascade mode
        fp.set_mode("CASCADE")
        self.assertEqual(fp.mode, "CASCADE")

    def test_dcs_alarm_annunciator_state_machine(self):
        """Test 4: Four-tier safety limits (HH/H/L/LL) and alarm acknowledgment cycle."""
        fp = DCSControllerFaceplate(
            loop_id="PIC-101",
            name="Reactor Pressure",
            unit_id="R-101",
            pv_init=100.0,
            sp_init=100.0,
            pv_range=(0.0, 200.0),
            hh_limit=140.0,
            h_limit=120.0,
            l_limit=80.0,
            ll_limit=60.0
        )
        self.assertEqual(fp.alarm_state, "NORMAL")
        self.assertIsNone(fp.active_alarm)

        # Trigger High alarm (125.0 >= 120.0 and < 140.0)
        fp.update_pv(125.0)
        self.assertEqual(fp.active_alarm, "H")
        self.assertEqual(fp.alarm_state, "UNACK_ALARM")

        # Escalate to High-High trip (145.0 >= 140.0)
        fp.update_pv(145.0)
        self.assertEqual(fp.active_alarm, "HH")
        self.assertEqual(fp.alarm_state, "UNACK_ALARM")

        # Operator acknowledges alarm
        fp.acknowledge_alarm()
        self.assertEqual(fp.alarm_state, "ACK_ALARM")

        # Process returns to normal (105.0)
        fp.update_pv(105.0)
        self.assertIsNone(fp.active_alarm)
        self.assertEqual(fp.alarm_state, "NORMAL")

    def test_heat_exchanger_fouling_diagnostics(self):
        """Test 5: Heat exchanger fouling factor Rf and projected cleaning wash."""
        foul = EquipmentHealthMonitor.evaluate_heat_exchanger_fouling(
            u_clean=900.0,
            duty_kw=250.0,
            area_m2=35.0,
            t_hot_in=95.0,
            t_hot_out=60.0,
            t_cold_in=25.0,
            t_cold_out=45.0,
            hours_operated=3000.0
        )

        self.assertIn("lmtd_K", foul)
        self.assertGreater(foul["lmtd_K"], 5.0)
        self.assertIn("u_actual_W_m2K", foul)
        self.assertIn("fouling_resistance_Rf", foul)
        self.assertGreaterEqual(foul["fouling_resistance_Rf"], 0.0)
        self.assertIn("hours_until_cleaning_wash", foul)
        self.assertIn("health_status", foul)

    def test_pump_cavitation_diagnostics(self):
        """Test 6: Centrifugal pump NPSHa and cavitation risk evaluation."""
        # Safe condition: high suction pressure
        safe_pump = EquipmentHealthMonitor.evaluate_pump_cavitation(
            p_suction_kpa=250.0,
            p_vapor_kpa=20.0,
            npsh_required_m=2.5
        )
        self.assertGreater(safe_pump["margin_m"], 1.5)
        self.assertIn("SAFE", safe_pump["cavitation_risk"])

        # Low suction pressure causing cavitation
        cav_pump = EquipmentHealthMonitor.evaluate_pump_cavitation(
            p_suction_kpa=30.0,
            p_vapor_kpa=25.0,
            npsh_required_m=3.0
        )
        self.assertLess(cav_pump["margin_m"], 1.0)
        self.assertIn("CAVITATION", cav_pump["cavitation_risk"])

    def test_column_hydraulic_health(self):
        """Test 7: Column tray weeping and flooding margin diagnostics."""
        health = EquipmentHealthMonitor.evaluate_column_hydraulic_stability(
            vapor_velocity_m_s=1.10,
            flood_velocity_m_s=1.60,
            weep_velocity_m_s=0.40
        )
        self.assertGreater(health["flooding_pct"], 60.0)
        self.assertGreater(health["weep_margin_pct"], 50.0)
        self.assertEqual(health["operating_regime"], "STABLE FROTH REGIME")

        # Test high jet entrainment
        health_high = EquipmentHealthMonitor.evaluate_column_hydraulic_stability(
            vapor_velocity_m_s=1.35,
            flood_velocity_m_s=1.60,
            weep_velocity_m_s=0.40
        )
        self.assertEqual(health_high["operating_regime"], "HIGH JET ENTRAINMENT")

    def test_3d_plant_scene_generation_and_flowsheet_compiler(self):
        """Test 8: Three.js HTML generation and flowsheet digital twin compilation."""
        # 1. Test 3D HTML generator
        units_dict = {
            "T-101": {"type": "DistillationColumn", "x": 150, "y": 150},
            "P-101": {"type": "Pump", "x": 300, "y": 150}
        }
        conns = [{"from": "T-101", "to": "P-101", "stream": "S-101"}]
        html = Plant3DViewer.generate_plant_3d_html(units_dict, conns, canvas_height=600)
        self.assertIn("canvas-container", html)
        self.assertIn("three.min.js", html)
        self.assertIn("OrbitControls", html)
        self.assertIn("T-101", html)

        # 2. Test Flowsheet digital twin compiler
        pump = FlowsheetPump("P-101", "Feed Pump")
        feed = MaterialStream("Feed-Stream")
        feed.T = 298.15
        feed.P = 101325.0
        feed.F = 20.0
        pump.connect_inlet(feed)

        heater = Heater("H-101", "Preheater", t_target=360.0)
        heater.connect_inlet(feed)

        flowsheet_units = [pump, heater]
        dt_res = FlowsheetSolver.compile_flowsheet_digital_twin(flowsheet_units)

        self.assertIn("registry", dt_res)
        self.assertIn("tags_list", dt_res)
        self.assertIn("dcs_faceplates", dt_res)
        self.assertIn("health_diagnostics", dt_res)
        self.assertGreater(dt_res["summary"]["total_tags_count"], 5)
        self.assertGreater(dt_res["summary"]["total_control_loops"], 0)


if __name__ == "__main__":
    unittest.main()
