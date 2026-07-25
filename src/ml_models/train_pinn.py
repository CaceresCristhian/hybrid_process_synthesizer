import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import torch
import torch.optim as optim
import pandas as pd
import numpy as np
from src.ml_models.pinn import ThermodynamicsPINN
from src.ml_models.dataset_builder import VLEDatasetBuilder

def train_pinn_model(epochs: int = 100, lr: float = 0.01, lambda_physics: float = 0.5):
    """Loads synthetic VLE dataset, trains ThermodynamicsPINN model, and saves weights."""
    
    # 1. Paths configurations
    dataset_path = r"c:\Users\crist\Projects\Thesis\hybrid_process_synthesizer\data\processed\vle_dataset.csv"
    model_save_path = r"c:\Users\crist\Projects\Thesis\hybrid_process_synthesizer\src\ml_models\pinn_vle_model.pt"
    
    # Generate dataset if missing
    if not os.path.exists(dataset_path):
        print("VLE dataset missing. Generating a new synthetic dataset...")
        VLEDatasetBuilder.save_dataset(dataset_path, num_points=500)
        
    df = pd.read_csv(dataset_path)
    
    # 2. Extract and scale features
    # Inputs: x1, T (scaled to [0, 1] range based on boiling range 350 - 380 K)
    x1 = df["x1"].values
    temp = df["T"].values
    t_scaled = (temp - 350.0) / 30.0  # Min-max normalization
    
    inputs_np = np.column_stack((x1, t_scaled))
    targets_np = np.column_stack((df["ln_gamma1"].values, df["ln_gamma2"].values))
    
    # Convert to PyTorch tensors
    inputs_tensor = torch.tensor(inputs_np, dtype=torch.float32)
    targets_tensor = torch.tensor(targets_np, dtype=torch.float32)
    
    # 3. Model initialization
    model = ThermodynamicsPINN()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    print(f"Starting PINN training for {epochs} epochs...")
    model.train()
    
    for epoch in range(1, epochs + 1):
        optimizer.zero_grad()
        
        # We need to compute gradients of output w.r.t input in the custom loss,
        # so requires_grad must be True during the forward pass.
        inputs_tensor.requires_grad_(True)
        
        loss, loss_data, loss_physics = model.compute_loss(
            inputs=inputs_tensor,
            targets=targets_tensor,
            lambda_physics=lambda_physics
        )
        
        loss.backward()
        optimizer.step()
        
        if epoch == 1 or epoch % 20 == 0 or epoch == epochs:
            print(f"Epoch {epoch:03d}/{epochs:03d} | Total Loss: {loss.item():.6f} | "
                  f"Data Loss: {loss_data.item():.6f} | Physics Loss: {loss_physics.item():.6f}")
            
    # Save the trained model parameters
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    torch.save(model.state_dict(), model_save_path)
    print(f"PINN model training complete. Weights saved to: {model_save_path}")

if __name__ == "__main__":
    train_pinn_model(epochs=50)
