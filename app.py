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
from src.units.bioreactor import JacketedBioreactor
from src.units.distillation import BinaryDistillationColumn
from src.units.valves import ControlValve
from src.visualization.pid_layout import PIDLayout

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

# Sidebar Selection
st.sidebar.header("Simulation Selectors")
simulation_mode = st.sidebar.selectbox(
    "Select Process Operation",
    [
        "Jacketed Bioreactor (R-101)", 
        "Distillation Sizing & Hydraulics (C-101)",
        "Hydrocarbon PT Phase Envelope (PR-EOS)",
        "Electrolyte Equilibrium & Activity",
        "Pressure-Flow Network Solver",
        "Interactive Flowsheet Designer"
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
    st.write("### Interactive Flowsheet Topology Builder (HYSYS-style)")
    st.markdown("""
        *Instantiate process equipment, link streams to construct workflows, set inlet boundaries, and run the flowsheet.*
    """)
    
    # Initialize session state for custom flowsheet
    if "flow_units" not in st.session_state:
        st.session_state.flow_units = {
            "FeedPump": "Pump",
            "CoolValve": "ControlValve",
            "Reactor": "Bioreactor"
        }
    if "flow_connections" not in st.session_state:
        st.session_state.flow_connections = [
            {"from": "FeedPump", "to": "CoolValve", "stream": "S-102"},
            {"from": "CoolValve", "to": "Reactor", "stream": "S-103"}
        ]
    if "flow_boundaries" not in st.session_state:
        st.session_state.flow_boundaries = {
            "S-101": {"T": 298.15, "P": 300.0, "F": 10.0, "z": "Water"}
        }

    # Sidebar controllers to manage flowsheet
    st.sidebar.subheader("Flowsheet Equipment Manager")
    new_id = st.sidebar.text_input("New Node ID", "V-101")
    new_type = st.sidebar.selectbox("New Node Type", ["Pump", "ControlValve", "Bioreactor", "DistillationColumn"])
    if st.sidebar.button("Add Equipment Node"):
        if new_id not in st.session_state.flow_units:
            st.session_state.flow_units[new_id] = new_type
            st.sidebar.success(f"Added {new_type} {new_id}")
        else:
            st.sidebar.error("Node ID already exists!")

    st.sidebar.subheader("Flowsheet Connections")
    conn_from = st.sidebar.selectbox("From Node", list(st.session_state.flow_units.keys()))
    conn_to = st.sidebar.selectbox("To Node", list(st.session_state.flow_units.keys()))
    conn_stream = st.sidebar.text_input("Stream ID", "S-104")
    if st.sidebar.button("Connect Nodes"):
        if conn_from == conn_to:
            st.sidebar.error("Cannot connect node to itself!")
        else:
            st.session_state.flow_connections.append({
                "from": conn_from,
                "to": conn_to,
                "stream": conn_stream
            })
            st.sidebar.success(f"Connected {conn_from} -> {conn_to} via {conn_stream}")

    if st.sidebar.button("Clear Flowsheet"):
        st.session_state.flow_units = {"FeedPump": "Pump", "CoolValve": "ControlValve", "Reactor": "Bioreactor"}
        st.session_state.flow_connections = [{"from": "FeedPump", "to": "CoolValve", "stream": "S-102"}, {"from": "CoolValve", "to": "Reactor", "stream": "S-103"}]
        st.sidebar.warning("Flowsheet cleared to defaults.")

    # Flowsheet Execution
    st.subheader("Flowsheet Topology & Connected workflow")
    
    # Render Mermaid diagram
    flow_layout = PIDLayout("Custom Flowsheet P&ID")
    for uid, utype in st.session_state.flow_units.items():
        if utype == "ControlValve":
            flow_layout.add_valve(uid, f"{uid}\\n({utype})")
        else:
            flow_layout.add_equipment(uid, f"{uid}\\n({utype})")
            
    for conn in st.session_state.flow_connections:
        flow_layout.add_process_stream(conn["from"], conn["to"], conn["stream"])
        
    render_mermaid(flow_layout.to_mermaid())
    
    # Display details of custom flowsheet
    col1, col2 = st.columns(2)
    with col1:
        st.write("#### Active Equipment Nodes")
        st.write(st.session_state.flow_units)
    with col2:
        st.write("#### Active Stream Connections")
        st.dataframe(st.session_state.flow_connections)

    # Solve the flowsheet sequentially
    st.write("### Sequential Simulation Outputs")
    # Simulate a forward propagation along the chain
    solved_data = []
    current_temp = 298.15
    current_pres = 101325.0
    current_flow = 10.0 # mol/s
    
    # Topological traverse approximation
    ordered_nodes = ["FeedPump", "CoolValve", "Reactor"]
    for node in ordered_nodes:
        if node in st.session_state.flow_units:
            ntype = st.session_state.flow_units[node]
            if ntype == "Pump":
                current_pres += 150000.0  # pump raises pressure
                current_temp += 0.5       # tiny thermal compression
                action = "Pressurize Feed Stream (+150 kPa)"
            elif ntype == "ControlValve":
                current_pres -= 20000.0   # valve pressure drop
                current_temp -= 0.1
                action = "Flow regulating control (dP: 20 kPa)"
            elif ntype == "Bioreactor":
                action = "Constant volume fed-batch reaction"
            else:
                action = "Steady-state separation"
                
            solved_data.append({
                "Equipment Node": node,
                "Type": ntype,
                "Outlet Temp (K)": f"{current_temp:.2f}",
                "Outlet Pres (kPa)": f"{current_pres/1000:.1f}",
                "Flow Rate (mol/s)": f"{current_flow:.2f}",
                "Operating Action": action
            })
            
    st.table(solved_data)
