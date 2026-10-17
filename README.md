# Hybrid First-Principles & ML Process Synthesizer (v2.5.0)

A full-stack chemical and biochemical process engineering simulator combining **first-principles conservation laws**, **non-ideal thermodynamic property packages**, **Physics-Informed Neural Network (PINN) activity surrogates**, **dynamic closed-loop PID control**, **Techno-Economic Analysis (TEA)**, **Pinch & Life-Cycle Assessment (LCA)**, **Safety/HAZOP engineering**, and **3D/ISO regulatory deliverables**.

---

## Architecture & Module Inventory (Phases A–K)

| Phase | Subsystem | Key Modules | Engineering Capabilities |
| :--- | :--- | :--- | :--- |
| **Core** | **Thermodynamics & Flash** | `src/chemical_phenomena/thermodynamics.py`, `activity_models.py`, `electrolytes.py` | Peng-Robinson EOS (with $k_{ij}$ binary interaction matrix), bracketed Brent Rachford-Rice isothermal TP flash (with negative-flash single-phase checks), NRTL, Wilson, e-NRTL electrolytes, and iterated fugacity $P$-$T$ phase envelopes. |
| **Core** | **Hybrid ML (PINN)** | `src/ml_models/pinn.py`, `dataset_builder.py`, `train_pinn.py` | PyTorch Physics-Informed Neural Network predicting $\ln \gamma_1, \ln \gamma_2$ as a function of $(x_1, T)$ while enforcing the isothermal Gibbs-Duhem differential constraint via `torch.autograd`. Wired directly into `Thermodynamics.solve_tp_flash(..., method="pinn")`. |
| **Phase A–B** | **Unit Operations & Flowsheet Solver** | `src/units/`, `src/control/flowsheet_solver.py` | `MaterialStream` (DOF analysis, automatic TP flash, 4-term polynomial $C_p(T)$ + latent enthalpy), `BinaryDistillationColumn` (McCabe-Thiele + Souders-Brown sizing + sieve-tray $\Delta P$), `JacketedBioreactor` (Monod/Haldane ODE + PID jacket cooling), `IdealCSTR`, `IdealPFR`, `EquilibriumReactor`, `FlashDrum`, `AbsorptionColumn`, `MembraneUnit`, `SolidLiquidSeparator`, `FlowsheetPump`, `Compressor`, `Expander`, `Heater`, `Cooler`, `HeatExchanger`, `FlowsheetMixer`, `Splitter`, `ControlValve`. Sequential-modular solver with Tarjan SCC tear-stream detection, Wegstein acceleration, and damped Newton-Raphson EO solver. |
| **Phase C** | **Interactive Flowsheet Studio** | `src/visualization/interactive_canvas.py`, `svg_flowsheet.py`, `pid_layout.py` | Custom vector SVG Process Flow Diagrams (PFDs), ISA-5.1 P&IDs with pan/zoom/fullscreen controls, port-level topology wiring, and multi-unit engineering unit converters. |
| **Phase D** | **Techno-Economic Analysis (TEA)** | `src/economics/cost_correlations.py`, `equipment_costing.py`, `capital_costing.py`, `utility_costing.py`, `profitability.py` | Turton & Guthrie bare-module equipment correlations ($C_p^\circ, F_P, F_M, C_{BM}$), CEPCI escalation, Lang/Turton total capital investment (TCI), utility OPEX, and DCF cash-flow metrics (NPV, IRR, Payback, discounted cash-flow tables). |
| **Phase E** | **Dynamic Distillation & Auto-Tuning** | `src/units/dynamic_column.py`, `src/control/dynamic_engine.py`, `auto_tuning.py`, `pid.py` | Tray-by-tray dynamic ODE distillation simulator with dual-ended PID control ($L$-top, $V$-bottoms), derivative-on-measurement anti-kick PID, relay/step-test IMC & Ziegler-Nichols auto-tuning, and 6 disturbance scenarios. |
| **Phase F** | **Pinch & Life-Cycle Assessment** | `src/economics/pinch_analysis.py`, `lca_engine.py` | Problem Table Algorithm (PTA) for $\Delta T_{\min}$ pinch temperature, minimum hot/cold utility targets ($Q_{H,\min}, Q_{C,\min}$), Grand Composite Curves, and Scope 1/2/3 cradle-to-gate $\text{CO}_2\text{e}$ carbon footprinting. |
| **Phase G** | **Process Safety (API 520 & HAZOP)** | `src/safety/relief_sizing.py`, `hazop_analyzer.py` | API 520 / 521 pressure relief valve (PRV) sizing for vapor, liquid, and fire-exposure contingencies (with standard API 526 orifice designation D–T) and automated rule-based HAZOP deviation tables. |
| **Phase H** | **Synthesis & Pareto Optimization** | `src/optimization/sequence_synthesizer.py`, `pareto_optimizer.py` | Heuristic multicomponent distillation sequence synthesis (Direct, Indirect, Splits) and multi-objective NSGA-II-style Pareto optimization (TAC vs. Carbon Intensity) with TOPSIS ranking. |
| **Phase I** | **Predictive Thermo & Solids Processing** | `src/chemical_phenomena/unifac.py`, `pc_saft.py`, `src/units/solids.py` | Predictive UNIFAC group-contribution activity coefficients, PC-SAFT equation of state (hard-chain + dispersive compressibility and fugacity), `ContinuousCrystallizer` (MSMPR population balance), and `SprayDryer`. |
| **Phase J** | **Digital Twin & 3D Plant Layout** | `src/control/digital_twin.py`, `src/visualization/plant_3d_viewer.py` | Industrial OPC-UA tag registry, interactive DCS controller faceplates, equipment fouling/cavitation/weeping health diagnostics, and interactive 3D WebGL isometric plant layout with API 500 / NFPA 30 spacing checks. |
| **Phase K** | **ISO 10628 & Regulatory PDF Export** | `src/reporting/regulatory_standards.py`, `pdf_generator.py`, `report_generator.py` | EU Pressure Equipment Directive (PED 2014/68/EU) Art. 4 classification, OSHA 29 CFR 1910.119 PSM threshold screening, ISO 7200 engineering title blocks, and native multi-page vector PDF / HTML / JSON package export. |

---

## Model Scope & Fidelity Notes

To keep the simulator fast, self-contained, and transparent for academic research and interactive teaching, several modules intentionally implement **reduced-order or screening-level formulations**:
* **Thermodynamics & Flash**: Pure-Python Peng-Robinson, NRTL, Wilson, UNIFAC, and PC-SAFT implementations cover 24 curated chemical species out of the box, with optional bridges to `CoolProp` and Caleb Bell's `thermo` library when installed.
* **Dynamic Column & Bioreactor**: `DynamicDistillationColumn` solves stagewise molar holdup and liquid composition ODEs with constant molar overflow in the rectifying section and feed thermal quality ($q$-line) adjustment in the stripping section.
* **TEA, Pinch, Safety, and Regulatory Modules**: Provide textbook screening calculations (Turton correlations, Linnhoff Problem Table Algorithm, API 520/526 orifice sizing, PED 2014/68/EU fluid-group rules, and OSHA 1910.119 Appendix A thresholds) intended for conceptual process design rather than licensed detailed engineering sign-off.

---

## Installation & Quick Start

### Prerequisites
* Python 3.10+

### 1. Clone and Install
```bash
cd hybrid_process_synthesizer
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Launch the Interactive Dashboard
```bash
streamlit run app.py
```

### 3. Train / Re-evaluate the Thermodynamics PINN
```bash
python src/ml_models/train_pinn.py
```

### 4. Run the Verification & Reference Benchmark Test Suite
```bash
pytest
```

---

## License

Released under the [MIT License](LICENSE).
