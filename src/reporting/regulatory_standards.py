"""
Official Regulatory Standards & Industrial Compliance Framework.
Covers Germany (DIN / VDI / BImSchG), European Union (EN / ISO / PED 2014/68/EU),
and United States (ANSI / ASME / ISA / OSHA / API / TEMA).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class TitleBlockData:
    """
    Standard Technical Document Header / Title Block data model.
    Compliant with DIN EN ISO 7200 and ASME Y14.1 / Y14.24.
    """
    project_title: str = "Industrial Process Plant Synthesis"
    plant_name: str = "Chemical Facility Alpha"
    document_title: str = "Process Flow Diagram & Heat/Material Balance"
    document_number: str = "HPS-DWG-001"
    revision: str = "0"
    sheet_number: str = "1 / 1"
    client_name: str = "Global Chemical Engineering Corp."
    contractor_name: str = "Hybrid Process Engineering GmbH"
    drawn_by: str = "Process Engineer"
    checked_by: str = "Lead Process Engineer"
    approved_by: str = "Project Director"
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    scale: str = "NTS"
    legal_owner: str = "Hybrid Process Synthesizer"
    jurisdiction: str = "DUAL"  # "DIN/ISO", "ASME", "EU/EN", "DUAL"
    confidentiality: str = "CONFIDENTIAL - APPROVED FOR FEED"


class RegulatoryStandards:
    """
    Comprehensive Catalog of Official Engineering Standards and Regulatory
    Directives across Germany, the European Union, and the United States.
    """

    STANDARDS_CATALOG: List[Dict[str, Any]] = [
        # --- GERMANY (DIN / VDI / BImSchG / BetrSichV) ---
        {
            "id": "DIN-EN-ISO-10628-1",
            "code": "DIN EN ISO 10628-1",
            "title": "Diagrams for the chemical and petrochemical industry - Part 1: Specification of diagrams",
            "authority": "DIN / ISO",
            "jurisdiction": "Germany / Europe",
            "legal_status": "Harmonized Technical Standard",
            "scope": "Defines basic principles and rules for block diagrams, process flow diagrams (PFD / Grundfließschema), and piping & instrumentation diagrams (P&ID / R&I-Fließschema).",
            "mandatory_fields": ["Flowsheet type", "Stream numbers", "Equipment tags", "Process operating conditions", "Mass/Energy balance table"]
        },
        {
            "id": "DIN-EN-ISO-10628-2",
            "code": "DIN EN ISO 10628-2",
            "title": "Diagrams for the chemical and petrochemical industry - Part 2: Graphical symbols",
            "authority": "DIN / ISO",
            "jurisdiction": "Germany / Europe",
            "legal_status": "Harmonized Technical Standard",
            "scope": "Standardized vector graphical symbols for vessels, heat exchangers, pumps, compressors, columns, reactors, valves, and piping connections.",
            "mandatory_fields": ["Symbol classification", "Nozzle orientation", "Fluid direction arrows", "Internals representation"]
        },
        {
            "id": "DIN-EN-ISO-7200",
            "code": "DIN EN ISO 7200",
            "title": "Technical product documentation - Data fields in title blocks and document headers",
            "authority": "DIN / ISO",
            "jurisdiction": "Germany / Europe / International",
            "legal_status": "International Mandatory Documentation Standard",
            "scope": "Specifies mandatory and optional data fields in drawing title blocks (legal owner, drawing number, revision index, approval, date, sheet number).",
            "mandatory_fields": ["Legal owner", "Identification number", "Date of issue", "Segment/sheet number", "Title", "Approving person", "Creator"]
        },
        {
            "id": "DIN-28004",
            "code": "DIN 28004 (Teile 1-4)",
            "title": "Fließschemata verfahrenstechnischer Anlagen (Flowsheets of process plants)",
            "authority": "DIN (Deutsches Institut für Normung)",
            "jurisdiction": "Germany",
            "legal_status": "National Industrial Standard",
            "scope": "Classification of flowsheets into Grundfließschema, Verfahrensfließschema, and R&I-Fließschema with representation of auxiliary systems.",
            "mandatory_fields": ["Verfahrensdaten (Process data)", "Bezeichnung von Apparaten und Maschinen", "Rohrleitungsbezeichnung"]
        },
        {
            "id": "DIN-EN-IEC-81346",
            "code": "DIN EN IEC 81346",
            "title": "Industrial systems, installations and equipment and industrial products - Structuring principles and reference designations (RDS-PP)",
            "authority": "DKE / IEC",
            "jurisdiction": "Germany / International",
            "legal_status": "Harmonized Reference Designation Standard",
            "scope": "Object-oriented reference designation system for plant equipment, functional units, and location-based tagging (=PLANT+SYS-P101).",
            "mandatory_fields": ["Aspect prefix (=, +, -)", "System letter code", "Sequential unit number", "Location reference"]
        },
        {
            "id": "BImSchG-TA-Luft",
            "code": "BImSchG / TA Luft 2021",
            "title": "Bundes-Immissionsschutzgesetz & Technische Anleitung zur Reinhaltung der Luft",
            "authority": "BMUV (German Federal Ministry for the Environment)",
            "jurisdiction": "Germany",
            "legal_status": "Mandatory Federal Law & Administrative Regulation",
            "scope": "Statutory emission limit values for industrial exhaust gases, volatile organic compounds (VOCs), dust, NOx, SO2, and odor emissions.",
            "mandatory_fields": ["Exhaust mass stream (kg/h)", "VOC concentration (mg/m3)", "Total carbon emission", "Abatement technology"]
        },
        {
            "id": "BetrSichV",
            "code": "BetrSichV",
            "title": "Betriebssicherheitsverordnung (German Health and Safety at Work Ordinance for Pressure Equipment)",
            "authority": "BAuA (Federal Institute for Occupational Safety and Health)",
            "jurisdiction": "Germany",
            "legal_status": "Mandatory Statutory Ordinance",
            "scope": "Safety assessment, recurring inspections by Approved Inspection Bodies (ZÜS) for overpressure systems, steam boilers, and hazardous plants.",
            "mandatory_fields": ["Prüfgruppe (Inspection class)", "ZÜS-Prüffristen", "Gefährdungsbeurteilung (Risk assessment)"]
        },

        # --- EUROPEAN UNION (EN / ISO / Directives) ---
        {
            "id": "PED-2014-68-EU",
            "code": "Directive 2014/68/EU (PED)",
            "title": "Pressure Equipment Directive (PED) - Harmonisation of the laws of the Member States relating to the making available on the market of pressure equipment",
            "authority": "European Parliament and Council of the EU",
            "jurisdiction": "European Union (EEA)",
            "legal_status": "Mandatory EU Directive (Legal Requirement for CE Marking)",
            "scope": "Design, manufacture, testing, and conformity assessment of pressure vessels, piping, safety accessories, and assemblies operating above 0.5 bar gauge.",
            "mandatory_fields": ["Fluid group (1 or 2)", "Fluid state (gas/liquid)", "PS (bar)", "V (liters)", "PS*V product", "Hazard Category (SEP to IV)", "Conformity Module (A to H1)", "CE Mark"]
        },
        {
            "id": "EN-13445",
            "code": "EN 13445 (Parts 1-5)",
            "title": "Unfired pressure vessels - Design, materials, manufacturing and inspection",
            "authority": "CEN (European Committee for Standardization)",
            "jurisdiction": "European Union",
            "legal_status": "Harmonized European Standard supporting PED 2014/68/EU",
            "scope": "Comprehensive European engineering standard for pressure vessel wall thickness, head design, nozzle reinforcement, fatigue analysis, and hydrostatic pressure testing.",
            "mandatory_fields": ["Allowable design stress f", "Joint efficiency z", "Corrosion allowance c", "Calculated shell thickness", "Hydrostatic test pressure Pt"]
        },
        {
            "id": "EN-1092-1",
            "code": "EN 1092-1",
            "title": "Flanges and their joints - Circular flanges for pipes, valves, fittings and accessories, PN designated",
            "authority": "CEN",
            "jurisdiction": "European Union",
            "legal_status": "Harmonized European Standard",
            "scope": "Pressure-temperature ratings, dimensions, tolerances, and bolt patterns for steel flanges designated by PN (PN 6 to PN 400).",
            "mandatory_fields": ["PN designation", "DN nominal diameter", "Facing type (Type A, B, C, D)", "Bolt size and count"]
        },
        {
            "id": "EN-ISO-4126",
            "code": "EN ISO 4126 (Parts 1-10)",
            "title": "Safety devices for protection against excessive pressure - Safety valves and bursting discs",
            "authority": "CEN / ISO",
            "jurisdiction": "European Union / International",
            "legal_status": "Harmonized European Standard",
            "scope": "Sizing, discharge capacity calculation, set pressure tolerances, and flow coefficient testing for pressure relief valves.",
            "mandatory_fields": ["Certified derated coefficient of discharge Kdr", "Flow area Ao", "Set pressure Pset", "Relieving capacity qm"]
        },
        {
            "id": "ATEX-2014-34-EU",
            "code": "Directive 2014/34/EU (ATEX)",
            "title": "Equipment and protective systems intended for use in potentially explosive atmospheres",
            "authority": "European Parliament and Council of the EU",
            "jurisdiction": "European Union",
            "legal_status": "Mandatory EU Directive",
            "scope": "Safety requirements for mechanical and electrical equipment operating in flammable vapor, gas, mist, or dust atmospheres (Zone 0, 1, 2).",
            "mandatory_fields": ["ATEX Equipment Group (II)", "Category (1G, 2G, 3G)", "Explosion group (IIA, IIB, IIC)", "Temperature class (T1 to T6)"]
        },

        # --- UNITED STATES (ANSI / ASME / ISA / OSHA / API / TEMA) ---
        {
            "id": "OSHA-1910-119",
            "code": "29 CFR 1910.119",
            "title": "Process Safety Management of Highly Hazardous Chemicals (PSM)",
            "authority": "US OSHA (Occupational Safety and Health Administration)",
            "jurisdiction": "United States",
            "legal_status": "Mandatory Federal Regulation (Statutory Law)",
            "scope": "Prevention of catastrophic releases of toxic, reactive, flammable, or explosive chemicals. Mandates Process Safety Information (PSI), PHA/HAZOP, and operating procedures.",
            "mandatory_fields": ["Chemical toxicity / PEL", "Process technology envelope (Safe upper/lower T & P limits)", "Maximum intended inventory", "Equipment materials of construction", "Relief system design basis", "P&ID certification"]
        },
        {
            "id": "ASME-BPVC-SEC-VIII-DIV-1",
            "code": "ASME Section VIII Div 1",
            "title": "Boiler and Pressure Vessel Code (BPVC) - Rules for Construction of Pressure Vessels",
            "authority": "ASME (American Society of Mechanical Engineers)",
            "jurisdiction": "United States / Global",
            "legal_status": "Mandatory Jurisdiction Code (Enacted in 50 US States)",
            "scope": "Design, fabrication, inspection, testing, and certification of pressure vessels operating at pressures exceeding 15 psig. Generates Form U-1A Manufacturer's Data Report.",
            "mandatory_fields": ["Maximum Allowable Working Pressure (MAWP)", "Design Temperature", "Minimum Design Metal Temperature (MDMT)", "Corrosion Allowance", "Radiography Type (RT-1 to RT-4)", "Weld Joint Efficiency E"]
        },
        {
            "id": "ASME-B31-3",
            "code": "ASME B31.3",
            "title": "Process Piping Code",
            "authority": "ASME",
            "jurisdiction": "United States / Global",
            "legal_status": "Consensus Engineering Code",
            "scope": "Piping design, material selection, fabrication, stress analysis, hydrostatic testing, and inspection for chemical plants and refineries.",
            "mandatory_fields": ["Fluid service category (Normal, Category D, Category M)", "Design pressure/temperature", "Pipe wall schedule", "Allowable stress S"]
        },
        {
            "id": "ASME-Y14-1",
            "code": "ASME Y14.1 / Y14.24",
            "title": "Drawing Sheet Size and Format & Types and Applications of Engineering Drawings",
            "authority": "ASME",
            "jurisdiction": "United States",
            "legal_status": "National Technical Standard",
            "scope": "Standardized drawing sizes (A, B, C, D, E), border zones, title block layout, revision blocks, and drawing conventions.",
            "mandatory_fields": ["CAGE code", "Drawing size", "Drawing number", "Revision letter", "Sheet number", "Signatures (Drawn, Checked, Approved)"]
        },
        {
            "id": "ISA-5-1",
            "code": "ANSI/ISA-5.1",
            "title": "Instrumentation Symbols and Identification",
            "authority": "ISA (International Society of Automation)",
            "jurisdiction": "United States / International",
            "legal_status": "Consensus Technical Standard",
            "scope": "Identification system for instruments and control systems on P&IDs, including bubble symbols, tag numbering (e.g. PIC-101, TT-204), and instrument line types.",
            "mandatory_fields": ["First letter (Measured variable)", "Succeeding letters (Readout/Output)", "Loop number", "Location indicator (Field vs. DCS board)"]
        },
        {
            "id": "API-520-521-526",
            "code": "API Standard 520 / 521 / 526",
            "title": "Sizing, Selection, and Installation of Pressure-Relieving Devices & Flanged Steel Pressure-Relief Valves",
            "authority": "API (American Petroleum Institute)",
            "jurisdiction": "United States / Global Refining",
            "legal_status": "Industrial Standard of Reference",
            "scope": "Vapor, liquid, and two-phase emergency relief sizing, fire overpressure scenarios, and standardized orifice letter designations (D through T).",
            "mandatory_fields": ["Governing sizing scenario", "Required discharge capacity (lb/h or kg/h)", "Overpressure percentage", "Standard orifice letter", "Valve inlet/outlet flange size"]
        },
        {
            "id": "TEMA-API-660",
            "code": "TEMA 10th Ed. / API 660",
            "title": "Standards of the Tubular Exchanger Manufacturers Association & Shell-and-Tube Heat Exchangers",
            "authority": "TEMA / API",
            "jurisdiction": "United States / Global",
            "legal_status": "Industrial Fabrication Standard",
            "scope": "Mechanical design, TEMA configuration classification (Front head, Shell, Rear head: e.g. BEM, AES, AET), tube pitch, and fouling margins.",
            "mandatory_fields": ["TEMA configuration type", "Shell inside diameter", "Tube OD and length", "Tube count and passes", "Baffle cut and spacing"]
        },
        {
            "id": "API-610",
            "code": "API Standard 610 (ISO 13709)",
            "title": "Centrifugal Pumps for Petroleum, Petrochemical and Natural Gas Industries",
            "authority": "API / ISO",
            "jurisdiction": "United States / Global",
            "legal_status": "Heavy-Duty Equipment Standard",
            "scope": "Design, construction, hydraulic performance, NPSH margin, mechanical seal configurations, and vibration limits for process pumps.",
            "mandatory_fields": ["Pump type (OH2, BB1, BB2, etc.)", "Design flow and differential head", "NPSHa vs NPSHr margin", "Motor driver rating (kW)"]
        }
    ]

    @classmethod
    def get_all_standards(cls) -> List[Dict[str, Any]]:
        """Returns the full standards repository."""
        return cls.STANDARDS_CATALOG

    @classmethod
    def filter_by_jurisdiction(cls, jurisdiction: str) -> List[Dict[str, Any]]:
        """
        Filters standards by jurisdiction:
        'germany', 'europe', 'usa', 'dual', or 'all'.
        Handles abbreviations and compound strings (e.g. 'EU/EN', 'DIN/VDI', 'ASME/US').
        """
        jur_lower = jurisdiction.lower()
        if jur_lower in ("all", "international", "dual"):
            return cls.STANDARDS_CATALOG

        results = []
        for s in cls.STANDARDS_CATALOG:
            s_jur = s.get("jurisdiction", "").lower()
            s_code = s.get("code", "").lower()
            matched = False

            if any(k in jur_lower for k in ["germany", "din", "vdi", "bimschg"]):
                if "germany" in s_jur or "din" in s_code:
                    matched = True
            if any(k in jur_lower for k in ["europe", "eu", "en", "ped"]):
                if "europe" in s_jur or "european" in s_jur or "en" in s_code:
                    matched = True
            if any(k in jur_lower for k in ["usa", "us", "asme", "osha", "ansi", "api", "tema", "isa"]):
                if "united states" in s_jur or "asme" in s_code or "osha" in s_code or "api" in s_code:
                    matched = True

            if matched:
                results.append(s)

        return results if results else cls.STANDARDS_CATALOG

    @classmethod
    def search_standards(cls, query: str) -> List[Dict[str, Any]]:
        """Searches standards by code, title, or scope keywords."""
        q = query.lower().strip()
        if not q:
            return cls.STANDARDS_CATALOG
        return [
            s for s in cls.STANDARDS_CATALOG
            if q in s["code"].lower() or q in s["title"].lower() or q in s["scope"].lower() or q in s["authority"].lower()
        ]


class PEDClassifier:
    """
    Pressure Equipment Directive (PED 2014/68/EU) CE Conformity Evaluation Engine.
    Implements Annex II Conformity Assessment Tables 1 through 4 for process vessels.
    """

    # Group 1 Fluids: Explosive, extremely flammable, toxic, oxidizing
    GROUP_1_CHEMICALS = {
        "methane", "ethane", "propane", "butane", "isobutane", "pentane",
        "hexane", "heptane", "octane", "benzene", "toluene", "xylene",
        "ethylene", "propylene", "hydrogen", "carbon_monoxide", "ammonia",
        "methanol", "ethanol", "acetone", "chlorine", "hydrogen_sulfide"
    }

    @classmethod
    def determine_fluid_group(cls, composition: Dict[str, float]) -> int:
        """
        Determines PED fluid group (1 or 2):
        - Group 1: Hazardous (flammable, toxic, oxidizing). If Group 1 species > 1.0 mol%.
        - Group 2: All other fluids (steam, water, nitrogen, air, inert).
        """
        if not composition:
            return 2
        for comp, frac in composition.items():
            if frac > 0.01 and comp.lower() in cls.GROUP_1_CHEMICALS:
                return 1
        return 2

    @classmethod
    def classify_vessel(cls, ps_bar: float, volume_m3: float,
                        fluid_group: int, is_gas_or_vapor: bool) -> Dict[str, Any]:
        """
        Classifies a process vessel according to PED 2014/68/EU Annex II:
        - ps_bar: Maximum Allowable Pressure PS in bar gauge (bar).
        - volume_m3: Internal volume V in cubic meters (m3).
        - fluid_group: 1 (Hazardous) or 2 (Non-hazardous).
        - is_gas_or_vapor: True if fluid vapor pressure at max temp > 0.5 bar above atmospheric.
        """
        v_liters = max(0.001, volume_m3 * 1000.0)  # V in Liters
        ps_v = ps_bar * v_liters  # bar * L product

        category = "SEP"  # Sound Engineering Practice (Art. 4(3))
        table_ref = "Table 1"
        ce_required = False
        modules: List[str] = ["Sound Engineering Practice (No CE Mark)"]
        notified_body_required = False

        if ps_bar <= 0.5:
            # Below PED lower threshold (0.5 bar gauge)
            category = "SEP"
            description = "Operating pressure <= 0.5 bar. Subject to Sound Engineering Practice (SEP), Article 4 Paragraph 3. CE mark not permitted."
            table_ref = "Article 4(3)"
        elif is_gas_or_vapor:
            if fluid_group == 1:
                # Table 1: Gases, Liquefied gases, dissolved gases in Group 1
                table_ref = "Annex II, Table 1 (Group 1 Gases)"
                if v_liters <= 1.0 and ps_v <= 25.0:
                    category = "SEP"
                elif ps_v <= 50.0 and v_liters > 1.0:
                    category = "Category I"
                elif 50.0 < ps_v <= 200.0:
                    category = "Category II"
                elif 200.0 < ps_v <= 1000.0 or ps_bar > 200.0:
                    category = "Category III"
                else:  # ps_v > 1000.0
                    category = "Category IV"
            else:
                # Table 2: Gases, Liquefied gases in Group 2 (e.g. steam, compressed air)
                table_ref = "Annex II, Table 2 (Group 2 Gases)"
                if ps_v <= 50.0 or v_liters <= 1.0:
                    category = "SEP"
                elif 50.0 < ps_v <= 200.0:
                    category = "Category I"
                elif 200.0 < ps_v <= 1000.0:
                    category = "Category II"
                elif 1000.0 < ps_v <= 3000.0 or ps_bar > 400.0:
                    category = "Category III"
                else:  # ps_v > 3000.0
                    category = "Category IV"
        else:
            # Liquids
            if fluid_group == 1:
                # Table 3: Liquids in Group 1
                table_ref = "Annex II, Table 3 (Group 1 Liquids)"
                if ps_v <= 200.0:
                    category = "SEP"
                elif 200.0 < ps_v <= 500.0:
                    category = "Category I"
                elif ps_v > 500.0 and ps_bar <= 500.0:
                    category = "Category II"
                else:
                    category = "Category III"
            else:
                # Table 4: Liquids in Group 2 (e.g. water, non-toxic liquid)
                table_ref = "Annex II, Table 4 (Group 2 Liquids)"
                if ps_bar <= 10.0 or ps_v <= 10000.0:
                    category = "SEP"
                elif ps_bar > 10.0 and 10000.0 < ps_v:
                    category = "Category I"
                elif ps_bar > 500.0:
                    category = "Category II"
                else:
                    category = "SEP"

        # Assign CE requirements and Conformity Modules
        if category == "Category I":
            ce_required = True
            notified_body_required = False
            modules = ["Module A (Internal Production Control)"]
            description = "Category I: CE mark applied by manufacturer. No Notified Body inspection required."
        elif category == "Category II":
            ce_required = True
            notified_body_required = True
            modules = ["Module A2 (Internal control with supervised checks)", "Module D1 (Production QA)", "Module E1 (Product QA)"]
            description = "Category II: Mandatory CE mark with Notified Body surveillance during final assessment."
        elif category == "Category III":
            ce_required = True
            notified_body_required = True
            modules = ["Module B (EU-Type Examination) + Module D (Production QA)", "Module B + Module F (Product Verification)", "Module H (Full Quality Assurance)"]
            description = "Category III: High hazard. Mandatory EU-Type Examination by Notified Body or Full Quality Assurance."
        elif category == "Category IV":
            ce_required = True
            notified_body_required = True
            modules = ["Module B (Design Type) + Module D (Production QA)", "Module G (Unit Verification)", "Module H1 (Full QA with Design Examination)"]
            description = "Category IV: Highest hazard classification. Requires comprehensive Notified Body design examination and testing."
        else:
            description = "Sound Engineering Practice (SEP): Safe design according to recognized technical codes (EN 13445 / AD 2000). CE mark forbidden under PED Article 4(3)."

        return {
            "category": category,
            "table_reference": table_ref,
            "ps_bar": round(ps_bar, 2),
            "volume_liters": round(v_liters, 1),
            "ps_x_v_bar_L": round(ps_v, 1),
            "fluid_group": fluid_group,
            "fluid_state": "Gas/Vapor" if is_gas_or_vapor else "Liquid",
            "ce_marking_required": ce_required,
            "notified_body_required": notified_body_required,
            "recommended_modules": modules,
            "legal_description": description,
            "harmonized_design_code": "EN 13445 (Unfired Pressure Vessels) or AD 2000 Merkblätter"
        }


class OSHAPSIChecker:
    """
    US OSHA 29 CFR 1910.119 Process Safety Information (PSI) Compliance Engine.
    Structures process safety technology, equipment design limits, and chemical hazards.
    """

    @classmethod
    def compile_chemical_hazards(cls, components: List[str]) -> List[Dict[str, Any]]:
        """Compiles 1910.119(d)(1) chemical hazard data for process components."""
        hazards_db = {
            "methane": {"cas": "74-82-8", "pel_ppm": "1000", "flammability_limits": "5.0 - 15.0%", "reactivity": "Stable, asphyxiant", "nfpa": "1-4-0"},
            "ethane": {"cas": "74-84-0", "pel_ppm": "1000", "flammability_limits": "3.0 - 12.4%", "reactivity": "Extremely flammable", "nfpa": "1-4-0"},
            "propane": {"cas": "74-98-6", "pel_ppm": "1000", "flammability_limits": "2.1 - 9.5%", "reactivity": "Extremely flammable", "nfpa": "1-4-0"},
            "butane": {"cas": "106-97-8", "pel_ppm": "800", "flammability_limits": "1.8 - 8.4%", "reactivity": "Extremely flammable", "nfpa": "1-4-0"},
            "octane": {"cas": "111-65-9", "pel_ppm": "500", "flammability_limits": "1.0 - 6.5%", "reactivity": "Flammable liquid", "nfpa": "1-3-0"},
            "benzene": {"cas": "71-43-2", "pel_ppm": "1 (Carcinogen)", "flammability_limits": "1.2 - 7.8%", "reactivity": "Carcinogen, flammable", "nfpa": "2-3-0"},
            "toluene": {"cas": "108-88-3", "pel_ppm": "200", "flammability_limits": "1.1 - 7.1%", "reactivity": "Flammable liquid, toxic", "nfpa": "2-3-0"},
            "phenol": {"cas": "108-95-2", "pel_ppm": "5 (Skin)", "flammability_limits": "1.7 - 8.6%", "reactivity": "Corrosive, highly toxic", "nfpa": "4-2-0"},
            "ethanol": {"cas": "64-17-5", "pel_ppm": "1000", "flammability_limits": "3.3 - 19.0%", "reactivity": "Flammable liquid", "nfpa": "2-3-0"},
            "methanol": {"cas": "67-56-1", "pel_ppm": "200 (Skin)", "flammability_limits": "6.0 - 36.0%", "reactivity": "Toxic, highly flammable", "nfpa": "1-3-0"},
            "water": {"cas": "7732-18-5", "pel_ppm": "N/A", "flammability_limits": "Non-flammable", "reactivity": "Inert", "nfpa": "0-0-0"},
            "ammonia": {"cas": "7664-41-7", "pel_ppm": "50", "flammability_limits": "15.0 - 28.0%", "reactivity": "Toxic gas, corrosive", "nfpa": "3-1-0"},
            "co2": {"cas": "124-38-9", "pel_ppm": "5000", "flammability_limits": "Non-flammable", "reactivity": "Simple asphyxiant", "nfpa": "2-0-0"}
        }

        results = []
        for c in components:
            c_low = c.lower()
            h = hazards_db.get(c_low, {
                "cas": "Proprietary",
                "pel_osha_ppm": "Standard",
                "flammability_range": "Non-flammable / Trace",
                "chemical_reactivity": "Standard industrial chemical",
                "nfpa_704": "1-1-0"
            })
            results.append({
                "component": c,
                "cas_number": h.get("cas", "Proprietary"),
                "pel_osha_ppm": h.get("pel_ppm", "1000"),
                "flammability_range": h.get("flammability_limits", "Non-flammable"),
                "chemical_reactivity": h.get("reactivity", "Stable"),
                "nfpa_704": h.get("nfpa", "1-0-0")
            })
        return results

    @classmethod
    def compile_technology_envelope(cls, unit_id: str, unit_type: str,
                                    oper_t_c: float, oper_p_bar: float,
                                    design_p_bar: float) -> Dict[str, Any]:
        """
        Compiles 1910.119(d)(2) Process Technology Safe Operating Limits:
        - Upper / lower temperature limits
        - Upper / lower pressure limits
        - Consequence of deviation
        """
        safe_p_max = max(design_p_bar, oper_p_bar * 1.2)
        safe_p_min = 0.05  # Avoid unintended vacuum collapse
        safe_t_max = oper_t_c + 50.0
        safe_t_min = max(-40.0, oper_t_c - 40.0)

        consequence_high_p = f"Overpressurization exceeding MAWP ({safe_p_max:.1f} bar). Relief valve trip or catastrophic vessel rupture."
        consequence_low_p = "Potential air ingress into flammable atmosphere or vessel vacuum buckling."
        consequence_high_t = f"Thermal runaway or thermal degradation of product above {safe_t_max:.1f}°C."
        consequence_low_t = f"Loss of kinetics, freezing or embrittlement below {safe_t_min:.1f}°C."

        return {
            "unit_id": unit_id,
            "unit_type": unit_type,
            "normal_operating_point": f"{oper_t_c:.1f}°C, {oper_p_bar:.2f} bar",
            "safe_upper_pressure_limit": f"{safe_p_max:.2f} bar (MAWP)",
            "safe_lower_pressure_limit": f"{safe_p_min:.2f} bar",
            "safe_upper_temp_limit": f"{safe_t_max:.1f}°C",
            "safe_lower_temp_limit": f"{safe_t_min:.1f}°C",
            "consequence_high_p": consequence_high_p,
            "consequence_low_p": consequence_low_p,
            "consequence_high_t": consequence_high_t,
            "consequence_low_t": consequence_low_t,
            "corrective_interlock": "Automated SIS ESD Trip + API 526 Safety Relief Valve"
        }
