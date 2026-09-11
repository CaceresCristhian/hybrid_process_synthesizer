"""
Techno-Economic Assessment & Capital Costing Module.
Implements Turton & Guthrie bare module costing, ASME pressure factors,
materials of construction multipliers, utility OPEX, and project profitability.
"""

from src.economics.cost_correlations import (
    CostCorrelations,
    BASE_CEPCI,
    DEFAULT_CEPCI,
    EQUIPMENT_COST_DATA,
    MATERIAL_FACTORS
)
from src.economics.equipment_costing import EquipmentCosting
from src.economics.capital_costing import CapitalCosting
from src.economics.utility_costing import UtilityCosting, DEFAULT_UTILITY_RATES
from src.economics.profitability import EconomicAnalyzer, DEFAULT_CHEMICAL_PRICES_USD_KG
from src.economics.pinch_analysis import PinchAnalyzer, ThermalStream
from src.economics.lca_engine import (
    LCAAnalyzer,
    REGIONAL_GRID_FACTORS,
    STEAM_FUEL_FACTORS,
    FEEDSTOCK_EMBODIED_FACTORS
)

__all__ = [
    "CostCorrelations",
    "BASE_CEPCI",
    "DEFAULT_CEPCI",
    "EQUIPMENT_COST_DATA",
    "MATERIAL_FACTORS",
    "EquipmentCosting",
    "CapitalCosting",
    "UtilityCosting",
    "DEFAULT_UTILITY_RATES",
    "EconomicAnalyzer",
    "DEFAULT_CHEMICAL_PRICES_USD_KG",
    "PinchAnalyzer",
    "ThermalStream",
    "LCAAnalyzer",
    "REGIONAL_GRID_FACTORS",
    "STEAM_FUEL_FACTORS",
    "FEEDSTOCK_EMBODIED_FACTORS"
]
