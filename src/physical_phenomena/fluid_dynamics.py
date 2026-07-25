import numpy as np

class FluidDynamics:
    """Calculates pressure drops, friction factors, and hydraulic requirements."""
    
    @staticmethod
    def calculate_reynolds(density: float, velocity: float, diameter: float, viscosity: float) -> float:
        """Calculate dimensionless Reynolds number."""
        if viscosity <= 0:
            raise ValueError("Viscosity must be greater than zero.")
        return (density * velocity * diameter) / viscosity

    @staticmethod
    def calculate_friction_factor(reynolds: float, roughness: float, diameter: float) -> float:
        """Calculate Darcy friction factor using the Haaland approximation."""
        if reynolds < 2300:
            # Laminar flow region
            return 64.0 / max(reynolds, 1e-5)
        
        # Turbulent flow region (Haaland approximation)
        relative_roughness = roughness / diameter
        inner_log = (relative_roughness / 3.7) ** 1.11 + 6.9 / reynolds
        return (1.8 * np.log10(inner_log)) ** -2.0

    @staticmethod
    def calculate_pressure_drop(friction_factor: float, length: float, diameter: float, 
                                density: float, velocity: float, minor_losses: float = 0.0) -> float:
        """Calculate total pressure drop in Pa using Darcy-Weisbach."""
        head_loss = friction_factor * (length / diameter) + minor_losses
        return head_loss * 0.5 * density * (velocity ** 2)

    @staticmethod
    def size_pump(volumetric_flow: float, pressure_drop: float, efficiency: float) -> float:
        """Sizes hydraulic pump power requirements in Watts."""
        if efficiency <= 0 or efficiency > 1.0:
            raise ValueError("Pump efficiency must be between 0 and 1.0.")
        return (volumetric_flow * pressure_drop) / efficiency

    @staticmethod
    def calculate_ergun_pressure_drop(length: float, viscosity: float, density: float, 
                                      superficial_velocity: float, porosity: float, 
                                      particle_diameter: float) -> float:
        """
        Calculates pressure drop across a packed bed using the Ergun equation:
        dP/dL = 150 * [mu * v0 * (1 - eps)^2] / [Dp^2 * eps^3] + 1.75 * [rho * v0^2 * (1 - eps)] / [Dp * eps^3]
        """
        if porosity <= 0 or porosity >= 1.0:
            raise ValueError("Porosity must be between 0 and 1.0.")
        if particle_diameter <= 0:
            raise ValueError("Particle diameter must be greater than zero.")
            
        term_viscous = 150.0 * (viscosity * superficial_velocity * (1.0 - porosity)**2) / ((particle_diameter**2) * (porosity**3))
        term_inertial = 1.75 * (density * (superficial_velocity**2) * (1.0 - porosity)) / (particle_diameter * (porosity**3))
        return (term_viscous + term_inertial) * length

    @staticmethod
    def calculate_blake_kozeny_pressure_drop(length: float, viscosity: float, 
                                             superficial_velocity: float, porosity: float, 
                                             particle_diameter: float) -> float:
        """Calculates packed bed pressure drop in viscous limit (Re_p < 10)."""
        if porosity <= 0 or porosity >= 1.0:
            raise ValueError("Porosity must be between 0 and 1.0.")
        return 150.0 * (viscosity * superficial_velocity * (1.0 - porosity)**2) / ((particle_diameter**2) * (porosity**3)) * length

    @staticmethod
    def calculate_burke_plummer_pressure_drop(length: float, density: float, 
                                              superficial_velocity: float, porosity: float, 
                                              particle_diameter: float) -> float:
        """Calculates packed bed pressure drop in turbulent limit (Re_p > 1000)."""
        if porosity <= 0 or porosity >= 1.0:
            raise ValueError("Porosity must be between 0 and 1.0.")
        return 1.75 * (density * (superficial_velocity**2) * (1.0 - porosity)) / (particle_diameter * (porosity**3)) * length

