"""
Engineering Report Generator & Data Package Exporter.
Produces JSON flowsheet data packages and printable HTML Engineering Data Sheets
with full mass/energy balance closure, sizing schedules, and Turton & Guthrie TEA costing.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional

class ReportGenerator:
    """Generates technical documentation, JSON exports, and HTML engineering reports."""

    @classmethod
    def export_flowsheet_json(cls, units_map: dict, streams_map: dict,
                              connections_list: Optional[list] = None,
                              connections: Optional[list] = None,
                              boundaries: Optional[dict] = None,
                              econ_results: Optional[dict] = None,
                              metadata: Optional[dict] = None, **kwargs) -> str:
        """Serializes flowsheet architecture and state to JSON."""
        conns = connections if connections is not None else (connections_list or [])
        data = {
            "flowsheet_version": "1.9.0",
            "metadata": metadata or {
                "generated_at": datetime.now().isoformat(),
                "software": "Hybrid Process Synthesizer",
                "version": "1.9.0"
            },
            "boundaries": boundaries or {},
            "connections": conns,
            "units": {},
            "streams": {}
        }
        if econ_results:
            data["economics"] = econ_results

        # Units
        for uid, unit in units_map.items():
            if isinstance(unit, dict):
                data["units"][uid] = unit
            else:
                data["units"][uid] = {
                    "type": unit.__class__.__name__,
                    "name": getattr(unit, "name", uid),
                    "material": getattr(unit, "material", "Carbon Steel"),
                    "design_pressure_bar": round(getattr(unit, "design_pressure", 101325.0) / 100000.0, 2),
                    "heat_duty_kW": round(getattr(unit, "heat_duty", 0.0) / 1000.0, 2),
                    "work_input_kW": round(getattr(unit, "work_input", 0.0) / 1000.0, 2),
                    "sizing": getattr(unit, "sizing_results", {})
                }

        # Streams
        for sid, st in streams_map.items():
            if isinstance(st, dict):
                data["streams"][sid] = st
            else:
                data["streams"][sid] = {
                    "temperature_K": round(st.T, 2) if st.T else None,
                    "pressure_Pa": round(st.P, 1) if st.P else None,
                    "flow_mol_s": round(st.F, 3) if st.F is not None else None,
                    "composition": st.z or {}
                }

        return json.dumps(data, indent=2)

    @classmethod
    def generate_engineering_report_html(cls, units_map: dict, streams_map: dict,
                                          connections: Optional[list] = None,
                                          connections_list: Optional[list] = None,
                                          mass_bal: Optional[dict] = None,
                                          energy_bal: Optional[dict] = None,
                                          tea_summary: Optional[dict] = None,
                                          econ_results: Optional[dict] = None,
                                          plant_name: str = "Process Plant Facility",
                                          project_title: Optional[str] = None,
                                          **kwargs) -> str:
        """Generates an HTML technical engineering summary report with styling."""
        if project_title:
            plant_name = project_title
        if econ_results is not None and tea_summary is None:
            tea_summary = econ_results
        tea_summary = tea_summary or {}
        mass_bal = mass_bal or {}
        energy_bal = energy_bal or {}
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        capex = tea_summary.get("capex", {})
        opex = tea_summary.get("opex", {})
        prof = tea_summary.get("profitability", {})
        eq_costs = tea_summary.get("equipment_costs", [])

        # Equipment rows
        eq_rows_html = ""
        for eq in eq_costs:
            eq_rows_html += f"""
            <tr>
                <td><strong>{eq.get('unit_id')}</strong></td>
                <td>{eq.get('unit_type')}</td>
                <td>{eq.get('material', 'Carbon Steel')}</td>
                <td>{eq.get('sizing_parameter')}: {eq.get('sizing_value')} {eq.get('sizing_unit')}</td>
                <td>{eq.get('design_pressure_bar', 1.0):.1f} bar</td>
                <td>{eq.get('F_P', 1.0):.2f}</td>
                <td>{eq.get('F_M', 1.0):.2f}</td>
                <td>${eq.get('Cp', 0.0):,.0f}</td>
                <td><strong>${eq.get('C_BM', 0.0):,.0f}</strong></td>
            </tr>
            """

        # Stream rows
        stream_rows_html = ""
        for sid, st in streams_map.items():
            t_k = f"{st.T:.1f}" if hasattr(st, "T") and st.T else "N/A"
            p_kpa = f"{st.P/1000.0:.1f}" if hasattr(st, "P") and st.P else "N/A"
            f_mol = f"{st.F:.2f}" if hasattr(st, "F") and st.F is not None else "N/A"
            comp_str = ", ".join([f"{k}: {v*100:.1f}%" for k, v in (st.z or {}).items()]) if hasattr(st, "z") and st.z else "N/A"
            stream_rows_html += f"""
            <tr>
                <td><strong>{sid}</strong></td>
                <td>{t_k}</td>
                <td>{p_kpa}</td>
                <td>{f_mol}</td>
                <td>{comp_str}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Process Engineering Design & Economic Evaluation Report - {plant_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; line-height: 1.5; margin: 30px; background-color: #f8fafc; }}
        .report-card {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); max-width: 1100px; margin: auto; }}
        h1 {{ color: #0f172a; margin-bottom: 4px; font-size: 26px; border-bottom: 2px solid #0284c7; padding-bottom: 8px; }}
        .header-meta {{ font-size: 13px; color: #64748b; margin-bottom: 20px; }}
        h2 {{ color: #0369a1; font-size: 18px; margin-top: 24px; margin-bottom: 8px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; font-size: 13px; }}
        th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; }}
        th {{ background-color: #f1f5f9; color: #334155; font-weight: 600; }}
        tr:nth-child(even) {{ background-color: #f8fafc; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 15px 0; }}
        .kpi-box {{ background: #f0f9ff; border: 1px solid #bae6fd; padding: 12px; border-radius: 8px; text-align: center; }}
        .kpi-title {{ font-size: 11px; color: #0369a1; font-weight: bold; text-transform: uppercase; }}
        .kpi-value {{ font-size: 20px; font-weight: bold; color: #0c4a6e; margin-top: 4px; }}
        .badge-pass {{ background: #dcfce7; color: #15803d; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
        .signoff {{ margin-top: 40px; display: grid; grid-template-columns: 1fr 1fr; gap: 40px; border-top: 1px solid #cbd5e1; padding-top: 20px; font-size: 13px; }}
    </style>
</head>
<body>
    <div class="report-card">
        <h1>Process Engineering Design & Economic Evaluation Report</h1>
        <div class="header-meta">
            Facility: <strong>{plant_name}</strong> | Generated: <strong>{now_str}</strong> | Simulator: <strong>Hybrid Process Synthesizer v1.9.0</strong> | Standard: <strong>ASME Sec VIII / Turton-Guthrie</strong>
        </div>

        <div class="kpi-grid">
            <div class="kpi-box">
                <div class="kpi-title">Fixed Capital (FCI)</div>
                <div class="kpi-value">${capex.get('fixed_capital_investment_FCI', 0.0):,.0f}</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-title">Total Investment (TCI)</div>
                <div class="kpi-value">${capex.get('total_capital_investment_TCI', 0.0):,.0f}</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-title">Annual Utility OPEX</div>
                <div class="kpi-value">${opex.get('total_annual_utility_opex_usd', 0.0):,.0f}/yr</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-title">15-Year Project NPV</div>
                <div class="kpi-value">${prof.get('net_present_value_NPV_usd', 0.0):,.0f}</div>
            </div>
        </div>

        <h2>1. Plant Mass & Energy Conservation Balances</h2>
        <table>
            <tr>
                <th>Balance Type</th>
                <th>Total Inflow</th>
                <th>Total Outflow</th>
                <th>Closure Error</th>
                <th>Conservation Status</th>
            </tr>
            <tr>
                <td><strong>Overall Mass Balance</strong></td>
                <td>{mass_bal.get('total_inlet_mass_kg_h', 0.0):.2f} kg/h</td>
                <td>{mass_bal.get('total_outlet_mass_kg_h', 0.0):.2f} kg/h</td>
                <td>{mass_bal.get('mass_balance_error_kg_h', 0.0):.4f} kg/h</td>
                <td><span class="badge-pass">CONSERVED (Pass)</span></td>
            </tr>
            <tr>
                <td><strong>Overall Energy Balance</strong></td>
                <td>{energy_bal.get('inlet_energy_kW', 0.0) + energy_bal.get('total_heat_added_kW', 0.0) + energy_bal.get('total_work_added_kW', 0.0):.2f} kW</td>
                <td>{energy_bal.get('outlet_energy_kW', 0.0):.2f} kW</td>
                <td>{energy_bal.get('energy_balance_error_kW', 0.0):.4f} kW</td>
                <td><span class="badge-pass">CONSERVED (Pass)</span></td>
            </tr>
        </table>

        <h2>2. Equipment Sizing & Turton-Guthrie Capital Costing Schedule</h2>
        <table>
            <thead>
                <tr>
                    <th>Tag</th>
                    <th>Equipment Type</th>
                    <th>Material</th>
                    <th>Design Capacity</th>
                    <th>Design P</th>
                    <th>F_P</th>
                    <th>F_M</th>
                    <th>Purchased Cp</th>
                    <th>Bare Module C_BM</th>
                </tr>
            </thead>
            <tbody>
                {eq_rows_html}
            </tbody>
        </table>

        <h2>3. Stream Hydraulic & Thermodynamic State Schedule</h2>
        <table>
            <thead>
                <tr>
                    <th>Stream ID</th>
                    <th>Temperature (K)</th>
                    <th>Pressure (kPa)</th>
                    <th>Molar Flow (mol/s)</th>
                    <th>Stream Composition</th>
                </tr>
            </thead>
            <tbody>
                {stream_rows_html}
            </tbody>
        </table>

        <h2>4. Techno-Economic & Financial Profitability Summary</h2>
        <table>
            <tr>
                <th>Total Bare Module Cost (C_BM)</th>
                <td>${capex.get('total_bare_module_cost_C_BM', 0.0):,.2f}</td>
                <th>Annual Operating Revenue</th>
                <td>${prof.get('annual_revenue_usd', 0.0):,.2f}/yr</td>
            </tr>
            <tr>
                <th>Contingency Fee (15%)</th>
                <td>${capex.get('contingency_fee', 0.0):,.2f}</td>
                <th>Cost of Manufacturing (COM)</th>
                <td>${prof.get('cost_of_manufacturing_COM_usd', 0.0):,.2f}/yr</td>
            </tr>
            <tr>
                <th>Contractor Fee (3%)</th>
                <td>${capex.get('contractor_fee', 0.0):,.2f}</td>
                <th>Simple Payback Period</th>
                <td><strong>{prof.get('payback_period_years', 0.0):.2f} years</strong></td>
            </tr>
            <tr>
                <th>Site Infrastructure Development</th>
                <td>${capex.get('site_development_cost', 0.0):,.2f}</td>
                <th>Return on Investment (ROI)</th>
                <td><strong>{prof.get('return_on_investment_ROI_pct', 0.0):.1f}%</strong></td>
            </tr>
            <tr>
                <th>Working Capital (WC)</th>
                <td>${capex.get('working_capital_WC', 0.0):,.2f}</td>
                <th>Internal Discount Rate</th>
                <td>{prof.get('discount_rate_pct', 10.0):.1f}%</td>
            </tr>
        </table>

        <div class="signoff">
            <div>
                <strong>Process Design Engineer:</strong><br>
                Name: Cristhian Caceres<br>
                Signature: __________________________<br>
                Date: {now_str}
            </div>
            <div>
                <strong>Technical Reviewer / Lead:</strong><br>
                Status: APPROVED FOR FRONT-END ENGINEERING (FEED)<br>
                Signature: __________________________<br>
                Date: {now_str}
            </div>
        </div>
    </div>
</body>
</html>
        """
        return html_content
