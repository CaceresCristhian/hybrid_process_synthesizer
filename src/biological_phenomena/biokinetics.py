class Biokinetics:
    """Calculates cell growth rates and biological kinetics."""
    
    @staticmethod
    def monod_growth_rate(mu_max: float, substrate_conc: float, half_saturation_constant: float) -> float:
        """
        Calculates specific growth rate (mu) using the Monod equation:
        mu = mu_max * S / (Ks + S)
        """
        if substrate_conc < 0:
            return 0.0
        return mu_max * substrate_conc / (half_saturation_constant + substrate_conc)

    @staticmethod
    def haldane_growth_rate(mu_max: float, substrate_conc: float, half_saturation_constant: float, 
                            inhibition_constant: float) -> float:
        """
        Calculates specific growth rate (mu) using the Haldane (substrate inhibition) equation:
        mu = mu_max * S / (Ks + S + (S^2 / Ki))
        """
        if substrate_conc <= 0:
            return 0.0
        denominator = half_saturation_constant + substrate_conc + (substrate_conc ** 2) / inhibition_constant
        return mu_max * substrate_conc / denominator

    @staticmethod
    def luedeking_piret_product_rate(rx: float, X: float, alpha: float, beta: float) -> float:
        """
        Calculates product formation rate using the Luedeking-Piret model:
        rP = alpha * rx + beta * X
        where:
          - rx: growth rate dX/dt (g/L/h)
          - X: cell concentration (g/L)
          - alpha: growth-associated product constant (g/g)
          - beta: non-growth-associated product constant (g/g/h)
        """
        return alpha * rx + beta * X

