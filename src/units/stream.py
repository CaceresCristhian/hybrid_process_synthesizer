import numpy as np

class MaterialStream:
    """
    HYSYS-style material stream representation.
    Tracks specification state of physical variables and propagates information.
    Includes mass and energy calculations for flowsheet-wide balance reports.
    """
    def __init__(self, stream_id: str, name: str = "", T: float = None, P: float = None,
                 F: float = None, z: dict = None, H: float = None, Vf: float = None):
        self.stream_id = stream_id
        self.name = name if name else stream_id
        
        # State variables
        self._T = None      # Temperature in K
        self._P = None      # Pressure in Pa
        self._F = None      # Molar Flow rate in mol/s
        self._z = {}        # Composition (dict of species_id: mole_fraction)
        self._H = None      # Molar Enthalpy in J/mol
        self._Vf = None     # Vapor fraction (0.0 to 1.0)
        self._x = {}        # Liquid phase composition
        self._y = {}        # Vapor phase composition
        
        # Specification tracking: True if set by user or unit operation
        self.specs = {
            "T": False,
            "P": False,
            "F": False,
            "z": False,
            "H": False,
            "Vf": False
        }
        
        # Listeners for propagation (Unit operations connected to this stream)
        self.upstream_unit = None
        self.downstream_units = []

        if T is not None:
            self.set_val("T", T)
        if P is not None:
            self.set_val("P", P)
        if F is not None:
            self.set_val("F", F)
        if z is not None:
            self.set_val("z", z)
        if H is not None:
            self.set_val("H", H)
        if Vf is not None:
            self.set_val("Vf", Vf)

    @property
    def T(self):
        return self._T

    @T.setter
    def T(self, val):
        self.set_val("T", val)

    @property
    def P(self):
        return self._P

    @P.setter
    def P(self, val):
        self.set_val("P", val)

    @property
    def F(self):
        return self._F

    @F.setter
    def F(self, val):
        self.set_val("F", val)

    @property
    def z(self):
        return self._z

    @z.setter
    def z(self, val):
        self.set_val("z", val)

    @property
    def H(self):
        return self._H

    @H.setter
    def H(self, val):
        self.set_val("H", val)

    @property
    def Vf(self):
        return self._Vf

    @Vf.setter
    def Vf(self, val):
        self.set_val("Vf", val)

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    def set_val(self, prop: str, val, specified: bool = True):
        """Sets a property value and marks its specification state."""
        if val is None:
            # Clear spec
            setattr(self, f"_{prop}", None)
            self.specs[prop] = False
            return
            
        if prop == "z":
            # Normalize composition
            total = sum(val.values())
            if total > 0:
                normalized = {k: v / total for k, v in val.items()}
                self._z = normalized
                self.specs["z"] = True
            else:
                self._z = {}
                self.specs["z"] = False
        else:
            setattr(self, f"_{prop}", float(val))
            self.specs[prop] = specified
            
        # Trigger local flash calculations if degrees of freedom are met
        self.run_flash()
        
        # Propagate changes to connected unit operations
        self.propagate()

    def get_degrees_of_freedom(self) -> int:
        """
        Calculates Gibbs/Duhem stream degrees of freedom.
        A material stream requires composition (z), molar flow (F), and 2 intensive
        state variables among (T, P, Vf, H) to be fully specified (DOF = 0).
        """
        intensive_specified = sum(1 for k in ("T", "P", "Vf", "H") if self.specs.get(k, False))
        intensive_dof = max(0, 2 - intensive_specified)
        extensive_dof = (0 if self.specs.get("F", False) else 1) + (0 if self.specs.get("z", False) else 1)
        return intensive_dof + extensive_dof

    def run_flash(self, species_map: dict = None):
        """
        Evaluates thermodynamic state (Vf, liquid x, vapor y) when composition z
        and at least two intensive properties (e.g., T and P) are specified.
        """
        if not self.specs["z"] or len(self._z) == 0:
            return
        if self._T is not None and self._P is not None and not self.specs.get("Vf", False):
            try:
                from src.database.loader import ChemicalDatabaseLoader
                from src.chemical_phenomena.thermodynamics import Thermodynamics
                sp_lookup = species_map if species_map else ChemicalDatabaseLoader.load_all_species()
                sp_list = []
                valid_z = {}
                for k, v in self._z.items():
                    if v > 0:
                        sp_obj = sp_lookup.get(k) or sp_lookup.get(k.lower())
                        if sp_obj is not None:
                            sp_list.append(sp_obj)
                            valid_z[sp_obj.id] = v
                if sp_list:
                    tot = sum(valid_z.values())
                    valid_z = {k: v / tot for k, v in valid_z.items()}
                    flash_res = Thermodynamics.solve_tp_flash(sp_list, valid_z, float(self._T), float(self._P))
                    self._Vf = float(flash_res["beta"])
                    self._x = flash_res["x"]
                    self._y = flash_res["y"]
            except Exception:
                pass

    def get_mixture_mw(self, species_map: dict) -> float:
        """Calculates molecular weight of mixture (g/mol)."""
        if not self._z:
            return 18.015  # default to water MW
        mw = 0.0
        for sp_id, x in self._z.items():
            sp = species_map.get(sp_id) if species_map else None
            sp_mw = sp.micro.molecular_weight if sp else 18.015
            mw += x * sp_mw
        return mw

    def get_mass_flow(self, species_map: dict) -> float:
        """Calculates mass flow in kg/h."""
        if self._F is None:
            return 0.0
        mw = self.get_mixture_mw(species_map)
        # mol/s * g/mol = g/s => * 3600 / 1000 = kg/h
        return self._F * mw * 3.6

    def get_enthalpy(self, species_map: dict) -> float:
        """
        Calculates molar enthalpy in J/mol by integrating the polynomial heat capacity
        Cp(T) = C0 + C1*T + C2*T^2 + C3*T^3 from T_ref = 298.15 K to T, plus the
        Trouton/Riedel latent heat of vaporization when vapor fraction Vf > 0 and H is not overridden.
        """
        if self._H is not None:
            return self._H

        if self._T is None:
            return 0.0

        t_ref = 298.15
        t_val = float(self._T)
        h_sensible = 0.0
        for sp_id, x in self._z.items():
            sp = species_map.get(sp_id) if species_map else None
            coeffs = sp.macro.cp_constants if (sp and sp.macro.cp_constants) else [75.3]
            c0 = coeffs[0] if len(coeffs) > 0 else 75.3
            c1 = coeffs[1] if len(coeffs) > 1 else 0.0
            c2 = coeffs[2] if len(coeffs) > 2 else 0.0
            c3 = coeffs[3] if len(coeffs) > 3 else 0.0
            dh_i = (
                c0 * (t_val - t_ref)
                + 0.5 * c1 * (t_val**2 - t_ref**2)
                + (1.0 / 3.0) * c2 * (t_val**3 - t_ref**3)
                + 0.25 * c3 * (t_val**4 - t_ref**4)
            )
            h_sensible += x * dh_i

        # Include latent heat if two-phase/vapor (Vf explicitly set by user or flash unit)
        h_latent = 0.0
        if self.specs.get("Vf", False) and self._Vf is not None and self._Vf > 0.0:
            for sp_id, x in self._z.items():
                sp = species_map.get(sp_id) if species_map else None
                tb = sp.macro.boiling_point if sp else 373.15
                # Trouton-Vetere latent heat estimate: dH_vap ~ 88 * Tb (J/mol)
                dh_vap_i = 88.0 * tb
                h_latent += x * dh_vap_i * float(self._Vf)

        return float(h_sensible + h_latent)

    def get_energy_flow(self, species_map: dict) -> float:
        """Calculates energy flow rate in kW (kJ/s)."""
        if self._F is None:
            return 0.0
        h_molar = self.get_enthalpy(species_map)
        # mol/s * J/mol = J/s = W => / 1000 = kW
        return self._F * h_molar / 1000.0

    def propagate(self):
        """Propagates stream properties to connected units (forward and backward)."""
        # Forward propagation
        for unit in self.downstream_units:
            if hasattr(unit, "propagate_forward"):
                unit.propagate_forward(self)
            
        # Backward propagation
        if self.upstream_unit and hasattr(self.upstream_unit, "propagate_backward"):
            self.upstream_unit.propagate_backward(self)

    def __repr__(self):
        t_str = f"{self._T:.1f} K" if self._T else "None"
        p_str = f"{self._P:.1f} Pa" if self._P else "None"
        f_str = f"{self._F:.2f} mol/s" if self._F else "None"
        vf_str = f"{self._Vf:.2f}" if self._Vf else "None"
        return f"MaterialStream({self.stream_id}, T={t_str}, P={p_str}, F={f_str}, Vf={vf_str})"
