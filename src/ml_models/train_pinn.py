import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch
import torch.optim as optim
import pandas as pd
import numpy as np
from src.ml_models.pinn import ThermodynamicsPINN, DEFAULT_MODEL_PATH
from src.ml_models.dataset_builder import VLEDatasetBuilder, DEFAULT_DATASET_PATH


def train_pinn_model(
    epochs: int = 200,
    lr: float = 0.01,
    lambda_physics: float = 0.5,
    dataset_path: str | Path | None = None,
    model_save_path: str | Path | None = None,
    regenerate_dataset: bool = False,
) -> dict:
    """Loads VLE dataset, trains ThermodynamicsPINN with an 80/20 train/val split, and saves weights."""

    ds_path = Path(dataset_path) if dataset_path is not None else DEFAULT_DATASET_PATH
    save_path = Path(model_save_path) if model_save_path is not None else DEFAULT_MODEL_PATH

    if regenerate_dataset or not ds_path.exists():
        print("Generating VLE dataset...")
        VLEDatasetBuilder.save_dataset(ds_path, num_points=500)

    df = pd.read_csv(ds_path)

    # Extract and scale features: x1 in [0, 1], T scaled via ThermodynamicsPINN.scale_temperature
    x1 = df["x1"].values
    temp = df["T"].values
    t_scaled = ThermodynamicsPINN.scale_temperature(temp)

    inputs_np = np.column_stack((x1, t_scaled))
    targets_np = np.column_stack((df["ln_gamma1"].values, df["ln_gamma2"].values))

    # Deterministic 80/20 train/validation split
    rng = np.random.default_rng(42)
    indices = rng.permutation(len(inputs_np))
    split_idx = int(0.8 * len(inputs_np))
    train_idx, val_idx = indices[:split_idx], indices[split_idx:]

    train_inputs = torch.tensor(inputs_np[train_idx], dtype=torch.float32)
    train_targets = torch.tensor(targets_np[train_idx], dtype=torch.float32)
    val_inputs = torch.tensor(inputs_np[val_idx], dtype=torch.float32)
    val_targets = torch.tensor(targets_np[val_idx], dtype=torch.float32)

    torch.manual_seed(42)
    model = ThermodynamicsPINN()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    print(f"Starting PINN training for {epochs} epochs ({len(train_idx)} train / {len(val_idx)} val)...")
    model.train()

    for epoch in range(1, epochs + 1):
        optimizer.zero_grad()
        train_inputs.requires_grad_(True)

        loss, loss_data, loss_physics = model.compute_loss(
            inputs=train_inputs,
            targets=train_targets,
            lambda_physics=lambda_physics,
        )

        loss.backward()
        optimizer.step()

        if epoch == 1 or epoch % 20 == 0 or epoch == epochs:
            model.eval()
            val_loss, val_data, val_phys = model.compute_loss(
                inputs=val_inputs.detach().clone(),
                targets=val_targets,
                lambda_physics=lambda_physics,
            )
            model.train()
            print(
                f"Epoch {epoch:03d}/{epochs:03d} | Train Total: {loss.item():.6f} "
                f"(Data: {loss_data.item():.6f}, GD: {loss_physics.item():.6f}) | "
                f"Val MSE: {val_data.item():.6f}"
            )

    model.eval()
    _, val_mse, val_gd = model.compute_loss(
        inputs=val_inputs.detach().clone(),
        targets=val_targets,
        lambda_physics=lambda_physics,
    )
    val_rmse = float(np.sqrt(val_mse.item()))

    save_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), save_path)
    # Reset cached model so subsequent predict_gammas calls reload the updated weights
    ThermodynamicsPINN._cached_model = None
    print(f"PINN training complete. Held-out Val RMSE: {val_rmse:.4f}. Saved to: {save_path}")

    return {
        "train_loss": float(loss.item()),
        "val_mse": float(val_mse.item()),
        "val_rmse": val_rmse,
        "val_gibbs_duhem_mse": float(val_gd.item()),
        "model_path": str(save_path),
    }


if __name__ == "__main__":
    train_pinn_model(epochs=200, regenerate_dataset=True)
