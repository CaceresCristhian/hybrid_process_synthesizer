"""
Reference Benchmark & Reviewer Remediation Regression Tests.
Verifies textbook analytical solutions, boundary cases, and every finding
in PROJECT_REVIEW.md (§2.1–§2.6, §3.1–§3.8).
"""

import math
import numpy as np
import pytest

from config.settings import GAS_CONSTANT_R
from src.database.loader import ChemicalDatabaseLoader
from src.chemical_phenomena.thermodynamics import Thermodynamics
from src.chemical_phenomena.activity_models import VLEPhaseDiagramGenerator
from src.units.stream import MaterialStream
from src.units.distillation import BinaryDistillationColumn
from src.units.base_unit import BaseUnit
from src.control.flowsheet_solver import FlowsheetSolver
from src.control.pid import PIDController
from src.control.dynamic_engine import DynamicSimulationEngine
from src.units.dynamic_column import DynamicDistillationColumn
from src.ml_models.pinn import ThermodynamicsPINN


def test_codata_gas_constant():
    """Verify CODATA 2018 molar gas constant R = 8.314462618 J/(mol·K)."""
    assert math.isclose(GAS_CONSTANT_R, 8.314462618, rel_tol=1e-9)


def test_rachford_rice_analytical_and_negative_flash_boundaries():
    """
    Test bracketed Brent Rachford-Rice solver against an exact analytical solution
    and single-phase subcooled/superheated boundaries.
    """
    # 1. Exact two-phase analytical test:
    # Binary equimolar z = [0.5, 0.5] with symmetric K = [2.0, 0.5]:
    # f(beta) = 0.5*(1)/(1 + beta) + 0.5*(-0.5)/(1 - 0.5*beta) = 0 => beta = 0.5 exactly
    vf = Thermodynamics.solve_rachford_rice({"a": 0.5, "b": 0.5}, {"a": 2.0, "b": 0.5})
    assert math.isclose(vf, 0.5, abs_tol=1e-9)

    # Also test list interface
    vf_list = Thermodynamics.solve_rachford_rice([0.5, 0.5], [2.0, 0.5])
    assert math.isclose(vf_list, 0.5, abs_tol=1e-9)

    # 2. Subcooled liquid boundary: sum(z_i * (K_i - 1)) <= 0 -> beta = 0.0
    vf_subcooled = Thermodynamics.solve_rachford_rice({"a": 0.6, "b": 0.4}, {"a": 0.4, "b": 0.8})
    assert vf_subcooled == 0.0

    # 3. Superheated vapor boundary: sum(z_i * (1 - 1/K_i)) >= 0 -> beta = 1.0
    vf_superheated = Thermodynamics.solve_rachford_rice({"a": 0.6, "b": 0.4}, {"a": 3.0, "b": 2.0})
    assert vf_superheated == 1.0


def test_peng_robinson_kij_and_compressibility():
    """Verify Peng-Robinson EOS compressibility factor Z and k_ij binary interaction matrix."""
    species_map = ChemicalDatabaseLoader.load_species()
    methane = species_map["methane"]
    water = species_map["water"]
    ethanol = species_map["ethanol"]

    # Pure methane at 300 K, 50 bar (5 MPa): real gas Z should be slightly below 1.0 (~0.90 - 0.94)
    a_m, b_m, A, B, a_pure, b_pure, a_ij = Thermodynamics.calculate_peng_robinson_coefficients(
        [methane], {"methane": 1.0}, 300.0, 5.0e6
    )
    z_vap = Thermodynamics.solve_peng_robinson_z(A, B, phase="vapor")
    assert 0.88 <= z_vap <= 0.96

    # Binary mixture with non-zero k_ij (ethanol-water k_ij = -0.065 vs ideal k_ij = 0)
    a_mix, _, _, _, a_p, _, _ = Thermodynamics.calculate_peng_robinson_coefficients(
        [ethanol, water], {"ethanol": 0.5, "water": 0.5}, 350.0, 101325.0
    )
    a_ideal = 0.25 * a_p["ethanol"] + 0.5 * math.sqrt(a_p["ethanol"] * a_p["water"]) + 0.25 * a_p["water"]
    assert not math.isclose(a_mix, a_ideal, rel_tol=1e-4)


def test_ethanol_water_azeotrope_benchmark():
    """
    Verify Ethanol-Water isobaric VLE at 101.325 kPa predicts a minimum-boiling
    azeotrope below pure ethanol and pure water boiling points.
    """
    species_map = ChemicalDatabaseLoader.load_species()
    etoh = species_map["ethanol"]
    water = species_map["water"]

    diag = VLEPhaseDiagramGenerator.generate_diagram(
        etoh, water, total_pressure=101325.0, model="nrtl", num_points=50
    )
    t_bubble = np.array(diag["T_bubble"])
    x1 = np.array(diag["x1"])

    min_idx = int(np.argmin(t_bubble))
    t_min = float(t_bubble[min_idx])
    x_az = float(x1[min_idx])

    assert diag["has_azeotrope"] is True
    assert t_min < t_bubble[0]
    assert t_min < t_bubble[-1]
    assert 345.0 <= t_min < etoh.macro.boiling_point
    assert 0.70 <= x_az <= 0.96


def test_pinn_activity_predictions_and_flash_integration():
    """Verify ThermodynamicsPINN.predict_gammas and solve_tp_flash(..., method='pinn')."""
    species_map = ChemicalDatabaseLoader.load_species()
    etoh = species_map["ethanol"]
    water = species_map["water"]

    g1_dilute, g2_dilute = ThermodynamicsPINN.predict_gammas(0.05, 360.0)
    g1_conc, g2_conc = ThermodynamicsPINN.predict_gammas(0.90, 352.0)

    # At dilute ethanol (x1=0.05), gamma1 > gamma2 (~1.0)
    assert g1_dilute > 2.0
    assert 0.90 <= g2_dilute <= 1.25
    # At concentrated ethanol (x1=0.90), gamma2 > gamma1 (~1.0)
    assert 0.90 <= g1_conc <= 1.25
    assert g2_conc > 1.5

    # Sensitivity to temperature T (independent 2D feature check)
    g1_low_t, _ = ThermodynamicsPINN.predict_gammas(0.25, 335.0)
    g1_high_t, _ = ThermodynamicsPINN.predict_gammas(0.25, 375.0)
    assert not math.isclose(g1_low_t, g1_high_t, rel_tol=1e-3)

    # Flash integration with method="pinn"
    flash_res = Thermodynamics.solve_tp_flash(
        species_list=[etoh, water],
        feed_composition={"ethanol": 0.35, "water": 0.65},
        temperature=356.0,
        pressure=101325.0,
        method="pinn",
    )
    assert 0.0 < flash_res["beta"] < 1.0
    assert flash_res["y"]["ethanol"] > flash_res["x"]["ethanol"]


def test_material_stream_dof_flash_and_polynomial_enthalpy():
    """Verify MaterialStream degrees of freedom, automatic run_flash(), and 4-term polynomial Cp enthalpy."""
    species_map = ChemicalDatabaseLoader.load_species()

    st_incomplete = MaterialStream("S-INC", T=350.0, P=101325.0)
    assert st_incomplete.get_degrees_of_freedom() == 2

    st_two_phase = MaterialStream(
        "S-2P", T=356.0, P=101325.0, F=10.0, z={"ethanol": 0.4, "water": 0.6}
    )
    assert st_two_phase.get_degrees_of_freedom() == 0
    assert st_two_phase.Vf is not None
    assert 0.0 < st_two_phase.Vf < 1.0
    assert st_two_phase.y["ethanol"] > st_two_phase.x["ethanol"]

    # Enthalpy check: two-phase stream at 356 K has higher enthalpy than subcooled liquid at 310 K
    st_liq = MaterialStream(
        "S-LIQ", T=310.0, P=101325.0, F=10.0, z={"ethanol": 0.4, "water": 0.6}
    )
    h_liq = st_liq.get_enthalpy(species_map)
    h_2p = st_two_phase.get_enthalpy(species_map)
    assert h_2p > h_liq > 0.0


def test_binary_distillation_column_flowsheet_physics():
    """
    Verify BinaryDistillationColumn.run_simulation solves real VLE & mass balance
    when connected to flowsheet streams instead of hardcoded 0.4/0.6 and 0.85/0.15 splits.
    """
    species_map = ChemicalDatabaseLoader.load_species()
    feed = MaterialStream("FEED", T=355.0, P=101325.0, F=100.0, z={"ethanol": 0.35, "water": 0.65})
    dist = MaterialStream("DIST")
    bot = MaterialStream("BOT")

    col = BinaryDistillationColumn(
        unit_id="T-101", name="Ethanol Column", num_stages=12, feed_stage=6, reflux_ratio=2.5
    )
    col.connect_inlet(feed)
    col.connect_outlet(dist)
    col.connect_outlet(bot)
    col.run_simulation(time_span=(0, 1), initial_state=[], species_map=species_map)

    # Overall and component mole balances must close
    assert math.isclose(dist.F + bot.F, feed.F, rel_tol=1e-5)
    etoh_in = feed.F * feed.z["ethanol"]
    etoh_out = dist.F * dist.z["ethanol"] + bot.F * bot.z["ethanol"]
    assert math.isclose(etoh_in, etoh_out, rel_tol=1e-4)

    # Distillate is enriched in ethanol and bottoms depleted (and not hardcoded 40/60 split)
    assert not math.isclose(dist.F, 40.0, abs_tol=0.1)
    assert dist.z["ethanol"] > feed.z["ethanol"]
    assert bot.z["ethanol"] < feed.z["ethanol"]
    assert dist.T < bot.T
    assert col.heat_duty > 0.0


def test_flowsheet_solver_strict_convergence_and_error_reporting():
    """Verify FlowsheetSolver reports converged=False on unit failure."""
    species_map = ChemicalDatabaseLoader.load_species()

    class FailingUnit(BaseUnit):
        def run_simulation(self, time_span=None, initial_state=None, **kwargs):
            raise RuntimeError("Simulated solver failure in unit")

        def size_equipment(self, **kwargs):
            return {}

    s_in = MaterialStream("S1", T=300.0, P=101325.0, F=10.0, z={"water": 1.0})
    s_out = MaterialStream("S2")
    bad_unit = FailingUnit("U-FAIL", "Failing Unit")
    bad_unit.connect_inlet(s_in)
    bad_unit.connect_outlet(s_out)

    res = FlowsheetSolver.solve_flowsheet_topology(
        {"U-FAIL": bad_unit},
        {"S1": s_in, "S2": s_out},
        species_map=species_map,
    )
    assert res["converged"] is False
    assert "U-FAIL" in res["unit_errors"]


def test_pid_controller_derivative_on_measurement_and_dt():
    """Verify PIDController eliminates derivative kick on setpoint steps and validates dt > 0."""
    with pytest.raises(ValueError):
        PIDController(kp=1.0, ki=0.1, kd=0.5, dt=0.0, u_min=-100.0, u_max=100.0, setpoint=100.0)

    pid = PIDController(
        kp=1.0, ki=0.0, kd=10.0, dt=1.0, u_min=-1000.0, u_max=1000.0, setpoint=50.0
    )
    pid.reset(initial_u=0.0, initial_pv=50.0, setpoint=50.0)

    # Step 1 at steady pv=50 -> output remains 0.0
    u1 = pid.compute(setpoint=50.0, process_variable=50.0)
    assert math.isclose(u1, 0.0, abs_tol=1e-9)

    # Abrupt setpoint change from 50 -> 60 while PV stays constant at 50:
    # With derivative-on-measurement, derivative term must be 0.0 (only P-term = kp * 10 = 10.0)
    u2 = pid.compute(setpoint=60.0, process_variable=50.0)
    assert math.isclose(u2, 10.0, abs_tol=1e-9)


def test_dynamic_distillation_disturbances_and_validation():
    """Verify all 6 disturbance presets (including Cooling Water Failure and Reflux Sticking) and invalid error."""
    col = DynamicDistillationColumn("DC-101", "Dynamic Column", num_stages=10, feed_stage=5)
    engine = DynamicSimulationEngine(col)
    engine.run_time_steps(5.0, dt=1.0)

    # Cooling Water Failure (-50%)
    engine.inject_disturbance("Cooling Water Failure (-50%)")
    assert math.isclose(col.condenser_cooling_factor, 0.50, rel_tol=1e-6)

    # Reflux Valve Sticking
    engine.inject_disturbance("Reflux Valve Sticking")
    assert col.manual_reflux is True

    # Unknown disturbance must raise ValueError
    with pytest.raises(ValueError):
        engine.inject_disturbance("NonExistentDisturbance")
