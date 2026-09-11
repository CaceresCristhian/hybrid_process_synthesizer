"""
Utility Operating Cost (OPEX) Engine.
Evaluates thermal and electrical utility demands from flowsheet units
and calculates annual operational expenditures.
"""

from typing import Dict, List, Any

# Standard Industrial Utility Rates (USD)
DEFAULT_UTILITY_RATES = {
    "electricity_usd_per_kwh": 0.085,
    "cooling_water_usd_per_gj": 0.354,
    "low_pressure_steam_usd_per_gj": 4.50,
    "high_pressure_steam_usd_per_gj": 10.50,
    "refrigeration_usd_per_gj": 12.50
}

class UtilityCosting:
    """Evaluates utility duties and annual operating expenditure across flowsheet units."""

    @classmethod
    def calculate_utility_opex(cls, units_list: list,
                               operating_hours_per_year: float = 8000.0,
                               rates: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Calculates utility consumption and annual costs.
        """
        active_rates = DEFAULT_UTILITY_RATES.copy()
        if rates:
            active_rates.update(rates)

        total_electricity_kw = 0.0
        total_cooling_duty_kw = 0.0
        total_heating_duty_kw = 0.0
        total_refrig_duty_kw = 0.0

        unit_utility_details = []

        for unit in units_list:
            u_id = getattr(unit, "unit_id", "Unknown")
            u_name = getattr(unit, "name", u_id)
            w_watts = getattr(unit, "work_input", 0.0)
            q_watts = getattr(unit, "heat_duty", 0.0)

            # 1. Electrical Power
            power_kw = max(0.0, w_watts / 1000.0)
            elec_annual_kwh = power_kw * operating_hours_per_year
            elec_annual_cost = elec_annual_kwh * active_rates["electricity_usd_per_kwh"]

            # 2. Thermal Duties
            heat_kw = max(0.0, q_watts / 1000.0)
            cool_kw = max(0.0, -q_watts / 1000.0)

            # Check operating temperatures to discern steam level / refrigeration
            t_out = unit.outlets[0].T if (unit.outlets and unit.outlets[0].T) else 350.0

            steam_annual_cost = 0.0
            cooling_annual_cost = 0.0

            if heat_kw > 0:
                gj_yr = heat_kw * 3600.0 * operating_hours_per_year / 1.0e6
                rate = active_rates["high_pressure_steam_usd_per_gj"] if t_out > 473.15 else active_rates["low_pressure_steam_usd_per_gj"]
                steam_annual_cost = gj_yr * rate
                total_heating_duty_kw += heat_kw

            if cool_kw > 0:
                gj_yr = cool_kw * 3600.0 * operating_hours_per_year / 1.0e6
                if t_out < 288.15: # < 15 C requires chiller
                    cooling_annual_cost = gj_yr * active_rates["refrigeration_usd_per_gj"]
                    total_refrig_duty_kw += cool_kw
                else:
                    cooling_annual_cost = gj_yr * active_rates["cooling_water_usd_per_gj"]
                    total_cooling_duty_kw += cool_kw

            total_electricity_kw += power_kw
            unit_total_annual = elec_annual_cost + steam_annual_cost + cooling_annual_cost

            if power_kw > 0 or heat_kw > 0 or cool_kw > 0:
                unit_utility_details.append({
                    "unit_id": u_id,
                    "unit_name": u_name,
                    "power_kw": round(power_kw, 2),
                    "heating_duty_kw": round(heat_kw, 2),
                    "cooling_duty_kw": round(cool_kw, 2),
                    "electricity_cost_yr": round(elec_annual_cost, 2),
                    "heating_cost_yr": round(steam_annual_cost, 2),
                    "cooling_cost_yr": round(cooling_annual_cost, 2),
                    "total_utility_cost_yr": round(unit_total_annual, 2)
                })

        # Totals
        annual_elec_cost = (total_electricity_kw * operating_hours_per_year) * active_rates["electricity_usd_per_kwh"]
        annual_steam_gj = total_heating_duty_kw * 3600.0 * operating_hours_per_year / 1.0e6
        annual_steam_cost = annual_steam_gj * active_rates["low_pressure_steam_usd_per_gj"]
        annual_cooling_gj = total_cooling_duty_kw * 3600.0 * operating_hours_per_year / 1.0e6
        annual_cooling_cost = annual_cooling_gj * active_rates["cooling_water_usd_per_gj"]
        annual_refrig_gj = total_refrig_duty_kw * 3600.0 * operating_hours_per_year / 1.0e6
        annual_refrig_cost = annual_refrig_gj * active_rates["refrigeration_usd_per_gj"]

        total_annual_utility_opex = annual_elec_cost + annual_steam_cost + annual_cooling_cost + annual_refrig_cost

        return {
            "total_electricity_kW": round(total_electricity_kw, 2),
            "total_heating_duty_kW": round(total_heating_duty_kw, 2),
            "total_cooling_duty_kW": round(total_cooling_duty_kw, 2),
            "total_refrigeration_duty_kW": round(total_refrig_duty_kw, 2),
            "annual_electricity_cost_usd": round(annual_elec_cost, 2),
            "annual_steam_cost_usd": round(annual_steam_cost, 2),
            "annual_cooling_water_cost_usd": round(annual_cooling_cost, 2),
            "annual_refrigeration_cost_usd": round(annual_refrig_cost, 2),
            "total_annual_utility_opex_usd": round(total_annual_utility_opex, 2),
            "operating_hours_per_year": operating_hours_per_year,
            "unit_breakdown": unit_utility_details
        }
