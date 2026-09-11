"""
Turton & Guthrie Bare Module Cost correlations and parameters.
Based on 'Analysis, Synthesis, and Design of Chemical Processes' (Turton et al.).
Provides purchased equipment cost regressions, bare module factors,
material correction factors (F_M), and ASME pressure design factors (F_P).
"""

import numpy as np
from typing import Dict, Tuple, Optional

# Chemical Engineering Plant Cost Index (CEPCI) benchmarks
BASE_CEPCI = 397.0    # Turton 2001 equipment correlation baseline
DEFAULT_CEPCI = 825.0 # Modern 2024-2026 industrial benchmark

# Purchased Equipment Cost Correlation Coefficients (Turton Table A.1, CEPCI = 397)
# log10(Cp0) = K1 + K2 * log10(A) + K3 * (log10(A))^2
# Bare Module Factor: C_BM = Cp * (B1 + B2 * F_M * F_P)
EQUIPMENT_COST_DATA = {
    "heat_exchanger_fixed_tubesheet": {
        "K1": 4.3247, "K2": -0.3030, "K3": 0.1634,
        "A_min": 10.0, "A_max": 1000.0, "unit": "m2",
        "B1": 1.63, "B2": 1.66, "category": "heat_exchangers"
    },
    "heat_exchanger_floating_head": {
        "K1": 4.8306, "K2": -0.0807, "K3": 0.0573,
        "A_min": 10.0, "A_max": 1000.0, "unit": "m2",
        "B1": 1.63, "B2": 1.66, "category": "heat_exchangers"
    },
    "pump_centrifugal": {
        "K1": 3.3892, "K2": 0.0536, "K3": 0.1538,
        "A_min": 1.0, "A_max": 300.0, "unit": "kW",
        "B1": 1.89, "B2": 1.35, "category": "pumps"
    },
    "compressor_centrifugal": {
        "K1": 2.2897, "K2": 1.3604, "K3": -0.1027,
        "A_min": 10.0, "A_max": 3000.0, "unit": "kW",
        "B1": 1.00, "B2": 1.15, "category": "compressors"
    },
    "expander_turbine": {
        "K1": 2.7051, "K2": 0.7456, "K3": 0.0475,
        "A_min": 10.0, "A_max": 3000.0, "unit": "kW",
        "B1": 1.00, "B2": 1.15, "category": "turbines"
    },
    "vessel_vertical": {
        "K1": 3.4974, "K2": 0.4485, "K3": 0.1074,
        "A_min": 0.3, "A_max": 520.0, "unit": "m3",
        "B1": 2.25, "B2": 1.82, "category": "vessels"
    },
    "vessel_horizontal": {
        "K1": 3.5565, "K2": 0.3776, "K3": 0.0905,
        "A_min": 0.1, "A_max": 628.0, "unit": "m3",
        "B1": 1.49, "B2": 1.52, "category": "vessels"
    },
    "reactor_jacketed": {
        "K1": 4.1052, "K2": 0.5320, "K3": -0.0005,
        "A_min": 0.1, "A_max": 35.0, "unit": "m3",
        "B1": 2.25, "B2": 1.82, "category": "reactors"
    },
    "tray_sieve": {
        "K1": 2.9949, "K2": 0.4465, "K3": 0.3961,
        "A_min": 0.07, "A_max": 12.3, "unit": "m2",
        "B1": 0.0, "B2": 1.0, "category": "trays"
    },
    "filter_centrifuge": {
        "K1": 4.6975, "K2": -0.1984, "K3": 0.1610,
        "A_min": 1.0, "A_max": 50.0, "unit": "m2",
        "B1": 1.65, "B2": 1.35, "category": "filters"
    }
}

# Material Factors (F_M) by equipment category
MATERIAL_FACTORS = {
    "Carbon Steel": {
        "heat_exchangers": 1.0,
        "vessels": 1.0,
        "reactors": 1.0,
        "pumps": 1.0,
        "compressors": 1.0,
        "turbines": 1.0,
        "trays": 1.0,
        "filters": 1.0,
        "general": 1.0
    },
    "Stainless Steel 316": {
        "heat_exchangers": 2.70,
        "vessels": 3.10,
        "reactors": 3.10,
        "pumps": 2.40,
        "compressors": 2.20,
        "turbines": 2.00,
        "trays": 2.50,
        "filters": 2.30,
        "general": 2.60
    },
    "Titanium": {
        "heat_exchangers": 7.70,
        "vessels": 7.70,
        "reactors": 7.70,
        "pumps": 6.50,
        "compressors": 5.00,
        "turbines": 5.00,
        "trays": 5.50,
        "filters": 6.00,
        "general": 6.50
    },
    "Hastelloy C-276": {
        "heat_exchangers": 4.50,
        "vessels": 4.80,
        "reactors": 4.80,
        "pumps": 4.20,
        "compressors": 3.80,
        "turbines": 3.50,
        "trays": 4.00,
        "filters": 4.20,
        "general": 4.40
    },
    "Monel": {
        "heat_exchangers": 3.40,
        "vessels": 3.60,
        "reactors": 3.60,
        "pumps": 3.20,
        "compressors": 3.00,
        "turbines": 2.80,
        "trays": 3.00,
        "filters": 3.20,
        "general": 3.30
    }
}


class CostCorrelations:
    """Mathematical calculations for purchased and bare module equipment costing."""

    @classmethod
    def calculate_cp0(cls, equip_type: str, capacity: float) -> float:
        """
        Calculates base purchased equipment cost Cp0 (USD at CEPCI=397, Carbon Steel, 1 atm).
        log10(Cp0) = K1 + K2*log10(A) + K3*(log10(A))^2
        """
        if equip_type not in EQUIPMENT_COST_DATA:
            raise KeyError(f"Unknown equipment type '{equip_type}'. Available: {list(EQUIPMENT_COST_DATA.keys())}")

        data = EQUIPMENT_COST_DATA[equip_type]
        # Safeguard capacity bounds to prevent unphysical extrapolation
        cap = max(data["A_min"] * 0.2, min(data["A_max"] * 5.0, capacity))
        log_a = np.log10(cap)

        log_cp0 = data["K1"] + data["K2"] * log_a + data["K3"] * (log_a ** 2)
        return float(10.0 ** log_cp0)

    @classmethod
    def calculate_pressure_factor(cls, equip_type: str, design_pressure_pa: float,
                                  diameter_m: Optional[float] = None) -> float:
        """
        Calculates pressure factor F_P based on operating/design pressure.
        Uses ASME Section VIII shell wall thickness for pressure vessels/columns/reactors,
        and Turton empirical pressure regressions for heat exchangers and pumps.
        """
        p_barg = max(0.0, (design_pressure_pa - 101325.0) / 100000.0)

        # Baseline: if gauge pressure is <= 5 bar, pressure factor is unity
        if p_barg <= 5.0:
            return 1.0

        cat = EQUIPMENT_COST_DATA.get(equip_type, {}).get("category", "general")

        if cat == "heat_exchangers":
            # Turton Eq: log10(F_P) = 0.03881 - 0.11272*log10(P) + 0.08183*(log10(P))^2
            log_p = np.log10(p_barg)
            log_fp = 0.03881 - 0.11272 * log_p + 0.08183 * (log_p ** 2)
            return float(max(1.0, 10.0 ** log_fp))

        elif cat == "pumps":
            if p_barg <= 10.0:
                return 1.0
            log_p = np.log10(p_barg)
            log_fp = -0.3935 + 0.3957 * log_p - 0.00226 * (log_p ** 2)
            return float(max(1.0, 10.0 ** log_fp))

        elif cat in ["vessels", "reactors"]:
            # ASME Section VIII Division 1 Pressure Factor:
            # F_P = ( (P+1)*D / (2 * [S*E - 0.6*(P+1)]) ) / t_min + 1
            # Where t_min = 6.3 mm = 0.0063 m
            d = diameter_m if (diameter_m and diameter_m > 0) else 1.0
            s_allowable = 115.0e6 # Pa (typical allowable stress)
            joint_eff = 0.85
            p_des = design_pressure_pa
            denom = (s_allowable * joint_eff) - (0.6 * p_des)
            if denom > 0:
                t_shell = (p_des * (d / 2.0)) / denom + 0.0015 # 1.5mm corrosion allowance
                t_min = 0.0063
                fp = max(1.0, t_shell / t_min)
                return float(min(15.0, fp))
            return 2.5

        elif cat in ["compressors", "turbines"]:
            # Compressors scale mildly with discharge pressure
            return float(max(1.0, 1.0 + 0.03 * (p_barg - 5.0)))

        return 1.0

    @classmethod
    def get_material_factor(cls, equip_type: str, material: str = "Carbon Steel") -> float:
        """Retrieves material factor F_M based on equipment category and material."""
        mat_dict = MATERIAL_FACTORS.get(material, MATERIAL_FACTORS["Carbon Steel"])
        cat = EQUIPMENT_COST_DATA.get(equip_type, {}).get("category", "general")
        return float(mat_dict.get(cat, mat_dict.get("general", 1.0)))

    @classmethod
    def calculate_bare_module_cost(cls, equip_type: str, capacity: float,
                                   design_pressure_pa: float = 101325.0,
                                   material: str = "Carbon Steel",
                                   cepci: float = DEFAULT_CEPCI,
                                   diameter_m: Optional[float] = None) -> Dict[str, float]:
        """
        Full bare module cost calculation for an equipment item.
        Returns:
            Cp0: Base purchased cost (CEPCI=397, CS)
            Cp: Inflated purchased cost at specified CEPCI
            F_P: Pressure factor
            F_M: Material factor
            C_BM: Bare module cost (USD)
        """
        if equip_type not in EQUIPMENT_COST_DATA:
            raise KeyError(f"Equipment '{equip_type}' not in costing database.")

        data = EQUIPMENT_COST_DATA[equip_type]
        cp0 = cls.calculate_cp0(equip_type, capacity)
        cp = cp0 * (cepci / BASE_CEPCI)

        fp = cls.calculate_pressure_factor(equip_type, design_pressure_pa, diameter_m)
        fm = cls.get_material_factor(equip_type, material)

        b1 = data["B1"]
        b2 = data["B2"]

        c_bm = cp * (b1 + b2 * fm * fp)

        return {
            "Cp0": round(cp0, 2),
            "Cp": round(cp, 2),
            "F_P": round(fp, 3),
            "F_M": round(fm, 2),
            "B1": b1,
            "B2": b2,
            "C_BM": round(c_bm, 2),
            "capacity": round(capacity, 2),
            "capacity_unit": data["unit"],
            "material": material,
            "CEPCI": cepci
        }
