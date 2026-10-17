import os
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "vle_dataset.csv"


class VLEDatasetBuilder:
    """Generates binary Ethanol-Water VLE datasets with temperature-dependent non-ideal activity coefficients."""

    # Isobaric 101.325 kPa Ethanol(1)-Water(2) experimental benchmark points (DECHEMA / Gmehling & Onken)
    EXPERIMENTAL_BENCHMARKS = [
        # (x1, T [K], gamma1_exp, gamma2_exp)
        (0.0190, 369.05, 4.185, 1.002),
        (0.0721, 362.15, 3.235, 1.018),
        (0.1238, 358.45, 2.585, 1.046),
        (0.2337, 355.45, 1.832, 1.125),
        (0.3273, 354.15, 1.498, 1.215),
        (0.5079, 352.95, 1.189, 1.448),
        (0.6763, 352.05, 1.062, 1.738),
        (0.8943, 351.30, 1.006, 2.245),  # Azeotrope (~89.4 mol% EtOH, 351.3 K)
        (0.9500, 351.35, 1.001, 2.410),
    ]

    @staticmethod
    def generate_margules_vle_data(num_points: int = 500, noise_std: float = 0.015) -> pd.DataFrame:
        """
        Generates binary VLE data across independent (x1, T) domain using a temperature-dependent
        two-suffix Margules model anchored to Ethanol (1) - Water (2) VLE:
            A12(T) = A12_ref * (353.15 / T)
            A21(T) = A21_ref * (353.15 / T)
            ln(gamma1) = x2^2 * [A12(T) + 2*(A21(T) - A12(T))*x1]
            ln(gamma2) = x1^2 * [A21(T) + 2*(A12(T) - A21(T))*x2]
        Note: At any fixed temperature T, this exact functional form satisfies the isothermal
        Gibbs-Duhem identity x1*(d ln_gamma1 / dx1)_T + x2*(d ln_gamma2 / dx1)_T = 0.
        """
        rng = np.random.default_rng(42)

        n_bench = len(VLEDatasetBuilder.EXPERIMENTAL_BENCHMARKS)
        n_synth = max(num_points - n_bench, 10)

        # Sample x1 and T independently across the full liquid composition and operating T range
        x1_synth = rng.uniform(0.01, 0.99, n_synth)
        x2_synth = 1.0 - x1_synth
        temp_synth = rng.uniform(330.0, 380.0, n_synth)

        # Temperature-dependent Margules parameters (anchored at 353.15 K)
        a12_ref = 1.60
        a21_ref = 0.79
        a12_t = a12_ref * (353.15 / temp_synth)
        a21_t = a21_ref * (353.15 / temp_synth)

        ln_gamma1_clean = (x2_synth ** 2) * (a12_t + 2.0 * (a21_t - a12_t) * x1_synth)
        ln_gamma2_clean = (x1_synth ** 2) * (a21_t + 2.0 * (a12_t - a21_t) * x2_synth)

        ln_gamma1_noisy = ln_gamma1_clean + rng.normal(0.0, noise_std, n_synth)
        ln_gamma2_noisy = ln_gamma2_clean + rng.normal(0.0, noise_std, n_synth)

        # Combine with experimental DECHEMA benchmark points
        bench_arr = np.array(VLEDatasetBuilder.EXPERIMENTAL_BENCHMARKS, dtype=float)
        x1_bench = bench_arr[:, 0]
        x2_bench = 1.0 - x1_bench
        t_bench = bench_arr[:, 1]
        g1_bench = bench_arr[:, 2]
        g2_bench = bench_arr[:, 3]
        ln_g1_bench = np.log(g1_bench)
        ln_g2_bench = np.log(g2_bench)

        x1 = np.concatenate([x1_synth, x1_bench])
        x2 = np.concatenate([x2_synth, x2_bench])
        temperature = np.concatenate([temp_synth, t_bench])
        ln_gamma1 = np.concatenate([ln_gamma1_noisy, ln_g1_bench])
        ln_gamma2 = np.concatenate([ln_gamma2_noisy, ln_g2_bench])

        gamma1_experimental = np.exp(ln_gamma1)
        gamma2_experimental = np.exp(ln_gamma2)

        df = pd.DataFrame({
            "x1": x1,
            "x2": x2,
            "T": temperature,
            "ln_gamma1": ln_gamma1,
            "ln_gamma2": ln_gamma2,
            "gamma1": gamma1_experimental,
            "gamma2": gamma2_experimental,
        })
        return df

    @classmethod
    def save_dataset(cls, target_path: str | Path | None = None, num_points: int = 500) -> Path:
        """Saves generated dataset to a CSV file using portable paths."""
        path = Path(target_path) if target_path is not None else DEFAULT_DATASET_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        df = cls.generate_margules_vle_data(num_points=num_points)
        df.to_csv(path, index=False)
        print(f"Generated and saved VLE dataset containing {len(df)} points to: {path}")
        return path


if __name__ == "__main__":
    VLEDatasetBuilder.save_dataset()
