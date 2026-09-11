import unittest
from src.visualization.ports import PortRegistry, PortDefinition
from src.visualization.interactive_canvas import InteractiveCanvasStudio
from src.visualization.svg_flowsheet import SVGFlowsheet
from src.units.distillation import BinaryDistillationColumn
from src.units.thermal import HeatExchanger
from src.units.stream import MaterialStream
from src.control.flowsheet_solver import FlowsheetSolver
from src.database.loader import ChemicalDatabaseLoader

class TestInteractivePorts(unittest.TestCase):

    def setUp(self):
        self.species_map = {
            "water": ChemicalDatabaseLoader.get_water_metadata(),
            "ethanol": ChemicalDatabaseLoader.get_ethanol_metadata(),
            "hydrogen": ChemicalDatabaseLoader.get_hydrogen_metadata(),
            "nitrogen": ChemicalDatabaseLoader.get_nitrogen_metadata()
        }

    def test_port_registry_all_units(self):
        """Verify that all 16 industrial unit operations plus boundaries have valid ports registered."""
        expected_units = [
            "Pump", "Compressor", "Expander", "ControlValve", 
            "Heater", "Cooler", "HeatExchanger", "CSTR", "PFR", 
            "BinaryDistillationColumn", "AbsorptionColumn", "FlashDrum", 
            "Splitter", "Mixer", "SolidLiquidSeparator", "MembraneUnit",
            "Feed Boundary", "Product Boundary"
        ]
        
        for utype in expected_units:
            ports = PortRegistry.get_ports(utype)
            self.assertTrue(len(ports) > 0, f"Unit would have no ports: {utype}")
            for p in ports:
                self.assertIsInstance(p, PortDefinition)
                self.assertIn(p.type, ["inlet", "outlet"])
                self.assertTrue(0.0 <= p.x_rel <= 1.0, f"Port {p.id} x_rel out of range")
                self.assertTrue(0.0 <= p.y_rel <= 1.0, f"Port {p.id} y_rel out of range")

    def test_distillation_multi_ports(self):
        """Verify BinaryDistillationColumn has feed, distillate, and bottoms ports."""
        dist_ports = {p.id: p for p in PortRegistry.get_ports("BinaryDistillationColumn")}
        self.assertIn("feed", dist_ports)
        self.assertIn("distillate", dist_ports)
        self.assertIn("bottoms", dist_ports)
        
        self.assertEqual(dist_ports["feed"].type, "inlet")
        self.assertEqual(dist_ports["distillate"].type, "outlet")
        self.assertEqual(dist_ports["bottoms"].type, "outlet")
        
        # Distillate is near top, bottoms is near bottom
        self.assertLessEqual(dist_ports["distillate"].y_rel, 0.25)
        self.assertGreaterEqual(dist_ports["bottoms"].y_rel, 0.8)

    def test_heat_exchanger_four_ports(self):
        """Verify HeatExchanger has 4 discrete ports for tube-side and shell-side flows."""
        hx_ports = {p.id: p for p in PortRegistry.get_ports("HeatExchanger")}
        self.assertEqual(len(hx_ports), 4)
        self.assertIn("tube_in", hx_ports)
        self.assertIn("shell_in", hx_ports)
        self.assertIn("tube_out", hx_ports)
        self.assertIn("shell_out", hx_ports)
        
        self.assertEqual(hx_ports["tube_in"].type, "inlet")
        self.assertEqual(hx_ports["shell_in"].type, "inlet")
        self.assertEqual(hx_ports["tube_out"].type, "outlet")
        self.assertEqual(hx_ports["shell_out"].type, "outlet")

    def test_calculate_port_coordinates(self):
        """Verify coordinate scaling with node position and bounding box dimensions."""
        coords = PortRegistry.calculate_port_coordinates("BinaryDistillationColumn", "distillate", 100.0, 200.0, 90.0, 150.0)
        # In ports.py, DistillationColumn distillate is at x_rel=0.5, y_rel=0.0
        p = PortRegistry.get_port("BinaryDistillationColumn", "distillate")
        self.assertAlmostEqual(coords[0], 100.0 + 90.0 * p.x_rel)
        self.assertAlmostEqual(coords[1], 200.0 + 150.0 * p.y_rel)

    def test_interactive_canvas_html_generation(self):
        """Verify InteractiveCanvasStudio produces a complete standalone HTML document."""
        units_dict = {
            "C-101": {"type": "BinaryDistillationColumn", "thermo": "Ideal", "variation": "Sieve Tray Column", "x": 100, "y": 100, "width": 90, "height": 150},
            "P-101": {"type": "Pump", "thermo": "Ideal", "variation": "Standard", "x": 300, "y": 150, "width": 75, "height": 70}
        }
        conns_list = [
            {"stream": "S-101", "from": "C-101", "from_port": "distillate", "to": "P-101", "to_port": "suction"}
        ]
        
        html = InteractiveCanvasStudio.render_studio_html(units_dict, conns_list, canvas_height=600)
        
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn('id="canvas"', html)
        self.assertIn('id="viewport"', html)
        self.assertIn('id="active-wire"', html)
        self.assertIn('id="btn-export-sync"', html)
        self.assertIn("C-101", html)
        self.assertIn("P-101", html)
        self.assertIn("distillate", html)
        self.assertIn("suction", html)
        self.assertIn("resize-handle", html)
        self.assertIn("stream-modal", html)

    def test_svg_flowsheet_port_offsets(self):
        """Verify SVGFlowsheet accurately renders multi-port connections without errors."""
        units_dict = {
            "C-101": {"type": "BinaryDistillationColumn", "thermo": "Peng-Robinson EOS"},
            "E-101": {"type": "HeatExchanger", "thermo": "Peng-Robinson EOS"}
        }
        conns_list = [
            {"stream": "S-101", "from": "Feed Boundary", "from_port": "out", "to": "C-101", "to_port": "feed"},
            {"stream": "S-102", "from": "C-101", "from_port": "distillate", "to": "E-101", "to_port": "tube_in"},
            {"stream": "S-103", "from": "C-101", "from_port": "bottoms", "to": "Product Boundary", "to_port": "in"}
        ]
        variations = {"C-101": "Sieve Tray Column", "E-101": "Standard"}
        
        svg = SVGFlowsheet.generate_flowsheet_svg(units_dict, conns_list, variations)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("</svg>", svg)
        self.assertIn("S-101", svg)
        self.assertIn("S-102", svg)
        self.assertIn("S-103", svg)

    def test_multi_port_solver_execution(self):
        """Verify simulation correctly assigns multi-port stream outlets to column distillate and bottoms."""
        col = BinaryDistillationColumn("C-101", "C-101", num_stages=10, feed_stage=5, reflux_ratio=2.0)
        s_feed = MaterialStream("S-101")
        s_feed.T = 360.0
        s_feed.P = 101325.0
        s_feed.F = 20.0
        s_feed.z = {"ethanol": 0.4, "water": 0.6}
        
        s_dist = MaterialStream("S-102")
        s_bot = MaterialStream("S-103")
        
        # Connect inlet
        col.connect_inlet(s_feed)
        # In multi-port logic, distillate is outlet[0], bottoms is outlet[1]
        col.connect_outlet(s_dist)
        col.connect_outlet(s_bot)
        
        units = {"C-101": col}
        streams = {"S-101": s_feed, "S-102": s_dist, "S-103": s_bot}
        
        res = FlowsheetSolver.solve_flowsheet_topology(units, streams, self.species_map)
        self.assertTrue(res["converged"])
        
        # Distillate should be enriched in ethanol
        self.assertGreater(s_dist.z["ethanol"], 0.4)
        # Bottoms should be enriched in water
        self.assertGreater(s_bot.z["water"], 0.6)
        # Mass balance check
        self.assertAlmostEqual(s_dist.F + s_bot.F, s_feed.F, places=4)

if __name__ == '__main__':
    unittest.main()
