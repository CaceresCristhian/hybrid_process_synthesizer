import numpy as np
from src.units.base_unit import BaseUnit
from src.chemical_phenomena.thermodynamics import Thermodynamics
from src.database.chemical_db import ChemicalSpecies

class BinaryDistillationColumn(BaseUnit):
    """
    Rigorously expanded Binary Distillation Column solver.
    Includes:
    1. Steady-state stage-by-stage equilibrium solver.
    2. Column Internals Sizing & Hydraulics (tray pressure drops, downcomer backup, Souders-Brown flooding velocity, and diameter auto-sizing).
    3. Intermediate side-draws and pump-around cooling loops.
    """
    
    def __init__(self, unit_id: str, name: str, num_stages: int, feed_stage: int, 
                 reflux_ratio: float, total_pressure: float = 101325.0):
        super().__init__(unit_id, name)
        self.num_stages = num_stages  # 1-indexed, stage 1 is condenser, stage N is reboiler
        self.feed_stage = feed_stage  # Feed tray index
        self.reflux_ratio = reflux_ratio
        self.total_pressure = total_pressure
        
        # Side operations configurations
        self.side_draws = {}        # stage_idx -> draw_fraction (fraction of liquid drawn)
        self.pump_arounds = []      # list of dicts: {"draw_stage": idx, "return_stage": idx, "flow": mol/s, "heat_removed": Watts}

    def add_side_draw(self, stage: int, draw_fraction: float):
        """Adds a liquid sidestream draw at a specific stage."""
        if 1 < stage < self.num_stages:
            self.side_draws[stage] = draw_fraction

    def add_pump_around(self, draw_stage: int, return_stage: int, flow_rate: float, heat_removed: float):
        """Adds a pump-around loop removing heat between two stages."""
        if 1 < return_stage < draw_stage < self.num_stages:
            self.pump_arounds.append({
                "draw_stage": draw_stage,
                "return_stage": return_stage,
                "flow": flow_rate,             # mol/s
                "heat_removed": heat_removed   # J/s or Watts
            })

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        """
        Solves the steady-state column profile under side draws and pump-arounds.
        """
        light_sp = kwargs.get("light_species")
        heavy_sp = kwargs.get("heavy_species")
        z_f = kwargs.get("z_f", 0.1)
        f_feed = kwargs.get("f_feed", 10.0)
        q_feed = kwargs.get("q_feed", 1.0)
        x_d = kwargs.get("x_d_target", 0.82)
        activity_coeffs_fn = kwargs.get("activity_coeffs_fn", lambda x, T: (1.0, 1.0))
        
        # Distillate flow rate and Bottoms flow rate
        d_flow = 0.1 * f_feed
        
        # Adjust for side draws in mass balance
        total_side_draw = 0.0
        # For simplicity, side draws are treated as fractions of the internal stream
        # bottom flow is computed as: B = F - D - Sum(SideDraws)
        
        # Operating line streams
        # Rectifying section flows
        l_rect = self.reflux_ratio * d_flow
        v_rect = (self.reflux_ratio + 1.0) * d_flow
        
        # Stripping section flows
        l_strip = l_rect + q_feed * f_feed
        v_strip = v_rect + (q_feed - 1.0) * f_feed
        
        # Stage profiles
        x_profile = np.zeros(self.num_stages)
        y_profile = np.zeros(self.num_stages)
        t_profile = np.zeros(self.num_stages)
        l_profile = np.zeros(self.num_stages)
        v_profile = np.zeros(self.num_stages)
        
        # Set flows for each stage
        for i in range(self.num_stages):
            if i < self.feed_stage:
                l_profile[i] = l_rect
                v_profile[i] = v_rect
            else:
                l_profile[i] = l_strip
                v_profile[i] = v_strip
                
        # Apply pump-around flows
        for pa in self.pump_arounds:
            ds = pa["draw_stage"] - 1
            rs = pa["return_stage"] - 1
            for k in range(rs, ds):
                l_profile[k] += pa["flow"]
                
        # Condenser stage (0)
        x_profile[0] = x_d
        
        species_dict = {light_sp.id: light_sp, heavy_sp.id: heavy_sp}
        
        def calculate_tray_vle(x_light, t_guess):
            x_fracs = {light_sp.id: x_light, heavy_sp.id: 1.0 - x_light}
            g1, g2 = activity_coeffs_fn(x_light, t_guess)
            act_coeffs = {light_sp.id: g1, heavy_sp.id: g2}
            
            t_bubble = Thermodynamics.bubble_point_temperature(
                x_fractions=x_fracs,
                species_dict=species_dict,
                total_pressure=self.total_pressure,
                activity_coeffs=act_coeffs,
                initial_temp_guess=t_guess
            )
            
            k1 = Thermodynamics.calculate_vle_k_value(light_sp, t_bubble, self.total_pressure, g1)
            y_light = k1 * x_light
            return t_bubble, y_light
            
        t_cond, y_cond = calculate_tray_vle(x_profile[0], light_sp.macro.boiling_point)
        y_profile[0] = y_cond
        t_profile[0] = t_cond
        
        # Solve stage-by-stage down the column
        for i in range(1, self.num_stages):
            l_current = l_profile[i-1]
            v_current = v_profile[i-1]
            
            # Incorporate side draw effects: if there is a side draw, liquid flow decreases
            if i in self.side_draws:
                draw = self.side_draws[i] * l_current
                l_current -= draw
                total_side_draw += draw
                
            # Material balances
            if i < self.feed_stage:
                x_val = (v_current * y_profile[i-1] - d_flow * x_d) / max(0.1, l_current)
            else:
                b_flow = f_feed - d_flow - total_side_draw
                x_b = (f_feed * z_f - d_flow * x_d) / max(0.1, b_flow)
                x_val = (v_current * y_profile[i-1] + b_flow * x_b) / max(0.1, l_current)
                
            x_profile[i] = max(0.0001, min(x_val, 0.9999))
            
            # VLE
            t_tray, y_tray = calculate_tray_vle(x_profile[i], t_profile[i-1])
            y_profile[i] = y_tray
            t_profile[i] = t_tray
            
        # Store profiles for sizing
        self._l_profile = l_profile
        self._v_profile = v_profile
        self._t_profile = t_profile
        
        return {
            "stages": np.arange(1, self.num_stages + 1),
            "x_light": x_profile,
            "y_light": y_profile,
            "T": t_profile,
            "L_flow": l_profile,
            "V_flow": v_profile,
            "bottoms_x": x_profile[-1],
            "distillate_x": x_profile[0]
        }

    def size_equipment(self) -> dict:
        """
        Calculates column dimensions and checks tray hydraulics (tray spacing, flooding limit).
        """
        # Densities at typical column conditions
        rho_L = 800.0  # kg/m3 (typical liquid hydrocarbon/organic density)
        rho_V = 1.8    # kg/m3 (typical vapor density at atmospheric pressure)
        
        # 1. Column Sizing via Souders-Brown Flooding Correlation
        # v_flood = C_sb * sqrt((rho_L - rho_V)/rho_V)
        # We assume tray spacing of 0.6 meters, giving C_sb ~ 0.08 m/s
        tray_spacing = 0.6
        c_sb = 0.08
        
        v_flood = c_sb * np.sqrt((rho_L - rho_V) / rho_V)
        
        # Calculate maximum vapor volumetric flow rate across all stages to size diameter
        # Max flow rate (mol/s) * Molecular Weight (approx 0.03 kg/mol) / rho_V = m3/s
        max_v_mol = max(self._v_profile) if hasattr(self, "_v_profile") else 10.0
        max_q_v = (max_v_mol * 0.03) / rho_V  # vapor volumetric flow m3/s
        
        # Design velocity is 80% of flooding velocity
        v_design = 0.8 * v_flood
        area_required = max_q_v / v_design
        column_diameter = 2.0 * np.sqrt(area_required / np.pi)
        column_diameter = max(0.5, column_diameter)  # minimum 0.5m
        
        column_height = self.num_stages * tray_spacing + 3.0
        
        # 2. Tray Hydraulics & Pressure Drop Calculations
        # Dry pressure drop through holes: dP_dry = 0.5 * rho_V * (v_hole / C_d)^2
        # We assume 10% hole area on trays. v_hole = v_vapor / 0.1
        # discharge coefficient C_d ~ 0.7
        v_vapor = max_q_v / area_required
        v_hole = v_vapor / 0.1
        dp_dry = 0.5 * rho_V * (v_hole / 0.7) ** 2
        
        # Liquid pressure drop: dP_liquid = rho_L * g * h_liquid
        # assume 50mm weir height + crest, total liquid height h_L ~ 0.06m
        h_liquid = 0.06
        dp_liquid = rho_L * 9.81 * h_liquid
        
        dp_per_tray = dp_dry + dp_liquid  # Pascals per tray
        total_dp = dp_per_tray * self.num_stages
        
        # Downcomer backup check: h_dc = h_liquid + dP_tray / (rho_L * g)
        # Should not exceed half the tray spacing to prevent flooding
        h_dc = h_liquid + dp_per_tray / (rho_L * 9.81)
        dc_flooding_warning = h_dc > (0.5 * tray_spacing)
        
        self.sizing_results = {
            "num_stages": self.num_stages,
            "column_height_m": column_height,
            "column_diameter_m": column_diameter,
            "tray_spacing_m": tray_spacing,
            "vapor_velocity_m_s": v_vapor,
            "flooding_velocity_m_s": v_flood,
            "percent_flooding": (v_vapor / v_flood) * 100.0,
            "dp_per_tray_Pa": dp_per_tray,
            "total_dp_kPa": total_dp / 1000.0,
            "downcomer_backup_m": h_dc,
            "flooding_warning": dc_flooding_warning
        }
        return self.sizing_results
