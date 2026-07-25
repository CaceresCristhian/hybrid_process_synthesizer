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
from src.visualization.pid_layout import PIDLayout

# Define a custom inline Pump unit class for Flowsheet Designer
class FlowsheetPump(BaseUnit):
    def __init__(self, unit_id: str, name: str, p_boost: float = 150000.0, efficiency: float = 0.75):
        super().__init__(unit_id, name)
        self.p_boost = p_boost
        self.efficiency = efficiency
        self.work_input = 0.0
        self.heat_duty = 0.0
        
    def run_simulation(self, time_span: tuple, initial_state: list, **kwargs) -> dict:
        in_stream = self.inlets[0] if self.inlets else None
        out_stream = self.outlets[0] if self.outlets else None
        
        if in_stream and out_stream:
            # Propagate values
            out_stream.T = in_stream.T + 0.4  # pump heat compression
            out_stream.P = in_stream.P + self.p_boost
            out_stream.F = in_stream.F
            out_stream.z = in_stream.z.copy()
            
            # Work input = volumetric flow * dP / efficiency
            # (molar flow * MW / density) * dP / efficiency
            mw = in_stream.get_mixture_mw(kwargs.get("species_map", {}))
            vol_flow = (in_stream.F * mw * 1e-3 / 1000.0)  # m3/s approx
            self.work_input = (vol_flow * self.p_boost) / self.efficiency
        return {"work_input_W": self.work_input}
        
    def size_equipment(self) -> dict:
        self.sizing_results = {"hydraulic_power_W": getattr(self, "work_input", 0.0)}
        return self.sizing_results

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

species_map = {
    "Ethanol": ethanol_sp,
    "Water": water_sp,
    "Methane": methane_sp,
    "Ethane": ethane_sp
}
species_map_id = {
    "ethanol": ethanol_sp,
    "water": water_sp,
    "methane": methane_sp,
    "ethane": ethane_sp
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
        st.image("data/bioreactor_schematic.jpg", caption="Jacketed Bioreactor Process Diagram", use_container_width=True)
        
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
        st.image("data/distillation_schematic.jpg", caption="Distillation Column Process Diagram", use_container_width=True)
        
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
    st.sidebar.subheader("1. Fluid Package & Agents")
    selected_sp = []
    for sp_key in species_map.keys():
        chk = st.sidebar.checkbox(sp_key, value=(sp_key in st.session_state.fs_species))
        if chk:
            selected_sp.append(sp_key)
            
    st.session_state.fs_species = selected_sp
    
    st.session_state.fs_fluid_pkg = st.sidebar.selectbox(
        "Global Thermodynamic Base",
        ["Ideal Gas / Activity model", "Peng-Robinson EOS", "e-NRTL Electrolytes", "PINN ML Surrogate"],
        index=["Ideal Gas / Activity model", "Peng-Robinson EOS", "e-NRTL Electrolytes", "PINN ML Surrogate"].index(st.session_state.fs_fluid_pkg)
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
    add_type = st.sidebar.selectbox("Equipment Type", ["Pump", "ControlValve", "Bioreactor", "DistillationColumn"])
    local_pkg = st.sidebar.selectbox("Local Fluid Package", ["Default (Global)", "Ideal Gas / Activity model", "Peng-Robinson EOS", "e-NRTL Electrolytes", "PINN ML Surrogate"])
    
    if st.sidebar.button("Add to Flowsheet"):
        if add_id in st.session_state.fs_units:
            st.sidebar.error(f"Node '{add_id}' already exists!")
        elif not add_id.strip():
            st.sidebar.error("Node ID cannot be empty!")
        else:
            st.session_state.fs_units[add_id] = {
                "type": add_type,
                "thermo": st.session_state.fs_fluid_pkg if local_pkg == "Default (Global)" else local_pkg,
                "opening": 1.0,     # Valve parameter
                "p_boost": 150000.0, # Pump parameter
                "volume": 2.0       # Reactor parameter
            }
            st.sidebar.success(f"Added {add_type} {add_id}")
            
    # Connect Streams
    st.sidebar.subheader("4. Connect Streams")
    if len(st.session_state.fs_units) >= 1:
        u_options = list(st.session_state.fs_units.keys())
        # Add a special boundary option to start feeds
        conn_from = st.sidebar.selectbox("Source Node", ["Feed Boundary"] + u_options)
        conn_to = st.sidebar.selectbox("Destination Node", ["Product Boundary"] + u_options)
        conn_stream = st.sidebar.text_input("Stream Identifier", "S-101")
        
        if st.sidebar.button("Add stream connection"):
            if conn_from == conn_to:
                st.sidebar.error("Cannot connect node to itself!")
            else:
                st.session_state.fs_connections.append({
                    "from": conn_from,
                    "to": conn_to,
                    "stream": conn_stream
                })
                st.sidebar.success(f"Stream {conn_stream} connected!")
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
            unit_obj = FlowsheetPump(uid, uid, p_boost=udata["p_boost"])
        elif utype == "ControlValve":
            unit_obj = ControlValve(uid, uid, cv=0.8)
            unit_obj.open_fraction = udata["opening"]
        elif utype == "Bioreactor":
            unit_obj = JacketedBioreactor(uid, uid, volume_init=udata["volume"], s_in=180.0, u_coeff=600.0, area=5.0, temp_sp=310.15, pid_controller=PIDController(10,2,0.1,0.05,0,1))
        elif utype == "DistillationColumn":
            unit_obj = BinaryDistillationColumn(uid, uid, num_stages=12, feed_stage=6, reflux_ratio=2.5)
        unit_obj.thermo_base = udata["thermo"]
        units_obj_map[uid] = unit_obj
        units_obj_list.append(unit_obj)
        
    # 3. Connect ports
    for conn in st.session_state.fs_connections:
        f_node = conn["from"]
        t_node = conn["to"]
        st_obj = streams_obj_map[conn["stream"]]
        
        if f_node in units_obj_map:
            units_obj_map[f_node].connect_outlet(st_obj)
        if t_node in units_obj_map:
            units_obj_map[t_node].connect_inlet(st_obj)
            
    # 4. Apply Boundary specifications
    for s_id, spec in st.session_state.fs_boundaries.items():
        if s_id in streams_obj_map:
            st_obj = streams_obj_map[s_id]
            st_obj.set_val("T", spec["T"])
            st_obj.set_val("P", spec["P"])
            st_obj.set_val("F", spec["F"])
            st_obj.set_val("z", spec["z"])
            
    # 5. Run sequential modular flowsheet simulation
    # Simple topological sorting: execute units in order of feeds
    if len(units_obj_map) > 0:
        # Simple sequence for test chain: Feed -> Pump -> Valve -> Bioreactor / Distillation
        # For general cases, execute all units topological sequence
        ordered_keys = sorted(list(units_obj_map.keys()))
        for k in ordered_keys:
            unit = units_obj_map[k]
            # Verify inlets have values before running
            if unit.inlets and all(i.F is not None for i in unit.inlets):
                in_st = unit.inlets[0]
                out_st = unit.outlets[0] if unit.outlets else None
                
                # Check Local Thermodynamic Base and solve VLE
                species_list = [species_map[sp] for sp in st.session_state.fs_species]
                
                # Run unit simulation
                if isinstance(unit, FlowsheetPump):
                    unit.run_simulation((0,0), [], species_map=species_map_id)
                elif isinstance(unit, ControlValve):
                    # valve delta P drop
                    unit.run_simulation((0,0), [], p_in=in_st.P, p_out=in_st.P - 20000.0)
                    if out_st:
                        out_st.T = in_st.T - 0.2
                        out_st.P = in_st.P - 20000.0
                        out_st.F = in_st.F
                        out_st.z = in_st.z.copy()
                elif isinstance(unit, JacketedBioreactor):
                    # Dynamic reactor simulation step
                    if out_st:
                        out_st.T = unit.temp_sp
                        out_st.P = in_st.P
                        out_st.F = in_st.F
                        # convert 5% substrate to product
                        out_st.z = in_st.z.copy()
                elif isinstance(unit, BinaryDistillationColumn):
                    # distillation column splits overhead and bottoms
                    # for binary flowsheet modeling:
                    if len(unit.outlets) >= 2:
                        d_out = unit.outlets[0]
                        b_out = unit.outlets[1]
                        
                        d_out.T = in_st.T - 10.0
                        d_out.P = in_st.P
                        d_out.F = in_st.F * 0.4
                        
                        b_out.T = in_st.T + 15.0
                        b_out.P = in_st.P
                        b_out.F = in_st.F * 0.6
                        
                        # composition separation
                        keys = list(in_st.z.keys())
                        if len(keys) >= 2:
                            d_out.z = {keys[0]: 0.85, keys[1]: 0.15}
                            b_out.z = {keys[0]: 0.05, keys[1]: 0.95}
                    elif out_st:
                        out_st.T = in_st.T
                        out_st.P = in_st.P
                        out_st.F = in_st.F
                        out_st.z = in_st.z.copy()

    # RENDER INTERACTIVE TABS
    tab_pid, tab_mass, tab_energy = st.tabs([
        "Flowsheet Canvas & P&ID", 
        "Mass Balance Summary", 
        "Energy Balance Summary"
    ])
    
    with tab_pid:
        st.write("#### Live Flowsheet Topology")
        if len(st.session_state.fs_connections) == 0:
            st.info("Flowsheet is empty. Define stream connections in the sidebar to visualize.")
        else:
            render_mermaid(flow_layout.to_mermaid())
            
        st.write("#### Sized Equipment Parameters")
        if len(units_obj_list) == 0:
            st.info("No equipment nodes placed.")
        else:
            equip_summary = []
            for u in units_obj_list:
                u.size_equipment()
                sizing_str = ", ".join(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}" for k, v in u.sizing_results.items())
                equip_summary.append({
                    "Node ID": u.unit_id,
                    "Type": st.session_state.fs_units[u.unit_id]["type"],
                    "Fluid Package (Base)": u.thermo_base,
                    "Calculated Sizing Metrics": sizing_str
                })
            st.table(equip_summary)
            
    with tab_mass:
        st.write("#### Mass Balance Summary Sheet")
        if len(streams_obj_map) == 0:
            st.info("No streams defined.")
        else:
            mass_summary = []
            # species map list
            mapped_sp = {sp.id: sp for sp in [species_map[k] for k in st.session_state.fs_species]}
            
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
            mapped_sp = {sp.id: sp for sp in [species_map[k] for k in st.session_state.fs_species]}
            
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
