"""
Solids Processing Unit Operations:
1. Continuous MSMPR Crystallizer with Population Balance Modeling (PBM)
2. Industrial Convective Spray Dryer with Psychrometric Gas Balances
"""

import numpy as np
from typing import Dict, List, Any, Optional
from src.units.base_unit import BaseUnit


class ContinuousCrystallizer(BaseUnit):
    """
    Continuous Mixed-Suspension Mixed-Product Removal (MSMPR) Crystallizer.
    Inlet: [0] Solution / Saturated Feed.
    Outlets: [0] Mother Liquor Overflow, [1] Crystal Product Slurry.
    Solves steady-state Population Balance Modeling (PBM):
        n(L) = n0 * exp(-L / (G * tau))
    Moments: m_j = j! * n0 * (G * tau)^(j+1)
    Magma density: M_T = rho_c * k_v * m_3
    """
    def __init__(self, unit_id: str, name: str,
                 cryst_volume_m3: float = 8.0,
                 temp_cryst_k: float = 298.15,
                 crystal_density_kg_m3: float = 1500.0,
                 growth_k: float = 0.05,        # um / s
                 nucleation_k: float = 2.0e6,   # # / (m3 s)
                 volumetric_shape_kv: float = 0.5236): # pi / 6 for spheres/cubes
        super().__init__(unit_id, name)
        self.cryst_volume_m3 = cryst_volume_m3
        self.temp_cryst_k = temp_cryst_k
        self.crystal_density_kg_m3 = crystal_density_kg_m3
        self.growth_k = growth_k
        self.nucleation_k = nucleation_k
        self.volumetric_shape_kv = volumetric_shape_kv

        self.heat_duty = 0.0
        self.work_input = 2500.0  # Agitator motor in Watts
        self.pbm_results: Dict[str, Any] = {}

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_st = self.inlets[0] if self.inlets else None
        if not in_st or in_st.F is None or in_st.F <= 0:
            return {"status": "unsolved"}

        # Solution volumetric flow Q_slurry (m3/s)
        mw = getattr(in_st, "MW", 0.080)
        m_dot_kg_s = (in_st.F * mw) if in_st.F else 5.0
        q_slurry_m3_s = max(0.0005, m_dot_kg_s / 1100.0)

        # Mean residence time tau (seconds)
        tau = self.cryst_volume_m3 / q_slurry_m3_s

        # Crystallization growth & nucleation kinetics
        g_growth = self.growth_k     # um / s
        b0_nucl = self.nucleation_k  # # / (m3 s)
        n0 = b0_nucl / max(1e-6, g_growth) # # / (um m3)

        # Characteristic size parameter (G * tau) in um
        gt_um = g_growth * tau
        gt_m = gt_um * 1e-6  # meters

        # Moment Equations: m_j = j! * n0 * (G*tau)^(j+1)
        m0 = n0 * gt_um
        m1 = n0 * (gt_um ** 2)
        m2 = 2.0 * n0 * (gt_um ** 3)
        m3_um = 6.0 * n0 * (gt_um ** 4)
        m4_um = 24.0 * n0 * (gt_um ** 5)

        # Magma Suspension Density M_T (kg crystal / m3 slurry)
        n0_si = n0 * 1e6  # per meter^3 per meter
        m3_si = 6.0 * n0_si * (gt_m ** 4)
        magma_density_kg_m3 = self.crystal_density_kg_m3 * self.volumetric_shape_kv * m3_si

        # Crystal Production Rate (kg/s and kg/h)
        solids_rate_kg_s = q_slurry_m3_s * magma_density_kg_m3
        solids_rate_kg_h = solids_rate_kg_s * 3600.0

        # Mean and Median Crystal Sizes
        l10_um = gt_um          # Number-weighted mean size
        l43_um = 4.0 * gt_um    # Mass/volume-weighted mean size
        l50_um = 3.67 * gt_um   # Median size (50% cumulative mass)
        cv_pct = 100.0          # Theoretical MSMPR coefficient of variation

        # Discrete Particle Size Distribution (PSD) Histogram
        l_bins = np.linspace(10.0, 1200.0, 25)
        # Volume-weighted frequency distribution: q3(L) = L^3 * n(L) / m3
        psd_density = [float((L ** 3) * n0 * np.exp(-L / max(1e-3, gt_um)) / max(1e-6, m3_um)) for L in l_bins]

        # Cooling Heat Duty: sensible heat + heat of crystallization (approx 120 kJ/kg)
        delta_t = max(0.0, (in_st.T or 340.0) - self.temp_cryst_k)
        q_cool_w = m_dot_kg_s * 3800.0 * delta_t + solids_rate_kg_s * 120000.0
        self.heat_duty = -q_cool_w  # Cooling

        # Route to outlets
        if len(self.outlets) >= 2:
            overflow_st = self.outlets[0]
            slurry_st = self.outlets[1]

            overflow_st.T = self.temp_cryst_k
            overflow_st.P = in_st.P
            overflow_st.F = in_st.F * 0.70
            overflow_st.z = in_st.z.copy() if in_st.z else {}

            slurry_st.T = self.temp_cryst_k
            slurry_st.P = in_st.P
            slurry_st.F = in_st.F * 0.30
            slurry_st.z = in_st.z.copy() if in_st.z else {}

        self.pbm_results = {
            "residence_time_min": round(tau / 60.0, 1),
            "residence_time_s": round(tau, 1),
            "growth_rate_um_s": g_growth,
            "nucleation_rate_no_m3_s": b0_nucl,
            "magma_density_kg_m3": round(magma_density_kg_m3, 2),
            "solids_production_kg_h": round(solids_rate_kg_h, 1),
            "L_10_um": round(l10_um, 1),
            "L_43_um": round(l43_um, 1),
            "L_50_um": round(l50_um, 1),
            "CV_pct": cv_pct,
            "cooling_duty_kW": round(abs(self.heat_duty) / 1000.0, 2),
            "psd_size_bins_um": [round(float(L), 1) for L in l_bins],
            "psd_volume_density": [round(float(v), 5) for v in psd_density]
        }

        return self.pbm_results

    def size_equipment(self) -> dict:
        # Sizing cylindrical vessel with 60 degree conical bottom
        vol = max(1.0, self.cryst_volume_m3)
        diam = round((4.0 * vol / (2.5 * np.pi)) ** (1.0 / 3.0), 2)
        height = round(diam * 2.5, 2)

        self.sizing_results = {
            "vessel_diameter_m": diam,
            "vessel_height_m": height,
            "vessel_volume_m3": vol,
            "agitator_power_kW": self.work_input / 1000.0,
            "heat_transfer_area_m2": round(np.pi * diam * height * 0.8, 1)
        }
        return self.sizing_results


class SprayDryer(BaseUnit):
    """
    Industrial Convective Spray Dryer.
    Inlets: [0] Wet Slurry/Liquid Feed, [1] Hot Drying Gas In.
    Outlets: [0] Exhaust Moist Air, [1] Dry Powder Product.
    Solves psychrometric drying gas balance, water evaporation rate,
    thermal drying efficiency, and cyclone powder recovery.
    """
    def __init__(self, unit_id: str, name: str,
                 inlet_gas_temp_c: float = 190.0,
                 outlet_target_moisture_pct: float = 4.0,
                 cyclone_efficiency_pct: float = 98.5):
        super().__init__(unit_id, name)
        self.inlet_gas_temp_c = inlet_gas_temp_c
        self.outlet_target_moisture_pct = outlet_target_moisture_pct
        self.cyclone_efficiency_pct = cyclone_efficiency_pct

        self.heat_duty = 0.0  # Gas burner / steam heater duty
        self.work_input = 4500.0  # Atomizer drive + exhaust blower in Watts
        self.dryer_results: Dict[str, Any] = {}

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        feed_st = self.inlets[0] if self.inlets else None
        if not feed_st or feed_st.F is None or feed_st.F <= 0:
            return {"status": "unsolved"}

        mw = getattr(feed_st, "MW", 0.060)
        m_feed_kg_h = (feed_st.F * mw * 3600.0) if feed_st.F else 1500.0

        # Feed moisture assumption (typically 55-65% water for pumpable slurry)
        w_in = 0.60
        w_out = self.outlet_target_moisture_pct / 100.0

        # Dry solid flow rate
        m_ds_kg_h = m_feed_kg_h * (1.0 - w_in)
        # Water evaporation rate
        m_evap_kg_h = m_feed_kg_h * w_in - m_ds_kg_h * (w_out / (1.0 - w_out))
        # Total dry powder product
        m_powder_kg_h = m_ds_kg_h / (1.0 - w_out)
        # Recovered powder via cyclone collector
        m_recovered_powder = m_powder_kg_h * (self.cyclone_efficiency_pct / 100.0)

        # Psychrometrics: Hot drying gas
        t_in_c = self.inlet_gas_temp_c
        t_out_c = max(75.0, 0.40 * t_in_c + 15.0)  # Standard empirical adiabatic spray dryer drop
        t_ambient_c = 20.0

        # Heat required to evaporate moisture and heat air (Cp_air ~ 1.005 kJ/kg K, dH_vap ~ 2400 kJ/kg)
        q_evap_kw = (m_evap_kg_h / 3600.0) * 2400.0
        air_delta_t = t_in_c - t_out_c
        m_air_kg_h = (q_evap_kw * 3600.0) / (1.005 * max(10.0, air_delta_t))

        # Total burner heating duty from ambient (20 C to T_in)
        q_heat_kw = (m_air_kg_h / 3600.0) * 1.005 * (t_in_c - t_ambient_c)
        self.heat_duty = q_heat_kw * 1000.0  # Watts

        # Thermal drying efficiency eta = (T_in - T_out) / (T_in - T_amb)
        thermal_eff_pct = (air_delta_t / (t_in_c - t_ambient_c)) * 100.0

        # Absolute humidity increase
        y_ambient = 0.010  # kg water / kg dry air
        y_exhaust = y_ambient + (m_evap_kg_h / max(1.0, m_air_kg_h))

        # Route to outlets
        if len(self.outlets) >= 2:
            exhaust_st = self.outlets[0]
            powder_st = self.outlets[1]

            exhaust_st.T = t_out_c + 273.15
            exhaust_st.P = 101325.0
            exhaust_st.F = (m_air_kg_h / (28.97 * 3.6))  # mol/s air

            powder_st.T = t_out_c + 273.15 - 10.0
            powder_st.P = 101325.0
            powder_st.F = (m_recovered_powder / (mw * 3.6))

        self.dryer_results = {
            "feed_rate_kg_h": round(m_feed_kg_h, 1),
            "water_evaporated_kg_h": round(m_evap_kg_h, 1),
            "powder_produced_kg_h": round(m_recovered_powder, 1),
            "drying_air_flow_kg_h": round(m_air_kg_h, 0),
            "inlet_air_temp_C": t_in_c,
            "outlet_air_temp_C": round(t_out_c, 1),
            "thermal_efficiency_pct": round(thermal_eff_pct, 1),
            "burner_heat_duty_kW": round(q_heat_kw, 1),
            "exhaust_humidity_kg_kg": round(y_exhaust, 4),
            "cyclone_recovery_pct": self.cyclone_efficiency_pct
        }

        return self.dryer_results

    def size_equipment(self) -> dict:
        # Sizing spray chamber based on drying air volumetric flow
        vol_flow_m3_s = (self.dryer_results.get("drying_air_flow_kg_h", 4000.0) / 3600.0) / 0.85
        tau_res = 20.0  # seconds droplet residence time
        vol_chamber = max(5.0, vol_flow_m3_s * tau_res)
        diam = round((4.0 * vol_chamber / (2.5 * np.pi)) ** (1.0 / 3.0), 2)
        height = round(diam * 2.5, 2)

        self.sizing_results = {
            "chamber_diameter_m": diam,
            "chamber_height_m": height,
            "chamber_volume_m3": round(vol_chamber, 1),
            "blower_power_kW": self.work_input / 1000.0,
            "cyclone_diameter_m": round(diam * 0.45, 2)
        }
        return self.sizing_results
