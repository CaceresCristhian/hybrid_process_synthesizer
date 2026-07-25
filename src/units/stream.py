import numpy as np

class MaterialStream:
    """
    HYSYS-style material stream representation.
    Tracks specification state of physical variables and propagates information.
    Includes mass and energy calculations for flowsheet-wide balance reports.
    """
    def __init__(self, stream_id: str, name: str = ""):
        self.stream_id = stream_id
        self.name = name if name else stream_id
        
        # State variables
        self._T = None      # Temperature in K
        self._P = None      # Pressure in Pa
        self._F = None      # Molar Flow rate in mol/s
        self._z = {}        # Composition (dict of species_id: mole_fraction)
        self._H = None      # Molar Enthalpy in J/mol
        self._Vf = None     # Vapor fraction (0.0 to 1.0)
        
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

    def run_flash(self):
        """Checks if enough state variables are specified to compute the rest."""
        if not self.specs["z"] or len(self._z) == 0:
            return  # Composition is required for VLE

    def get_mixture_mw(self, species_map: dict) -> float:
        """Calculates molecular weight of mixture (g/mol)."""
        if not self._z:
            return 18.015  # default to water MW
        mw = 0.0
        for sp_id, x in self._z.items():
            sp = species_map.get(sp_id)
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
        """Calculates molar enthalpy in J/mol."""
        if self._H is not None:
            return self._H
            
        # Fallback calculation if T is set: H = sum( x_i * Cp_i * (T - 298.15) )
        if self._T is None:
            return 0.0
            
        t_ref = 298.15
        h_val = 0.0
        for sp_id, x in self._z.items():
            sp = species_map.get(sp_id)
            cp = sp.macro.cp_constants[0] if sp and sp.macro.cp_constants else 75.3
            h_val += x * cp * (self._T - t_ref)
        return h_val

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
