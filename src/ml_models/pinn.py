import torch
import torch.nn as nn

class ThermodynamicsPINN(nn.Module):
    """
    PINN predicting non-ideal activity coefficients (gamma) for a binary mixture.
    Enforces the Gibbs-Duhem thermodynamic consistency equation.
    """
    
    def __init__(self):
        super(ThermodynamicsPINN, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(2, 64),  # Inputs: mole fraction x_1, temperature T
            nn.Tanh(),
            nn.Linear(64, 64),
            nn.Tanh(),
            nn.Linear(64, 2)   # Outputs: ln(gamma_1), ln(gamma_2)
        )
        
    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.net(inputs)

    def compute_loss(self, inputs: torch.Tensor, targets: torch.Tensor, 
                     lambda_physics: float = 0.1) -> tuple:
        """
        inputs: tensor of shape (N, 2) -> columns: [x_1, T]
        targets: tensor of shape (N, 2) -> columns: [ln_gamma_1_exp, ln_gamma_2_exp]
        """
        inputs.requires_grad_(True)
        predictions = self.forward(inputs)
        
        # Empirical Data Loss (MSE)
        loss_data = nn.MSELoss()(predictions, targets)
        
        # Physics Loss: Gibbs-Duhem constraint
        # sum( x_i * d(ln_gamma_i)/dx_1 ) = 0.0
        ln_g1 = predictions[:, 0:1]
        ln_g2 = predictions[:, 1:2]
        x1 = inputs[:, 0:1]
        x2 = 1.0 - x1  # Binary mixture assumption
        
        # Calculate gradients with autograd
        grad_g1 = torch.autograd.grad(ln_g1, inputs, grad_outputs=torch.ones_like(ln_g1), 
                                      create_graph=True)[0][:, 0:1]
        grad_g2 = torch.autograd.grad(ln_g2, inputs, grad_outputs=torch.ones_like(ln_g2), 
                                      create_graph=True)[0][:, 0:1]
        
        gibbs_duhem_residual = x1 * grad_g1 + x2 * grad_g2
        loss_physics = nn.MSELoss()(gibbs_duhem_residual, torch.zeros_like(gibbs_duhem_residual))
        
        total_loss = loss_data + lambda_physics * loss_physics
        return total_loss, loss_data, loss_physics
