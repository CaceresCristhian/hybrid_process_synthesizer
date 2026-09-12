"""
Unit tests for Engineering Deliverables, Regulatory Standards & Document Generation Studio.
Tests PED 2014/68/EU classification, OSHA 1910.119 PSI, ISO 7200 title blocks,
ReportLab vector PDF generation, and printable HTML templates.
"""

import unittest
from typing import Dict, Any

from src.reporting.regulatory_standards import (
    TitleBlockData, RegulatoryStandards, PEDClassifier, OSHAPSIChecker
)
from src.reporting.pdf_generator import PDFReportGenerator
from src.reporting.report_generator import ReportGenerator
from src.control.flowsheet_solver import FlowsheetSolver


class MockUnit:
    """Mock unit operation for reporting tests."""
    def __init__(self, unit_id: str, unit_type: str, design_p: float = 300000.0,
                 material: str = "Carbon Steel SA-516", vol_m3: float = 3.5):
        self.unit_id = unit_id
        self.name = f"{unit_type} {unit_id}"
        self.__class__.__name__ = unit_type
        self.design_pressure = design_p
        self.material = material
        self.heat_duty = 45000.0
        self.work_input = 5500.0
        self.sizing_results = {
            "volume_m3": vol_m3,
            "diameter_m": 1.2,
            "height_m": 12.0,
            "num_stages": 15,
            "area_m2": 35.0
        }


class MockStream:
    """Mock process stream for reporting tests."""
    def __init__(self, name: str, T: float = 350.0, P: float = 250000.0,
                 F: float = 12.5, z: Dict[str, float] = None, phase: str = "liquid"):
        self.name = name
        self.T = T
        self.P = P
        self.F = F
        self.z = z or {"ethanol": 0.35, "water": 0.65}
        self.phase = phase
        self.Vf = 0.0 if phase == "liquid" else 1.0
        self.H = 25000.0


class TestReportingRegulatory(unittest.TestCase):
    """Test suite for Phase L deliverables and regulatory compliance."""

    def setUp(self):
        self.tb = TitleBlockData(
            project_title="Green Bio-Ethanol Facility",
            plant_name="Hamburg Bio-Refinery",
            drawn_by="C. Caceres",
            approved_by="Dr. M. Weber",
            document_number="HPS-TEST-001",
            revision="A"
        )
        self.mock_units = {
            "C-101": MockUnit("C-101", "DistillationColumn", design_p=400000.0, vol_m3=8.5),
            "E-101": MockUnit("E-101", "HeatExchanger", design_p=600000.0, vol_m3=1.2),
            "P-101": MockUnit("P-101", "Pump", design_p=800000.0, vol_m3=0.5)
        }
        self.mock_streams = {
            "S-01": MockStream("S-01", T=320.0, P=150000.0, F=10.0, phase="liquid"),
            "S-02": MockStream("S-02", T=365.0, P=120000.0, F=6.5, phase="vapor", z={"ethanol": 0.85, "water": 0.15})
        }
        self.connections = [("E-101", "C-101", "S-01"), ("C-101", "P-101", "S-02")]

    def test_standards_catalog(self):
        """Test the official regulatory standards repository query and search."""
        all_std = RegulatoryStandards.get_all_standards()
        self.assertGreaterEqual(len(all_std), 14)

        ger_std = RegulatoryStandards.filter_by_jurisdiction("germany")
        self.assertTrue(any("DIN" in s["code"] or "BImSchG" in s["code"] for s in ger_std))

        eu_std = RegulatoryStandards.filter_by_jurisdiction("europe")
        self.assertTrue(any("PED" in s["code"] or "EN" in s["code"] for s in eu_std))

        us_std = RegulatoryStandards.filter_by_jurisdiction("usa")
        self.assertTrue(any("OSHA" in s["code"] or "ASME" in s["code"] for s in us_std))

        # Keyword search
        search_res = RegulatoryStandards.search_standards("10628")
        self.assertGreaterEqual(len(search_res), 1)
        self.assertIn("10628", search_res[0]["code"])

    def test_title_block_model(self):
        """Test TitleBlockData initialization and ISO 7200 compliance."""
        self.assertEqual(self.tb.project_title, "Green Bio-Ethanol Facility")
        self.assertEqual(self.tb.revision, "A")
        self.assertIn("HPS", self.tb.document_number)

    def test_ped_classification(self):
        """Test PED 2014/68/EU hazard category classification rules."""
        # 1. Atmospheric pressure (PS <= 0.5 bar) -> SEP
        res_sep = PEDClassifier.classify_vessel(ps_bar=0.3, volume_m3=10.0, fluid_group=1, is_gas_or_vapor=True)
        self.assertEqual(res_sep["category"], "SEP")
        self.assertFalse(res_sep["ce_marking_required"])

        # 2. Group 1 Gas, PS=2.0 bar, V=0.02 m3 (20 L) -> PS*V = 40 bar*L -> Category I
        res_cat1 = PEDClassifier.classify_vessel(ps_bar=2.0, volume_m3=0.02, fluid_group=1, is_gas_or_vapor=True)
        self.assertEqual(res_cat1["category"], "Category I")
        self.assertTrue(res_cat1["ce_marking_required"])
        self.assertFalse(res_cat1["notified_body_required"])

        # 3. Group 1 Gas, PS=4.0 bar, V=0.03 m3 (30 L) -> PS*V = 120 bar*L -> Category II
        res_cat2 = PEDClassifier.classify_vessel(ps_bar=4.0, volume_m3=0.03, fluid_group=1, is_gas_or_vapor=True)
        self.assertEqual(res_cat2["category"], "Category II")
        self.assertTrue(res_cat2["ce_marking_required"])
        self.assertTrue(res_cat2["notified_body_required"])

        # 4. Group 1 Gas, PS=10.0 bar, V=0.05 m3 (50 L) -> PS*V = 500 bar*L -> Category III
        res_cat3 = PEDClassifier.classify_vessel(ps_bar=10.0, volume_m3=0.05, fluid_group=1, is_gas_or_vapor=True)
        self.assertEqual(res_cat3["category"], "Category III")
        self.assertTrue(res_cat3["notified_body_required"])

        # 5. Group 1 Gas, PS=20.0 bar, V=0.1 m3 (100 L) -> PS*V = 2000 bar*L -> Category IV
        res_cat4 = PEDClassifier.classify_vessel(ps_bar=20.0, volume_m3=0.1, fluid_group=1, is_gas_or_vapor=True)
        self.assertEqual(res_cat4["category"], "Category IV")
        self.assertTrue(res_cat4["ce_marking_required"])
        self.assertTrue(res_cat4["notified_body_required"])

        # Fluid group determination
        grp1 = PEDClassifier.determine_fluid_group({"ethanol": 0.5, "water": 0.5})
        self.assertEqual(grp1, 1)
        grp2 = PEDClassifier.determine_fluid_group({"water": 1.0})
        self.assertEqual(grp2, 2)

    def test_osha_psi_checker(self):
        """Test OSHA 1910.119 Process Safety Information compilation."""
        hazards = OSHAPSIChecker.compile_chemical_hazards(["methane", "benzene", "water"])
        self.assertEqual(len(hazards), 3)
        benzene_h = next(h for h in hazards if h["component"] == "benzene")
        self.assertIn("1", benzene_h["pel_osha_ppm"])

        envelope = OSHAPSIChecker.compile_technology_envelope("T-101", "DistillationColumn", 85.0, 3.0, 5.0)
        self.assertIn("5.00 bar", envelope["safe_upper_pressure_limit"])
        self.assertIn("catastrophic", envelope["consequence_high_p"].lower())

    def test_pdf_report_generator_all_templates(self):
        """Test ReportLab PDF generation across all 5 official deliverable templates."""
        templates = ["pfd_stream", "equipment_datasheets", "ped_eu_dossier", "osha_psi", "feed_master"]
        for tid in templates:
            pdf_data = PDFReportGenerator.build_document(
                template_id=tid,
                units_map=self.mock_units,
                streams_map=self.mock_streams,
                connections=self.connections,
                title_data=self.tb
            )
            self.assertIsInstance(pdf_data, bytes)
            self.assertGreater(len(pdf_data), 1000)
            self.assertTrue(pdf_data.startswith(b"%PDF-"), f"Template {tid} failed to produce valid PDF header.")

    def test_html_deliverable_generator_all_templates(self):
        """Test printable HTML deliverables generation across all 5 templates."""
        templates = ["pfd_stream", "equipment_datasheets", "ped_eu_dossier", "osha_psi", "feed_master"]
        for tid in templates:
            html_out = ReportGenerator.generate_deliverable_html(
                template_id=tid,
                units_map=self.mock_units,
                streams_map=self.mock_streams,
                connections=self.connections,
                title_data=self.tb
            )
            self.assertIsInstance(html_out, str)
            self.assertIn("<!DOCTYPE html>", html_out)
            self.assertIn("DIN EN ISO 7200", html_out)
            self.assertIn(self.tb.project_title, html_out)

    def test_flowsheet_solver_compile_deliverables(self):
        """Test FlowsheetSolver.compile_flowsheet_deliverables compilation."""
        deliv = FlowsheetSolver.compile_flowsheet_deliverables(
            units_list=self.mock_units,
            streams_list=self.mock_streams,
            connections=self.connections,
            title_data=self.tb,
            jurisdiction="EU/EN"
        )
        self.assertIn("summary", deliv)
        self.assertEqual(deliv["summary"]["total_units"], 3)
        self.assertEqual(deliv["summary"]["total_streams"], 2)
        self.assertGreaterEqual(deliv["summary"]["ce_mark_required_count"], 1)
        self.assertIn("ped_evaluations", deliv)
        self.assertIn("osha_technology_envelopes", deliv)
        self.assertGreaterEqual(len(deliv["applicable_standards"]), 5)


if __name__ == "__main__":
    unittest.main()
