# CA Explorer v11.0

**Substrate Lattice + CANON viability analysis**

A visual laboratory for exploring persistent system dynamics through the 9D Substrate Lattice coordinate system with real-time CANON viability tracking.

---

## Quickstart

```bash
pip install -r requirements.txt
python run.py
```

---

## Architecture

```
X_{t+1} = Π_K(F(X_t))
```

| Symbol | Meaning |
|--------|---------|
| **X** | State in 9D Substrate Lattice (P × I × S) |
| **F** | Dynamic operator (CA evolution) |
| **K** | Constraint region (feasibility bounds) |
| **Π_K** | Projection to feasible space |

### Three planes

| Plane | Layer | Variable | Meaning |
|-------|-------|----------|---------|
| Physical | Constraint | K_P | Grid bounds |
| Physical | State | X_P | Raw CA grid |
| Physical | Dynamic | F_P | CA rule step |
| Informational | Constraint | K_I | Rule grammar |
| Informational | State | X_I | Pattern fingerprint (FFT) |
| Informational | Dynamic | F_I | Pattern evolution |
| Subjective | Constraint | K_S | Belief is a valid PDF |
| Subjective | State | X_S | Interpretation distribution |
| Subjective | Dynamic | F_S | Meaning evolution |

### CANON metrics

| Variable | Meaning |
|----------|---------|
| **ΩV** | Viability margin — distance to infeasibility |
| **Δc*** | Projected collapse margin — rate of ΩV decline |
| **Π** | Regulatory pressure — projection force |
| **H** | History load — accumulated coupling residue |
| **L_P** | Projection loss — information destroyed by Π_K |
| **Γ** | Trajectory entropy — belief spread |
| **T** | Constraint tension |

---

## CA Modes

| Mode | Engine | Notes |
|------|--------|-------|
| `binary` | 1D Elementary CA (rule 0–255) | Default: Rule 110 |
| `trinary` | 1D 3-state CA | Default: Rule 777 |
| `life` | 2D Conway Life variants | Conway, Highlife, Day&Night, Seeds |
| `wire` | 1D Wireworld | Left-click = energy pulse, right-click = wire |

---

## Controls

| Key / Action | Effect |
|---|---|
| `Space` | Pause / resume |
| `→` | Step once (when paused) |
| `R` | Reseed (single) |
| `D` | Reseed (random) |
| `T` | Cycle theme |
| Left-click grid | Inject stimulus |
| Right-click grid | Erase / inject wire (Wireworld) |
| Drag time dial | Adjust speed (0.1× – 10×) |
| Scroll on dial | Fine speed adjustment |
| Click panel title | Collapse / expand panel |
| Click `▷` arrow | Cycle view in panel |

---

## Views

### Physical plane (P)
- **cells** — raw X_P state
- **lattice** — X_P with K_P constraint overlay
- **spacetime** — F_P evolution (space × time)

### Informational plane (I)
- **structure** — X_I pattern spectrum (FFT bars)
- **rule** — K_I rule table heatmap
- **dynamic** — F_I variance over time

### Subjective plane (S)
- **belief** — X_S radial belief chart
- **interpretation** — K_S boundary gauges
- **meaning** — F_S belief evolution (stacked area)

### CANON diagnostics
- **viability** — ΩV trajectory
- **collapse** — Δc* trajectory
- **history** — H accumulation
- **projection_loss** — L_P tracking
- **canon_dashboard** — all CANON metrics at a glance
- **coupling** — P↔I↔S influence network
- **plane_interaction** — Sankey-style flow bars

---

## Presets

| Preset | Mode | Notes |
|--------|------|-------|
| `bacterial_lifecycle` | life | Conway Life, random seed |
| `empire_collapse` | binary | Rule 110, single seed |
| `musical_composition` | trinary | Trinary CA, gradient seed |
| `stable_system` | binary | Rule 4, low entropy |
| `hidden_failure` | binary | Rule 30, chaotic |

---

## Book of Holding Export

```python
from src.io import BookOfHoldingExport
exporter = BookOfHoldingExport(mode="binary")
exporter.export_trajectory(sim.substrate_history, sim.canon_history, "trajectory.json")
```

Exports full 9D trajectory (K, X, F per plane + CANON metrics) as JSON.

---

## Project Structure

```
ca_explorer_v11/
├── run.py                      # Entry point
├── requirements.txt
├── src/
│   ├── core/
│   │   ├── substrate_lattice.py   # 9D coordinate system
│   │   ├── canon_operators.py     # CANON viability math
│   │   ├── ca_engines.py          # F operators (4 types)
│   │   └── integration.py         # Unified simulation loop
│   ├── visualization/
│   │   ├── colors.py              # 4 themes × 3 plane palettes
│   │   ├── view_registry.py       # Abstract ViewRenderer
│   │   ├── physical_views.py      # P-plane views
│   │   ├── informational_views.py # I-plane views
│   │   └── canon_views.py         # CANON + coupling views
│   ├── ui/
│   │   ├── application.py         # Main application
│   │   ├── docking_system.py      # Collapsible panels
│   │   ├── control_panel.py       # Mode / rule / seed controls
│   │   └── time_dial.py           # Circular speed control
│   ├── analytics/
│   │   └── __init__.py            # Entropy, FFT, curvature
│   └── io/
│       └── __init__.py            # Presets, export, BoH format
└── tests/
    └── test_full.py               # 45 tests (4 phases)
```
