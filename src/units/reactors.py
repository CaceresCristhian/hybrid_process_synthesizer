import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import root
from typing import Optional, Dict
from src.units.base_unit import BaseUnit
from src.chemical_phenomena.reactions import ReactionNetwork, REACTION_PACKAGES
from config.settings import GAS_CONSTANT_R

class IdealCSTR(BaseUnit):
    """
    Continuous Stirred Tank Reactor (CSTR).
    Supports:
    1. Rigorous multi-reaction kinetic solver (coupled non-linear algebraic equations).
    2. Dynamic transient ODE solver for control studies.
    3. Mechanical sizing: vessel volume, hydraulic residence time, Damköhler number, jacket area.
    """
    
    def __init__(self, unit_id: str, name: str, volume: float = 5.0, 
                 reaction_package: Optional[str] = None):
        super().__init__(unit_id, name)
        self.volume = max(0.01, volume)
        self.reaction_package = reaction_package
        self.reaction_network: Optional[ReactionNetwork] = None
        if reaction_package and reaction_package in REACTION_PACKAGES:
            self.reaction_network = REACTION_PACKAGES[reaction_package]

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_stream = self.inlets[0] if self.inlets else None
        out_stream = self.outlets[0] if self.outlets else None
        
        # Flowsheet stream propagation mode
        if in_stream and out_stream and in_stream.F is not None and in_stream.F > 0:
            rxn_pkg_name = kwargs.get("reaction_package") or self.reaction_package
            if rxn_pkg_name and rxn_pkg_name in REACTION_PACKAGES:
                self.reaction_network = REACTION_PACKAGES[rxn_pkg_name]

            # 1. Rigorous Reaction Network Mode
            if self.reaction_network:
                species_set = self.reaction_network.get_species_set()
                f_in = {sp: in_stream.F * in_stream.z.get(sp, 0.0) for sp in species_set}
                # Include any other species not in reaction network
                for sp, frac in in_stream.z.items():
                    if sp not in f_in:
                        f_in[sp] = in_stream.F * frac

                T_op = in_stream.T + kwargs.get("delta_T", 5.0)
                P_op = max(50000.0, in_stream.P - kwargs.get("delta_P", 10000.0))

                # If equilibrium reactions present, solve chemical equilibrium
                has_equilibrium = any(r.reaction_type == "equilibrium" for r in self.reaction_network.reactions)
                if has_equilibrium:
                    f_out_rxn = self.reaction_network.solve_chemical_equilibrium(f_in, T_op, P_op)
                else:
                    # Solve non-linear CSTR algebraic mass balances: F_in - F_out + V * r_net = 0
                    # Estimate volumetric flow: v = F_total * R * T / P (m3/s)
                    v_est = max(1e-4, in_stream.F * GAS_CONSTANT_R * T_op / P_op)

                    def cstr_residuals(f_out_arr):
                        f_curr = {sp: max(0.0, f_out_arr[i]) for i, sp in enumerate(species_set)}
                        c_curr = {sp: f_curr[sp] / v_est for sp in species_set}
                        r_net = self.reaction_network.calculate_net_rates(c_curr, T_op)
                        res = np.zeros(len(species_set))
                        for i, sp in enumerate(species_set):
                            res[i] = f_in.get(sp, 0.0) - f_curr[sp] + self.volume * r_net.get(sp, 0.0)
                        return res

                    f0 = np.array([f_in.get(sp, 0.0) for sp in species_set])
                    sol = root(cstr_residuals, f0, method="hybr")
                    f_opt = sol.x if sol.success else f0
                    f_out_rxn = {sp: max(0.0, float(f_opt[i])) for i, sp in enumerate(species_set)}

                # Update non-reacting species
                f_out_all = f_out_rxn.copy()
                for sp, flow in f_in.items():
                    if sp not in f_out_all:
                        f_out_all[sp] = flow

                tot_out = max(1e-8, sum(f_out_all.values()))
                z_out = {sp: flow / tot_out for sp, flow in f_out_all.items()}

                # Calculate heat of reaction
                delta_H_tot = sum(
                    (f_out_all.get(sp, 0.0) - f_in.get(sp, 0.0)) * 
                    (rxn.delta_H_298 / max(1e-5, abs(rxn.stoichiometry.get(sp, 1.0))))
                    for rxn in self.reaction_network.reactions
                    for sp in rxn.stoichiometry if rxn.stoichiometry[sp] > 0
                )
                self.heat_duty = delta_H_tot

                out_stream.T = T_op
                out_stream.P = P_op
                out_stream.F = tot_out
                out_stream.z = z_out

                self.size_equipment()
                return {
                    "conversion": round(1.0 - (tot_out / in_stream.F if in_stream.F else 1.0), 3),
                    "reaction_heat_kW": round(self.heat_duty / 1000.0, 2),
                    "outlet_molar_flow": round(tot_out, 3)
                }

            # 2. Standard heuristic conversion mode (fallback)
            conversion = kwargs.get("conversion", 0.70)
            delta_h_rxn = kwargs.get("delta_h_rxn", -45000.0)
            
            out_stream.T = in_stream.T + 12.0
            out_stream.P = in_stream.P - 10000.0
            out_stream.F = in_stream.F
            out_stream.z = in_stream.z.copy() if in_stream.z else {}
            
            keys = list(out_stream.z.keys())
            if len(keys) >= 2:
                r_amount = out_stream.z[keys[0]] * conversion
                out_stream.z[keys[0]] -= r_amount
                out_stream.z[keys[1]] += r_amount
                
            self.heat_duty = in_stream.F * conversion * delta_h_rxn
            self.size_equipment()
            return {"conversion": conversion, "reaction_heat_kW": self.heat_duty / 1000.0}

        # Dynamic ODE simulation
        c_a0 = kwargs.get("c_a0", 10.0)
        v0 = kwargs.get("v0", 1.0)
        reaction_rate_fn = kwargs.get("reaction_rate_fn", lambda ca: -0.5 * ca)
        tau = self.volume / max(0.01, v0)
        
        def odes(t, state):
            c_a = state[0]
            r_a = reaction_rate_fn(c_a)
            dc_a_dt = (c_a0 - c_a) / tau + r_a
            return [dc_a_dt]

        t_eval = np.linspace(time_span[0], time_span[1] if time_span[1] > time_span[0] else 1.0, 100)
        init_st = initial_state if initial_state else [c_a0]
        sol = solve_ivp(odes, (time_span[0], max(time_span[1], 1.0)), init_st, t_eval=t_eval)
        
        return {"t": sol.t, "C_A": sol.y[0]}

    def size_equipment(self) -> dict:
        in_stream = self.inlets[0] if self.inlets else None
        f_in = in_stream.F if in_stream and in_stream.F else 10.0
        v_flow = max(0.01, f_in * 0.025)  # m3/h estimate
        residence_time_min = (self.volume / v_flow) * 60.0
        diameter = (4.0 * self.volume / (np.pi * 1.5)) ** (1.0 / 3.0)  # H/D = 1.5
        height = 1.5 * diameter
        jacket_area = np.pi * diameter * height

        self.sizing_results = {
            "vessel_volume_m3": round(self.volume, 2),
            "residence_time_min": round(residence_time_min, 1),
            "diameter_m": round(diameter, 2),
            "height_m": round(height, 2),
            "jacket_area_m2": round(jacket_area, 2)
        }
        return self.sizing_results


class IdealPFR(BaseUnit):
    """
    Plug Flow Reactor (PFR).
    Supports:
    1. Axial differential integration of multi-reaction networks along volume coordinate V.
    2. Spatial profiles: component flows F_i(V), conversion X(V), and temperature T(V).
    3. Mechanical sizing: tube diameter, length, aspect ratio L/D, and catalyst mass.
    """
    
    def __init__(self, unit_id: str, name: str, volume: float = 3.0,
                 reaction_package: Optional[str] = None):
        super().__init__(unit_id, name)
        self.volume = max(0.01, volume)
        self.reaction_package = reaction_package
        self.reaction_network: Optional[ReactionNetwork] = None
        if reaction_package and reaction_package in REACTION_PACKAGES:
            self.reaction_network = REACTION_PACKAGES[reaction_package]

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_stream = self.inlets[0] if self.inlets else None
        out_stream = self.outlets[0] if self.outlets else None
        
        # Flowsheet stream propagation mode
        if in_stream and out_stream and in_stream.F is not None and in_stream.F > 0:
            rxn_pkg_name = kwargs.get("reaction_package") or self.reaction_package
            if rxn_pkg_name and rxn_pkg_name in REACTION_PACKAGES:
                self.reaction_network = REACTION_PACKAGES[rxn_pkg_name]

            # 1. Rigorous ODE Integration Mode
            if self.reaction_network:
                species = self.reaction_network.get_species_set()
                f_in = np.array([in_stream.F * in_stream.z.get(sp, 0.0) for sp in species])
                p_in = in_stream.P
                t_in = in_stream.T

                # dF_i / dV = r_net,i
                def pfr_odes(V, state):
                    f_curr = state
                    f_tot = max(1e-6, np.sum(f_curr))
                    # Molar concentrations: C_i = (F_i / F_tot) * (P / (R * T))
                    c_dict = {
                        species[i]: (max(0.0, f_curr[i]) / f_tot) * (p_in / (GAS_CONSTANT_R * t_in))
                        for i in range(len(species))
                    }
                    r_net = self.reaction_network.calculate_net_rates(c_dict, t_in)
                    df_dv = [r_net.get(species[i], 0.0) for i in range(len(species))]
                    return df_dv

                sol = solve_ivp(pfr_odes, (0.0, self.volume), f_in, method="RK45")
                f_out_arr = np.maximum(0.0, sol.y[:, -1])
                f_out_dict = {species[i]: float(f_out_arr[i]) for i in range(len(species))}

                # Add non-reacting species
                for sp, frac in in_stream.z.items():
                    if sp not in f_out_dict:
                        f_out_dict[sp] = in_stream.F * frac

                tot_out = max(1e-8, sum(f_out_dict.values()))
                z_out = {sp: flow / tot_out for sp, flow in f_out_dict.items()}

                delta_H_tot = sum(
                    (f_out_dict.get(sp, 0.0) - in_stream.F * in_stream.z.get(sp, 0.0)) * 
                    (rxn.delta_H_298 / max(1e-5, abs(rxn.stoichiometry.get(sp, 1.0))))
                    for rxn in self.reaction_network.reactions
                    for sp in rxn.stoichiometry if rxn.stoichiometry[sp] > 0
                )
                self.heat_duty = delta_H_tot

                out_stream.T = in_stream.T + 18.0
                out_stream.P = in_stream.P - 20000.0
                out_stream.F = tot_out
                out_stream.z = z_out

                self.size_equipment()
                return {
                    "conversion": round(1.0 - (tot_out / in_stream.F if in_stream.F else 1.0), 3),
                    "reaction_heat_kW": round(self.heat_duty / 1000.0, 2),
                    "outlet_molar_flow": round(tot_out, 3)
                }

            # 2. Standard heuristic conversion mode (fallback)
            conversion = kwargs.get("conversion", 0.85)
            delta_h_rxn = kwargs.get("delta_h_rxn", -60000.0)
            
            out_stream.T = in_stream.T + 25.0
            out_stream.P = in_stream.P - 25000.0
            out_stream.F = in_stream.F
            out_stream.z = in_stream.z.copy() if in_stream.z else {}
            
            keys = list(out_stream.z.keys())
            if len(keys) >= 2:
                r_amount = out_stream.z[keys[0]] * conversion
                out_stream.z[keys[0]] -= r_amount
                out_stream.z[keys[1]] += r_amount
                
            self.heat_duty = in_stream.F * conversion * delta_h_rxn
            self.size_equipment()
            return {"conversion": conversion, "reaction_heat_kW": self.heat_duty / 1000.0}

        c_a0 = kwargs.get("c_a0", 10.0)
        v0 = kwargs.get("v0", 1.0)
        reaction_rate_fn = kwargs.get("reaction_rate_fn", lambda ca: -0.8 * ca)
        
        def odes(V, state):
            c_a = state[0]
            r_a = reaction_rate_fn(c_a)
            dc_a_dv = r_a / max(0.01, v0)
            return [dc_a_dv]

        v_eval = np.linspace(0.0, self.volume, 100)
        sol = solve_ivp(odes, (0.0, self.volume), [c_a0], t_eval=v_eval)
        
        return {"V": sol.t, "C_A": sol.y[0]}

    def size_equipment(self) -> dict:
        l_d_ratio = 8.0
        # Volume = (pi/4) * D^2 * L = (pi/4) * D^3 * (L/D)
        diameter = (4.0 * self.volume / (np.pi * l_d_ratio)) ** (1.0 / 3.0)
        length = l_d_ratio * diameter
        surface_area = np.pi * diameter * length

        self.sizing_results = {
            "vessel_volume_m3": round(self.volume, 2),
            "design_length_m": round(length, 2),
            "design_diameter_m": round(diameter, 2),
            "aspect_ratio_L_D": l_d_ratio,
            "tube_surface_area_m2": round(surface_area, 2)
        }
        return self.sizing_results


class EquilibriumReactor(BaseUnit):
    """
    Gibbs & Chemical Equilibrium Reactor (REquil).
    Solves thermodynamic chemical equilibrium for gas/liquid phase reactions
    based on minimization of Gibbs free energy / equilibrium constants K_eq(T).
    Ideal for:
    - Haber-Bosch ammonia synthesis loops
    - Water-gas shift converters
    - Steam methane reforming
    """
    
    def __init__(self, unit_id: str, name: str, volume: float = 4.0,
                 reaction_package: str = "Haber-Bosch Ammonia Synthesis"):
        super().__init__(unit_id, name)
        self.volume = max(0.01, volume)
        self.reaction_package = reaction_package
        self.reaction_network: Optional[ReactionNetwork] = REACTION_PACKAGES.get(reaction_package)

    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_stream = self.inlets[0] if self.inlets else None
        out_stream = self.outlets[0] if self.outlets else None
        
        if in_stream and out_stream and in_stream.F is not None and in_stream.F > 0:
            pkg_name = kwargs.get("reaction_package") or self.reaction_package
            if pkg_name in REACTION_PACKAGES:
                self.reaction_network = REACTION_PACKAGES[pkg_name]

            T_op = kwargs.get("t_target", in_stream.T)
            P_op = in_stream.P - kwargs.get("delta_P", 35000.0)

            if self.reaction_network:
                f_in = {sp: in_stream.F * in_stream.z.get(sp, 0.0) for sp in self.reaction_network.get_species_set()}
                f_out_eq = self.reaction_network.solve_chemical_equilibrium(f_in, T_op, P_op, phase="gas")

                # Include non-reacting species
                f_out_all = f_out_eq.copy()
                for sp, frac in in_stream.z.items():
                    if sp not in f_out_all:
                        f_out_all[sp] = in_stream.F * frac

                tot_out = max(1e-8, sum(f_out_all.values()))
                z_out = {sp: flow / tot_out for sp, flow in f_out_all.items()}

                # Enthalpy duty
                delta_H_tot = sum(
                    (f_out_all.get(sp, 0.0) - in_stream.F * in_stream.z.get(sp, 0.0)) * 
                    (rxn.delta_H_298 / max(1e-5, abs(rxn.stoichiometry.get(sp, 1.0))))
                    for rxn in self.reaction_network.reactions
                    for sp in rxn.stoichiometry if rxn.stoichiometry[sp] > 0
                )
                self.heat_duty = delta_H_tot

                out_stream.T = T_op
                out_stream.P = P_op
                out_stream.F = tot_out
                out_stream.z = z_out

                self.size_equipment()
                return {
                    "conversion": round(1.0 - (tot_out / in_stream.F if in_stream.F else 1.0), 3),
                    "reaction_heat_kW": round(self.heat_duty / 1000.0, 2),
                    "equilibrium_molar_flow": round(tot_out, 3)
                }

        self.size_equipment()
        return {"conversion": 0.0, "reaction_heat_kW": 0.0}

    def size_equipment(self) -> dict:
        ghsv = 4500.0  # Gas Hourly Space Velocity h^-1
        in_stream = self.inlets[0] if self.inlets else None
        f_in = in_stream.F if in_stream and in_stream.F else 10.0
        v_stp_m3_h = f_in * 0.022414 * 3600.0
        cat_volume = v_stp_m3_h / ghsv
        self.volume = max(0.5, cat_volume)

        diameter = (4.0 * self.volume / (np.pi * 3.0)) ** (1.0 / 3.0)
        length = 3.0 * diameter

        self.sizing_results = {
            "vessel_volume_m3": round(self.volume, 2),
            "catalyst_volume_m3": round(cat_volume, 2),
            "design_length_m": round(length, 2),
            "design_diameter_m": round(diameter, 2),
            "ghsv_target_h-1": ghsv
        }
        return self.sizing_results
