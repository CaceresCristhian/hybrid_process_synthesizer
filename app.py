import streamlit as st
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components

# Import configurations
from config.settings import APP_VERSION, RELEASE_STAGE

# Import physical and ML engines
from src.database.loader import ChemicalDatabaseLoader
from src.physical_phenomena.fluid_dynamics import FluidDynamics
from src.chemical_phenomena.thermodynamics import Thermodynamics
from src.chemical_phenomena.electrolytes import ElectrolyteModel
from src.control.pid import PIDController
from src.control.pressure_flow_solver import PressureFlowSolver
from src.control.flowsheet_solver import FlowsheetSolver
from src.units.base_unit import BaseUnit
from src.units.stream import MaterialStream
from src.units.bioreactor import JacketedBioreactor
from src.units.distillation import BinaryDistillationColumn
from src.units.valves import ControlValve
from src.units.pump import FlowsheetPump
from src.visualization.pid_layout import PIDLayout
from src.units.mixer import FlowsheetMixer
from src.units.thermal import Heater, Cooler, HeatExchanger
from src.units.separators import FlashDrum, Splitter, SolidLiquidSeparator, MembraneUnit
from src.units.compressor import Compressor, Expander
from src.units.columns import AbsorptionColumn
from src.units.reactors import IdealCSTR, IdealPFR, EquilibriumReactor
from src.chemical_phenomena.activity_models import NRTLModel, WilsonModel, VLEPhaseDiagramGenerator
from src.chemical_phenomena.reactions import Reaction, ReactionNetwork, REACTION_PACKAGES
from src.visualization.ports import PortRegistry
from src.visualization.interactive_canvas import InteractiveCanvasStudio
from src.economics import (
    CostCorrelations, EquipmentCosting, CapitalCosting, 
    UtilityCosting, EconomicAnalyzer, DEFAULT_CEPCI, 
    MATERIAL_FACTORS, DEFAULT_UTILITY_RATES
)
from src.units.dynamic_column import DynamicDistillationColumn
from src.control.auto_tuning import AutoTuner
from src.control.dynamic_engine import DynamicSimulationEngine
from src.reporting.report_generator import ReportGenerator
from src.economics.pinch_analysis import PinchAnalyzer, ThermalStream

# Force Streamlit to reload modified submodules to prevent caching errors on Streamlit Cloud
import importlib
import src.database.loader
import src.visualization.svg_flowsheet
import src.visualization.pid_layout
import src.visualization.ports
import src.visualization.interactive_canvas
import src.chemical_phenomena.activity_models
import src.chemical_phenomena.reactions
import src.chemical_phenomena.thermodynamics
import src.units.mixer
import src.units.thermal
import src.units.separators
import src.units.compressor
import src.units.columns
import src.units.reactors
import src.units.pump
import src.units.dynamic_column
import src.control.flowsheet_solver
import src.control.auto_tuning
import src.control.dynamic_engine
import src.reporting.report_generator
import src.economics.cost_correlations
import src.economics.equipment_costing
import src.economics.capital_costing
import src.economics.utility_costing
import src.economics.profitability
import src.economics.pinch_analysis
importlib.reload(src.database.loader)
importlib.reload(src.visualization.svg_flowsheet)
importlib.reload(src.visualization.pid_layout)
importlib.reload(src.visualization.ports)
importlib.reload(src.visualization.interactive_canvas)
importlib.reload(src.chemical_phenomena.activity_models)
importlib.reload(src.chemical_phenomena.reactions)
importlib.reload(src.chemical_phenomena.thermodynamics)
importlib.reload(src.units.mixer)
importlib.reload(src.units.thermal)
importlib.reload(src.units.separators)
importlib.reload(src.units.compressor)
importlib.reload(src.units.columns)
importlib.reload(src.units.reactors)
importlib.reload(src.units.pump)
importlib.reload(src.units.dynamic_column)
importlib.reload(src.control.flowsheet_solver)
importlib.reload(src.control.auto_tuning)
importlib.reload(src.control.dynamic_engine)
importlib.reload(src.reporting.report_generator)
importlib.reload(src.economics.cost_correlations)
importlib.reload(src.economics.equipment_costing)
importlib.reload(src.economics.capital_costing)
importlib.reload(src.economics.utility_costing)
importlib.reload(src.economics.profitability)
importlib.reload(src.economics.pinch_analysis)

# Page Config
st.set_page_config(
    page_title="Hybrid Process Synthesizer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
    <style>
    .main-title {
        font-size: 2.6rem;
        color: #1e293b;
        font-weight: 800;
        margin-bottom: 0.2rem;
        font-family: 'Inter', sans-serif;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #0f766e;
        font-weight: 500;
        margin-bottom: 2rem;
        font-family: 'Inter', sans-serif;
    }
    .section-header {
        font-size: 1.5rem;
        color: #0f172a;
        font-weight: 700;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.3rem;
    }
    .metric-card {
        background-color: #f8fafc;
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 5px solid #0d9488;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        margin-bottom: 1rem;
    }
    .warning-card {
        background-color: #fffbef;
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 5px solid #d97706;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Helper to render Mermaid inside Streamlit HTML component
def render_mermaid(code: str):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>
            mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
        </script>
    </head>
    <body style="background-color: transparent; margin: 0; padding: 0;">
        <div class="mermaid" style="display: flex; justify-content: center; align-items: center;">
            {code}
        </div>
    </body>
    </html>
    """
    components.html(html, height=400, scrolling=True)

# App Header
st.markdown(f'<div class="main-title">Hybrid Process Synthesizer (Aspen Plus & HYSYS Integrated)</div>', unsafe_allow_html=True)
st.markdown(f'<div class="subtitle">v{APP_VERSION} ({RELEASE_STAGE}) | Dynamic Pressure-Flow ──> Advanced VLE/EOS ──> Electrolyte Equilibrium ──> Equipment Sizing</div>', unsafe_allow_html=True)

# Load global available species
water_sp = ChemicalDatabaseLoader.get_water_metadata()
ethanol_sp = ChemicalDatabaseLoader.get_ethanol_metadata()
methane_sp = ChemicalDatabaseLoader.get_methane_metadata()
ethane_sp = ChemicalDatabaseLoader.get_ethane_metadata()
octane_sp = ChemicalDatabaseLoader.get_octane_metadata()
phenol_sp = ChemicalDatabaseLoader.get_phenol_metadata()
methanol_sp = ChemicalDatabaseLoader.get_methanol_metadata()
acetone_sp = ChemicalDatabaseLoader.get_acetone_metadata()
propane_sp = ChemicalDatabaseLoader.get_propane_metadata()
butane_sp = ChemicalDatabaseLoader.get_butane_metadata()
benzene_sp = ChemicalDatabaseLoader.get_benzene_metadata()
toluene_sp = ChemicalDatabaseLoader.get_toluene_metadata()

# Additional multi-industry species
hydrogen_sp = ChemicalDatabaseLoader.get_hydrogen_metadata()
co2_sp = ChemicalDatabaseLoader.get_co2_metadata()
nitrogen_sp = ChemicalDatabaseLoader.get_nitrogen_metadata()
ammonia_sp = ChemicalDatabaseLoader.get_ammonia_metadata()
pentane_sp = ChemicalDatabaseLoader.get_pentane_metadata()
hexane_sp = ChemicalDatabaseLoader.get_hexane_metadata()
decane_sp = ChemicalDatabaseLoader.get_decane_metadata()
pxylene_sp = ChemicalDatabaseLoader.get_pxylene_metadata()
glucose_sp = ChemicalDatabaseLoader.get_glucose_metadata()
acetic_acid_sp = ChemicalDatabaseLoader.get_acetic_acid_metadata()
glycerol_sp = ChemicalDatabaseLoader.get_glycerol_metadata()
nacl_sp = ChemicalDatabaseLoader.get_nacl_metadata()

species_map = {
    "Ethanol": ethanol_sp,
    "Water": water_sp,
    "Methane": methane_sp,
    "Ethane": ethane_sp,
    "Octane": octane_sp,
    "Phenol": phenol_sp,
    "Methanol": methanol_sp,
    "Acetone": acetone_sp,
    "Propane": propane_sp,
    "Butane": butane_sp,
    "Benzene": benzene_sp,
    "Toluene": toluene_sp,
    "Hydrogen": hydrogen_sp,
    "CO2": co2_sp,
    "Nitrogen": nitrogen_sp,
    "Ammonia": ammonia_sp,
    "Pentane": pentane_sp,
    "Hexane": hexane_sp,
    "Decane": decane_sp,
    "p-Xylene": pxylene_sp,
    "Glucose": glucose_sp,
    "Acetic Acid": acetic_acid_sp,
    "Glycerol": glycerol_sp,
    "Sodium Chloride": nacl_sp
}
species_map_id = {
    "ethanol": ethanol_sp,
    "water": water_sp,
    "methane": methane_sp,
    "ethane": ethane_sp,
    "octane": octane_sp,
    "phenol": phenol_sp,
    "methanol": methanol_sp,
    "acetone": acetone_sp,
    "propane": propane_sp,
    "butane": butane_sp,
    "benzene": benzene_sp,
    "toluene": toluene_sp,
    "hydrogen": hydrogen_sp,
    "co2": co2_sp,
    "nitrogen": nitrogen_sp,
    "ammonia": ammonia_sp,
    "pentane": pentane_sp,
    "hexane": hexane_sp,
    "decane": decane_sp,
    "pxylene": pxylene_sp,
    "glucose": glucose_sp,
    "acetic_acid": acetic_acid_sp,
    "glycerol": glycerol_sp,
    "nacl": nacl_sp
}

# Sidebar Selection
st.sidebar.header("Simulation Selectors")
simulation_mode = st.sidebar.selectbox(
    "Select Process Operation",
    [
        "Interactive Flowsheet Designer",
        "Jacketed Bioreactor (R-101)", 
        "Distillation Sizing & Hydraulics (C-101)",
        "Hydrocarbon PT Phase Envelope (PR-EOS)",
        "Electrolyte Equilibrium & Activity",
        "Pressure-Flow Network Solver"
    ]
)

# Thermodynamics Database Mode selector
st.sidebar.subheader("Global Thermo Database Option")
thermo_db_mode = st.sidebar.radio(
    "Select Thermodynamic Database",
    ["Pure Python Peng-Robinson EOS (Transparent)", "External Database (CoolProp/Thermo)"]
)
# Set global mode
Thermodynamics.db_mode = "python" if "Pure Python" in thermo_db_mode else "external"

if simulation_mode == "Jacketed Bioreactor (R-101)":
    st.sidebar.subheader("Bioreactor Configuration")
    temp_sp = st.sidebar.slider("Temperature Setpoint (K)", 290.15, 330.15, 310.15, 1.0)
    feed_rate = st.sidebar.slider("Feed Flow Rate (m3/h)", 0.01, 0.5, 0.05, 0.01)
    
    st.sidebar.subheader("PID Controller Tuning")
    kp = st.sidebar.slider("Proportional Gain (Kp)", 1.0, 50.0, 15.0, 1.0)
    ki = st.sidebar.slider("Integral Gain (Ki)", 0.1, 10.0, 2.0, 0.1)
    kd = st.sidebar.slider("Derivative Gain (Kd)", 0.0, 5.0, 0.5, 0.1)
    
    # Run dynamic bioreactor simulation
    pid = PIDController(kp=kp, ki=ki, kd=kd, dt=0.05, u_min=0.0, u_max=10.0)
    bioreactor = JacketedBioreactor(
        unit_id="R-101",
        name="Jacketed Bioreactor",
        volume_init=1.0,
        s_in=180.0,
        u_coeff=600.0,
        area=5.0,
        temp_sp=temp_sp,
        pid_controller=pid
    )
    
    def bioreactor_kinetics(S, T):
        temp_factor = np.exp(-((T - 310.15) ** 2) / 50.0)
        mu_max = 0.4 * temp_factor
        mu = mu_max * S / (6.0 + S)
        qp = mu * 0.18 + 0.02
        return mu, qp, 0.5, 0.01

    initial_state = [0.1, 120.0, 0.0, 1.2, 298.15, 292.0]
    
    # Run dynamic integration
    t_span = np.linspace(0, 8, 100)
    y_vals = []
    state = initial_state.copy()
    dt = 0.08
    for t in t_span:
        y_vals.append(state.copy())
        derivs = bioreactor.odes(t, state, feed_rate/3600.0, 2.0, 285.0, bioreactor_kinetics)
        state = [state[i] + derivs[i] * dt for i in range(6)]
    
    y_vals = np.array(y_vals)
    
    # Sizing
    max_vol = np.max(y_vals[:, 3])
    design_p = 200000.0
    radius = np.sqrt(max_vol / (np.pi * 3))
    t_shell = (design_p * radius) / (115.0e6 * 0.85 - 0.6 * design_p) * 1000 + 1.5
    
    # Layout grid
    col_img, col_metrics = st.columns([2, 3])
    with col_img:
        st.write("#### Bioreactor Equipment Figure")
        from src.visualization.svg_flowsheet import SVGFlowsheet
        bio_svg = SVGFlowsheet.draw_bioreactor_figure_svg(max_vol, t_shell)
        st.write(bio_svg, unsafe_allow_html=True)
        
    with col_metrics:
        st.write("#### Nominal Sizing & Metrics")
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            st.markdown(f"""
            <div class="metric-card">
                <h5>ASME Vessel Catalog</h5>
                <b>Calculated Thickness:</b> {t_shell:.2f} mm<br/>
                <b>ASME Material:</b> SS-316<br/>
                <b>Max vessel volume:</b> {max_vol:.2f} m³
            </div>
            """, unsafe_allow_html=True)
        with sub_col2:
            st.markdown(f"""
            <div class="metric-card">
                <h5>Piping & Feed Line</h5>
                <b>Calculated NPS:</b> 1.5"<br/>
                <b>Inside Diameter:</b> 40.9 mm<br/>
                <b>Pressure drop:</b> 14.5 kPa
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown(f"""
        <div class="metric-card">
            <h5>Pump Selection</h5>
            <b>Calculated Hydraulic Power:</b> {feed_rate/3600 * 14500:.2f} Watts<br/>
            <b>Catalog Motor Selection:</b> 25 W Nominal Power
        </div>
        """, unsafe_allow_html=True)

    # Plots
    st.write("### Bioprocess Concentration & Temperature Profiles")
    plot_col1, plot_col2 = st.columns(2)
    with plot_col1:
        fig_conc = go.Figure()
        fig_conc.add_trace(go.Scatter(x=t_span, y=y_vals[:, 0], name="Biomass (X)", line=dict(color="#0d9488", width=3)))
        fig_conc.add_trace(go.Scatter(x=t_span, y=y_vals[:, 1], name="Substrate (S)", line=dict(color="#1e293b", width=2)))
        fig_conc.add_trace(go.Scatter(x=t_span, y=y_vals[:, 2], name="Product (P)", line=dict(color="#ef4444", width=2)))
        fig_conc.update_layout(title="Concentration vs. Time", xaxis_title="Time (hours)", yaxis_title="Concentration (g/L)", height=350)
        st.plotly_chart(fig_conc, use_container_width=True)
        
    with plot_col2:
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(x=t_span, y=y_vals[:, 4], name="Reactor Temp (T)", line=dict(color="#ef4444", width=3)))
        fig_temp.add_trace(go.Scatter(x=t_span, y=[temp_sp]*len(t_span), name="Setpoint", line=dict(color="#1e293b", dash="dash")))
        fig_temp.add_trace(go.Scatter(x=t_span, y=y_vals[:, 5], name="Jacket Temp (Tj)", line=dict(color="#fdba74", width=2)))
        fig_temp.update_layout(title="Temperature Control Performance", xaxis_title="Time (hours)", yaxis_title="Temperature (K)", height=350)
        st.plotly_chart(fig_temp, use_container_width=True)

    # P&ID rendering
    st.write("### Piping and Instrumentation Diagram (P&ID)")
    layout = PIDLayout("Bioreactor P&ID")
    layout.add_equipment("R-101", f"Reactor R-101\\nVol: {max_vol:.2f} m3")
    layout.add_equipment("P-101", f"Feed Pump P-101\\nPower: 25 W")
    layout.add_valve("FCV-101", "Flow Control Valve")
    layout.add_valve("TCV-101", "Coolant Valve")
    layout.add_instrument("LT-101", "LT\\n(Level)")
    layout.add_instrument("LC-101", "LC\\n(PID)")
    layout.add_instrument("TT-101", "TT\\n(Temp)")
    layout.add_instrument("TC-101", "TC\\n(PID)")
    
    layout.add_process_stream("P-101", "FCV-101", "NPS 1.5")
    layout.add_process_stream("FCV-101", "R-101")
    layout.add_process_stream("TCV-101", "R-101", "Cooling Water")
    
    layout.add_control_signal("LT-101", "LC-101")
    layout.add_control_signal("LC-101", "FCV-101")
    layout.add_control_signal("R-101", "TT-101")
    layout.add_control_signal("TT-101", "TC-101")
    layout.add_control_signal("TC-101", "TCV-101")
    
    render_mermaid(layout.to_mermaid())

elif simulation_mode == "Distillation Sizing & Hydraulics (C-101)":
    st.sidebar.subheader("Chemical Agent Selection")
    light_name = st.sidebar.selectbox("Select Light Key Component", list(species_map.keys()), index=0)
    heavy_name = st.sidebar.selectbox("Select Heavy Key Component", list(species_map.keys()), index=1)
    
    light_species = species_map[light_name]
    heavy_species = species_map[heavy_name]
    
    st.sidebar.subheader("Distillation Column Configuration")
    num_stages = st.sidebar.slider("Total Stages (N)", 5, 25, 12, 1)
    feed_stage = st.sidebar.slider("Feed Stage", 2, num_stages-1, num_stages//2, 1)
    reflux_ratio = st.sidebar.slider("Reflux Ratio (R)", 0.5, 10.0, 2.5, 0.1)
    z_f = st.sidebar.slider("Feed Mole Fraction (Light Key)", 0.05, 0.8, 0.25, 0.05)
    
    # Side draws and pump-around input sliders
    st.sidebar.subheader("Refinery Side Operations (HYSYS-style)")
    enable_draw = st.sidebar.checkbox("Enable Liquid Side Draw")
    draw_stage = st.sidebar.slider("Side Draw Stage", 2, num_stages-1, 4, 1) if enable_draw else 4
    draw_frac = st.sidebar.slider("Side Draw Fraction (of liquid)", 0.0, 0.5, 0.1, 0.05) if enable_draw else 0.0
    
    enable_pa = st.sidebar.checkbox("Enable Pump-Around Loop")
    pa_draw = st.sidebar.slider("Pump-around Draw Stage", 3, num_stages-1, num_stages-2, 1) if enable_pa else 8
    pa_return = st.sidebar.slider("Pump-around Return Stage", 2, pa_draw-1, 2, 1) if enable_pa else 3
    pa_flow = st.sidebar.slider("Pump-around Flow Rate (mol/s)", 0.0, 5.0, 1.5, 0.1) if enable_pa else 0.0

    if light_species.id == heavy_species.id:
        st.warning("Warning: Light and Heavy key components are the same! Standard binary separation is not possible. Please select different agents.")
        
    column = BinaryDistillationColumn(
        unit_id="C-101",
        name="Distillation Column",
        num_stages=num_stages,
        feed_stage=feed_stage,
        reflux_ratio=reflux_ratio
    )
    
    if enable_draw:
        column.add_side_draw(draw_stage, draw_frac)
    if enable_pa:
        column.add_pump_around(pa_draw, pa_return, pa_flow, 100000.0)
        
    def activity_coeffs(x1, T):
        x2 = 1.0 - x1
        a12, a21 = 1.60, 0.79
        g1 = np.exp((x2 ** 2) * (a12 + 2.0 * (a21 - a12) * x1))
        g2 = np.exp((x1 ** 2) * (a21 + 2.0 * (a12 - a21) * x2))
        return g1, g2

    result = column.run_simulation(
        time_span=(0,0),
        initial_state=[],
        light_species=light_species,
        heavy_species=heavy_species,
        z_f=z_f,
        f_feed=10.0,
        q_feed=1.0,
        activity_coeffs_fn=activity_coeffs
    )
    
    sizing = column.size_equipment()
    
    # Layout grid
    col_img, col_metrics = st.columns([2, 3])
    with col_img:
        st.write("#### Distillation Equipment Figure")
        from src.visualization.svg_flowsheet import SVGFlowsheet
        dist_svg = SVGFlowsheet.draw_distillation_figure_svg(sizing, result)
        st.write(dist_svg, unsafe_allow_html=True)
        
    with col_metrics:
        st.write("#### Nominal Outputs & Sizing")
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            st.markdown(f"""
            <div class="metric-card">
                <h5>Distillate Output</h5>
                <b>Purity:</b> {result['distillate_x']*100:.2f} mol%<br/>
                <b>Condenser Temp:</b> {result['T'][0]:.2f} K<br/>
                <b>Light BP:</b> {light_species.macro.boiling_point:.1f} K
            </div>
            """, unsafe_allow_html=True)
        with sub_col2:
            st.markdown(f"""
            <div class="metric-card">
                <h5>Bottoms Output</h5>
                <b>Bottoms Fraction:</b> {result['bottoms_x']*100:.2f} mol%<br/>
                <b>Reboiler Temp:</b> {result['T'][-1]:.2f} K<br/>
                <b>Heavy BP:</b> {heavy_species.macro.boiling_point:.1f} K
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown(f"""
        <div class="metric-card">
            <h5>Column Internals & Hydraulics</h5>
            <b>Sized Column Diameter:</b> {sizing['column_diameter_m']:.2f} m<br/>
            <b>Sized Height:</b> {sizing['column_height_m']:.2f} m<br/>
            <b>Total Pressure Drop:</b> {sizing['total_dp_kPa']:.2f} kPa<br/>
            <b>Downcomer Backup:</b> {sizing['downcomer_backup_m']*1000:.1f} mm ({'FLOODING WARNING!' if sizing['flooding_warning'] else 'Normal'})
        </div>
        """, unsafe_allow_html=True)

    # Plots
    st.write("### Column Stage Profiles")
    plot_col1, plot_col2 = st.columns(2)
    with plot_col1:
        fig_profile = go.Figure()
        fig_profile.add_trace(go.Scatter(x=result["stages"], y=result["x_light"], name=f"Liquid x ({light_species.name})", line=dict(color="#0d9488", width=3)))
        fig_profile.add_trace(go.Scatter(x=result["stages"], y=result["y_light"], name=f"Vapor y ({light_species.name})", line=dict(color="#ef4444", width=2)))
        fig_profile.update_layout(title="Composition Profiles", xaxis_title="Stage Number", yaxis_title="Mole Fraction", height=350)
        st.plotly_chart(fig_profile, use_container_width=True)
        
    with plot_col2:
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(x=result["stages"], y=result["T"], name="Stage Temperature (T)", line=dict(color="#ef4444", width=3)))
        fig_temp.update_layout(title="Temperature Profile along Column", xaxis_title="Stage Number", yaxis_title="Temperature (K)", height=350)
        st.plotly_chart(fig_temp, use_container_width=True)

    # P&ID rendering
    st.write("### Column Piping and Instrumentation Diagram (P&ID)")
    layout = PIDLayout("Distillation P&ID")
    layout.add_equipment("Column", f"Distillation Column C-101\\nSized Diam: {sizing['column_diameter_m']:.2f}m")
    layout.add_equipment("Condenser", "Condenser E-101")
    layout.add_equipment("Reboiler", "Reboiler E-102")
    layout.add_valve("RefluxValve", "Reflux Control Valve")
    layout.add_instrument("TC-102", "TC\\n(Stage Temp)")
    
    if enable_draw:
        layout.add_equipment("SideTank", f"Side draw tank\\nStage: {draw_stage}")
        layout.add_process_stream("Column", "SideTank", f"Side draw: {draw_frac*100:.0f}%")
        
    if enable_pa:
        layout.add_equipment("PACooler", "PA Cooler\\nE-103")
        layout.add_process_stream("Column", "PACooler", f"PA Draw Stage {pa_draw}")
        layout.add_process_stream("PACooler", "Column", f"PA Return Stage {pa_return}")

    layout.add_process_stream("Column", "Condenser", "Overhead Vapor")
    layout.add_process_stream("Condenser", "RefluxValve", "Distillate Liquid")
    layout.add_process_stream("RefluxValve", "Column", "Reflux Return")
    layout.add_process_stream("Column", "Reboiler", "Bottoms Liquid")
    layout.add_process_stream("Reboiler", "Column", "Boilup Vapor")
    
    layout.add_control_signal("Column", "TC-102")
    layout.add_control_signal("TC-102", "RefluxValve")
    
    render_mermaid(layout.to_mermaid())

elif simulation_mode == "Hydrocarbon PT Phase Envelope (PR-EOS)":
    st.write("### Multi-component Phase Envelope Solver")
    
    st.sidebar.subheader("Chemical Mixture Selection")
    comp1_name = st.sidebar.selectbox("Select Component 1", list(species_map.keys()), index=2)
    comp2_name = st.sidebar.selectbox("Select Component 2", list(species_map.keys()), index=3)
    
    comp1 = species_map[comp1_name]
    comp2 = species_map[comp2_name]
    
    st.sidebar.subheader("Mixture Fraction Configuration")
    methane_fraction = st.sidebar.slider(f"{comp1_name} Mole Fraction", 0.05, 0.95, 0.40, 0.05)
    ethane_fraction = 1.0 - methane_fraction
    
    species_list = [comp1, comp2]
    composition = {comp1.id: methane_fraction, comp2.id: ethane_fraction}
    
    # Show warning if external database is unavailable
    if Thermodynamics.db_mode == "external":
        st.markdown("""
            <div class="warning-card">
                <b>External Database Notice:</b> CoolProp/Thermo library not detected in local path. 
                Running with <i>pure Python Peng-Robinson Equation of State (EOS)</i> fallback for transparency.
            </div>
        """, unsafe_allow_html=True)
        
    # Generate Phase Envelope
    with st.spinner("Calculating phase envelope via PR-EOS..."):
        envelope = Thermodynamics.generate_pt_envelope(species_list, composition)
        
    # Plot PT-Envelope
    fig_env = go.Figure()
    fig_env.add_trace(go.Scatter(x=envelope["bubble_T_K"], y=envelope["pressures_kPa"], name="Bubble Point Curve (Liquid)", line=dict(color="#0d9488", width=3)))
    fig_env.add_trace(go.Scatter(x=envelope["dew_T_K"], y=envelope["pressures_kPa"], name="Dew Point Curve (Vapor)", line=dict(color="#ef4444", width=3, dash="dash")))
    fig_env.update_layout(
        title=f"{comp1_name}-{comp2_name} PT Phase Envelope ({methane_fraction*100:.0f}% {comp1_name} / {ethane_fraction*100:.0f}% {comp2_name})",
        xaxis_title="Temperature (Kelvin)",
        yaxis_title="Pressure (kPa)",
        height=500
    )
    st.plotly_chart(fig_env, use_container_width=True)
    
    # Interactive single point solver
    st.write("### Single Point VLE Flash Solver")
    col1, col2 = st.columns(2)
    with col1:
        test_T = st.slider("Flash Temperature (K)", 100.0, 400.0, 200.0, 5.0)
    with col2:
        test_P = st.slider("Flash Pressure (kPa)", 200.0, 4500.0, 1500.0, 50.0)
        
    res = Thermodynamics.solve_tp_flash(species_list, composition, test_T, test_P * 1000.0)
    
    col3, col4, col5 = st.columns(3)
    with col3:
        st.metric("Vapor Fraction (beta)", f"{res['beta']*100:.2f} %")
    with col4:
        st.write("**Liquid Phase Compositions (x)**")
        st.write(f"- {comp1_name}: {res['x'].get(comp1.id, 0.0)*100:.2f} mol%")
        st.write(f"- {comp2_name}: {res['x'].get(comp2.id, 0.0)*100:.2f} mol%")
    with col5:
        st.write("**Vapor Phase Compositions (y)**")
        st.write(f"- {comp1_name}: {res['y'].get(comp1.id, 0.0)*100:.2f} mol%")
        st.write(f"- {comp2_name}: {res['y'].get(comp2.id, 0.0)*100:.2f} mol%")

elif simulation_mode == "Electrolyte Equilibrium & Activity":
    st.write("### Electrolyte Systems modeling (Aspen Plus style)")
    
    electrolyte_option = st.radio(
        "Select Electrolyte Engine Mode",
        ["e-NRTL Activity Coefficients Correction", "Full Chemical Equilibrium Solver (pH, Dissociation & Precipitation)"]
    )
    
    if "e-NRTL" in electrolyte_option:
        st.subheader("e-NRTL Molalities Configuration")
        col1, col2 = st.columns(2)
        with col1:
            m_na = st.slider("Sodium Ion (Na+) molality (mol/kg)", 0.0, 5.0, 1.0, 0.1)
            m_cl = st.slider("Chloride Ion (Cl-) molality (mol/kg)", 0.0, 5.0, 1.0, 0.1)
        with col2:
            m_temp = st.slider("System Temperature (K)", 273.15, 373.15, 298.15, 1.0)
            
        charges = {'Na+': 1, 'Cl-': -1, 'water': 0}
        molalities = {'Na+': m_na, 'Cl-': m_cl, 'water': 55.5}
        
        coeffs = ElectrolyteModel.calculate_enrtl(charges, molalities, m_temp)
        
        st.write("#### Calculated Activity Coefficients (gamma)")
        st.metric("Water Activity Coefficient", f"{coeffs['water']:.4f}")
        st.metric("Na+ Ion Activity Coefficient", f"{coeffs['Na+']:.4f}")
        st.metric("Cl- Ion Activity Coefficient", f"{coeffs['Cl-']:.4f}")
        
    else:
        st.subheader("Chemical Equilibrium Configuration")
        col1, col2 = st.columns(2)
        with col1:
            total_acid = st.slider("Total Acetic Acid concentration (mol/L)", 0.0, 1.0, 0.1, 0.01)
            total_base = st.slider("Total Strong Base (NaOH) concentration (mol/L)", 0.0, 1.5, 0.05, 0.01)
        with col2:
            total_salt = st.slider("Total Sparingly Soluble Salt MX added (mol/L)", 0.0, 0.1, 0.02, 0.005)
            e_temp = st.slider("Temperature (K)", 273.15, 373.15, 298.15, 1.0)
            
        eq = ElectrolyteModel.solve_chemical_equilibrium(total_acid, total_base, total_salt, e_temp)
        
        col3, col4, col5 = st.columns(3)
        with col3:
            st.metric("System pH", f"{eq['pH']:.2f}")
        with col4:
            st.write("**Species concentrations (mol/L):**")
            st.write(f"- $H^+$: {eq['H+']:.2e} M")
            st.write(f"- $OH^-$: {eq['OH-']:.2e} M")
            st.write(f"- $HA$ (Undissociated acid): {eq['HA']:.4f} M")
            st.write(f"- $A^-$ (Acetate ion): {eq['A-']:.4f} M")
        with col5:
            st.write("**Salt Precipitation status:**")
            st.write(f"- $M^+$: {eq['M+']:.4f} M")
            st.write(f"- $X^-$: {eq['X-']:.4f} M")
            st.metric("Precipitated Solid MX", f"{eq['precipitated_MX_mol_L']*1000:.1f} mmol/L")

elif simulation_mode == "Pressure-Flow Network Solver":
    st.write("### Pressure-Flow Valve Dynamics (HYSYS-style)")
    
    st.sidebar.subheader("Pressure Boundaries")
    p_source = st.sidebar.slider("Inlet Source Pressure (kPa)", 150.0, 500.0, 300.0, 10.0) * 1000.0
    p_sink = st.sidebar.slider("Outlet Sink Pressure (kPa)", 100.0, 130.0, 101.3, 1.0) * 1000.0
    
    col1, col2 = st.columns(2)
    with col1:
        v1_open = st.slider("Valve 1 opening fraction", 0.0, 1.0, 0.70, 0.05)
    with col2:
        v2_open = st.slider("Valve 2 opening fraction", 0.0, 1.0, 0.50, 0.05)
        
    p_mid, flow = PressureFlowSolver.solve_series_valves(p_source, p_sink, 0.5, v1_open, 0.5, v2_open)
    
    col3, col4, col5 = st.columns(3)
    with col3:
        st.metric("Source Pressure", f"{p_source/1000:.1f} kPa")
    with col4:
        st.metric("Mid Node Pressure", f"{p_mid/1000:.2f} kPa")
    with col5:
        st.metric("Network Flow Rate", f"{flow:.3f} mol/s")
        
    # Render P&ID of valve network
    st.write("### Valve Network topology")
    layout = PIDLayout("Valve Network P&ID")
    layout.add_equipment("Source", f"Source Boundary\\n{p_source/1000:.1f} kPa")
    layout.add_valve("V1", f"Valve V-101\\nOpen: {v1_open*100:.0f}%")
    layout.add_instrument("P_Mid", f"Mid Node\\n{p_mid/1000:.1f} kPa")
    layout.add_valve("V2", f"Valve V-102\\nOpen: {v2_open*100:.0f}%")
    layout.add_equipment("Sink", f"Sink Boundary\\n{p_sink/1000:.1f} kPa")
    
    layout.add_process_stream("Source", "V1")
    layout.add_process_stream("V1", "P_Mid", f"Flow: {flow:.3f} mol/s")
    layout.add_process_stream("P_Mid", "V2")
    layout.add_process_stream("V2", "Sink")
    
    render_mermaid(layout.to_mermaid())

elif simulation_mode == "Interactive Flowsheet Designer":
    st.write("### Flowsheet Design Studio (AutoCAD & HYSYS-style)")
    st.markdown("""
        *Add components, select fluid packages, construct your custom workflow from scratch, set boundary parameters, and analyze mass & energy conservation.*
    """)
    
    # Initialize flowsheet session states from scratch if empty
    if "fs_species" not in st.session_state:
        st.session_state.fs_species = ["Ethanol", "Water"]
    if "fs_fluid_pkg" not in st.session_state:
        st.session_state.fs_fluid_pkg = "Ideal Gas / Activity model"
    if "fs_units" not in st.session_state:
        st.session_state.fs_units = {}  # dict of node_id -> {"type": type, "thermo": package}
    if "fs_connections" not in st.session_state:
        st.session_state.fs_connections = []  # list of {"from": u1, "to": u2, "stream": stream_id}
    if "fs_boundaries" not in st.session_state:
        st.session_state.fs_boundaries = {}  # stream_id -> {"T": T, "P": P, "F": F, "z": {sp_id: frac}}
    if "display_unit_system" not in st.session_state:
        st.session_state.display_unit_system = "Molar Flow (mol/s)"

    # ==========================================
    # SIDEBAR: FLOWSHEET BUILDER CONTROLLERS
    # ==========================================
    
    # 0. PLANT ARCHITECTURE PRESETS
    st.sidebar.subheader("0. Plant Architecture Presets")
    selected_preset = st.sidebar.selectbox(
        "Load Plant Preset",
        [
            "Select or Customize Scratch Canvas...",
            "Crude Oil Refinery (Atmospheric & Hydrotreater)",
            "Craft Beer Brewery & Fermentation Facility",
            "Green Ammonia Synthesis Plant (Haber-Bosch Loop)",
            "Carbon Capture & Acid Gas Sweetening Facility",
            "Bio-Ethanol Fermentation & Distillation Plant",
            "Seawater Desalination Plant (RO Membrane & Minerals)"
        ]
    )
    if st.sidebar.button("⚡ Load Plant Preset"):
        if selected_preset == "Crude Oil Refinery (Atmospheric & Hydrotreater)":
            st.session_state.fs_species = ["Pentane", "Hexane", "Octane", "Decane", "Hydrogen"]
            st.session_state.fs_fluid_pkg = "Peng-Robinson EOS"
            st.session_state.fs_units = {
                "P-101": {"type": "Pump", "thermo": "Peng-Robinson EOS", "p_boost": 250000.0, "variation": ""},
                "E-101": {"type": "Heater", "thermo": "Peng-Robinson EOS", "t_target": 610.0, "variation": ""},
                "C-101": {"type": "DistillationColumn", "thermo": "Peng-Robinson EOS", "variation": "Sieve Tray Column"},
                "M-101": {"type": "Mixer", "thermo": "Peng-Robinson EOS", "variation": ""},
                "R-101": {"type": "CSTR", "thermo": "Peng-Robinson EOS", "volume": 5.0, "variation": ""},
                "F-101": {"type": "FlashDrum", "thermo": "Peng-Robinson EOS", "variation": ""}
            }
            st.session_state.fs_connections = [
                {"from": "Feed Boundary", "from_port": "out", "to": "P-101", "to_port": "suction", "stream": "S-101"},
                {"from": "P-101", "from_port": "discharge", "to": "E-101", "to_port": "inlet", "stream": "S-102"},
                {"from": "E-101", "from_port": "outlet", "to": "C-101", "to_port": "feed", "stream": "S-103"},
                {"from": "C-101", "from_port": "distillate", "to": "Product Boundary", "to_port": "in", "stream": "S-104"},
                {"from": "C-101", "from_port": "bottoms", "to": "M-101", "to_port": "in_1", "stream": "S-105"},
                {"from": "Feed Boundary", "from_port": "out", "to": "M-101", "to_port": "in_2", "stream": "S-106"},
                {"from": "M-101", "from_port": "mixed_out", "to": "R-101", "to_port": "feed", "stream": "S-107"},
                {"from": "R-101", "from_port": "product", "to": "F-101", "to_port": "feed", "stream": "S-108"},
                {"from": "F-101", "from_port": "vapor", "to": "Product Boundary", "to_port": "in", "stream": "S-109"},
                {"from": "F-101", "from_port": "liquid", "to": "Product Boundary", "to_port": "in", "stream": "S-110"}
            ]
            st.session_state.fs_boundaries = {
                "S-101": {"T": 298.15, "P": 101325.0, "F": 25.0, "z": {"pentane": 0.25, "hexane": 0.25, "octane": 0.25, "decane": 0.25}},
                "S-106": {"T": 320.0, "P": 300000.0, "F": 10.0, "z": {"hydrogen": 1.0}}
            }
            st.rerun()

        elif selected_preset == "Craft Beer Brewery & Fermentation Facility":
            st.session_state.fs_species = ["Water", "Glucose", "Ethanol", "CO2", "Acetic Acid"]
            st.session_state.fs_fluid_pkg = "Ideal Gas / Activity model"
            st.session_state.fs_units = {
                "M-101": {"type": "Mixer", "thermo": "Ideal Gas / Activity model", "variation": ""},
                "H-101": {"type": "Heater", "thermo": "Ideal Gas / Activity model", "t_target": 372.0, "variation": ""},
                "S-101": {"type": "SolidLiquidSeparator", "thermo": "Ideal Gas / Activity model", "variation": ""},
                "E-101": {"type": "Cooler", "thermo": "Ideal Gas / Activity model", "t_target": 293.0, "variation": ""},
                "R-101": {"type": "Bioreactor", "thermo": "Ideal Gas / Activity model", "volume": 10.0, "variation": ""},
                "F-101": {"type": "SolidLiquidSeparator", "thermo": "Ideal Gas / Activity model", "variation": ""}
            }
            st.session_state.fs_connections = [
                {"from": "Feed Boundary", "from_port": "out", "to": "M-101", "to_port": "in_1", "stream": "S-101"},
                {"from": "Feed Boundary", "from_port": "out", "to": "M-101", "to_port": "in_2", "stream": "S-102"},
                {"from": "M-101", "from_port": "mixed_out", "to": "H-101", "to_port": "inlet", "stream": "S-103"},
                {"from": "H-101", "from_port": "outlet", "to": "S-101", "to_port": "slurry_in", "stream": "S-104"},
                {"from": "S-101", "from_port": "solids_out", "to": "Product Boundary", "to_port": "in", "stream": "S-105"},
                {"from": "S-101", "from_port": "liquid_out", "to": "E-101", "to_port": "inlet", "stream": "S-106"},
                {"from": "E-101", "from_port": "outlet", "to": "R-101", "to_port": "feed", "stream": "S-107"},
                {"from": "R-101", "from_port": "product", "to": "F-101", "to_port": "slurry_in", "stream": "S-108"},
                {"from": "F-101", "from_port": "liquid_out", "to": "Product Boundary", "to_port": "in", "stream": "S-109"},
                {"from": "F-101", "from_port": "solids_out", "to": "Product Boundary", "to_port": "in", "stream": "S-110"}
            ]
            st.session_state.fs_boundaries = {
                "S-101": {"T": 295.0, "P": 101325.0, "F": 35.0, "z": {"water": 1.0}},
                "S-102": {"T": 295.0, "P": 101325.0, "F": 12.0, "z": {"glucose": 0.85, "water": 0.15}}
            }
            st.rerun()

        elif selected_preset == "Green Ammonia Synthesis Plant (Haber-Bosch Loop)":
            st.session_state.fs_species = ["Hydrogen", "Nitrogen", "Ammonia", "Methane"]
            st.session_state.fs_fluid_pkg = "Peng-Robinson EOS"
            st.session_state.fs_units = {
                "M-101": {"type": "Mixer", "thermo": "Peng-Robinson EOS", "variation": ""},
                "K-101": {"type": "Compressor", "thermo": "Peng-Robinson EOS", "variation": ""},
                "E-101": {"type": "Heater", "thermo": "Peng-Robinson EOS", "t_target": 670.0, "variation": ""},
                "R-101": {"type": "EquilibriumReactor", "thermo": "Peng-Robinson EOS", "volume": 8.0, "reaction_package": "Haber-Bosch Ammonia Synthesis", "variation": ""},
                "E-102": {"type": "Cooler", "thermo": "Peng-Robinson EOS", "t_target": 245.0, "variation": ""},
                "V-101": {"type": "FlashDrum", "thermo": "Peng-Robinson EOS", "variation": ""},
                "SP-101": {"type": "Splitter", "thermo": "Peng-Robinson EOS", "variation": ""}
            }
            st.session_state.fs_connections = [
                {"from": "Feed Boundary", "from_port": "out", "to": "M-101", "to_port": "in_1", "stream": "S-101"},
                {"from": "M-101", "from_port": "mixed_out", "to": "K-101", "to_port": "suction", "stream": "S-102"},
                {"from": "K-101", "from_port": "discharge", "to": "E-101", "to_port": "inlet", "stream": "S-103"},
                {"from": "E-101", "from_port": "outlet", "to": "R-101", "to_port": "feed", "stream": "S-104"},
                {"from": "R-101", "from_port": "product", "to": "E-102", "to_port": "inlet", "stream": "S-105"},
                {"from": "E-102", "from_port": "outlet", "to": "V-101", "to_port": "feed", "stream": "S-106"},
                {"from": "V-101", "from_port": "liquid", "to": "Product Boundary", "to_port": "in", "stream": "S-107"},
                {"from": "V-101", "from_port": "vapor", "to": "SP-101", "to_port": "inlet", "stream": "S-108"},
                {"from": "SP-101", "from_port": "out_1", "to": "Product Boundary", "to_port": "in", "stream": "S-109"},
                {"from": "SP-101", "from_port": "out_2", "to": "Product Boundary", "to_port": "in", "stream": "S-110"}
            ]
            st.session_state.fs_boundaries = {
                "S-101": {"T": 300.0, "P": 2500000.0, "F": 40.0, "z": {"hydrogen": 0.74, "nitrogen": 0.25, "methane": 0.01}}
            }
            st.rerun()

        elif selected_preset == "Carbon Capture & Acid Gas Sweetening Facility":
            st.session_state.fs_species = ["CO2", "Nitrogen", "Water", "Methane"]
            st.session_state.fs_fluid_pkg = "Ideal Gas / Activity model"
            st.session_state.fs_units = {
                "C-101": {"type": "AbsorptionColumn", "thermo": "Ideal Gas / Activity model", "variation": ""},
                "P-101": {"type": "Pump", "thermo": "Ideal Gas / Activity model", "p_boost": 200000.0, "variation": ""},
                "HEX-101": {"type": "HeatExchanger", "thermo": "Ideal Gas / Activity model", "variation": ""},
                "H-101": {"type": "Heater", "thermo": "Ideal Gas / Activity model", "t_target": 393.0, "variation": ""},
                "F-101": {"type": "FlashDrum", "thermo": "Ideal Gas / Activity model", "variation": ""}
            }
            st.session_state.fs_connections = [
                {"from": "Feed Boundary", "from_port": "out", "to": "C-101", "to_port": "gas_in", "stream": "S-101"},
                {"from": "Feed Boundary", "from_port": "out", "to": "C-101", "to_port": "solvent_in", "stream": "S-102"},
                {"from": "C-101", "from_port": "clean_gas", "to": "Product Boundary", "to_port": "in", "stream": "S-103"},
                {"from": "C-101", "from_port": "rich_solvent", "to": "P-101", "to_port": "suction", "stream": "S-104"},
                {"from": "P-101", "from_port": "discharge", "to": "HEX-101", "to_port": "tube_in", "stream": "S-105"},
                {"from": "HEX-101", "from_port": "tube_out", "to": "H-101", "to_port": "inlet", "stream": "S-106"},
                {"from": "H-101", "from_port": "outlet", "to": "F-101", "to_port": "feed", "stream": "S-107"},
                {"from": "F-101", "from_port": "vapor", "to": "Product Boundary", "to_port": "in", "stream": "S-108"},
                {"from": "F-101", "from_port": "liquid", "to": "Product Boundary", "to_port": "in", "stream": "S-109"}
            ]
            st.session_state.fs_boundaries = {
                "S-101": {"T": 320.0, "P": 105000.0, "F": 30.0, "z": {"co2": 0.15, "nitrogen": 0.85}},
                "S-102": {"T": 310.0, "P": 110000.0, "F": 25.0, "z": {"water": 0.95, "co2": 0.05}}
            }
            st.rerun()

        elif selected_preset == "Seawater Desalination Plant (RO Membrane & Minerals)":
            st.session_state.fs_species = ["Water", "Sodium Chloride"]
            st.session_state.fs_fluid_pkg = "e-NRTL Electrolytes"
            st.session_state.fs_units = {
                "P-101": {"type": "Pump", "thermo": "e-NRTL Electrolytes", "p_boost": 5500000.0, "variation": ""},
                "M-101": {"type": "MembraneUnit", "thermo": "e-NRTL Electrolytes", "variation": ""},
                "V-101": {"type": "ControlValve", "thermo": "e-NRTL Electrolytes", "opening": 0.8, "variation": ""},
                "MIX-101": {"type": "Mixer", "thermo": "e-NRTL Electrolytes", "variation": ""}
            }
            st.session_state.fs_connections = [
                {"from": "Feed Boundary", "from_port": "out", "to": "P-101", "to_port": "suction", "stream": "S-101"},
                {"from": "P-101", "from_port": "discharge", "to": "M-101", "to_port": "feed_in", "stream": "S-102"},
                {"from": "M-101", "from_port": "permeate_out", "to": "MIX-101", "to_port": "in_1", "stream": "S-103"},
                {"from": "M-101", "from_port": "retentate_out", "to": "V-101", "to_port": "inlet", "stream": "S-104"},
                {"from": "V-101", "from_port": "outlet", "to": "Product Boundary", "to_port": "in", "stream": "S-105"},
                {"from": "Feed Boundary", "from_port": "out", "to": "MIX-101", "to_port": "in_2", "stream": "S-106"},
                {"from": "MIX-101", "from_port": "mixed_out", "to": "Product Boundary", "to_port": "in", "stream": "S-107"}
            ]
            st.session_state.fs_boundaries = {
                "S-101": {"T": 293.15, "P": 101325.0, "F": 50.0, "z": {"water": 0.965, "nacl": 0.035}},
                "S-106": {"T": 293.15, "P": 101325.0, "F": 1.0, "z": {"water": 0.99, "nacl": 0.01}}
            }
            st.rerun()

        elif selected_preset == "Bio-Ethanol Fermentation & Distillation Plant":
            st.session_state.fs_species = ["Ethanol", "Water", "Glucose", "CO2"]
            st.session_state.fs_fluid_pkg = "NRTL Activity Model"
            st.session_state.fs_units = {
                "R-101": {"type": "CSTR", "thermo": "NRTL Activity Model", "volume": 15.0, "reaction_package": "Bio-Ethanol Fermentation", "variation": ""},
                "P-101": {"type": "Pump", "thermo": "NRTL Activity Model", "p_boost": 150000.0, "variation": ""},
                "V-101": {"type": "ControlValve", "thermo": "NRTL Activity Model", "opening": 1.0, "variation": ""},
                "C-101": {"type": "DistillationColumn", "thermo": "NRTL Activity Model", "variation": "Sieve Tray Column"}
            }
            st.session_state.fs_connections = [
                {"from": "Feed Boundary", "from_port": "out", "to": "R-101", "to_port": "feed", "stream": "S-101"},
                {"from": "R-101", "from_port": "product", "to": "P-101", "to_port": "suction", "stream": "S-102"},
                {"from": "P-101", "from_port": "discharge", "to": "V-101", "to_port": "inlet", "stream": "S-103"},
                {"from": "V-101", "from_port": "outlet", "to": "C-101", "to_port": "feed", "stream": "S-104"},
                {"from": "C-101", "from_port": "distillate", "to": "Product Boundary", "to_port": "in", "stream": "S-105"},
                {"from": "C-101", "from_port": "bottoms", "to": "Product Boundary", "to_port": "in", "stream": "S-106"}
            ]
            st.session_state.fs_boundaries = {
                "S-101": {"T": 305.0, "P": 101325.0, "F": 20.0, "z": {"water": 0.80, "glucose": 0.15, "ethanol": 0.05}}
            }
            st.rerun()

    # 1. FLUID PACKAGE & AGENTS
    st.sidebar.subheader("1. Fluid Package & Agents")
    search_list = ["Search and Add Chemical..."] + [k for k in species_map.keys() if k not in st.session_state.fs_species]
    selected_add_sp = st.sidebar.selectbox("Lookup Compounds", search_list, index=0)
    
    if selected_add_sp != "Search and Add Chemical...":
        st.session_state.fs_species.append(selected_add_sp)
        st.rerun()
        
    st.sidebar.write("**Active Process Chemicals:**")
    if not st.session_state.fs_species:
        st.sidebar.info("No chemicals selected. Search above.")
    else:
        for sp_name in st.session_state.fs_species:
            sp_cols = st.sidebar.columns([4, 1])
            sp_cols[0].write(f"- {sp_name} ({species_map[sp_name].formula})")
            if sp_cols[1].button("❌", key=f"del_sp_btn_{sp_name}"):
                st.session_state.fs_species.remove(sp_name)
                st.rerun()
    
    fluid_pkg_options = [
        "Peng-Robinson EOS", "NRTL Activity Model", "Wilson Activity Model", 
        "Ideal Gas / Activity model", "e-NRTL Electrolytes", "PINN ML Surrogate"
    ]
    cur_pkg_idx = fluid_pkg_options.index(st.session_state.fs_fluid_pkg) if st.session_state.fs_fluid_pkg in fluid_pkg_options else 0
    st.session_state.fs_fluid_pkg = st.sidebar.selectbox(
        "Global Thermodynamic Base",
        fluid_pkg_options,
        index=cur_pkg_idx
    )
    
    # Toggle Display Units
    st.sidebar.subheader("2. Unit System Selection")
    st.session_state.display_unit_system = st.sidebar.radio(
        "Flowsheet Display Scale",
        ["Molar Flow (mol/s)", "Mass Flow (kg/h) / Energy Flow (kW)"]
    )
    
    # Add Equipment node
    st.sidebar.subheader("3. Add Equipment Node")
    add_id = st.sidebar.text_input("Node Identifier", "P-101")
    add_type = st.sidebar.selectbox(
        "Equipment Type", 
        [
            "Pump", "Compressor", "Expander", "ControlValve", 
            "Heater", "Cooler", "HeatExchanger", 
            "FlashDrum", "Splitter", "SolidLiquidSeparator", "MembraneUnit", 
            "AbsorptionColumn", "DistillationColumn", "DynamicDistillationColumn", "Bioreactor", "CSTR", "PFR", "EquilibriumReactor", "Mixer"
        ]
    )
    add_material = st.sidebar.selectbox("Material of Construction", ["Carbon Steel", "Stainless Steel 316", "Titanium", "Hastelloy C-276", "Monel"])
    local_pkg = st.sidebar.selectbox("Local Fluid Package", ["Default (Global)"] + fluid_pkg_options)
    
    col_variation = "Sieve Tray Column"
    rxn_pkg = "None"
    if add_type == "DistillationColumn":
        col_variation = st.sidebar.selectbox("Symbol Style", ["Sieve Tray Column", "Packed Bed Column"])
    elif add_type in ["CSTR", "PFR", "EquilibriumReactor"]:
        rxn_pkg = st.sidebar.selectbox("Reaction Scheme", ["None", "Haber-Bosch Ammonia Synthesis", "Bio-Ethanol Fermentation", "Water-Gas Shift", "Generic 1st-Order Exothermic"])
        
    if st.sidebar.button("Add to Flowsheet"):
        if add_id in st.session_state.fs_units:
            st.sidebar.error(f"Node '{add_id}' already exists!")
        elif not add_id.strip():
            st.sidebar.error("Node ID cannot be empty!")
        else:
            st.session_state.fs_units[add_id] = {
                "type": add_type,
                "material": add_material,
                "thermo": st.session_state.fs_fluid_pkg if local_pkg == "Default (Global)" else local_pkg,
                "opening": 1.0,
                "p_boost": 150000.0,
                "volume": 2.0,
                "variation": col_variation,
                "reaction_package": rxn_pkg if rxn_pkg != "None" else None,
                "t_target": 350.0
            }
            st.sidebar.success(f"Added {add_type} {add_id}")
            
    # Connect Streams
    st.sidebar.subheader("4. Connect Streams")
    if len(st.session_state.fs_units) >= 1:
        u_options = list(st.session_state.fs_units.keys())
        conn_from = st.sidebar.selectbox("Source Node", ["Feed Boundary"] + u_options)
        from_type = st.session_state.fs_units.get(conn_from, {}).get("type", "Feed Boundary") if conn_from != "Feed Boundary" else "Feed Boundary"
        out_ports = [p.id for p in PortRegistry.get_ports(from_type) if p.type == "outlet"] or ["out"]
        conn_from_port = st.sidebar.selectbox("From Nozzle / Port", out_ports, format_func=lambda pid: f"{pid} ({PortRegistry.get_port(from_type, pid).label if PortRegistry.get_port(from_type, pid) else pid})")

        conn_to = st.sidebar.selectbox("Destination Node", ["Product Boundary"] + u_options)
        to_type = st.session_state.fs_units.get(conn_to, {}).get("type", "Product Boundary") if conn_to != "Product Boundary" else "Product Boundary"
        in_ports = [p.id for p in PortRegistry.get_ports(to_type) if p.type == "inlet"] or ["in"]
        conn_to_port = st.sidebar.selectbox("To Nozzle / Port", in_ports, format_func=lambda pid: f"{pid} ({PortRegistry.get_port(to_type, pid).label if PortRegistry.get_port(to_type, pid) else pid})")

        conn_stream = st.sidebar.text_input("Stream Identifier", f"S-{len(st.session_state.fs_connections)+101}")
        
        if st.sidebar.button("Add stream connection"):
            if conn_from == conn_to:
                st.sidebar.error("Cannot connect node to itself!")
            else:
                st.session_state.fs_connections.append({
                    "from": conn_from,
                    "from_port": conn_from_port,
                    "to": conn_to,
                    "to_port": conn_to_port,
                    "stream": conn_stream
                })
                st.sidebar.success(f"Stream {conn_stream} connected ({conn_from_port} ➔ {conn_to_port})!")
    else:
        st.sidebar.info("Add equipment to define stream connections.")

    # Boundary Stream Setter
    st.sidebar.subheader("5. Set Feed Boundary Values")
    # Identify inlet boundary streams (either starting at "Feed Boundary" or has no upstream unit)
    inlets = []
    for c in st.session_state.fs_connections:
        if c["from"] == "Feed Boundary":
            inlets.append(c["stream"])
            
    if inlets:
        b_stream = st.sidebar.selectbox("Select Feed Stream", inlets)
        b_F = st.sidebar.slider("Feed Molar Flow (mol/s)", 0.1, 50.0, 10.0, 0.5)
        b_T = st.sidebar.slider("Feed Temp (K)", 150.0, 400.0, 298.15, 1.0)
        b_P = st.sidebar.slider("Feed Press (kPa)", 100.0, 2000.0, 101.3, 10.0)
        
        # Composition sliders based on selected species
        comp_vals = {}
        for sp_name in st.session_state.fs_species:
            sp = species_map[sp_name]
            comp_vals[sp.id] = st.sidebar.slider(f"{sp_name} fraction", 0.0, 1.0, 0.5, 0.05)
            
        if st.sidebar.button("Set Feed Boundary"):
            st.session_state.fs_boundaries[b_stream] = {
                "T": b_T,
                "P": b_P * 1000.0,
                "F": b_F,
                "z": comp_vals
            }
            st.sidebar.success(f"Boundary stream {b_stream} set!")
    else:
        st.sidebar.info("Create a stream connection starting at 'Feed Boundary' to set boundary feeds.")
        
    if st.sidebar.button("Reset Designer Studio"):
        st.session_state.fs_species = ["Ethanol", "Water"]
        st.session_state.fs_fluid_pkg = "Ideal Gas / Activity model"
        st.session_state.fs_units = {}
        st.session_state.fs_connections = []
        st.session_state.fs_boundaries = {}
        st.sidebar.warning("Flowsheet cleared to scratch canvas.")

    # ==========================================
    # MAIN WORKSPACE AND TABS
    # ==========================================
    
    # Compile actual objects and run simulation
    streams_obj_map = {}
    units_obj_list = []
    
    # 1. Initialize MaterialStream objects
    all_streams_set = set(c["stream"] for c in st.session_state.fs_connections)
    for s_id in all_streams_set:
        streams_obj_map[s_id] = MaterialStream(s_id)
        
    # 2. Initialize BaseUnit objects
    units_obj_map = {}
    for uid, udata in st.session_state.fs_units.items():
        utype = udata["type"]
        if utype == "Pump":
            unit_obj = FlowsheetPump(uid, uid, p_boost=udata.get("p_boost", 150000.0))
        elif utype == "Compressor":
            unit_obj = Compressor(uid, uid, pressure_ratio=udata.get("pressure_ratio", 3.0))
        elif utype == "Expander":
            unit_obj = Expander(uid, uid, pressure_ratio=udata.get("pressure_ratio", 0.33))
        elif utype == "ControlValve":
            unit_obj = ControlValve(uid, uid, cv=0.8)
            unit_obj.open_fraction = udata.get("opening", 1.0)
        elif utype == "Heater":
            unit_obj = Heater(uid, uid, t_target=udata.get("t_target", 373.15))
        elif utype == "Cooler":
            unit_obj = Cooler(uid, uid, t_target=udata.get("t_target", 298.15))
        elif utype == "HeatExchanger":
            unit_obj = HeatExchanger(uid, uid, u_area=2500.0)
        elif utype == "FlashDrum":
            unit_obj = FlashDrum(uid, uid, temp_vessel=udata.get("t_target", 350.0))
        elif utype == "Splitter":
            unit_obj = Splitter(uid, uid, split_ratios=[0.5, 0.5])
        elif utype == "SolidLiquidSeparator":
            unit_obj = SolidLiquidSeparator(uid, uid, recovery_liquid=0.90)
        elif utype == "MembraneUnit":
            unit_obj = MembraneUnit(uid, uid, recovery_ratio=0.65)
        elif utype == "AbsorptionColumn":
            unit_obj = AbsorptionColumn(uid, uid, target_solute="co2")
        elif utype == "Bioreactor":
            unit_obj = JacketedBioreactor(uid, uid, volume_init=udata.get("volume", 2.0), s_in=180.0, u_coeff=600.0, area=5.0, temp_sp=310.15, pid_controller=PIDController(10,2,0.1,0.05,0,1))
        elif utype == "CSTR":
            unit_obj = IdealCSTR(uid, uid, volume=udata.get("volume", 2.0), reaction_package=udata.get("reaction_package"))
        elif utype == "PFR":
            unit_obj = IdealPFR(uid, uid, volume=udata.get("volume", 3.0), reaction_package=udata.get("reaction_package"))
        elif utype == "EquilibriumReactor":
            unit_obj = EquilibriumReactor(uid, uid, volume=udata.get("volume", 4.0), reaction_package=udata.get("reaction_package", "Haber-Bosch Ammonia Synthesis"))
        elif utype == "DistillationColumn":
            unit_obj = BinaryDistillationColumn(uid, uid, num_stages=12, feed_stage=6, reflux_ratio=2.5)
        elif utype == "DynamicDistillationColumn":
            unit_obj = DynamicDistillationColumn(uid, uid, num_stages=12, feed_stage=6, reflux_ratio=2.5)
        elif utype == "Mixer":
            unit_obj = FlowsheetMixer(uid, uid)
        else:
            unit_obj = FlowsheetPump(uid, uid)

        unit_obj.thermo_base = udata.get("thermo", st.session_state.fs_fluid_pkg)
        unit_obj.material = udata.get("material", "Carbon Steel")
        units_obj_map[uid] = unit_obj
        units_obj_list.append(unit_obj)
        
    # 3. Connect ports with port-index resolution
    for conn in st.session_state.fs_connections:
        f_node = conn["from"]
        t_node = conn["to"]
        s_id = conn["stream"]
        st_obj = streams_obj_map[s_id]
        
        f_port = conn.get("from_port")
        t_port = conn.get("to_port")
        
        if f_node in units_obj_map:
            u = units_obj_map[f_node]
            utype = st.session_state.fs_units.get(f_node, {}).get("type", "Pump")
            out_ports = [p.id for p in PortRegistry.get_ports(utype) if p.type == "outlet"]
            target_idx = out_ports.index(f_port) if f_port in out_ports else len(u.outlets)
            
            while len(u.outlets) <= target_idx:
                u.outlets.append(None)
            u.outlets[target_idx] = st_obj
            st_obj.upstream_unit = u
            
        if t_node in units_obj_map:
            u = units_obj_map[t_node]
            utype = st.session_state.fs_units.get(t_node, {}).get("type", "Pump")
            in_ports = [p.id for p in PortRegistry.get_ports(utype) if p.type == "inlet"]
            target_idx = in_ports.index(t_port) if t_port in in_ports else len(u.inlets)
            
            while len(u.inlets) <= target_idx:
                u.inlets.append(None)
            u.inlets[target_idx] = st_obj
            if u not in st_obj.downstream_units:
                st_obj.downstream_units.append(u)

    # Clean up any None gaps in unit ports
    for u in units_obj_map.values():
        u.inlets = [s for s in u.inlets if s is not None]
        u.outlets = [s for s in u.outlets if s is not None]
            
    # 4. Apply Boundary specifications
    for s_id, spec in st.session_state.fs_boundaries.items():
        if s_id in streams_obj_map:
            st_obj = streams_obj_map[s_id]
            st_obj.set_val("T", spec["T"])
            st_obj.set_val("P", spec["P"])
            st_obj.set_val("F", spec["F"])
            st_obj.set_val("z", spec["z"])
            
    # 5. Multi-Pass Sequential Modular Flowsheet Simulation Engine
    # Eliminates naming order bugs and converges forward chains & recycle loops
    if len(units_obj_map) > 0:
        max_sweeps = 25
        tol = 1e-4
        for sweep in range(max_sweeps):
            prev_snapshot = {
                s_id: (s.F if s.F is not None else -1.0, s.T if s.T is not None else -1.0)
                for s_id, s in streams_obj_map.items()
            }
            
            for uid, unit in units_obj_map.items():
                if unit.inlets and all(i.F is not None and i.F >= 0 for i in unit.inlets):
                    in_st = unit.inlets[0]
                    out_st = unit.outlets[0] if unit.outlets else None
                    
                    if isinstance(unit, FlowsheetPump):
                        unit.run_simulation((0,0), [], species_map=species_map_id)
                    elif isinstance(unit, Compressor):
                        unit.run_simulation((0,0), [], species_map=species_map_id)
                    elif isinstance(unit, Expander):
                        unit.run_simulation((0,0), [], species_map=species_map_id)
                    elif isinstance(unit, Heater):
                        unit.run_simulation((0,0), [], species_map=species_map_id)
                    elif isinstance(unit, Cooler):
                        unit.run_simulation((0,0), [], species_map=species_map_id)
                    elif isinstance(unit, HeatExchanger):
                        unit.run_simulation((0,0), [], species_map=species_map_id)
                    elif isinstance(unit, FlashDrum):
                        unit.run_simulation((0,0), [], species_map=species_map_id)
                    elif isinstance(unit, Splitter):
                        unit.run_simulation((0,0), [], species_map=species_map_id)
                    elif isinstance(unit, SolidLiquidSeparator):
                        unit.run_simulation((0,0), [], species_map=species_map_id)
                    elif isinstance(unit, MembraneUnit):
                        unit.run_simulation((0,0), [], species_map=species_map_id)
                    elif isinstance(unit, AbsorptionColumn):
                        unit.run_simulation((0,0), [], species_map=species_map_id)
                    elif isinstance(unit, (IdealCSTR, IdealPFR, EquilibriumReactor)):
                        unit.run_simulation((0,0), [], species_map=species_map_id)
                    elif isinstance(unit, FlowsheetMixer):
                        unit.run_simulation((0,0), [], species_map=species_map_id)
                    elif isinstance(unit, ControlValve):
                        unit.run_simulation((0,0), [], p_in=in_st.P, p_out=max(1000.0, in_st.P - 20000.0))
                        if out_st:
                            out_st.T = in_st.T - 0.2
                            out_st.P = max(1000.0, in_st.P - 20000.0)
                            out_st.F = in_st.F
                            out_st.z = in_st.z.copy()
                    elif isinstance(unit, JacketedBioreactor):
                        if out_st:
                            out_st.T = unit.temp_sp
                            out_st.P = in_st.P
                            out_st.F = in_st.F
                            out_st.z = in_st.z.copy()
                            if "glucose" in out_st.z and "ethanol" in out_st.z:
                                conv = out_st.z["glucose"] * 0.40
                                out_st.z["glucose"] -= conv
                                out_st.z["ethanol"] += conv * 0.60
                                if "co2" in out_st.z:
                                    out_st.z["co2"] += conv * 0.40
                    elif isinstance(unit, BinaryDistillationColumn):
                        if len(unit.outlets) >= 2:
                            d_out = unit.outlets[0]
                            b_out = unit.outlets[1]
                            d_out.T = in_st.T - 10.0
                            d_out.P = in_st.P
                            d_out.F = in_st.F * 0.4
                            b_out.T = in_st.T + 15.0
                            b_out.P = in_st.P
                            b_out.F = in_st.F * 0.6
                            keys = list(in_st.z.keys())
                            if len(keys) >= 2:
                                d_out.z = {keys[0]: 0.85, keys[1]: 0.15}
                                b_out.z = {keys[0]: 0.05, keys[1]: 0.95}
                        elif out_st:
                            out_st.T = in_st.T
                            out_st.P = in_st.P
                            out_st.F = in_st.F
                            out_st.z = in_st.z.copy()
                            
            # Check convergence
            deltas = []
            for s_id, s in streams_obj_map.items():
                prev_f, prev_t = prev_snapshot.get(s_id, (-1.0, -1.0))
                curr_f = s.F if s.F is not None else -1.0
                curr_t = s.T if s.T is not None else -1.0
                if prev_f >= 0 and curr_f >= 0:
                    deltas.append(max(abs(curr_f - prev_f) / max(prev_f, 1e-4), abs(curr_t - prev_t) / max(prev_t, 1e-4)))
            if deltas and max(deltas) < tol:
                break

    # Compile flowsheet layout for Mermaid P&ID representation
    flow_layout = PIDLayout("Custom Flowsheet P&ID")
    
    for uid, udata in st.session_state.fs_units.items():
        utype = udata["type"]
        if utype == "ControlValve":
            flow_layout.add_valve(uid, f"{uid}\\n({utype})")
        else:
            flow_layout.add_equipment(uid, f"{uid}\\n({utype})")
            
    feed_nodes_m = []
    prod_nodes_m = []
    
    for conn in st.session_state.fs_connections:
        src = conn["from"]
        dst = conn["to"]
        s_id = conn["stream"]
        
        if src == "Feed Boundary":
            src_id = f"Feed_{s_id}"
            feed_nodes_m.append((src_id, f"Feed ({s_id})"))
        else:
            src_id = src.replace(" ", "_")
            
        if dst == "Product Boundary":
            dst_id = f"Product_{s_id}"
            prod_nodes_m.append((dst_id, f"Product ({s_id})"))
        else:
            dst_id = dst.replace(" ", "_")
            
        flow_layout.add_process_stream(src_id, dst_id, s_id)
        
    if feed_nodes_m:
        flow_layout.add_subgraph("Feed Boundaries", feed_nodes_m)
    if prod_nodes_m:
        flow_layout.add_subgraph("Product Boundaries", prod_nodes_m)

    # Global species map for tooltips and summaries
    mapped_sp = {sp.id: sp for sp in [species_map[k] for k in st.session_state.fs_species]}

    # RENDER INTERACTIVE TABS
    tab_pid, tab_mass, tab_energy, tab_vle, tab_econ, tab_dynamic, tab_pinch = st.tabs([
        "Flowsheet Canvas & P&ID", 
        "Mass Balance Summary", 
        "Energy Balance Summary", 
        "VLE & Reaction Kinetics Explorer",
        "Economics & Capital Costing (Turton/Guthrie)",
        "Dynamic Control & Real-Time Transients",
        "Pinch Energy Integration & Heat Recovery"
    ])
    
    with tab_pid:
        st.write("#### Live Flowsheet Topology")
        if len(st.session_state.fs_connections) == 0:
            st.info("Flowsheet is empty. Define stream connections in the sidebar to visualize.")
        else:
            view_mode = st.radio(
                "Render Engine Mode", 
                ["Interactive Studio (Drag-and-Drop)", "CAD Vector Flowsheet (SVG)", "Mermaid Logic Flowsheet"], 
                horizontal=True
            )
            if view_mode == "Interactive Studio (Drag-and-Drop)":
                st.info("💡 **Interactive Studio**: Click and drag equipment to move. Drag the bottom-right corner of any node to resize it. Drag from an orange outlet nozzle to a green inlet nozzle to wire a stream.")
                studio_html = InteractiveCanvasStudio.render_studio_html(
                    st.session_state.fs_units, 
                    st.session_state.fs_connections, 
                    stream_states=streams_obj_map,
                    units_states=units_obj_map,
                    species_map=mapped_sp,
                    canvas_height=650
                )
                components.html(studio_html, height=670, scrolling=False)
                
                with st.expander("Import / Paste Canvas Layout JSON"):
                    sync_json_input = st.text_area("Paste Canvas JSON from 'Copy / Sync Config' button", height=90, key="sync_canvas_json_area")
                    if st.button("Apply Canvas Config to Flowsheet"):
                        try:
                            import json
                            parsed = json.loads(sync_json_input)
                            if "units" in parsed:
                                for uid, udata in parsed["units"].items():
                                    if uid in st.session_state.fs_units:
                                        st.session_state.fs_units[uid]["x"] = udata.get("x", 100)
                                        st.session_state.fs_units[uid]["y"] = udata.get("y", 100)
                                        st.session_state.fs_units[uid]["width"] = udata.get("width", 80)
                                        st.session_state.fs_units[uid]["height"] = udata.get("height", 80)
                            if "connections" in parsed:
                                st.session_state.fs_connections = parsed["connections"]
                            st.success("Canvas configuration applied successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error applying JSON: {e}")
            elif view_mode == "CAD Vector Flowsheet (SVG)":
                from src.visualization.svg_flowsheet import SVGFlowsheet
                variations = {uid: udata.get("variation", "Sieve Tray Column") for uid, udata in st.session_state.fs_units.items()}
                svg_code = SVGFlowsheet.generate_flowsheet_svg(
                    st.session_state.fs_units, 
                    st.session_state.fs_connections, 
                    variations,
                    stream_states=streams_obj_map,
                    units_states=units_obj_map,
                    species_map=mapped_sp
                )
                st.write(svg_code, unsafe_allow_html=True)
            else:
                render_mermaid(flow_layout.to_mermaid())
            
        st.write("#### Sized Equipment Parameters")
        if len(units_obj_list) == 0:
            st.info("No equipment nodes placed.")
        else:
            # Header Row
            h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([1, 1, 1.2, 4, 1])
            h_col1.markdown("**Node ID**")
            h_col2.markdown("**Type**")
            h_col3.markdown("**Fluid Package**")
            h_col4.markdown("**Calculated Sizing Metrics**")
            h_col5.markdown("**Action**")
            
            for u in units_obj_list:
                u.size_equipment()
                sizing_str = ", ".join(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}" for k, v in u.sizing_results.items())
                utype = st.session_state.fs_units[u.unit_id]["type"]
                
                row_col1, row_col2, row_col3, row_col4, row_col5 = st.columns([1, 1, 1.2, 4, 1])
                row_col1.write(u.unit_id)
                row_col2.write(utype)
                row_col3.write(f"{u.thermo_base} ({st.session_state.fs_units[u.unit_id].get('variation', 'Standard')})")
                row_col4.write(sizing_str)
                if row_col5.button("Delete", key=f"del_node_btn_{u.unit_id}"):
                    # Remove unit
                    del st.session_state.fs_units[u.unit_id]
                    # Remove connections
                    st.session_state.fs_connections = [
                        c for c in st.session_state.fs_connections 
                        if c["from"] != u.unit_id and c["to"] != u.unit_id
                    ]
                    st.success(f"Deleted equipment {u.unit_id} and associated streams.")
                    st.rerun()

        st.write("#### Active Stream Connections")
        if len(st.session_state.fs_connections) == 0:
            st.info("No stream connections defined.")
        else:
            sh_col1, sh_col2, sh_col3, sh_col4 = st.columns([1.2, 2.2, 2.2, 1.0])
            sh_col1.markdown("**Stream ID**")
            sh_col2.markdown("**From (Port)**")
            sh_col3.markdown("**To (Port)**")
            sh_col4.markdown("**Action**")
            
            for c in st.session_state.fs_connections:
                s_col1, s_col2, s_col3, s_col4 = st.columns([1.2, 2.2, 2.2, 1.0])
                from_p = f" [{c['from_port']}]" if c.get("from_port") else ""
                to_p = f" [{c['to_port']}]" if c.get("to_port") else ""
                s_col1.write(c["stream"])
                s_col2.write(f"{c['from']}{from_p}")
                s_col3.write(f"{c['to']}{to_p}")
                if s_col4.button("Delete", key=f"del_stream_btn_{c['stream']}"):
                    stream_id_del = c["stream"]
                    # Remove connection
                    st.session_state.fs_connections = [
                        conn for conn in st.session_state.fs_connections if conn["stream"] != stream_id_del
                    ]
                    # Remove boundary if present
                    if stream_id_del in st.session_state.fs_boundaries:
                        del st.session_state.fs_boundaries[stream_id_del]
                    st.success(f"Deleted stream {stream_id_del}.")
                    st.rerun()
            
    with tab_mass:
        st.write("#### Mass Balance Summary Sheet")
        if len(streams_obj_map) == 0:
            st.info("No streams defined.")
        else:
            mass_summary = []
            
            for s_id, s_obj in streams_obj_map.items():
                if s_obj.F is not None:
                    # check display units selection
                    if "Molar Flow" in st.session_state.display_unit_system:
                        flow_str = f"{s_obj.F:.3f} mol/s"
                    else:
                        flow_str = f"{s_obj.get_mass_flow(mapped_sp):.2f} kg/h"
                        
                    comp_str = ", ".join(f"{k}: {v*100:.1f}%" for k, v in s_obj.z.items())
                    
                    # identify source and dest names
                    src_name = s_obj.upstream_unit.unit_id if s_obj.upstream_unit else "Feed Boundary"
                    dest_name = ", ".join(d.unit_id for d in s_obj.downstream_units) if s_obj.downstream_units else "Product Boundary"
                    
                    mass_summary.append({
                        "Stream ID": s_id,
                        "Source Node": src_name,
                        "Destination Node": dest_name,
                        "Total Flow": flow_str,
                        "Compositions": comp_str
                    })
            if mass_summary:
                st.table(mass_summary)
                
                # Overall Conservation balance report
                m_bal = FlowsheetSolver.compile_mass_balance(list(streams_obj_map.values()), mapped_sp)
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("Total Boundary Inlet Mass", f"{m_bal['total_inlet_mass_kg_h']:.2f} kg/h")
                with col_m2:
                    st.metric("Total Boundary Outlet Mass", f"{m_bal['total_outlet_mass_kg_h']:.2f} kg/h")
                with col_m3:
                    diff_val = f"{m_bal['mass_balance_error_kg_h']:.3f} kg/h"
                    status_lbl = "Conserved (Green)" if m_bal["is_conserved"] else "Mass Imbalance (Red)"
                    st.metric(f"Mass Balance Error ({status_lbl})", diff_val)
            else:
                st.info("Set boundaries and run simulation to populate balances.")
                
    with tab_energy:
        st.write("#### Energy Balance Summary Sheet")
        if len(streams_obj_map) == 0:
            st.info("No streams defined.")
        else:
            energy_summary = []
            
            for s_id, s_obj in streams_obj_map.items():
                if s_obj.F is not None:
                    # check display units selection
                    if "Molar Flow" in st.session_state.display_unit_system:
                        flow_str = f"{s_obj.F:.2f} mol/s"
                        energy_flow_str = f"{s_obj.get_energy_flow(mapped_sp)*1e3:.1f} W"
                    else:
                        flow_str = f"{s_obj.get_mass_flow(mapped_sp):.1f} kg/h"
                        energy_flow_str = f"{s_obj.get_energy_flow(mapped_sp):.3f} kW"
                        
                    energy_summary.append({
                        "Stream ID": s_id,
                        "Temperature (K)": f"{s_obj.T:.2f}" if s_obj.T else "None",
                        "Pressure (kPa)": f"{s_obj.P/1000:.1f}" if s_obj.P else "None",
                        "Molar Enthalpy (J/mol)": f"{s_obj.get_enthalpy(mapped_sp):.1f}",
                        "Total Flow": flow_str,
                        "Energy Flow Rate": energy_flow_str
                    })
            if energy_summary:
                st.write("##### Streams Energy Flows")
                st.table(energy_summary)
                
                st.write("##### Equipment Energy Inputs (Q & W)")
                equip_energy = []
                for u in units_obj_list:
                    equip_energy.append({
                        "Node ID": u.unit_id,
                        "Heat Duty (Q)": f"{u.heat_duty/1000:.3f} kW",
                        "Mechanical Work (W)": f"{u.work_input/1000:.3f} kW"
                    })
                st.table(equip_energy)
                
                # Overall Energy conservation report
                e_bal = FlowsheetSolver.compile_energy_balance(units_obj_list, list(streams_obj_map.values()), mapped_sp)
                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1:
                    st.metric("Boundary Inlet Energy Flow", f"{e_bal['inlet_energy_kW']:.3f} kW")
                with col_e2:
                    st.metric("Boundary Outlet Energy Flow", f"{e_bal['outlet_energy_kW']:.3f} kW")
                with col_e3:
                    diff_val = f"{e_bal['energy_balance_error_kW']:.3f} kW"
                    status_lbl = "Conserved (Green)" if e_bal["is_conserved"] else "Energy Imbalance (Red)"
                    st.metric(f"Energy Balance Error ({status_lbl})", diff_val)
            else:
                st.info("Set boundaries and run simulation to populate balances.")

    with tab_vle:
        st.write("#### Non-Ideal VLE & Reaction Kinetics Explorer")
        st.markdown("Analyze binary phase behavior, **NRTL / Wilson azeotropes**, and **Arrhenius reaction rates** in real-time.")
        
        vle_col1, vle_col2 = st.columns([1.2, 2.0])
        with vle_col1:
            st.write("##### VLE System Configuration")
            sp_choices = list(species_map.keys())
            def_sp1 = "Ethanol" if "Ethanol" in sp_choices else sp_choices[0]
            def_sp2 = "Water" if "Water" in sp_choices else sp_choices[min(1, len(sp_choices)-1)]
            
            vle_sp1 = st.selectbox("Light Component (Species 1)", sp_choices, index=sp_choices.index(def_sp1), key="vle_sp1_sel")
            vle_sp2 = st.selectbox("Heavy Component (Species 2)", sp_choices, index=sp_choices.index(def_sp2), key="vle_sp2_sel")
            
            vle_model = st.radio("Activity Model", ["NRTL", "Wilson"], horizontal=True, key="vle_model_rad")
            vle_press_kpa = st.number_input("System Pressure (kPa)", min_value=10.0, max_value=2000.0, value=101.325, step=10.0, key="vle_press_num")
            
            st.write("##### Reaction Kinetics Inspector")
            rxn_options = list(REACTION_PACKAGES.keys())
            chosen_rxn_pkg = st.selectbox("Inspect Reaction Scheme", rxn_options, key="vle_rxn_pkg_sel")
            rxn_net = REACTION_PACKAGES[chosen_rxn_pkg]
            for r_item in rxn_net.reactions:
                st.caption(f"**{r_item.name}** | $\\Delta H_{{298}} = {r_item.delta_H_298/1000.0:.1f}$ kJ/mol | $E_a = {r_item.Ea_f/1000.0:.1f}$ kJ/mol")
                
        with vle_col2:
            if vle_sp1 == vle_sp2:
                st.warning("Please choose two different chemical species for VLE evaluation.")
            else:
                sp1_obj = species_map[vle_sp1]
                sp2_obj = species_map[vle_sp2]
                diag_data = VLEPhaseDiagramGenerator.generate_diagram(
                    sp1_obj, sp2_obj, total_pressure=vle_press_kpa * 1000.0, model=vle_model.lower(), num_points=50
                )
                
                if diag_data["has_azeotrope"]:
                    st.success(f"🎯 **Azeotropic Inversion Detected ({vle_model})**: $x_{{{vle_sp1}}} = {diag_data['azeotrope_x1']*100.0:.2f}\\,\\text{{mol}}\\%$, $T_{{az}} = {diag_data['azeotrope_T_K'] - 273.15:.2f}\\,^\\circ\\text{{C}}$ (${diag_data['azeotrope_T_K']:.2f}\\,\\text{{K}}$)")
                else:
                    st.info(f"Zeotropic System: No binary azeotrope under {vle_press_kpa:.1f} kPa with {vle_model}.")
                    
                # Plot x-y Equilibrium Curve
                fig_vle = go.Figure()
                fig_vle.add_trace(go.Scatter(x=diag_data["x1"], y=diag_data["y1"], mode="lines", name="VLE Curve (x vs y)", line=dict(color="#0ea5e9", width=3)))
                fig_vle.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Diagonal (x = y)", line=dict(color="#64748b", dash="dash")))
                if diag_data["has_azeotrope"]:
                    fig_vle.add_trace(go.Scatter(
                        x=[diag_data["azeotrope_x1"]], y=[diag_data["azeotrope_x1"]],
                        mode="markers", name="Azeotrope Pinch",
                        marker=dict(size=12, color="#ef4444", symbol="star")
                    ))
                fig_vle.update_layout(
                    title=f"x-y Equilibrium Curve: {vle_sp1} + {vle_sp2} ({vle_model} at {vle_press_kpa:.1f} kPa)",
                    xaxis_title=f"Liquid Mole Fraction x ({vle_sp1})",
                    yaxis_title=f"Vapor Mole Fraction y ({vle_sp1})",
                    height=320,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_vle, use_container_width=True)
                
                # Plot T-x-y Phase Envelope
                fig_txy = go.Figure()
                t_celsius = [t - 273.15 for t in diag_data["T_bubble"]]
                fig_txy.add_trace(go.Scatter(x=diag_data["x1"], y=t_celsius, mode="lines", name="Bubble Point T-x", line=dict(color="#10b981", width=2.5)))
                fig_txy.add_trace(go.Scatter(x=diag_data["y1"], y=t_celsius, mode="lines", name="Dew Point T-y", line=dict(color="#f97316", width=2.5)))
                fig_txy.update_layout(
                    title=f"T-x-y Phase Envelope: {vle_sp1} + {vle_sp2}",
                    xaxis_title=f"Mole Fraction of {vle_sp1}",
                    yaxis_title="Temperature (°C)",
                    height=300,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_txy, use_container_width=True)

    with tab_econ:
        st.write("#### Techno-Economic Assessment & Capital Costing (Turton & Guthrie)")
        st.markdown("Rigorous equipment sizing, materials of construction, Bare Module Cost ($C_{BM}$), plant-wide CAPEX, utility OPEX, and project profitability.")

        # Economic Configuration
        with st.expander("⚙️ Economic Parameters & Utility Cost Rates", expanded=False):
            tea_c1, tea_c2, tea_c3 = st.columns(3)
            with tea_c1:
                econ_cepci = st.slider("CEPCI Cost Index (Base: 397 in 2001)", min_value=397.0, max_value=1200.0, value=825.0, step=5.0)
                econ_plant_mode = st.selectbox("Project Investment Type", ["Grassroots Plant", "Battery-Limits Expansion"])
            with tea_c2:
                econ_mat_override = st.selectbox("Material Override (All Units)", ["None (Use Unit Specified)", "Carbon Steel", "Stainless Steel 316", "Titanium", "Hastelloy C-276", "Monel"])
                econ_op_hours = st.number_input("Annual Operating Hours (h/yr)", min_value=1000.0, max_value=8760.0, value=8000.0, step=500.0)
            with tea_c3:
                econ_elec_rate = st.number_input("Electricity Rate ($/kWh)", min_value=0.01, max_value=0.50, value=0.085, step=0.01)
                econ_steam_rate = st.number_input("LP Steam Rate ($/GJ)", min_value=0.5, max_value=30.0, value=4.50, step=0.5)
                econ_cool_rate = st.number_input("Cooling Water Rate ($/GJ)", min_value=0.05, max_value=5.0, value=0.354, step=0.05)

        if not units_obj_list:
            st.info("No equipment units in flowsheet. Add equipment in the sidebar to view capital costing.")
        else:
            mat_arg = None if econ_mat_override.startswith("None") else econ_mat_override
            custom_rates = {
                "electricity_usd_per_kwh": econ_elec_rate,
                "low_pressure_steam_usd_per_gj": econ_steam_rate,
                "cooling_water_usd_per_gj": econ_cool_rate
            }

            econ_results = FlowsheetSolver.compile_flowsheet_economics(
                units_list=units_obj_list,
                streams_list=list(streams_obj_map.values()),
                species_map=mapped_sp,
                cepci=econ_cepci,
                plant_mode=econ_plant_mode,
                operating_hours=econ_op_hours,
                material_override=mat_arg,
                utility_rates=custom_rates
            )
            capex = econ_results["capex"]
            opex = econ_results["opex"]
            prof = econ_results["profitability"]
            eq_costs = econ_results["equipment_costs"]

            # 1. Top KPI Metric Cards
            kpi_c1, kpi_c2, kpi_c3, kpi_c4, kpi_c5 = st.columns(5)
            kpi_c1.metric("Bare Module Cost ($C_{BM}$)", f"${capex['total_bare_module_cost_C_BM']:,.0f}")
            kpi_c2.metric("Fixed Capital (FCI)", f"${capex['fixed_capital_investment_FCI']:,.0f}")
            kpi_c3.metric("Total Investment (TCI)", f"${capex['total_capital_investment_TCI']:,.0f}")
            kpi_c4.metric("Annual Utility OPEX", f"${opex['total_annual_utility_opex_usd']:,.0f}/yr")
            npv_val = prof['net_present_value_NPV_usd']
            kpi_c5.metric("15-Yr Project NPV", f"${npv_val:,.0f}", f"Payback: {prof['payback_period_years']} yrs")

            st.write("---")

            # 2. Detailed Equipment Breakdown Table
            st.write("##### Equipment Sizing & Bare Module Cost Breakdown")
            table_rows = []
            for item in eq_costs:
                table_rows.append({
                    "Node ID": item.get("unit_id"),
                    "Unit Type": item.get("unit_type"),
                    "Sizing Metric": f"{item.get('sizing_parameter')}: {item.get('sizing_value')} {item.get('sizing_unit')}",
                    "Material": item.get("material"),
                    "P (bar)": f"{item.get('design_pressure_bar'):.1f}",
                    "F_P": f"{item.get('F_P'):.2f}",
                    "F_M": f"{item.get('F_M'):.2f}",
                    "Purchased Cp ($)": f"${item.get('Cp', 0.0):,.0f}",
                    "Bare Module C_BM ($)": f"${item.get('C_BM', 0.0):,.0f}",
                    "Notes": item.get("notes", "")
                })
            st.dataframe(table_rows, use_container_width=True)

            # 3. Visualizations
            st.write("##### Capital & Operational Expenditure Analysis")
            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                # Donut Chart: Equipment C_BM Distribution
                labels = [f"{item['unit_id']} ({item['unit_type']})" for item in eq_costs]
                values = [item['C_BM'] for item in eq_costs]
                fig_donut = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.45)])
                fig_donut.update_layout(
                    title="Bare Module Cost Distribution ($C_{BM}$ by Unit)",
                    height=340,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_donut, use_container_width=True)

            with chart_col2:
                # Waterfall Chart: CAPEX Buildup
                cp_total = capex["total_purchased_cost_Cp"]
                c_bm_total = capex["total_bare_module_cost_C_BM"]
                field_install = max(0.0, c_bm_total - cp_total)
                contingency = capex["contingency_fee"]
                contractor = capex["contractor_fee"]
                site_dev = capex["site_development_cost"]
                wc = capex["working_capital_WC"]
                tci = capex["total_capital_investment_TCI"]

                wf_x = ["Purchased Eq (Cp)", "Direct/Indirect Field", "Bare Module (C_BM)", "Contingency (15%)", "Contractor Fee (3%)", "Site Infrastructure", "Working Capital (15%)", "Total Investment (TCI)"]
                wf_y = [cp_total, field_install, 0, contingency, contractor, site_dev, wc, 0]
                wf_measure = ["relative", "relative", "total", "relative", "relative", "relative", "relative", "total"]

                fig_wf = go.Figure(go.Waterfall(
                    name="CAPEX",
                    orientation="v",
                    measure=wf_measure,
                    x=wf_x,
                    textposition="outside",
                    text=[f"${v/1000:,.0f}k" if v != 0 else "" for v in [cp_total, field_install, c_bm_total, contingency, contractor, site_dev, wc, tci]],
                    y=wf_y,
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                ))
                fig_wf.update_layout(
                    title="CAPEX Buildup Waterfall ($ USD)",
                    height=340,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_wf, use_container_width=True)

            chart_col3, chart_col4 = st.columns(2)

            with chart_col3:
                # Donut Chart: Utility OPEX
                u_labels = ["Electricity", "Steam Heating", "Cooling Water", "Refrigeration"]
                u_vals = [
                    opex["annual_electricity_cost_usd"],
                    opex["annual_steam_cost_usd"],
                    opex["annual_cooling_water_cost_usd"],
                    opex["annual_refrigeration_cost_usd"]
                ]
                active_u = [(l, v) for l, v in zip(u_labels, u_vals) if v > 0]
                if active_u:
                    fig_u = go.Figure(data=[go.Pie(labels=[x[0] for x in active_u], values=[x[1] for x in active_u], hole=0.45)])
                    fig_u.update_layout(
                        title=f"Annual Utility OPEX Breakdown (${opex['total_annual_utility_opex_usd']:,.0f}/yr)",
                        height=340,
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    st.plotly_chart(fig_u, use_container_width=True)
                else:
                    st.info("No utility duty recorded for current flowsheet operation.")

            with chart_col4:
                # Line Chart: Cumulative Discounted Cash Flow & NPV
                cum_cf = prof["cumulative_cash_flow"]
                years = prof["cash_flow_years"]
                fig_cf = go.Figure()
                fig_cf.add_trace(go.Scatter(
                    x=years, y=cum_cf, mode="lines+markers",
                    name="Cumulative DCF", line=dict(color="#10b981", width=3)
                ))
                fig_cf.add_hline(y=0.0, line_dash="dash", line_color="#ef4444", annotation_text="Break-Even Line")
                fig_cf.update_layout(
                    title=f"15-Year Cumulative Discounted Cash Flow (NPV: ${prof['net_present_value_NPV_usd']:,.0f})",
                    xaxis_title="Project Year",
                    yaxis_title="Cumulative Discounted Cash Flow ($ USD)",
                    height=340,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_cf, use_container_width=True)

    with tab_dynamic:
        st.write("#### Real-Time Dynamic Distillation Control & Transients")
        st.markdown(
            "Rigorous stage-by-stage dynamic simulation with transient molar holdups $M_i$, hydraulic coupling, "
            "decoupled level controllers ($LC_D$, $LC_B$), sensitive tray temperature control ($TC$), "
            "and real-time disturbance scenarios."
        )

        # Initialize session state for dynamic simulation
        if "dyn_engine" not in st.session_state:
            dyn_col = DynamicDistillationColumn(
                "C-101-DYN", "Dynamic Ethanol-Water Fractionator", 
                num_stages=12, feed_stage=6, reflux_ratio=2.5
            )
            dyn_eng = DynamicSimulationEngine(dyn_col)
            dyn_eng.run_transient(duration=50.0, dt=1.0)
            st.session_state.dyn_engine = dyn_eng

        dyn_eng = st.session_state.dyn_engine

        # Controls Toolbar
        st.write("##### 🕹️ Dynamic Simulation Operator Console")
        op_col1, op_col2, op_col3, op_col4 = st.columns([1, 1, 1, 3])

        with op_col1:
            if st.button("▶ Step +10s", use_container_width=True, help="Simulate forward 10 seconds (dt=1.0s)"):
                dyn_eng.run_transient(duration=10.0, dt=1.0)
                st.rerun()

        with op_col2:
            if st.button("⏩ Run +60s", use_container_width=True, help="Simulate forward 60 seconds (dt=1.0s)"):
                dyn_eng.run_transient(duration=60.0, dt=1.0)
                st.rerun()

        with op_col3:
            if st.button("🔄 Reset Baseline", use_container_width=True, help="Reset dynamic column to nominal steady baseline"):
                dyn_col = DynamicDistillationColumn(
                    "C-101-DYN", "Dynamic Ethanol-Water Fractionator", 
                    num_stages=12, feed_stage=6, reflux_ratio=2.5
                )
                dyn_eng = DynamicSimulationEngine(dyn_col)
                dyn_eng.run_transient(duration=50.0, dt=1.0)
                st.session_state.dyn_engine = dyn_eng
                st.rerun()

        with op_col4:
            dist_choice = st.selectbox(
                "Inject Process Disturbance Preset",
                [
                    "Nominal Baseline (Clear All Disturbances)",
                    "Feed Flowrate Surge (+25% Feed Load)",
                    "Feed Heavy Composition Drop (-20% Light Key)",
                    "Feed Subcooling Thermal Chill (-15 K)",
                    "Condenser Cooling Water Cut (-30% Condenser Duty)",
                    "Reboiler Steam Loss (-25% Boilup Duty)"
                ],
                index=0
            )

        # Disturbance trigger and reset row
        dist_c1, dist_c2 = st.columns([2, 4])
        with dist_c1:
            if st.button("⚡ Inject / Apply Disturbance", use_container_width=True):
                if "Surge" in dist_choice:
                    dyn_eng.inject_disturbance("feed_surge", magnitude=1.25)
                elif "Composition" in dist_choice:
                    dyn_eng.inject_disturbance("feed_composition_drop", magnitude=0.80)
                elif "Subcooling" in dist_choice:
                    dyn_eng.inject_disturbance("feed_subcooling", magnitude=15.0)
                elif "Cooling Water" in dist_choice:
                    dyn_eng.inject_disturbance("cooling_water_failure", magnitude=0.70)
                elif "Steam Loss" in dist_choice:
                    dyn_eng.inject_disturbance("steam_cut", magnitude=0.75)
                else:
                    dyn_eng.active_disturbances.clear()
                st.rerun()

        with dist_c2:
            active_dist = dyn_eng.get_active_disturbances_summary()
            st.info(f"**Active Disturbance Scenarios:** `{active_dist}` | **Current Simulation Clock:** `{dyn_eng.current_time:.1f} s`")

        # Alarms Banner
        alarms = dyn_eng.check_alarms()
        if alarms:
            for a in alarms:
                if a["severity"] in ["CRITICAL", "HIGH"]:
                    st.error(f"🚨 **Alarm {a['alarm_code']}** ({a['tag']}): {a['message']} | Measured: `{a['current_value']:.2f}` (Limit: `{a['threshold']:.2f}`)")
                else:
                    st.warning(f"⚠️ **Alarm {a['alarm_code']}** ({a['tag']}): {a['message']} | Measured: `{a['current_value']:.2f}` (Limit: `{a['threshold']:.2f}`)")
        else:
            st.success("🟢 **All Safety Alarms Normal**: Liquid holdups and tray temperatures operating within safety interlock boundaries.")

        st.write("---")

        # 4 Multi-channel strip charts
        st.write("##### 📈 Real-Time Multi-Channel Strip Charts")
        hist = dyn_eng.history
        t_hist = hist["time"]

        sc_col1, sc_col2 = st.columns(2)

        with sc_col1:
            # Channel 1: Compositions
            fig_comp = go.Figure()
            fig_comp.add_trace(go.Scatter(x=t_hist, y=hist["xD"], name="Distillate xD (Light)", line=dict(color="#3b82f6", width=2.5)))
            fig_comp.add_trace(go.Scatter(x=t_hist, y=hist["xB"], name="Bottoms xB (Light)", line=dict(color="#f59e0b", width=2.5)))
            fig_comp.add_trace(go.Scatter(x=t_hist, y=hist["x_sens"], name="Stage 6 x_sens", line=dict(color="#10b981", width=1.5, dash="dot")))
            fig_comp.update_layout(
                title="Channel 1: Product & Tray Compositions vs Time",
                xaxis_title="Simulation Time (s)",
                yaxis_title="Mole Fraction (x)",
                height=320,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_comp, use_container_width=True)

        with sc_col2:
            # Channel 2: Temperatures
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(x=t_hist, y=hist["T_condenser"], name="Condenser T_top (K)", line=dict(color="#06b6d4", width=2)))
            fig_temp.add_trace(go.Scatter(x=t_hist, y=hist["T_sensitive"], name="Stage 6 T_sens (Control)", line=dict(color="#ef4444", width=2.5)))
            fig_temp.add_trace(go.Scatter(x=t_hist, y=hist["T_reboiler"], name="Reboiler T_bot (K)", line=dict(color="#8b5cf6", width=2)))
            fig_temp.add_hline(y=dyn_eng.column.temp_controller.setpoint, line_dash="dash", line_color="#dc2626", annotation_text="T_SP")
            fig_temp.update_layout(
                title="Channel 2: Column Temperature Profiles vs Time",
                xaxis_title="Simulation Time (s)",
                yaxis_title="Temperature (K)",
                height=320,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_temp, use_container_width=True)

        sc_col3, sc_col4 = st.columns(2)

        with sc_col3:
            # Channel 3: Vessel Levels
            fig_lvl = go.Figure()
            # Normalize to percent of nominal holdup
            acc_pct = [m / 50.0 * 100.0 for m in hist["M_acc"]]
            sump_pct = [m / 60.0 * 100.0 for m in hist["M_sump"]]
            fig_lvl.add_trace(go.Scatter(x=t_hist, y=acc_pct, name="Accumulator Level (%)", line=dict(color="#0284c7", width=2.5)))
            fig_lvl.add_trace(go.Scatter(x=t_hist, y=sump_pct, name="Sump Reboiler Level (%)", line=dict(color="#d97706", width=2.5)))
            fig_lvl.add_hline(y=100.0, line_dash="dash", line_color="#10b981", annotation_text="Level Setpoint (100%)")
            fig_lvl.add_hline(y=120.0, line_dash="dot", line_color="#f87171", annotation_text="LAH (120%)")
            fig_lvl.add_hline(y=50.0, line_dash="dot", line_color="#ef4444", annotation_text="LAL (50%)")
            fig_lvl.update_layout(
                title="Channel 3: Vessel Liquid Inventories (% of Nominal)",
                xaxis_title="Simulation Time (s)",
                yaxis_title="Inventory (%)",
                height=320,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_lvl, use_container_width=True)

        with sc_col4:
            # Channel 4: Controller Flow Rates
            fig_flow = go.Figure()
            fig_flow.add_trace(go.Scatter(x=t_hist, y=hist["reflux_flow"], name="Reflux L (mol/s)", line=dict(color="#2563eb", width=2)))
            fig_flow.add_trace(go.Scatter(x=t_hist, y=hist["distillate_flow"], name="Distillate D (mol/s)", line=dict(color="#059669", width=2)))
            fig_flow.add_trace(go.Scatter(x=t_hist, y=hist["bottoms_flow"], name="Bottoms B (mol/s)", line=dict(color="#d97706", width=2)))
            fig_flow.add_trace(go.Scatter(x=t_hist, y=hist["vapor_boilup"], name="Vapor Boilup V (mol/s)", line=dict(color="#7c3aed", width=1.5, dash="dash")))
            fig_flow.update_layout(
                title="Channel 4: Manipulated & Output Flows vs Time",
                xaxis_title="Simulation Time (s)",
                yaxis_title="Molar Flow (mol/s)",
                height=320,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_flow, use_container_width=True)

        st.write("---")

        # Auto-Tuning Laboratory Expander
        with st.expander("🛠️ Distillation Temperature Auto-Tuning Laboratory (FOPDT & ZN/Cohen-Coon/IMC)", expanded=False):
            st.write(
                "Run an in-situ open-loop step test on the reflux flow $L$ to identify First-Order Plus Dead-Time (FOPDT) "
                "dynamics and compute industrial tuning parameters."
            )
            at_c1, at_c2, at_c3, at_c4 = st.columns([1, 1, 1, 1])
            with at_c1:
                step_amp = st.number_input("Step Amplitude Δu (mol/s)", value=0.5, step=0.1)
            with at_c2:
                step_t = st.number_input("Step Injection Time (s)", value=5.0, step=1.0)
            with at_c3:
                step_dur = st.number_input("Total Duration (s)", value=120.0, step=10.0)
            with at_c4:
                run_test_btn = st.button("⚡ Run Open-Loop Step Test", use_container_width=True)

            if run_test_btn:
                with st.spinner("Injecting step change and fitting FOPDT transfer function..."):
                    step_res = AutoTuner.perform_step_test(
                        column=dyn_eng.column,
                        step_input="reflux_flow",
                        step_amplitude=step_amp,
                        step_time=step_t,
                        total_time=step_dur,
                        dt=1.0
                    )
                    fopdt = AutoTuner.fit_fopdt(step_res["time"], step_res["input"], step_res["output"], dt=1.0)
                    tuning_rules = AutoTuner.get_full_tuning_comparison(fopdt["Kp"], fopdt["theta"], fopdt["tau_p"])
                    st.session_state.step_res = step_res
                    st.session_state.fopdt = fopdt
                    st.session_state.tuning_rules = tuning_rules
                    st.success("FOPDT Model Identification and Tuning Synthesis Complete!")

            if "fopdt" in st.session_state and st.session_state.fopdt is not None:
                fopdt = st.session_state.fopdt
                tr = st.session_state.tuning_rules

                f_c1, f_c2, f_c3, f_c4 = st.columns(4)
                f_c1.metric("Process Gain (Kp)", f"{fopdt['Kp']:.4f} K/(mol/s)")
                f_c2.metric("Apparent Dead Time (θ)", f"{fopdt['theta']:.2f} s")
                f_c3.metric("Time Constant (τp)", f"{fopdt['tau_p']:.2f} s")
                f_c4.metric("Model Fit (R²)", f"{fopdt['r_squared']:.4f}")

                # Step test response plot
                step_res = st.session_state.step_res
                fig_fit = go.Figure()
                fig_fit.add_trace(go.Scatter(x=step_res["time"], y=step_res["output"], name="Actual Stage 6 Temp", line=dict(color="#ef4444", width=2.5)))
                fig_fit.add_trace(go.Scatter(x=step_res["time"], y=fopdt["simulated_output"], name="FOPDT Model Fit", line=dict(color="#10b981", width=2, dash="dash")))
                fig_fit.update_layout(
                    title="Open-Loop Step Response vs FOPDT Model",
                    xaxis_title="Time (s)",
                    yaxis_title="Stage Temperature (K)",
                    height=280,
                    margin=dict(l=20, r=20, t=35, b=20)
                )
                st.plotly_chart(fig_fit, use_container_width=True)

                # Tuning Rules Comparison Table
                st.write("##### Synthesized Industrial PID / PI Tuning Rules")
                t_rows = []
                for rule_name, params in tr.items():
                    t_rows.append({
                        "Rule": rule_name,
                        "Type": params.get("type", "PID"),
                        "Gain Kc": f"{params.get('Kc', 0.0):.4f}",
                        "Integral Time τ_I (s)": f"{params.get('tau_I', 0.0):.2f}" if params.get('tau_I') else "N/A",
                        "Derivative Time τ_D (s)": f"{params.get('tau_D', 0.0):.2f}" if params.get('tau_D') else "0.0",
                        "Ki (1/s)": f"{params.get('Ki', 0.0):.4f}" if params.get('Ki') else "N/A",
                        "Kd (s)": f"{params.get('Kd', 0.0):.4f}" if params.get('Kd') else "0.0"
                    })
                st.dataframe(t_rows, use_container_width=True)

                # Apply selected tuning
                rule_options = list(tr.keys())
                sel_rule = st.selectbox("Select Tuning Rule to Apply to TC", rule_options, index=rule_options.index("IMC_Moderate") if "IMC_Moderate" in rule_options else 0)
                if st.button("Apply Selected Tuning to Temperature Controller"):
                    applied = tr[sel_rule]
                    dyn_eng.column.temp_controller.kp = abs(applied.get("Kc", 1.0))
                    dyn_eng.column.temp_controller.ki = abs(applied.get("Ki", 0.05))
                    dyn_eng.column.temp_controller.kd = abs(applied.get("Kd", 0.0))
                    st.success(f"Applied {sel_rule} to C-101 TC: Kp={dyn_eng.column.temp_controller.kp:.4f}, Ki={dyn_eng.column.temp_controller.ki:.4f}, Kd={dyn_eng.column.temp_controller.kd:.4f}")

        st.write("---")

        # 5. Flowsheet Data Packages & Engineering Reporting
        st.write("##### 📄 Flowsheet Data Packages & Engineering Reporting")
        st.markdown(
            "Export the complete flowsheet topology, mass/energy balance, equipment sizing, "
            "and Turton & Guthrie economics to standardized data formats."
        )

        rep_c1, rep_c2 = st.columns(2)

        # Baseline economics for export
        export_econ = FlowsheetSolver.compile_flowsheet_economics(
            units_list=units_obj_list,
            streams_list=list(streams_obj_map.values()),
            species_map=mapped_sp
        ) if len(units_obj_list) > 0 else None

        with rep_c1:
            st.write("###### 📦 Flowsheet Model JSON Data Package")
            st.write("Complete state package containing units, stream tables, compositions, and economics.")
            json_export = ReportGenerator.export_flowsheet_json(
                units_map=units_obj_map,
                streams_map=streams_obj_map,
                connections=st.session_state.fs_connections,
                boundaries=st.session_state.fs_boundaries,
                econ_results=export_econ
            )
            st.download_button(
                label="📥 Download Flowsheet JSON Model",
                data=json_export,
                file_name="flowsheet_model_data.json",
                mime="application/json",
                use_container_width=True
            )

        with rep_c2:
            st.write("###### 📑 Turton & Guthrie Engineering Data Sheet")
            st.write("Printable HTML engineering report with mass/energy stream schedules and CAPEX/OPEX.")
            html_export = ReportGenerator.generate_engineering_report_html(
                units_map=units_obj_map,
                streams_map=streams_obj_map,
                connections=st.session_state.fs_connections,
                econ_results=export_econ,
                project_title="Process Engineering Design & Economic Evaluation Report"
            )
            st.download_button(
                label="📄 Download Engineering Data Sheet (HTML)",
                data=html_export,
                file_name="engineering_datasheet.html",
                mime="text/html",
                use_container_width=True
            )

    with tab_pinch:
        st.write("### 🌡️ Pinch Energy Integration & Thermal Network Optimization")
        st.markdown(
            "Synthesize optimal Heat Exchanger Networks (HEN) and determine thermodynamically achievable "
            "**Maximum Energy Recovery (MER)** utility targets via Bodo Linnhoff\'s Problem Table Algorithm."
        )

        # 1. Configuration & Source Controls
        p_c1, p_c2, p_c3, p_c4 = st.columns([3, 2, 2, 2])
        with p_c1:
            stream_source = st.selectbox(
                "Thermal Streams Source",
                [
                    "Auto-Extract from Flowsheet Units",
                    "Linnhoff 4-Stream Classical Benchmark (1982)",
                    "Aromatics BTX Fractionation Train (5 Streams)"
                ],
                index=0,
                help="Choose between live flowsheet thermal units or classical chemical engineering pinch benchmarks."
            )
        with p_c2:
            dt_min = st.slider(
                "Pinch Approach ΔT_min (K)",
                min_value=2.0, max_value=35.0, value=10.0, step=0.5,
                help="Minimum allowable temperature difference between hot and cold streams."
            )
        with p_c3:
            steam_price = st.number_input(
                "LP/HP Steam ($/GJ)",
                min_value=0.5, max_value=50.0, value=4.50, step=0.25,
                help="Cost of hot utility steam per gigajoule."
            )
        with p_c4:
            cw_price = st.number_input(
                "Cooling Water ($/GJ)",
                min_value=0.05, max_value=10.0, value=0.35, step=0.05,
                help="Cost of cold utility cooling water per gigajoule."
            )

        # 2. Extract or Load Streams
        current_streams = []
        if stream_source == "Auto-Extract from Flowsheet Units":
            current_streams = PinchAnalyzer.extract_streams_from_flowsheet(units_obj_map, streams_obj_map)
            if not current_streams:
                st.info(
                    "💡 **No thermal duties detected in current flowsheet.**\n\n"
                    "Add Heaters, Coolers, Heat Exchangers, Distillation Columns, or Flash Drums to the canvas, "
                    "or select **Linnhoff 4-Stream Classical Benchmark** above to explore the Pinch engine."
                )
                if st.button("🧪 Quick-Load Linnhoff 4-Stream Benchmark"):
                    stream_source = "Linnhoff 4-Stream Classical Benchmark (1982)"

        if stream_source == "Linnhoff 4-Stream Classical Benchmark (1982)":
            current_streams = [
                ThermalStream("H1_ReactorEffluent", "HOT", 170.0, 60.0, 330.0, 3.0),
                ThermalStream("H2_ColumnCondenser", "HOT", 150.0, 30.0, 180.0, 1.5),
                ThermalStream("C1_ColumnFeed", "COLD", 20.0, 135.0, 230.0, 2.0),
                ThermalStream("C2_ReboilerBoilup", "COLD", 80.0, 140.0, 240.0, 4.0)
            ]
        elif stream_source == "Aromatics BTX Fractionation Train (5 Streams)":
            current_streams = [
                ThermalStream("H1_AromaticsResidue", "HOT", 210.0, 110.0, 300.0, 3.0),
                ThermalStream("H2_ReboilerCondensate", "HOT", 180.0, 80.0, 450.0, 4.5),
                ThermalStream("H3_TopDistillateVapor", "HOT", 125.0, 65.0, 360.0, 6.0),
                ThermalStream("C1_FreshNaphthaFeed", "COLD", 25.0, 115.0, 450.0, 5.0),
                ThermalStream("C2_StripperReboilerPreheat", "COLD", 70.0, 165.0, 380.0, 4.0)
            ]

        if current_streams:
            # 3. Solve Pinch Targets
            pt_res = PinchAnalyzer.solve_problem_table_algorithm(current_streams, delta_T_min=dt_min)
            cc_res = PinchAnalyzer.generate_composite_curves(current_streams, delta_T_min=dt_min)
            gcc_res = PinchAnalyzer.generate_grand_composite_curve(current_streams, delta_T_min=dt_min)
            econ_res = PinchAnalyzer.calculate_utility_savings(
                current_streams, delta_T_min=dt_min, operating_hours=8000.0,
                utility_rates={"steam_usd_per_gj": steam_price, "cooling_water_usd_per_gj": cw_price}
            )

            # 4. Top KPI Cards
            st.write("##### 🎯 Thermodynamic Targets & Maximum Energy Recovery (MER)")
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric(
                "Pinch Temperatures",
                f"{pt_res['pinch_temperature_hot_C']:.1f} °C / {pt_res['pinch_temperature_cold_C']:.1f} °C",
                f"Shifted T* = {pt_res['pinch_temperature_shifted_C']:.1f} °C",
                help="Hot pinch temperature Th and Cold pinch temperature Tc separated by ΔT_min."
            )
            k2.metric(
                "Min Hot Utility (QH,min)",
                f"{pt_res['Q_hot_utility_min_kW']:.1f} kW",
                f"Unintegrated: {pt_res['total_cold_duty_kW']:.1f} kW",
                delta_color="inverse",
                help="Minimum external heating required above the pinch."
            )
            k3.metric(
                "Min Cold Utility (QC,min)",
                f"{pt_res['Q_cold_utility_min_kW']:.1f} kW",
                f"Unintegrated: {pt_res['total_hot_duty_kW']:.1f} kW",
                delta_color="inverse",
                help="Minimum external cooling required below the pinch."
            )
            k4.metric(
                "Internal Heat Recovery",
                f"{pt_res['Q_heat_recovery_max_kW']:.1f} kW",
                f"{econ_res['energy_reduction_pct']:.1f}% Energy Saved",
                delta_color="normal",
                help="Process-to-process heat exchange potential."
            )
            k5.metric(
                "Annual Energy Savings",
                f"${econ_res['annual_savings_usd']:,.0f} / yr",
                f"-{econ_res['energy_reduction_pct']:.1f}% Utility OPEX",
                delta_color="normal",
                help="Annual OPEX savings achieved by HEN pinch integration."
            )

            st.write("---")

            # 5. Visual Charts (Composite Curves & Grand Composite Curve)
            ch_col1, ch_col2 = st.columns(2)

            with ch_col1:
                # Hot & Cold Composite Curves
                fig_cc = go.Figure()
                fig_cc.add_trace(go.Scatter(
                    x=cc_res["hot_composite"]["enthalpy_kW"],
                    y=cc_res["hot_composite"]["temperature_C"],
                    mode="lines+markers",
                    name="Hot Composite (HCC)",
                    line=dict(color="#ef4444", width=3),
                    marker=dict(size=6, color="#b91c1c")
                ))
                fig_cc.add_trace(go.Scatter(
                    x=cc_res["cold_composite"]["enthalpy_kW"],
                    y=cc_res["cold_composite"]["temperature_C"],
                    mode="lines+markers",
                    name="Cold Composite (CCC)",
                    line=dict(color="#3b82f6", width=3),
                    marker=dict(size=6, color="#1d4ed8")
                ))
                # Add Pinch point annotation
                t_h_p = pt_res['pinch_temperature_hot_C']
                t_c_p = pt_res['pinch_temperature_cold_C']
                fig_cc.add_annotation(
                    text=f"Pinch: ΔT_min = {dt_min:.1f} K<br>(Th = {t_h_p:.1f}°C, Tc = {t_c_p:.1f}°C)",
                    xref="paper", yref="paper",
                    x=0.5, y=0.55,
                    showarrow=False,
                    bgcolor="rgba(255,255,255,0.85)",
                    bordercolor="#10b981",
                    borderwidth=1.5,
                    font=dict(size=11, color="#0f172a")
                )
                fig_cc.update_layout(
                    title="<b>Hot and Cold Composite Curves (T-H)</b>",
                    xaxis_title="Cumulative Enthalpy Flow H (kW)",
                    yaxis_title="Temperature (°C)",
                    legend=dict(x=0.02, y=0.98, bgcolor="rgba(255,255,255,0.6)"),
                    height=380,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_cc, use_container_width=True)

            with ch_col2:
                # Grand Composite Curve (GCC)
                fig_gcc = go.Figure()
                fig_gcc.add_trace(go.Scatter(
                    x=gcc_res["cascaded_heat_flow_kW"],
                    y=gcc_res["shifted_temperature_C"],
                    mode="lines+markers",
                    name="Grand Composite Curve (GCC)",
                    line=dict(color="#8b5cf6", width=3),
                    marker=dict(size=6, color="#6d28d9"),
                    fill="tozerox",
                    fillcolor="rgba(139, 92, 246, 0.12)"
                ))
                # Pinch Point on GCC (H = 0, T* = t_star_pinch)
                fig_gcc.add_trace(go.Scatter(
                    x=[0.0],
                    y=[gcc_res["pinch_shifted_temperature_C"]],
                    mode="markers",
                    name="Pinch Point (H = 0)",
                    marker=dict(size=12, color="#10b981", symbol="diamond")
                ))
                fig_gcc.add_vline(x=0.0, line_width=1, line_dash="dash", line_color="#94a3b8")
                fig_gcc.update_layout(
                    title="<b>Grand Composite Curve (GCC): Shifted T* vs Cascaded Heat</b>",
                    xaxis_title="Cascaded Heat Flow H_cascade (kW)",
                    yaxis_title="Interval Shifted Temperature T* (°C)",
                    legend=dict(x=0.62, y=0.98, bgcolor="rgba(255,255,255,0.6)"),
                    height=380,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_gcc, use_container_width=True)

            # 6. Economic Utility Comparison and HEN Synthesis Rules
            e_col1, e_col2 = st.columns([3, 2])

            with e_col1:
                st.write("##### 💰 Utility OPEX: Unintegrated vs. Pinch MER ($/yr)")
                fig_bar = go.Figure()
                categories = ["Steam Utility (Heating)", "Cooling Water (Cooling)", "Total Annual OPEX"]
                unint_vals = [
                    econ_res["unintegrated_steam_duty_kW"] * (3600.0 * 8000.0 / 1e6) * steam_price,
                    econ_res["unintegrated_cooling_duty_kW"] * (3600.0 * 8000.0 / 1e6) * cw_price,
                    econ_res["unintegrated_annual_cost_usd"]
                ]
                pinch_vals = [
                    econ_res["pinch_steam_duty_kW"] * (3600.0 * 8000.0 / 1e6) * steam_price,
                    econ_res["pinch_cooling_duty_kW"] * (3600.0 * 8000.0 / 1e6) * cw_price,
                    econ_res["pinch_annual_cost_usd"]
                ]
                fig_bar.add_trace(go.Bar(
                    name="Unintegrated Base",
                    x=categories,
                    y=unint_vals,
                    marker_color="#f59e0b",
                    text=[f"${v:,.0f}" for v in unint_vals],
                    textposition="auto"
                ))
                fig_bar.add_trace(go.Bar(
                    name="Pinch MER Optimized",
                    x=categories,
                    y=pinch_vals,
                    marker_color="#10b981",
                    text=[f"${v:,.0f}" for v in pinch_vals],
                    textposition="auto"
                ))
                fig_bar.update_layout(
                    barmode="group",
                    yaxis_title="Annual Utility OPEX ($/year)",
                    height=320,
                    legend=dict(x=0.65, y=0.98, bgcolor="rgba(255,255,255,0.6)"),
                    margin=dict(l=20, r=20, t=30, b=20)
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            with e_col2:
                st.write("##### 📐 HEN Synthesis & Euler Exchanger Targets")
                st.markdown(f"""
                - **Minimum Number of Exchangers (Euler Target):**
                  $$\\mathcal{{N}}_{{\\min}} = \\mathcal{{N}}_{{\\text{{streams}}}} + \\mathcal{{N}}_{{\\text{{utilities}}}} - 1 = \\mathbf{{{econ_res['min_number_of_heat_exchangers']}}}$$
                - **Pinch Decomposition Principle:**
                  - **Above Pinch:** Net heat sink. $\\sum CP_C \\ge \\sum CP_H$. Never use cold utility!
                  - **Below Pinch:** Net heat source. $\\sum CP_H \\ge \\sum CP_C$. Never use hot utility!
                - **Linnhoff Golden Rule:**
                  > *Do not transfer heat across the pinch.* Any heat $\\alpha$ transferred across the pinch penalizes 
                  > both heating and cooling utilities by exactly $+\\alpha$ kW.
                """)
                st.success(
                    f"🏆 **MER Potential:** Recovering **{pt_res['Q_heat_recovery_max_kW']:.1f} kW** eliminates "
                    f"**${econ_res['annual_savings_usd']:,.0f}/year** of recurring utility charges."
                )

            # 7. Thermal Streams Table
            st.write("##### 📋 Thermal Process Streams Schedule")
            streams_table_data = []
            for s in current_streams:
                streams_table_data.append({
                    "Stream Tag": s.stream_id,
                    "Service Type": "🔴 HOT (Requires Cooling)" if s.stream_type == "HOT" else "🔵 COLD (Requires Heating)",
                    "Supply Temp T_in (°C)": f"{s.T_supply_C:.1f}",
                    "Target Temp T_out (°C)": f"{s.T_target_C:.1f}",
                    "Flow Capacity CP (kW/K)": f"{s.CP_kW_per_K:.3f}",
                    "Thermal Duty ΔH (kW)": f"{s.heat_duty_kW:.1f}"
                })
            st.dataframe(streams_table_data, use_container_width=True)

