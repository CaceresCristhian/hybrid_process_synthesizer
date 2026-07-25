class VesselSizing:
    """Calculates mechanical dimensions and wall thicknesses of process vessels."""
    
    # Maximum allowable stress values (S) in Pascals at standard temperature (approx 38 C / 100 F)
    # Sourced from ASME Boiler and Pressure Vessel Code (Section II, Part D)
    MATERIAL_ALLOWABLE_STRESSES = {
        "stainless_steel_316": 115.0e6,  # 115 MPa
        "carbon_steel_a516": 138.0e6,    # 138 MPa
        "hastelloy_c276": 172.0e6        # 172 MPa
    }

    @classmethod
    def calculate_shell_thickness(cls, internal_pressure: float, internal_radius: float, 
                                  material: str, joint_efficiency: float = 0.85, 
                                  corrosion_allowance: float = 0.0015) -> float:
        """
        Calculates wall thickness of a cylindrical shell based on ASME Section VIII Division 1.
        t = (P * R) / (S * E - 0.6 * P) + CA
        where:
          - internal_pressure (P) in Pascals
          - internal_radius (R) in meters
          - joint_efficiency (E) (0.7 to 1.0)
          - corrosion_allowance (CA) in meters (default: 1.5 mm)
          - material (S) allowable stress lookups
        """
        if material not in cls.MATERIAL_ALLOWABLE_STRESSES:
            raise ValueError(f"Material {material} not supported. Options: {list(cls.MATERIAL_ALLOWABLE_STRESSES.keys())}")
            
        allowable_stress = cls.MATERIAL_ALLOWABLE_STRESSES[material]
        
        # Denominator calculation: S*E - 0.6*P
        denominator = (allowable_stress * joint_efficiency) - (0.6 * internal_pressure)
        if denominator <= 0:
            raise ValueError("Pressure is too high for the selected material allowable stress limits.")
            
        thickness = (internal_pressure * internal_radius) / denominator
        return thickness + corrosion_allowance
