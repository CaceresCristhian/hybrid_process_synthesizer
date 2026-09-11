"""
Multi-reaction kinetic and chemical equilibrium modeling engine.
Supports temperature-dependent Arrhenius rate laws, reversible equilibrium extents,
non-linear algebraic CSTR solvers, and pre-configured industrial reaction packages.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from scipy.optimize import root, minimize
from config.settings import GAS_CONSTANT_R

class Reaction:
    """
    Represents a single stoichiometric chemical reaction.
    Stoichiometry convention: negative for reactants, positive for products.
    e.g. N2 + 3 H2 <-> 2 NH3  =>  {"nitrogen": -1.0, "hydrogen": -3.0, "ammonia": 2.0}
    """
    def __init__(self, reaction_id: str, name: str, 
                 stoichiometry: Dict[str, float],
                 reaction_type: str = "kinetic",
                 A_forward: float = 1.0e5,
                 Ea_forward: float = 50000.0,
                 A_reverse: float = 0.0,
                 Ea_reverse: float = 0.0,
                 delta_H_298: float = 0.0,
                 delta_G_298: float = 0.0,
                 forward_orders: Optional[Dict[str, float]] = None,
                 reverse_orders: Optional[Dict[str, float]] = None):
        self.id = reaction_id
        self.name = name
        self.stoichiometry = {k.lower(): float(v) for k, v in stoichiometry.items()}
        self.reaction_type = reaction_type  # 'kinetic', 'equilibrium', 'irreversible'
        
        self.A_f = A_forward
        self.Ea_f = Ea_forward
        self.A_r = A_reverse
        self.Ea_r = Ea_reverse
        
        self.delta_H_298 = delta_H_298  # J/mol (negative = exothermic)
        self.delta_G_298 = delta_G_298  # J/mol
        
        # Reaction orders (defaults to stoichiometric coefficients for elementary reactions)
        self.forward_orders = forward_orders or {
            k: abs(v) for k, v in self.stoichiometry.items() if v < 0
        }
        self.reverse_orders = reverse_orders or {
            k: v for k, v in self.stoichiometry.items() if v > 0
        }

    def k_forward(self, temperature: float) -> float:
        """Calculates forward rate constant k_f(T) = A_f * exp(-Ea_f / (R * T))."""
        T = max(100.0, temperature)
        exponent = -self.Ea_f / (GAS_CONSTANT_R * T)
        return float(self.A_f * np.exp(np.clip(exponent, -60.0, 50.0)))

    def k_reverse(self, temperature: float) -> float:
        """Calculates reverse rate constant k_r(T)."""
        T = max(100.0, temperature)
        if self.A_r > 0 and self.Ea_r > 0:
            exponent = -self.Ea_r / (GAS_CONSTANT_R * T)
            return float(self.A_r * np.exp(np.clip(exponent, -60.0, 50.0)))
        
        # If A_r not supplied, calculate k_r from K_eq(T) = k_f / k_r
        K_eq = self.K_equilibrium(T)
        if K_eq > 1e-15:
            return self.k_forward(T) / K_eq
        return 0.0

    def K_equilibrium(self, temperature: float) -> float:
        """
        Calculates thermodynamic equilibrium constant K_eq(T) via the Van 't Hoff equation:
        ln(K_eq(T)) = -Delta_G_298 / (R * 298.15) - (Delta_H_298 / R) * (1/T - 1/298.15)
        """
        T = max(100.0, temperature)
        T0 = 298.15
        R = GAS_CONSTANT_R
        
        term_g = -self.delta_G_298 / (R * T0) if self.delta_G_298 != 0.0 else 0.0
        term_h = -(self.delta_H_298 / R) * (1.0 / T - 1.0 / T0) if self.delta_H_298 != 0.0 else 0.0
        
        ln_K = term_g + term_h
        return float(np.exp(np.clip(ln_K, -40.0, 40.0)))

    def calculate_rate(self, concentrations: Dict[str, float], temperature: float) -> float:
        """
        Calculates reaction rate r in mol/(m3*s) given concentrations in mol/m3:
        r = k_f * prod(C_reactants^alpha) - k_r * prod(C_products^beta)
        """
        kf = self.k_forward(temperature)
        kr = self.k_reverse(temperature) if self.reaction_type != "irreversible" else 0.0
        
        rate_f = kf
        for sp, order in self.forward_orders.items():
            c = max(1e-12, concentrations.get(sp.lower(), 0.0))
            rate_f *= (c ** order)
            
        rate_r = 0.0
        if kr > 0:
            rate_r = kr
            for sp, order in self.reverse_orders.items():
                c = max(1e-12, concentrations.get(sp.lower(), 0.0))
                rate_r *= (c ** order)
                
        return float(rate_f - rate_r)


class ReactionNetwork:
    """A collection of coupled simultaneous or sequential chemical reactions."""
    def __init__(self, name: str, reactions: List[Reaction]):
        self.name = name
        self.reactions = reactions

    def get_species_set(self) -> List[str]:
        sp = set()
        for rxn in self.reactions:
            sp.update(rxn.stoichiometry.keys())
        return sorted(list(sp))

    def calculate_net_rates(self, concentrations: Dict[str, float], temperature: float) -> Dict[str, float]:
        """
        Computes net formation rate for each species:
        r_net,i = sum_j (nu_ij * r_j) in mol/(m3*s)
        """
        species_list = self.get_species_set()
        net_rates = {sp: 0.0 for sp in species_list}
        
        for rxn in self.reactions:
            r = rxn.calculate_rate(concentrations, temperature)
            for sp, nu in rxn.stoichiometry.items():
                net_rates[sp] += nu * r
                
        return net_rates

    def calculate_heat_generation(self, concentrations: Dict[str, float], temperature: float) -> float:
        """
        Computes total volumetric heat generation Q_rxn in W/m3 (J/(m3*s)):
        Q_rxn = sum_j [ r_j * (-Delta_H_rxn,j) ]
        """
        q_total = 0.0
        for rxn in self.reactions:
            r = rxn.calculate_rate(concentrations, temperature)
            q_total += r * (-rxn.delta_H_298)
        return float(q_total)

    def solve_chemical_equilibrium(self, feed_flows: Dict[str, float], 
                                   temperature: float, pressure: float, 
                                   phase: str = "gas") -> Dict[str, float]:
        """
        Solves reaction extents xi_j such that each equilibrium reaction satisfies:
        prod( a_i ^ nu_ij ) = K_eq,j(T)
        Returns equilibrium outlet flow rates (mol/s).
        """
        species = self.get_species_set()
        m = len(self.reactions)
        
        # Initial flows vector
        f0 = np.array([max(1e-8, feed_flows.get(sp, 0.0)) for sp in species])
        
        # Stoichiometric matrix N (species x reactions)
        N = np.zeros((len(species), m))
        K_targets = np.zeros(m)
        
        for j, rxn in enumerate(self.reactions):
            K_targets[j] = rxn.K_equilibrium(temperature)
            for sp, nu in rxn.stoichiometry.items():
                i = species.index(sp)
                N[i, j] = nu

        def equilibrium_residuals(xi):
            # Current moles: f = f0 + N * xi
            f_curr = f0 + N @ xi
            f_curr = np.maximum(1e-12, f_curr)
            f_tot = np.sum(f_curr)
            
            # Mole fractions
            y = f_curr / f_tot
            
            # Activities: a_i = y_i * (P / P0) for gas
            p_ratio = pressure / 101325.0 if phase == "gas" else 1.0
            activities = y * p_ratio
            
            res = np.zeros(m)
            for j, rxn in enumerate(self.reactions):
                # Q = prod( a_i ^ nu_ij )
                q_ln = 0.0
                for sp, nu in rxn.stoichiometry.items():
                    i = species.index(sp)
                    q_ln += nu * np.log(max(1e-12, activities[i]))
                    
                ln_K = np.log(max(1e-15, K_targets[j]))
                res[j] = q_ln - ln_K
                
            return res

        xi_guess = np.zeros(m)
        sol = root(equilibrium_residuals, xi_guess, method="hybr")
        
        xi_opt = sol.x if sol.success else np.zeros(m)
        f_out = f0 + N @ xi_opt
        f_out = np.maximum(0.0, f_out)
        
        return {species[i]: float(f_out[i]) for i in range(len(species))}


# Pre-configured Industrial Reaction Packages
REACTION_PACKAGES: Dict[str, ReactionNetwork] = {
    "Haber-Bosch Ammonia Synthesis": ReactionNetwork(
        name="Haber-Bosch Ammonia Synthesis",
        reactions=[
            Reaction(
                reaction_id="HB-01",
                name="Ammonia Synthesis (N2 + 3H2 <-> 2NH3)",
                stoichiometry={"nitrogen": -1.0, "hydrogen": -3.0, "ammonia": 2.0},
                reaction_type="equilibrium",
                A_forward=1.79e4,
                Ea_forward=87000.0,
                delta_H_298=-92400.0,  # J/mol N2 (exothermic)
                delta_G_298=-33000.0   # J/mol N2
            )
        ]
    ),
    "Bio-Ethanol Fermentation": ReactionNetwork(
        name="Bio-Ethanol Fermentation",
        reactions=[
            Reaction(
                reaction_id="ETH-01",
                name="Enzymatic Glycolysis (Glucose -> 2 EtOH + 2 CO2)",
                stoichiometry={"glucose": -1.0, "ethanol": 2.0, "co2": 2.0},
                reaction_type="irreversible",
                A_forward=2.5e6,
                Ea_forward=52000.0,
                delta_H_298=-67000.0   # J/mol (exothermic)
            )
        ]
    ),
    "Water-Gas Shift": ReactionNetwork(
        name="Water-Gas Shift",
        reactions=[
            Reaction(
                reaction_id="WGS-01",
                name="Water-Gas Shift (CO + H2O <-> CO2 + H2)",
                stoichiometry={"water": -1.0, "co2": 1.0, "hydrogen": 1.0},
                reaction_type="equilibrium",
                A_forward=8.5e5,
                Ea_forward=67400.0,
                delta_H_298=-41200.0,
                delta_G_298=-28600.0
            )
        ]
    ),
    "Generic 1st-Order Exothermic": ReactionNetwork(
        name="Generic 1st-Order Exothermic",
        reactions=[
            Reaction(
                reaction_id="GEN-01",
                name="A -> B",
                stoichiometry={"a": -1.0, "b": 1.0},
                reaction_type="kinetic",
                A_forward=5.0e4,
                Ea_forward=45000.0,
                delta_H_298=-50000.0
            )
        ]
    )
}
