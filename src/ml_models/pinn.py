import math
from pathlib import Path
import torch
import torch.nn as nn

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "pinn_vle_model.pt"


class ThermodynamicsPINN(nn.Module):
    """
    PINN predicting non-ideal activity coefficients (gamma) for a binary mixture.
    Enforces the isothermal Gibbs-Duhem thermodynamic consistency equation:
        x1 * (d ln_gamma1 / dx1)_T + x2 * (d ln_gamma2 / dx1)_T = 0
    """

    _cached_model: "ThermodynamicsPINN | None" = None
    _cached_path: Path | None = None

    def __init__(self):
        super(ThermodynamicsPINN, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(2, 64),  # Inputs: mole fraction x_1, scaled temperature T_scaled
            nn.Tanh(),
            nn.Linear(64, 64),
            nn.Tanh(),
            nn.Linear(64, 2)   # Outputs: ln(gamma_1), ln(gamma_2)
        )

    @staticmethod
    def scale_temperature(T: float | torch.Tensor) -> float | torch.Tensor:
        """Normalizes temperature T [K] from [330, 380] K to [0, 1] (compatible with legacy 350-380 scaling)."""
        return (T - 350.0) / 30.0

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.net(inputs)

    def compute_loss(self, inputs: torch.Tensor, targets: torch.Tensor,
                     lambda_physics: float = 0.1) -> tuple:
        """
        inputs: tensor of shape (N, 2) -> columns: [x_1, T_scaled]
        targets: tensor of shape (N, 2) -> columns: [ln_gamma_1_exp, ln_gamma_2_exp]
        """
        inputs.requires_grad_(True)
        predictions = self.forward(inputs)

        # Empirical Data Loss (MSE)
        loss_data = nn.MSELoss()(predictions, targets)

        # Physics Loss: Isothermal Gibbs-Duhem constraint
        # sum( x_i * (d ln_gamma_i / dx_1)_T ) = 0.0
        ln_g1 = predictions[:, 0:1]
        ln_g2 = predictions[:, 1:2]
        x1 = inputs[:, 0:1]
        x2 = 1.0 - x1  # Binary mixture assumption

        # Calculate partial derivatives with respect to x_1 (column 0) at constant T (column 1)
        grad_g1 = torch.autograd.grad(
            ln_g1, inputs, grad_outputs=torch.ones_like(ln_g1), create_graph=True
        )[0][:, 0:1]
        grad_g2 = torch.autograd.grad(
            ln_g2, inputs, grad_outputs=torch.ones_like(ln_g2), create_graph=True
        )[0][:, 0:1]

        gibbs_duhem_residual = x1 * grad_g1 + x2 * grad_g2
        loss_physics = nn.MSELoss()(gibbs_duhem_residual, torch.zeros_like(gibbs_duhem_residual))

        total_loss = loss_data + lambda_physics * loss_physics
        return total_loss, loss_data, loss_physics

    @classmethod
    def load_trained_model(cls, model_path: str | Path | None = None) -> "ThermodynamicsPINN":
        """Loads trained PINN weights safely using weights_only=True and caches the instance."""
        path = Path(model_path) if model_path is not None else DEFAULT_MODEL_PATH
        if cls._cached_model is not None and cls._cached_path == path:
            return cls._cached_model

        model = cls()
        if path.exists():
            state_dict = torch.load(path, map_location="cpu", weights_only=True)
            model.load_state_dict(state_dict)
        model.eval()
        cls._cached_model = model
        cls._cached_path = path
        return model

    @classmethod
    def predict_gammas(cls, x1: float, T: float = 353.15, model_path: str | Path | None = None) -> tuple[float, float]:
        """
        Predicts activity coefficients (gamma_1, gamma_2) for a binary mixture at mole fraction x1 and temperature T [K].
        """
        x1_clamped = float(max(0.0, min(1.0, x1)))
        t_scaled = float(cls.scale_temperature(float(T)))
        model = cls.load_trained_model(model_path)
        with torch.no_grad():
            inp = torch.tensor([[x1_clamped, t_scaled]], dtype=torch.float32)
            out = model(inp)[0]
            g1 = float(math.exp(max(-10.0, min(10.0, float(out[0].item())))))
            g2 = float(math.exp(max(-10.0, min(10.0, float(out[1].item())))))
        return g1, g2
