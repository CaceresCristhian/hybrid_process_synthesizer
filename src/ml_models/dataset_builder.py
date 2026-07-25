import os
import numpy as np
import pandas as pd

class VLEDatasetBuilder:
    """Generates synthetic binary VLE datasets with non-ideal activity coefficients."""
    
    @staticmethod
    def generate_margules_vle_data(num_points: int = 500, noise_std: float = 0.02) -> pd.DataFrame:
        """
        Generates binary VLE data using Margules activity coefficient model:
        ln(gamma1) = x2^2 * [A12 + 2*(A21 - A12)*x1]
        ln(gamma2) = x1^2 * [A21 + 2*(A12 - A21)*x2]
        For Ethanol (1) - Water (2):
        A12 ~= 1.60, A21 ~= 0.79
        """
        # Set random seed for reproducibility
        np.random.seed(42)
        
        # Mole fractions of component 1
        x1 = np.random.uniform(0.01, 0.99, num_points)
        x2 = 1.0 - x1
        
        # Temperatures matching Ethanol-Water boiling range (351.5 K to 373.15 K)
        # Saturated temperature decreases as x1 (Ethanol fraction) increases
        t_pure_water = 373.15
        t_pure_ethanol = 351.5
        temperature = t_pure_water - (t_pure_water - t_pure_ethanol) * x1 + np.random.normal(0.0, 1.0, num_points)
        
        # Margules parameters
        a12 = 1.60
        a21 = 0.79
        
        # Pure Margules activity coefficients
        ln_gamma1 = (x2 ** 2) * (a12 + 2.0 * (a21 - a12) * x1)
        ln_gamma2 = (x1 ** 2) * (a21 + 2.0 * (a12 - a21) * x2)
        
        # Add experimental noise
        ln_gamma1_noisy = ln_gamma1 + np.random.normal(0.0, noise_std, num_points)
        ln_gamma2_noisy = ln_gamma2 + np.random.normal(0.0, noise_std, num_points)
        
        # Clip to avoid physical issues
        gamma1_experimental = np.exp(ln_gamma1_noisy)
        gamma2_experimental = np.exp(ln_gamma2_noisy)
        
        df = pd.DataFrame({
            "x1": x1,
            "x2": x2,
            "T": temperature,
            "ln_gamma1": ln_gamma1_noisy,
            "ln_gamma2": ln_gamma2_noisy,
            "gamma1": gamma1_experimental,
            "gamma2": gamma2_experimental
        })
        return df

    @classmethod
    def save_dataset(cls, target_path: str, num_points: int = 500):
        """Saves generated dataset to a CSV file."""
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        df = cls.generate_margules_vle_data(num_points=num_points)
        df.to_csv(target_path, index=False)
        print(f"Generated and saved VLE dataset containing {len(df)} points to: {target_path}")

if __name__ == "__main__":
    # Standard output directory in the processed data folder
    dataset_path = r"c:\Users\crist\Projects\Thesis\hybrid_process_synthesizer\data\processed\vle_dataset.csv"
    VLEDatasetBuilder.save_dataset(dataset_path)
