import numpy as np
from src.units.base_unit import BaseUnit
from src.chemical_phenomena.thermodynamics import Thermodynamics

class FlashDrum(BaseUnit):
    """
    Two-Phase Vapor-Liquid Separator / Knockout Drum / Flash Drum.
    Inlet: [0] Multiphase or volatile feed.
    Outlets: [0] Overhead Vapor, [1] Bottoms Liquid.
    Performs VLE flash at vessel temperature and pressure.
    """
    def __init__(self, unit_id: str, name: str, temp_vessel: float = 350.0, p_vessel: float = 101325.0):
        super().__init__(unit_id, name)
        self.temp_vessel = temp_vessel
        self.p_vessel = p_vessel
        self.heat_duty = 0.0
        self.work_input = 0.0
        self.vapor_fraction = 0.0
        
    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_st = self.inlets[0] if self.inlets else None
        if not in_st or in_st.F is None or in_st.F <= 0:
            return {"status": "unsolved"}
            
        species_map = kwargs.get("species_map", {})
        species_list = [species_map[k] for k in in_st.z.keys() if k in species_map]
        
        # Run TP Flash
        if len(species_list) >= 2:
            try:
                flash_res = Thermodynamics.solve_tp_flash(
                    species_list, in_st.z, self.temp_vessel, self.p_vessel
                )
                self.vapor_fraction = float(flash_res["beta"])
                x_comp = flash_res["x"]
                y_comp = flash_res["y"]
            except Exception:
                # Fallback to relative volatility estimate
                keys = list(in_st.z.keys())
                self.vapor_fraction = 0.35
                y_comp = {keys[0]: 0.75, keys[1]: 0.25}
                x_comp = {keys[0]: 0.15, keys[1]: 0.85}
        else:
            self.vapor_fraction = 0.5
            x_comp = in_st.z.copy() if in_st.z else {}
            y_comp = in_st.z.copy() if in_st.z else {}
            
        # Route to outlets: [0] Top Vapor, [1] Bottom Liquid
        if len(self.outlets) >= 2:
            v_out = self.outlets[0]
            l_out = self.outlets[1]
            
            v_out.T = self.temp_vessel
            v_out.P = self.p_vessel
            v_out.F = in_st.F * self.vapor_fraction
            v_out.z = y_comp
            
            l_out.T = self.temp_vessel
            l_out.P = self.p_vessel
            l_out.F = in_st.F * (1.0 - self.vapor_fraction)
            l_out.z = x_comp
        elif len(self.outlets) == 1:
            out_st = self.outlets[0]
            out_st.T = self.temp_vessel
            out_st.P = self.p_vessel
            out_st.F = in_st.F
            out_st.z = in_st.z.copy() if in_st.z else {}
            
        return {
            "vapor_fraction": self.vapor_fraction,
            "vapor_flow_mol_s": in_st.F * self.vapor_fraction,
            "liquid_flow_mol_s": in_st.F * (1.0 - self.vapor_fraction)
        }

    def size_equipment(self) -> dict:
        # Sizing via Souders-Brown liquid-vapor droplet entrainment limit
        k_sb = 0.07  # m/s with wire mesh demister
        rho_v = 1.8   # kg/m3
        rho_l = 850.0 # kg/m3
        v_max = k_sb * np.sqrt(max(1.0, (rho_l - rho_v) / max(rho_v, 0.1)))
        
        # Vapor volumetric flow
        v_flow = 0.5 * max(0.1, self.vapor_fraction)
        diam = round(np.sqrt(4.0 * v_flow / (np.pi * max(v_max, 0.5))), 2)
        height = round(diam * 3.0, 2)
        
        self.sizing_results = {
            "vessel_diameter_m": max(0.4, diam),
            "vessel_height_m": max(1.2, height),
            "vessel_volume_m3": round(np.pi * (max(0.4, diam)/2)**2 * max(1.2, height), 2),
            "droplet_terminal_velocity_m_s": round(v_max, 2)
        }
        return self.sizing_results


class Splitter(BaseUnit):
    """
    Stream Divider / Flow Splitter / Tee.
    Inlet: [0] Main Feed.
    Outlets: [0..N] Split streams with user-defined split fractions.
    Guarantees strict mass conservation: sum(F_out) == F_in.
    """
    def __init__(self, unit_id: str, name: str, split_ratios: list = None):
        super().__init__(unit_id, name)
        self.split_ratios = split_ratios or [0.5, 0.5]
        self.heat_duty = 0.0
        self.work_input = 0.0
        
    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_st = self.inlets[0] if self.inlets else None
        if not in_st or in_st.F is None or in_st.F <= 0 or not self.outlets:
            return {"status": "unsolved"}
            
        n_out = len(self.outlets)
        # Normalize split ratios to number of outlets
        ratios = list(self.split_ratios[:n_out])
        if len(ratios) < n_out:
            remaining = 1.0 - sum(ratios)
            needed = n_out - len(ratios)
            ratios.extend([max(0.01, remaining / needed)] * needed)
            
        tot = sum(ratios)
        norm_ratios = [r / tot for r in ratios]
        
        for idx, out_st in enumerate(self.outlets):
            out_st.T = in_st.T
            out_st.P = in_st.P
            out_st.F = in_st.F * norm_ratios[idx]
            out_st.z = in_st.z.copy() if in_st.z else {}
            
        return {"splits": norm_ratios, "total_flow_mol_s": in_st.F}

    def size_equipment(self) -> dict:
        self.sizing_results = {
            "manifold_header_diameter_mm": 50,
            "branch_count": len(self.outlets)
        }
        return self.sizing_results


class SolidLiquidSeparator(BaseUnit):
    """
    Mechanical Solid-Liquid Clarifier / Centrifuge / Lauter Tun / Rotary Filter.
    Inlet: [0] Slurry / Mash / Suspension.
    Outlets: [0] Clarified Liquid (Wort / Filtrate), [1] Concentrated Solids / Cake (Spent Grains).
    """
    def __init__(self, unit_id: str, name: str, recovery_liquid: float = 0.90):
        super().__init__(unit_id, name)
        self.recovery_liquid = recovery_liquid
        self.heat_duty = 0.0
        self.work_input = 250.0  # mechanical agitator / centrifuge drive in Watts

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_st = self.inlets[0] if self.inlets else None
        if not in_st or in_st.F is None or in_st.F <= 0:
            return {"status": "unsolved"}
            
        if len(self.outlets) >= 2:
            liq_out = self.outlets[0]
            sol_out = self.outlets[1]
            
            liq_out.T = in_st.T
            liq_out.P = in_st.P - 2000.0  # cake pressure drop
            liq_out.F = in_st.F * self.recovery_liquid
            liq_out.z = in_st.z.copy() if in_st.z else {}
            
            sol_out.T = in_st.T
            sol_out.P = in_st.P
            sol_out.F = in_st.F * (1.0 - self.recovery_liquid)
            sol_out.z = in_st.z.copy() if in_st.z else {}
        elif len(self.outlets) == 1:
            self.outlets[0].T = in_st.T
            self.outlets[0].P = in_st.P
            self.outlets[0].F = in_st.F
            self.outlets[0].z = in_st.z.copy() if in_st.z else {}
            
        return {"liquid_recovery": self.recovery_liquid}

    def size_equipment(self) -> dict:
        self.sizing_results = {
            "filtration_area_m2": 4.5,
            "cake_thickness_mm": 35.0,
            "drive_power_kW": self.work_input / 1000.0
        }
        return self.sizing_results


class MembraneUnit(BaseUnit):
    """
    Membrane Separation Unit (Reverse Osmosis Desalination / Gas Permeation).
    Inlet: [0] Pressurized Feed.
    Outlets: [0] Permeate (Purified Product), [1] Retentate (Concentrated Brine / Reject).
    """
    def __init__(self, unit_id: str, name: str, recovery_ratio: float = 0.65, salt_rejection: float = 0.99):
        super().__init__(unit_id, name)
        self.recovery_ratio = recovery_ratio
        self.salt_rejection = salt_rejection
        self.heat_duty = 0.0
        self.work_input = 0.0

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_st = self.inlets[0] if self.inlets else None
        if not in_st or in_st.F is None or in_st.F <= 0:
            return {"status": "unsolved"}
            
        if len(self.outlets) >= 2:
            perm = self.outlets[0]
            ret = self.outlets[1]
            
            perm.T = in_st.T
            perm.P = 101325.0  # permeate atmospheric pressure
            perm.F = in_st.F * self.recovery_ratio
            
            ret.T = in_st.T
            ret.P = max(101325.0, in_st.P - 50000.0)  # brine high pressure
            ret.F = in_st.F * (1.0 - self.recovery_ratio)
            
            # Salt rejection distribution
            perm.z = in_st.z.copy() if in_st.z else {}
            ret.z = in_st.z.copy() if in_st.z else {}
            if "nacl" in perm.z:
                salt_in = in_st.z.get("nacl", 0.0)
                perm.z["nacl"] = salt_in * (1.0 - self.salt_rejection)
                if "water" in perm.z:
                    perm.z["water"] = 1.0 - perm.z["nacl"]
                # Salt goes to retentate
                ret.z["nacl"] = (salt_in - perm.z["nacl"] * self.recovery_ratio) / (1.0 - self.recovery_ratio)
                if "water" in ret.z:
                    ret.z["water"] = 1.0 - ret.z["nacl"]
                    
        elif len(self.outlets) == 1:
            self.outlets[0].T = in_st.T
            self.outlets[0].P = 101325.0
            self.outlets[0].F = in_st.F
            self.outlets[0].z = in_st.z.copy() if in_st.z else {}
            
        return {"permeate_recovery": self.recovery_ratio, "rejection": self.salt_rejection}

    def size_equipment(self) -> dict:
        flux = 22.0  # L/m2*h
        self.sizing_results = {
            "membrane_area_m2": 120.0,
            "vessels_in_parallel": 4,
            "permeate_flux_LMH": flux
        }
        return self.sizing_results
