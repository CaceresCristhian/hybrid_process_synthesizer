import unittest
from src.visualization.svg_flowsheet import SVGFlowsheet

class TestSVGFlowsheet(unittest.TestCase):
    
    def test_svg_generation(self):
        units = {
            "P-101": {"type": "Pump", "thermo": "Ideal"},
            "C-101": {"type": "DistillationColumn", "thermo": "Ideal", "variation": "Packed Bed Column"}
        }
        connections = [
            {"from": "Feed Boundary", "to": "P-101", "stream": "S-101"},
            {"from": "P-101", "to": "C-101", "stream": "S-102"},
            {"from": "C-101", "to": "Product Boundary", "stream": "S-103"}
        ]
        
        svg = SVGFlowsheet.generate_flowsheet_svg(units, connections)
        
        # Core structural checks
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.endswith("</svg>"))
        
        # Bounding box checks
        self.assertIn("Feed Boundaries", svg)
        self.assertIn("Product Boundaries", svg)
        
        # Equipment symbols and connections checks
        self.assertIn("P-101", svg)
        self.assertIn("C-101", svg)
        self.assertIn("S-101", svg)
        self.assertIn("S-102", svg)
        self.assertIn("S-103", svg)

if __name__ == "__main__":
    unittest.main()
