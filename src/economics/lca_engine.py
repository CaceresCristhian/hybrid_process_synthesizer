"""
Environmental Life Cycle Assessment (LCA) and Decarbonization Engine.
Implements ISO 14040/14044 and GHG Protocol Scope 1, Scope 2, and Scope 3
greenhouse gas (GHG) accounting, product carbon intensity, carbon tax sensitivity,
electrification pathways (MVR and Heat Pumps), and Marginal Abatement Cost (MAC).
"""

from typing import Dict, List, Any, Optional
import numpy as np

# Regional Electric Grid Emission Factors (kg CO2-eq per kWh)
# Sources: US EPA eGRID (2024), European Environment Agency (EEA 2024), IEA
REGIONAL_GRID_FACTORS: Dict[str, float] = {
    "US_Average": 0.386,
    "EU27_Average": 0.230,
    "California_CAISO": 0.210,
    "Coal_Heavy_Grid": 0.820,
    "Low_Carbon_Nuclear_Hydro": 0.025,
    "Green_PPA_100Pct_Renewable": 0.000
}

# Steam Boiler Fuel Carbon Intensity Factors (kg CO2-eq per GJ of steam delivered)
# Incorporates 85% typical industrial boiler thermal efficiency
STEAM_FUEL_FACTORS: Dict[str, float] = {
    "natural_gas_boiler": 66.0,  # 56.1 kg/GJ fuel / 0.85
    "fuel_oil_boiler": 88.0,
    "biomass_boiler": 5.0,       # processing/harvesting transport overhead (biogenic neutral)
    "electric_boiler": 0.0,      # indirect accounted via Scope 2 electricity
    "waste_heat_boiler": 0.0
}

# Cradle-to-Gate Feedstock Embodied Carbon Factors (kg CO2-eq per kg chemical)
# Sources: Ecoinvent 3.9, BioSTEAM database, ICIS Carbon Footprint Index
FEEDSTOCK_EMBODIED_FACTORS: Dict[str, float] = {
    "methane": 0.45,
    "natural_gas": 0.45,
    "ethanol": 1.25,      # conventional corn starch benchmark
    "ethanol_bio": 0.40,  # sugarcane low-carbon pathway
    "glucose": 0.65,
    "methanol": 0.70,
    "ammonia": 2.10,      # conventional Haber-Bosch from SMR
    "ammonia_green": 0.35,# green hydrogen Haber-Bosch
    "hydrogen": 10.50,    # gray hydrogen via SMR
    "hydrogen_green": 0.80,# renewable electrolysis
    "water": 0.0003,
    "octane": 0.42,
    "benzene": 0.55,
    "toluene": 0.50,
    "acetone": 1.40,
    "propane": 0.40,
    "butane": 0.41,
    "pentane": 0.43,
    "phenol": 1.65,
    "co2": 0.00,
    "nitrogen": 0.05,
    "oxygen": 0.08,
    "general": 0.60
}


class LCAAnalyzer:
    """Rigorous Environmental LCA and Decarbonization Assessment Engine."""

    @classmethod
    def calculate_scope_1_emissions(cls, units_list: list, streams_list: list,
                                     fuel_type: str = "natural_gas_boiler",
                                     operating_hours: float = 8000.0) -> Dict[str, Any]:
        """
        Calculates Scope 1 direct emissions from fuel combustion in heaters/furnaces
        and direct process reaction vents (CO2 release).
        """
        fuel_factor_kg_gj = STEAM_FUEL_FACTORS.get(fuel_type, STEAM_FUEL_FACTORS["natural_gas_boiler"])

        combustion_co2_kg_yr = 0.0
        reaction_vent_co2_kg_yr = 0.0
        unit_details = []

        # 1. Fuel combustion emissions from process heaters and thermal equipment
        for u in units_list:
            u_id = getattr(u, "unit_id", "Unknown")
            u_type = u.__class__.__name__
            q_watts = getattr(u, "heat_duty", 0.0)

            # Heaters and distillation reboilers with positive heating duty
            if q_watts > 0 and u_type in ["Heater", "BinaryDistillationColumn", "DynamicDistillationColumn"]:
                heat_kw = q_watts / 1000.0
                # Fuel duty assuming 85% thermal efficiency
                gj_yr = (heat_kw * 3600.0 * operating_hours) / 1.0e6
                u_comb_co2 = gj_yr * fuel_factor_kg_gj
                combustion_co2_kg_yr += u_comb_co2
                unit_details.append({
                    "unit_id": u_id,
                    "unit_type": u_type,
                    "emission_type": "Fuel Combustion",
                    "duty_kW": round(heat_kw, 2),
                    "annual_gj": round(gj_yr, 2),
                    "annual_co2_tonnes": round(u_comb_co2 / 1000.0, 2)
                })

        # 2. Process vents: Streams with uncollected CO2 exiting boundary
        for s in streams_list:
            if not getattr(s, "downstream_units", []) and getattr(s, "F", 0):
                z_co2 = (getattr(s, "z", {}) or {}).get("co2", 0.0)
                if z_co2 > 0.001:
                    f_mol_s = s.F * z_co2
                    co2_kg_h = f_mol_s * 0.04401 * 3600.0  # 44.01 g/mol
                    annual_vent_kg = co2_kg_h * operating_hours
                    reaction_vent_co2_kg_yr += annual_vent_kg
                    unit_details.append({
                        "unit_id": getattr(s, "stream_id", "VentStream"),
                        "unit_type": "Process Vent",
                        "emission_type": "Direct Reaction/Vent CO2",
                        "duty_kW": 0.0,
                        "annual_gj": 0.0,
                        "annual_co2_tonnes": round(annual_vent_kg / 1000.0, 2)
                    })

        total_scope_1_kg = combustion_co2_kg_yr + reaction_vent_co2_kg_yr
        return {
            "combustion_co2_kg_yr": round(combustion_co2_kg_yr, 2),
            "reaction_vent_co2_kg_yr": round(reaction_vent_co2_kg_yr, 2),
            "total_scope_1_kg_yr": round(total_scope_1_kg, 2),
            "total_scope_1_tonnes_yr": round(total_scope_1_kg / 1000.0, 2),
            "unit_details": unit_details
        }

    @classmethod
    def calculate_scope_2_emissions(cls, utility_opex_dict: Dict[str, Any],
                                     grid_region: str = "US_Average",
                                     custom_grid_factor: Optional[float] = None,
                                     steam_source: str = "natural_gas_boiler") -> Dict[str, Any]:
        """
        Calculates Scope 2 indirect emissions from purchased electricity and steam utilities.
        """
        grid_factor = custom_grid_factor if custom_grid_factor is not None else REGIONAL_GRID_FACTORS.get(grid_region, 0.386)
        steam_factor = STEAM_FUEL_FACTORS.get(steam_source, 66.0)

        op_hours = utility_opex_dict.get("operating_hours_per_year", 8000.0)
        power_kw = utility_opex_dict.get("total_electricity_kW", 0.0)
        steam_kw = utility_opex_dict.get("total_heating_duty_kW", 0.0)
        cooling_kw = utility_opex_dict.get("total_cooling_duty_kW", 0.0)
        refrig_kw = utility_opex_dict.get("total_refrigeration_duty_kW", 0.0)

        # 1. Electricity emissions (kg CO2 = kWh * grid_factor)
        annual_kwh = power_kw * op_hours
        elec_co2_kg = annual_kwh * grid_factor

        # 2. Steam emissions (kg CO2 = GJ * steam_factor)
        annual_steam_gj = (steam_kw * 3600.0 * op_hours) / 1.0e6
        steam_co2_kg = annual_steam_gj * steam_factor

        # 3. Cooling water pump & fan emissions (0.5 kg CO2/GJ)
        annual_cooling_gj = (cooling_kw * 3600.0 * op_hours) / 1.0e6
        cooling_co2_kg = annual_cooling_gj * 0.50

        # 4. Chiller electrical refrigeration emissions (COP ~ 3.5 -> 0.285 kWh electric per kWh thermal)
        annual_refrig_kwh_elec = (refrig_kw / 3.5) * op_hours
        refrig_co2_kg = annual_refrig_kwh_elec * grid_factor

        total_scope_2_kg = elec_co2_kg + steam_co2_kg + cooling_co2_kg + refrig_co2_kg

        return {
            "electricity_co2_kg_yr": round(elec_co2_kg, 2),
            "steam_co2_kg_yr": round(steam_co2_kg, 2),
            "cooling_co2_kg_yr": round(cooling_co2_kg, 2),
            "refrigeration_co2_kg_yr": round(refrig_co2_kg, 2),
            "total_scope_2_kg_yr": round(total_scope_2_kg, 2),
            "total_scope_2_tonnes_yr": round(total_scope_2_kg / 1000.0, 2),
            "grid_factor_kg_per_kwh": round(grid_factor, 4),
            "steam_factor_kg_per_gj": round(steam_factor, 2)
        }

    @classmethod
    def calculate_scope_3_emissions(cls, streams_list: list, species_map: dict,
                                     operating_hours: float = 8000.0) -> Dict[str, Any]:
        """
        Calculates Scope 3 Category 1 (Purchased Goods and Services) cradle-to-gate
        embodied emissions of all raw material feedstocks entering flowsheet boundary.
        """
        total_scope_3_kg = 0.0
        feedstock_breakdown = []

        for st in streams_list:
            # Boundary feed streams: no upstream unit and active flow
            if getattr(st, "upstream_unit", None) is None and getattr(st, "F", 0) and st.F > 0:
                s_id = getattr(st, "stream_id", "Feed")
                # Calculate total mass flow rate in kg/h
                total_kg_h = 0.0
                for sp_id, mole_frac in (st.z or {}).items():
                    sp = species_map.get(sp_id)
                    mw = getattr(getattr(sp, "physical_constants", None), "molecular_weight", 0.050) if sp else 0.050
                    total_kg_h += st.F * mole_frac * mw * 3600.0

                annual_feed_mass_kg = total_kg_h * operating_hours

                # Component-level embodied emissions
                for sp_id, mole_frac in (st.z or {}).items():
                    if mole_frac > 0.01:
                        factor = FEEDSTOCK_EMBODIED_FACTORS.get(sp_id.lower(), FEEDSTOCK_EMBODIED_FACTORS["general"])
                        comp_annual_mass_kg = annual_feed_mass_kg * mole_frac
                        comp_co2_kg = comp_annual_mass_kg * factor
                        total_scope_3_kg += comp_co2_kg
                        feedstock_breakdown.append({
                            "stream_id": s_id,
                            "species_id": sp_id,
                            "mole_fraction": round(mole_frac, 3),
                            "annual_feed_mass_tonnes": round(comp_annual_mass_kg / 1000.0, 2),
                            "embodied_factor_kg_per_kg": factor,
                            "annual_co2_tonnes": round(comp_co2_kg / 1000.0, 2)
                        })

        return {
            "total_scope_3_kg_yr": round(total_scope_3_kg, 2),
            "total_scope_3_tonnes_yr": round(total_scope_3_kg / 1000.0, 2),
            "feedstock_breakdown": feedstock_breakdown
        }

    @classmethod
    def calculate_carbon_intensity(cls, scope_1_dict: Dict[str, Any],
                                   scope_2_dict: Dict[str, Any],
                                   scope_3_dict: Dict[str, Any],
                                   streams_list: list,
                                   species_map: dict,
                                   operating_hours: float = 8000.0,
                                   include_scope_3: bool = False) -> Dict[str, Any]:
        """
        Normalizes emissions per kilogram of primary product output.
        Complies with ISO 14040 / 14044 functional unit declarations.
        """
        s1_kg = scope_1_dict.get("total_scope_1_kg_yr", 0.0)
        s2_kg = scope_2_dict.get("total_scope_2_kg_yr", 0.0)
        s3_kg = scope_3_dict.get("total_scope_3_kg_yr", 0.0)

        # Gate-to-gate (Scope 1 + 2) vs Cradle-to-gate (Scope 1 + 2 + 3)
        total_eval_kg = (s1_kg + s2_kg + s3_kg) if include_scope_3 else (s1_kg + s2_kg)

        # Find primary product output mass (valuable non-water stream leaving boundary)
        primary_product_id = "MainProduct"
        primary_product_mass_kg_yr = 0.0

        for st in streams_list:
            if not getattr(st, "downstream_units", []) and getattr(st, "F", 0) and st.F > 0:
                s_mass_kg_h = 0.0
                for sp_id, frac in (st.z or {}).items():
                    if sp_id != "water" and frac > 0.10:
                        sp = species_map.get(sp_id)
                        mw = getattr(getattr(sp, "physical_constants", None), "molecular_weight", 0.050) if sp else 0.050
                        s_mass_kg_h += st.F * frac * mw * 3600.0
                        primary_product_id = sp_id

                if s_mass_kg_h > 0:
                    primary_product_mass_kg_yr += s_mass_kg_h * operating_hours

        if primary_product_mass_kg_yr <= 0:
            primary_product_mass_kg_yr = 1000000.0  # 1,000 tonnes default baseline

        carbon_intensity_kg_co2_per_kg_prod = total_eval_kg / primary_product_mass_kg_yr
        gate_to_gate_intensity = (s1_kg + s2_kg) / primary_product_mass_kg_yr

        tot_all_tonnes = (s1_kg + s2_kg + s3_kg) / 1000.0
        pct_s1 = (s1_kg / max(1.0, s1_kg + s2_kg + s3_kg)) * 100.0
        pct_s2 = (s2_kg / max(1.0, s1_kg + s2_kg + s3_kg)) * 100.0
        pct_s3 = (s3_kg / max(1.0, s1_kg + s2_kg + s3_kg)) * 100.0

        return {
            "total_ghg_emissions_tonnes_yr": round(total_eval_kg / 1000.0, 2),
            "total_cradle_to_gate_tonnes_yr": round(tot_all_tonnes, 2),
            "primary_product": primary_product_id,
            "annual_product_production_tonnes": round(primary_product_mass_kg_yr / 1000.0, 2),
            "carbon_intensity_kg_co2_per_kg_product": round(carbon_intensity_kg_co2_per_kg_prod, 3),
            "gate_to_gate_carbon_intensity": round(gate_to_gate_intensity, 3),
            "scope_1_pct": round(pct_s1, 1),
            "scope_2_pct": round(pct_s2, 1),
            "scope_3_pct": round(pct_s3, 1)
        }

    @classmethod
    def calculate_carbon_tax_impact(cls, lca_results: Dict[str, Any],
                                     profitability_dict: Dict[str, Any],
                                     carbon_tax_usd_per_tonne: float = 50.0,
                                     scope_policy: str = "Scope1_and_Scope2") -> Dict[str, Any]:
        """
        Evaluates the economic penalty of carbon pricing on plant profitability and discounted cash flow.
        """
        s1_t = lca_results.get("scope_1", {}).get("total_scope_1_tonnes_yr", 0.0)
        s2_t = lca_results.get("scope_2", {}).get("total_scope_2_tonnes_yr", 0.0)
        s3_t = lca_results.get("scope_3", {}).get("total_scope_3_tonnes_yr", 0.0)

        if scope_policy == "Scope1_only":
            taxed_tonnes = s1_t
        elif scope_policy == "Scope1_and_Scope2":
            taxed_tonnes = s1_t + s2_t
        else:
            taxed_tonnes = s1_t + s2_t + s3_t

        annual_carbon_tax_usd = taxed_tonnes * carbon_tax_usd_per_tonne

        base_gross_profit = profitability_dict.get("gross_profit_usd", 100000.0)
        base_deprec = profitability_dict.get("depreciation_annual_usd", 10000.0)
        base_npv = profitability_dict.get("net_present_value_NPV_usd", 500000.0)
        fci = profitability_dict.get("fixed_capital_investment_FCI", 1000000.0)
        lifetime = profitability_dict.get("project_lifetime_years", 15)
        disc_rate = profitability_dict.get("discount_rate_pct", 10.0) / 100.0

        # Adjust EBITDA and Net Profit
        adj_gross_profit = base_gross_profit - annual_carbon_tax_usd
        adj_ebit = adj_gross_profit - base_deprec
        adj_taxes = max(0.0, adj_ebit * 0.25)
        adj_net_profit = adj_ebit - adj_taxes
        adj_net_cash_flow = adj_gross_profit - adj_taxes

        # Recompute Payback and NPV
        adj_payback = round(fci / max(adj_net_cash_flow, 1.0), 2) if adj_net_cash_flow > 0 else 99.0
        adj_roi = round((adj_net_profit / max(fci, 1.0)) * 100.0, 2)

        # Annuity factor for discounted carbon tax impact over lifetime
        annuity_factor = (1.0 - (1.0 + disc_rate) ** (-lifetime)) / disc_rate
        tax_npv_penalty = (annual_carbon_tax_usd * (1.0 - 0.25)) * annuity_factor
        adj_npv = round(base_npv - tax_npv_penalty, 2)

        return {
            "carbon_tax_usd_per_tonne": carbon_tax_usd_per_tonne,
            "taxed_emissions_tonnes_yr": round(taxed_tonnes, 2),
            "annual_carbon_tax_usd": round(annual_carbon_tax_usd, 2),
            "base_net_present_value_usd": base_npv,
            "adjusted_net_present_value_usd": adj_npv,
            "npv_reduction_usd": round(base_npv - adj_npv, 2),
            "adjusted_net_profit_annual_usd": round(adj_net_profit, 2),
            "adjusted_payback_years": adj_payback,
            "adjusted_ROI_pct": adj_roi
        }

    @classmethod
    def evaluate_decarbonization_pathways(cls, units_list: list,
                                          utility_opex_dict: Dict[str, Any],
                                          lca_results: Dict[str, Any],
                                          grid_factor: float = 0.386,
                                          electricity_price_usd_kwh: float = 0.085,
                                          steam_price_usd_gj: float = 4.50,
                                          operating_hours: float = 8000.0) -> Dict[str, Any]:
        """
        Evaluates industrial electrification and decarbonization retrofits:
        1. Mechanical Vapor Recompression (MVR) for distillation column reboilers
        2. High-Temperature Industrial Heat Pump (HTHP) upgrading waste cooling heat
        3. Carbon Capture & Storage (CCUS) post-combustion amine scrubbing
        """
        tot_steam_kw = utility_opex_dict.get("total_heating_duty_kW", 100.0)
        base_s1_tonnes = lca_results.get("scope_1", {}).get("total_scope_1_tonnes_yr", 50.0)
        base_s2_tonnes = lca_results.get("scope_2", {}).get("total_scope_2_tonnes_yr", 50.0)
        base_tot_tonnes = base_s1_tonnes + base_s2_tonnes

        # -------------------------------------------------------------
        # Pathway 1: Mechanical Vapor Recompression (MVR)
        # -------------------------------------------------------------
        cop_mvr = 5.0  # Typical MVR COP
        mvr_power_kw = tot_steam_kw / cop_mvr
        mvr_elec_kwh = mvr_power_kw * operating_hours
        mvr_elec_cost_yr = mvr_elec_kwh * electricity_price_usd_kwh
        steam_saved_gj = (tot_steam_kw * 3600.0 * operating_hours) / 1.0e6
        steam_cost_saved_yr = steam_saved_gj * steam_price_usd_gj

        # MVR Capital Cost (Centrifugal Vapor Compressor)
        # Base Turton centrifugal compressor: ~ $650 per kW electric
        mvr_capex = 650.0 * (mvr_power_kw ** 0.82) if mvr_power_kw > 0 else 50000.0
        mvr_annualized_capex = mvr_capex / 10.0  # 10-year capital recovery

        # MVR Emissions Impact
        mvr_added_co2_tonnes = (mvr_elec_kwh * grid_factor) / 1000.0
        steam_co2_eliminated_tonnes = (steam_saved_gj * 66.0) / 1000.0
        mvr_net_co2_abated = max(0.0, steam_co2_eliminated_tonnes - mvr_added_co2_tonnes)

        mvr_delta_opex_yr = mvr_elec_cost_yr - steam_cost_saved_yr
        mvr_net_annual_cost = mvr_annualized_capex + mvr_delta_opex_yr
        mvr_mac = (mvr_net_annual_cost / max(0.1, mvr_net_co2_abated)) if mvr_net_co2_abated > 0 else 999.0

        # -------------------------------------------------------------
        # Pathway 2: Industrial High-Temperature Heat Pump (HTHP)
        # -------------------------------------------------------------
        cop_hp = 3.5
        hp_power_kw = (tot_steam_kw * 0.70) / cop_hp
        hp_elec_kwh = hp_power_kw * operating_hours
        hp_elec_cost_yr = hp_elec_kwh * electricity_price_usd_kwh
        hp_steam_saved_gj = ((tot_steam_kw * 0.70) * 3600.0 * operating_hours) / 1.0e6
        hp_steam_cost_saved_yr = hp_steam_saved_gj * steam_price_usd_gj

        # HTHP Package Cost (~ $800/kW thermal)
        hp_capex = 800.0 * ((tot_steam_kw * 0.70) ** 0.85) if tot_steam_kw > 0 else 60000.0
        hp_annualized_capex = hp_capex / 10.0

        hp_added_co2_tonnes = (hp_elec_kwh * grid_factor) / 1000.0
        hp_steam_co2_eliminated = (hp_steam_saved_gj * 66.0) / 1000.0
        hp_net_co2_abated = max(0.0, hp_steam_co2_eliminated - hp_added_co2_tonnes)

        hp_delta_opex_yr = hp_elec_cost_yr - hp_steam_cost_saved_yr
        hp_net_annual_cost = hp_annualized_capex + hp_delta_opex_yr
        hp_mac = (hp_net_annual_cost / max(0.1, hp_net_co2_abated)) if hp_net_co2_abated > 0 else 999.0

        # -------------------------------------------------------------
        # Pathway 3: Carbon Capture & Storage (CCUS Amine Scrubbing)
        # -------------------------------------------------------------
        capture_fraction = 0.90
        ccus_co2_abated = base_s1_tonnes * capture_fraction
        # CCUS Amine regeneration steam penalty: ~ 3.2 GJ steam per tonne CO2
        ccus_steam_gj = ccus_co2_abated * 3.2
        ccus_steam_cost = ccus_steam_gj * steam_price_usd_gj
        ccus_capex = 120.0 * max(100.0, ccus_co2_abated)  # ~$120/tonne-yr capacity
        ccus_annualized_capex = ccus_capex / 15.0
        ccus_opex_yr = ccus_steam_cost + (ccus_co2_abated * 15.0)  # chemical solvent makeup
        ccus_net_annual_cost = ccus_annualized_capex + ccus_opex_yr
        ccus_mac = (ccus_net_annual_cost / max(0.1, ccus_co2_abated)) if ccus_co2_abated > 0 else 999.0

        return {
            "baseline": {
                "name": "Fossil Baseline (Current Flowsheet)",
                "annual_emissions_tonnes": round(base_tot_tonnes, 2),
                "annual_utility_opex_usd": round(utility_opex_dict.get("total_annual_utility_opex_usd", 50000.0), 2),
                "marginal_abatement_cost_usd_per_tonne": 0.0
            },
            "mvr_electrification": {
                "name": "Mechanical Vapor Recompression (MVR)",
                "cop": cop_mvr,
                "power_demand_kW": round(mvr_power_kw, 2),
                "capex_investment_usd": round(mvr_capex, 2),
                "net_annual_cost_usd": round(mvr_net_annual_cost, 2),
                "co2_abated_tonnes_yr": round(mvr_net_co2_abated, 2),
                "post_retrofit_emissions_tonnes": round(max(0.0, base_tot_tonnes - mvr_net_co2_abated), 2),
                "marginal_abatement_cost_usd_per_tonne": round(mvr_mac, 2)
            },
            "heat_pump_electrification": {
                "name": "Industrial Heat Pump (HTHP)",
                "cop": cop_hp,
                "power_demand_kW": round(hp_power_kw, 2),
                "capex_investment_usd": round(hp_capex, 2),
                "net_annual_cost_usd": round(hp_net_annual_cost, 2),
                "co2_abated_tonnes_yr": round(hp_net_co2_abated, 2),
                "post_retrofit_emissions_tonnes": round(max(0.0, base_tot_tonnes - hp_net_co2_abated), 2),
                "marginal_abatement_cost_usd_per_tonne": round(hp_mac, 2)
            },
            "carbon_capture_ccus": {
                "name": "Post-Combustion CCUS Retrofit",
                "capture_rate_pct": 90.0,
                "capex_investment_usd": round(ccus_capex, 2),
                "net_annual_cost_usd": round(ccus_net_annual_cost, 2),
                "co2_abated_tonnes_yr": round(ccus_co2_abated, 2),
                "post_retrofit_emissions_tonnes": round(max(0.0, base_tot_tonnes - ccus_co2_abated), 2),
                "marginal_abatement_cost_usd_per_tonne": round(ccus_mac, 2)
            }
        }
