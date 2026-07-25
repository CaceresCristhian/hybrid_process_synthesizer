# Hybrid First-Principles & ML Process Synthesizer (Version 1.0.0)

A hybrid chemical and biochemical process simulator integrating first-principles conservation equations, dynamic control loops, pressure-flow networks, and Physics-Informed Neural Network (PINN) surrogates.

---

## Core Features

1. **HYSYS-Style Stream Propagation**: material streams automatically calculate degrees of freedom and propagate state variables ($T, P, F, \mathbf{z}, H, V_f$) forward and backward through connected unit operations.
2. **Advanced Thermodynamics (PR-EOS)**: Includes a pure Python implementation of the multi-component Peng-Robinson Equation of State (PR-EOS), isothermal Rachford-Rice flash, and automatic PT Phase Envelope tracers. Supports external wrappers (CoolProp/Thermo) with pure Python fallbacks.
3. **Electrolyte Solutions (e-NRTL & Equilibrium)**: Simulates local composition activity corrections (e-NRTL long-range Debye-Huckel + short-range local composition) and solves multi-species chemical equilibrium systems (pH, weak acid dissociation, salt precipitation limits).
4. **Sequential Modular (SM) & Equation-Oriented (EO) Solvers**: Implements Wegstein acceleration for recycle loops and simultaneous flowsheet equation solving via Newton-Raphson.
5. **Rigorous Column Sizing & Tray Hydraulics**: Auto-sizes column diameter based on the Souders-Brown flooding velocity correlation, calculates sieve tray pressure drops (dry orifice + liquid head), and models side draws and pump-around loops.
6. **Dynamic Pressure-Flow Solver**: Dynamic simulations where flow rates are driven by pressure differentials ($\Delta P$) and valve open fractions.
7. **Streamlit Interactive Dashboard**: User-friendly GUI displaying VLE profiles, strip-charts, and dynamic P&ID layout visualizations.

---

## Directory Structure

*   `app.py` — Streamlit dashboard and user interface.
*   `config/settings.py` — Global constants, solver margins, and version controls.
*   `src/chemical_phenomena/` — Thermodynamics, flash, and electrolytes engines.
*   `src/biological_phenomena/` — Biokinetic (Monod, Haldane) growth rate expressions.
*   `src/control/` — Flowsheet solvers, pressure-flow solver, and PID loops.
*   `src/units/` — Material stream classes, distillation, CSTR, PFR, bioreactor, and control valves.
*   `src/database/` — Component databank loaders, catalog selections.
*   `src/ml_models/` — PINN architecture and training loops.
*   `src/visualization/` — P&ID layout Mermaid generator.

---

## Getting Started

### Prerequisites
*   Python 3.10+
*   pip

### Installation
1. Clone the repository and navigate to the project directory:
   ```bash
   cd hybrid_process_synthesizer
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Simulator
Launch the interactive Streamlit dashboard:
```bash
streamlit run app.py
```

### Running Verification Tests
Execute the test suite to verify thermodynamic and mechanical calculations:
```bash
python -c "import sys; sys.path.append('src'); from tests import run_verification; run_verification.run_tests()"
# Or run the scratch script:
python ../brain/deb365c8-709d-4849-a726-fcc3b3a86708/scratch/run_verification.py
```
