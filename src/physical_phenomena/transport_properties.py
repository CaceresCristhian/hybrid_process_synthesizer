import numpy as np

class TransportProperties:
    """Calculates transport dimensionless groups and coefficients."""
    
    @staticmethod
    def reynolds(velocity: float, length: float, density: float, viscosity: float) -> float:
        """Ratio of inertial forces to viscous forces."""
        if viscosity <= 0:
            raise ValueError("Viscosity must be greater than zero.")
        return (density * velocity * length) / viscosity

    @staticmethod
    def prandtl(cp: float, viscosity: float, conductivity: float) -> float:
        """Ratio of momentum diffusivity to thermal diffusivity."""
        if conductivity <= 0:
            raise ValueError("Thermal conductivity must be greater than zero.")
        return (cp * viscosity) / conductivity

    @staticmethod
    def schmidt(viscosity: float, density: float, diffusivity: float) -> float:
        """Ratio of momentum diffusivity to mass diffusivity."""
        denom = density * diffusivity
        if denom <= 0:
            raise ValueError("Density and diffusivity must be greater than zero.")
        return viscosity / denom

    @staticmethod
    def nusselt(convective_h: float, length: float, fluid_conductivity: float) -> float:
        """Ratio of convective heat transfer to molecular conduction in fluid."""
        if fluid_conductivity <= 0:
            raise ValueError("Fluid thermal conductivity must be greater than zero.")
        return (convective_h * length) / fluid_conductivity

    @staticmethod
    def sherwood(mass_transfer_k: float, length: float, diffusivity: float) -> float:
        """Ratio of convective mass transfer to molecular diffusion."""
        if diffusivity <= 0:
            raise ValueError("Diffusivity must be greater than zero.")
        return (mass_transfer_k * length) / diffusivity

    @staticmethod
    def biot(convective_h: float, length: float, solid_conductivity: float) -> float:
        """Ratio of convective heat transfer at solid surface to internal conduction."""
        if solid_conductivity <= 0:
            raise ValueError("Solid thermal conductivity must be greater than zero.")
        return (convective_h * length) / solid_conductivity

    @staticmethod
    def grashof(gravity: float, thermal_expansion: float, temp_diff: float, 
                length: float, density: float, viscosity: float) -> float:
        """Ratio of buoyancy forces to viscous forces in natural convection."""
        if viscosity <= 0:
            raise ValueError("Viscosity must be greater than zero.")
        numerator = gravity * thermal_expansion * temp_diff * (length ** 3) * (density ** 2)
        return numerator / (viscosity ** 2)

    @staticmethod
    def damkohler_diffusion(reaction_k: float, length: float, diffusivity: float) -> float:
        """Ratio of chemical reaction rate to molecular mass diffusion rate (Da = k * L^2 / D)."""
        if diffusivity <= 0:
            raise ValueError("Diffusivity must be greater than zero.")
        return (reaction_k * (length ** 2)) / diffusivity

    @staticmethod
    def damkohler_flow(reaction_k: float, space_time: float) -> float:
        """Ratio of reaction rate to flow rate in a continuous reactor (Da = k * tau)."""
        return reaction_k * space_time
