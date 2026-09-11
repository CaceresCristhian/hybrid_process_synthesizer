"""
Equipment Costing Engine.
Evaluates mechanical sizing metrics from unit operations and computes
purchased equipment costs and bare module costs using Turton/Guthrie correlations.
"""

import numpy as np
from typing import Dict, Any, Optional
from src.economics.cost_correlations import (
    CostCorrelations, DEFAULT_CEPCI, BASE_CEPCI
)

class EquipmentCosting:
    """Evaluates purchased cost Cp0, inflated Cp, and bare module cost C_BM for any flowsheet unit."""

    @classmethod
    def cost_unit(cls, unit: Any, material: Optional[str] = None,
                  cepci: float = DEFAULT_CEPCI) -> Dict[str, Any]:
        """
        Extracts sizing results from a unit operation and computes Turton/Guthrie costing.
        """
        # Ensure unit is sized
        if not hasattr(unit, "sizing_results") or not unit.sizing_results:
            if hasattr(unit, "size_equipment"):
                unit.size_equipment()

        sizing = getattr(unit, "sizing_results", {})
        unit_type = unit.__class__.__name__
        unit_mat = material or getattr(unit, "material", "Carbon Steel")

        # Determine operating/design pressure from inlet/outlet streams
        p_in = unit.inlets[0].P if (unit.inlets and unit.inlets[0].P) else 101325.0
        p_out = unit.outlets[0].P if (unit.outlets and unit.outlets[0].P) else 101325.0
        p_design = max(p_in, p_out, getattr(unit, "design_pressure", 101325.0))

        cost_info = {
            "unit_id": unit.unit_id,
            "unit_name": unit.name,
            "unit_type": unit_type,
            "material": unit_mat,
            "design_pressure_bar": round(p_design / 100000.0, 2),
            "sizing_parameter": "",
            "sizing_value": 0.0,
            "sizing_unit": "",
            "Cp0": 0.0,
            "Cp": 0.0,
            "F_P": 1.0,
            "F_M": 1.0,
            "C_BM": 0.0,
            "internals_cost": 0.0,
            "notes": ""
        }

        # 1. Thermal Units (Heater, Cooler, HeatExchanger)
        if unit_type in ["Heater", "Cooler", "HeatExchanger"]:
            area = max(0.5, sizing.get("heat_transfer_area_m2", 5.0))
            equip_type = "heat_exchanger_fixed_tubesheet" if unit_type in ["Heater", "Cooler"] else "heat_exchanger_floating_head"
            res = CostCorrelations.calculate_bare_module_cost(
                equip_type=equip_type,
                capacity=area,
                design_pressure_pa=p_design,
                material=unit_mat,
                cepci=cepci
            )
            cost_info.update({
                "sizing_parameter": "Heat Transfer Area",
                "sizing_value": area,
                "sizing_unit": "m2",
                "Cp0": res["Cp0"],
                "Cp": res["Cp"],
                "F_P": res["F_P"],
                "F_M": res["F_M"],
                "C_BM": res["C_BM"]
            })

        # 2. Flowsheet Pump
        elif unit_type == "FlowsheetPump":
            p_w = sizing.get("hydraulic_power_W", getattr(unit, "work_input", 500.0))
            power_kw = max(0.2, p_w / 1000.0)
            res = CostCorrelations.calculate_bare_module_cost(
                equip_type="pump_centrifugal",
                capacity=power_kw,
                design_pressure_pa=p_design,
                material=unit_mat,
                cepci=cepci
            )
            cost_info.update({
                "sizing_parameter": "Shaft Driver Power",
                "sizing_value": round(power_kw, 2),
                "sizing_unit": "kW",
                "Cp0": res["Cp0"],
                "Cp": res["Cp"],
                "F_P": res["F_P"],
                "F_M": res["F_M"],
                "C_BM": res["C_BM"]
            })

        # 3. Compressor
        elif unit_type == "Compressor":
            power_kw = max(1.0, sizing.get("driver_power_kW", getattr(unit, "work_input", 10000.0) / 1000.0))
            res = CostCorrelations.calculate_bare_module_cost(
                equip_type="compressor_centrifugal",
                capacity=power_kw,
                design_pressure_pa=p_design,
                material=unit_mat,
                cepci=cepci
            )
            cost_info.update({
                "sizing_parameter": "Driver Power",
                "sizing_value": round(power_kw, 2),
                "sizing_unit": "kW",
                "Cp0": res["Cp0"],
                "Cp": res["Cp"],
                "F_P": res["F_P"],
                "F_M": res["F_M"],
                "C_BM": res["C_BM"]
            })

        # 4. Expander
        elif unit_type == "Expander":
            power_kw = max(1.0, abs(getattr(unit, "work_input", 5000.0) / 1000.0))
            res = CostCorrelations.calculate_bare_module_cost(
                equip_type="expander_turbine",
                capacity=power_kw,
                design_pressure_pa=p_design,
                material=unit_mat,
                cepci=cepci
            )
            cost_info.update({
                "sizing_parameter": "Shaft Power Extracted",
                "sizing_value": round(power_kw, 2),
                "sizing_unit": "kW",
                "Cp0": res["Cp0"],
                "Cp": res["Cp"],
                "F_P": res["F_P"],
                "F_M": res["F_M"],
                "C_BM": res["C_BM"]
            })

        # 5. Distillation Column (Vessel Shell + Sieve Trays)
        elif unit_type in ["DistillationColumn", "BinaryDistillationColumn"]:
            d_col = max(0.4, sizing.get("column_diameter_m", 1.0))
            h_col = max(2.0, sizing.get("column_height_m", 12.0))
            num_trays = getattr(unit, "num_stages", 12)
            vessel_vol = round((np.pi / 4.0) * (d_col ** 2) * h_col, 2)

            # Sizing vessel shell
            vessel_res = CostCorrelations.calculate_bare_module_cost(
                equip_type="vessel_vertical",
                capacity=vessel_vol,
                design_pressure_pa=p_design,
                material=unit_mat,
                cepci=cepci,
                diameter_m=d_col
            )

            # Sizing Sieve Trays
            tray_area = max(0.1, (np.pi / 4.0) * (d_col ** 2))
            single_tray_cost0 = CostCorrelations.calculate_cp0("tray_sieve", tray_area)
            single_tray_cost = single_tray_cost0 * (cepci / BASE_CEPCI)
            f_m_tray = CostCorrelations.get_material_factor("tray_sieve", unit_mat)
            total_trays_cost = single_tray_cost * num_trays * f_m_tray

            total_c_bm = vessel_res["C_BM"] + total_trays_cost
            cost_info.update({
                "sizing_parameter": f"D={d_col:.2f}m, H={h_col:.2f}m ({num_trays} Trays)",
                "sizing_value": vessel_vol,
                "sizing_unit": "m3",
                "Cp0": round(vessel_res["Cp0"] + single_tray_cost0 * num_trays, 2),
                "Cp": round(vessel_res["Cp"] + single_tray_cost * num_trays, 2),
                "F_P": vessel_res["F_P"],
                "F_M": vessel_res["F_M"],
                "internals_cost": round(total_trays_cost, 2),
                "C_BM": round(total_c_bm, 2),
                "notes": f"Vessel C_BM=${vessel_res['C_BM']:,.0f} + Trays=${total_trays_cost:,.0f}"
            })

        # 6. Absorption Column (Vessel Shell + Structured Packing)
        elif unit_type == "AbsorptionColumn":
            d_col = max(0.4, sizing.get("column_diameter_m", 1.2))
            h_pack = max(2.0, sizing.get("packing_height_m", 8.5))
            h_total = h_pack + 2.5
            vessel_vol = round((np.pi / 4.0) * (d_col ** 2) * h_total, 2)
            pack_vol = (np.pi / 4.0) * (d_col ** 2) * h_pack

            vessel_res = CostCorrelations.calculate_bare_module_cost(
                equip_type="vessel_vertical",
                capacity=vessel_vol,
                design_pressure_pa=p_design,
                material=unit_mat,
                cepci=cepci,
                diameter_m=d_col
            )
            # Mellapak 250Y Structured Packing ~ $2,800/m3 at base CEPCI
            f_m_pack = CostCorrelations.get_material_factor("tray_sieve", unit_mat)
            packing_cost = pack_vol * 2800.0 * (cepci / BASE_CEPCI) * f_m_pack
            total_c_bm = vessel_res["C_BM"] + packing_cost

            cost_info.update({
                "sizing_parameter": f"D={d_col:.2f}m, H_pack={h_pack:.2f}m",
                "sizing_value": vessel_vol,
                "sizing_unit": "m3",
                "Cp0": vessel_res["Cp0"],
                "Cp": vessel_res["Cp"],
                "F_P": vessel_res["F_P"],
                "F_M": vessel_res["F_M"],
                "internals_cost": round(packing_cost, 2),
                "C_BM": round(total_c_bm, 2),
                "notes": f"Vessel C_BM=${vessel_res['C_BM']:,.0f} + Packing=${packing_cost:,.0f}"
            })

        # 7. Flash Drum / Separator
        elif unit_type in ["FlashDrum", "Separator"]:
            vol = max(0.1, sizing.get("vessel_volume_m3", 1.5))
            d_vess = sizing.get("vessel_diameter_m", 0.8)
            res = CostCorrelations.calculate_bare_module_cost(
                equip_type="vessel_vertical",
                capacity=vol,
                design_pressure_pa=p_design,
                material=unit_mat,
                cepci=cepci,
                diameter_m=d_vess
            )
            cost_info.update({
                "sizing_parameter": "Drum Volume",
                "sizing_value": vol,
                "sizing_unit": "m3",
                "Cp0": res["Cp0"],
                "Cp": res["Cp"],
                "F_P": res["F_P"],
                "F_M": res["F_M"],
                "C_BM": res["C_BM"]
            })

        # 8. Reactors (IdealCSTR, IdealPFR, EquilibriumReactor, JacketedBioreactor, Bioreactor)
        elif unit_type in ["IdealCSTR", "IdealPFR", "EquilibriumReactor", "JacketedBioreactor", "Bioreactor"]:
            vol = max(0.1, sizing.get("vessel_volume_m3", getattr(unit, "volume", 3.0)))
            d_react = sizing.get("diameter_m", sizing.get("design_diameter_m", sizing.get("bed_diameter_m", 1.0)))
            res = CostCorrelations.calculate_bare_module_cost(
                equip_type="reactor_jacketed",
                capacity=vol,
                design_pressure_pa=p_design,
                material=unit_mat,
                cepci=cepci,
                diameter_m=d_react
            )
            cost_info.update({
                "sizing_parameter": "Reactor Volume",
                "sizing_value": vol,
                "sizing_unit": "m3",
                "Cp0": res["Cp0"],
                "Cp": res["Cp"],
                "F_P": res["F_P"],
                "F_M": res["F_M"],
                "C_BM": res["C_BM"]
            })

        # 9. Solid Liquid Separator
        elif unit_type == "SolidLiquidSeparator":
            area = max(1.0, sizing.get("filter_area_m2", 4.0))
            res = CostCorrelations.calculate_bare_module_cost(
                equip_type="filter_centrifuge",
                capacity=area,
                design_pressure_pa=p_design,
                material=unit_mat,
                cepci=cepci
            )
            cost_info.update({
                "sizing_parameter": "Filter Area",
                "sizing_value": area,
                "sizing_unit": "m2",
                "Cp0": res["Cp0"],
                "Cp": res["Cp"],
                "F_P": res["F_P"],
                "F_M": res["F_M"],
                "C_BM": res["C_BM"]
            })

        # 10. Membrane Unit
        elif unit_type == "MembraneUnit":
            area = max(10.0, sizing.get("membrane_area_m2", 50.0))
            # Membrane skid module regression: Cp0 = 380 * Area^0.85
            cp0 = 380.0 * (area ** 0.85)
            cp = cp0 * (cepci / BASE_CEPCI)
            f_m = CostCorrelations.get_material_factor("heat_exchangers", unit_mat)
            f_p = 1.0 + 0.02 * max(0.0, (p_design - 101325.0) / 100000.0)
            c_bm = cp * (1.2 + 0.8 * f_m * f_p)
            cost_info.update({
                "sizing_parameter": "Membrane Area",
                "sizing_value": area,
                "sizing_unit": "m2",
                "Cp0": round(cp0, 2),
                "Cp": round(cp, 2),
                "F_P": round(f_p, 3),
                "F_M": round(f_m, 2),
                "C_BM": round(c_bm, 2)
            })

        # 11. Control Valve
        elif unit_type == "ControlValve":
            # Valve purchased cost correlation
            cp0 = 1250.0
            cp = cp0 * (cepci / BASE_CEPCI)
            f_m = CostCorrelations.get_material_factor("pumps", unit_mat)
            f_p = 1.0 + 0.015 * max(0.0, (p_design - 101325.0) / 100000.0)
            c_bm = cp * (1.1 + 0.6 * f_m * f_p)
            cost_info.update({
                "sizing_parameter": "Nominal Valve Size",
                "sizing_value": 2.0,
                "sizing_unit": "in",
                "Cp0": round(cp0, 2),
                "Cp": round(cp, 2),
                "F_P": round(f_p, 3),
                "F_M": round(f_m, 2),
                "C_BM": round(c_bm, 2)
            })

        # 12. Flowsheet Mixer / Splitter
        elif unit_type in ["FlowsheetMixer", "Splitter"]:
            cp0 = 850.0
            cp = cp0 * (cepci / BASE_CEPCI)
            f_m = CostCorrelations.get_material_factor("pumps", unit_mat)
            f_p = 1.0
            c_bm = cp * (1.2 + 0.4 * f_m)
            cost_info.update({
                "sizing_parameter": "Manifold Module",
                "sizing_value": 1.0,
                "sizing_unit": "ea",
                "Cp0": round(cp0, 2),
                "Cp": round(cp, 2),
                "F_P": round(f_p, 3),
                "F_M": round(f_m, 2),
                "C_BM": round(c_bm, 2)
            })

        # Fallback for any generic or custom unit
        else:
            cp0 = 2500.0
            cp = cp0 * (cepci / BASE_CEPCI)
            c_bm = cp * 2.5
            cost_info.update({
                "sizing_parameter": "Custom Unit",
                "sizing_value": 1.0,
                "sizing_unit": "ea",
                "Cp0": round(cp0, 2),
                "Cp": round(cp, 2),
                "F_P": 1.0,
                "F_M": 1.0,
                "C_BM": round(c_bm, 2)
            })

        return cost_info
