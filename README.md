# CA Explorer v11
### Substrate Lattice Visualization + CANON Viability Analysis

**Version:** 11.2.0  
**Status:** Active development  
**Author:** Paul Tobin Peck  
**Framework:** Scalar-3³ Persistence Architecture

---

## What This Is

CA Explorer is an interactive instrument for studying how systems persist, fail, and interact under constraint. It is not a toy or a screensaver.

The program runs one or more cellular automata simultaneously, maps each one into a 9-dimensional coordinate system called the **Substrate Lattice**, and computes **CANON viability metrics** in real time — telling you not just what the system is doing, but how close it is to collapse and why.

The foundational equation governing every system in this program:

```
X_{t+1} = Π_K(F(X_t))
```

Where `X` is a 9D state vector, `F` is the CA evolution operator, `K` is the constraint region, and `Π_K` is the feasibility projection. Every tick, every system, every mode: this is the law.

---

## Quickstart

```bash
pip install -r requirements.txt
python run.py
```

**Requirements:** Python 3.9+, pygame ≥ 2.1, numpy ≥ 1.21, scipy ≥ 1.7

---

## CA Modes

| Mode | Type | Description | Default Rule |
|---|---|---|---|
| **binary** | 1D Elementary CA | 2-state, Wolfram rules 0–255 | Rule 110 |
| **trinary** | 1D 3-state CA | States map to −/0/+ (shed/contain/reinforce) | Rule 777 |
| **life** | 2D Conway variants | Conway, Highlife, Day & Night, Seeds | Conway |
| **wire** | 1D Wireworld | Electron heads propagate through wire | — |

### State Colors (discrete, not gradients)

**Binary:** background = dead · primary color = live  
**Trinary:** grey = contain (0) · green = reinforce (+) · red = shed (−)  
**Wireworld:** dark = empty · dim blue-grey = wire · bright yellow = electron head · orange = tail  
**Life:** background = dead · system color = live

---

## Multi-System Operation

CA Explorer runs up to **6 independent systems simultaneously**. Each system has its own mode, rule, color, and CANON state. They can be coupled to interact.

### Adding and Managing Systems

| Action | How |
|---|---|
| Add system | Click **+** in system strip, or press **=** |
| Select system | Click its tab in the strip, or press **1–6** |
| Remove system | Click **×** on its tab (minimum 1 always kept) |
| Switch display mode | Click **SIDE-BY / OVERLAY** or press **O** |

### Display Modes

**Side-by-side (default):** Each system gets its own column. Interaction is visible as each system evolves under its own rules plus any coupling.

**Overlay (collision chamber):** All systems render to the same surface. This is the right mode for studying how two or more systems with different rules occupy the same space. Use when you want to see interference, not comparison.

### System Coupling

The **COUP** slider sets how much each system's state bleeds into the others. At 0, systems run in complete isolation. At 1, they are strongly coupled and will influence each other's evolution. Coupling is directional (every system pushes to every other), governed by the `CouplingMatrix` in the simulation core.

You can also inject directly from one system into another by clicking within that system's column viewport.

---

## Controls

### Keyboard

| Key | Action |
|---|---|
| `Space` | Pause / resume |
| `→` | Step one generation (while paused) |
| `R` | Reseed selected system (centre seed) |
| `D` | Reseed selected system (random) |
| `T` | Cycle color theme |
| `S` | Toggle settings panel |
| `O` | Toggle side-by-side / overlay |
| `=` / `+` | Add a new system |
| `1`–`6` | Select system 1–6 |
| `Esc` | Quit |

### Mouse

| Action | Effect |
|---|---|
| Left-click viewport | Inject stimulus into that system at that position |
| Right-click viewport | Erase (binary/trinary/life) or write wire (wireworld) |
| Click and drag | Paint continuously |
| Scroll on time dial | Adjust simulation speed |
| Drag time dial centre | Move dial anywhere on screen |
| Click panel title | Collapse / expand that sidebar panel |
| Click ⟳ on panel | Cycle to next view in that panel |
| Drag panel bottom edge | Resize that panel |
| Drag sidebar left edge | Resize the whole sidebar |
| Scroll over sidebar | Scroll through panels |

---

## Settings Panel

Toggle with **S** or the **settings** button. Contains sliders that apply to the currently selected system.

| Slider | Range | Effect |
|---|---|---|
| **RULE** | 0–255 | CA rule number (binary/trinary) |
| **THR** | 0.1–3.0 | Activation threshold |
| **COUP** | 0.0–2.0 | Inter-system coupling strength |
| **INERT** | 0.0–1.0 | State inertia (resistance to change) |
| **PULSE_R** | 1–10 | Injection pulse radius |

---

## Time Dial

The circular dial in the top area controls simulation speed (0.1× – 100×, logarithmic).

- **Drag the needle** (outer arc): adjust speed
- **Drag the centre hub**: move the dial anywhere
- **Scroll while hovering**: fine speed adjustment

Speed is logarithmically spaced. The arc colour shifts from red (slow) to green (fast) proportional to the log-speed position.

---

## Sidebar Views

The right sidebar contains panels. Each panel can show any view — click **⟳** to cycle through them. Panels can be collapsed, resized, and the sidebar itself can be dragged narrower or wider.

### Physical Plane (P) — what the CA is doing

| View | Description |
|---|---|
| **cells** | Raw cell state as a horizontal colour bar |
| **lattice** | Cell state overlaid with constraint boundary indicators |
| **spacetime** | Time × space strip (the canonical CA view) |
| **scope** | Oscilloscope waveform of the current generation |
| **radial** | Time-collapsed polar cross-section — recent history mapped to a circle |
| **vect** | Vectorscope — cell state plotted radially around a circle, trails included |
| **transverse** | End-on cross-section view — concentric rings coloured by spatial zone activity |

### Informational Plane (I) — pattern structure

| View | Description |
|---|---|
| **structure** | FFT pattern fingerprint — spatial frequency spectrum as a bar chart |
| **rule** | Rule table heatmap for the current CA |
| **dynamic** | Pattern variance over time |

### Subjective Plane (S) — interpretation distribution

| View | Description |
|---|---|
| **belief** | Radial belief chart across 8 interpretation categories |
| **interpretation** | Belief constraint boundaries as horizontal gauges |
| **meaning** | Belief distribution evolution (stacked area) |

### CANON Diagnostics — viability tracking

| View | Description |
|---|---|
| **viability** | ΩV — distance to infeasibility, over time |
| **collapse** | Δc* — projected collapse margin |
| **history** | H — accumulated coupling residue (history load) |
| **projection_loss** | L_P — information destroyed by constraint projection |
| **canon_dashboard** | All 7 CANON metrics as vertical bars |
| **coupling** | P↔I↔S influence network diagram |
| **waveform** | 5 orthogonal diagnostic channels: v(t) E(t) H(t) B(t) D(t) |

### The WAVEFORM View (accurate signal analysis)

Five *lawful* projections of the pattern manifold — each measures something real:

| Channel | What it measures |
|---|---|
| **v(t)** | Trajectory velocity — how fast the system state is moving |
| **E(t)** | Transition energy — fraction of cells that changed this step |
| **H(t)** | Novelty entropy — windowed Shannon entropy of the physical state |
| **B(t)** | Boundary proximity — ΩV, distance from infeasibility |
| **D(t)** | Attractor dwell — how long the system has been near a stable state |

These are orthogonal projections: each tells you something the others cannot. Together they form a complete diagnostic waveform.

---

## Presets

Five built-in presets accessible from the IO module:

| Preset | Mode | Description |
|---|---|---|
| `bacterial_lifecycle` | life | Conway Life at 35% density |
| `empire_collapse` | binary | Rule 110 — complex civilisation dynamics |
| `musical_composition` | trinary | Trinary CA — harmonic progression analogue |
| `stable_system` | binary | Rule 4 — low entropy baseline |
| `hidden_failure` | binary | Rule 30 — chaotic, unpredictable collapse |

---

## Exporting Data

### Book of Holding Format

Export the full 9D trajectory as JSON for external visualization:

```python
from src.io import BookOfHoldingExport
exporter = BookOfHoldingExport(mode="binary")
exporter.export_trajectory(
    sim.substrate_history,
    sim.canon_history,
    "trajectory.json"
)
```

Each timestep in the export contains K, X, F for all three planes plus the full CANON state vector.

---

## Themes

Four built-in color themes, toggled with **T** or the theme buttons:

| Theme | Character |
|---|---|
| **dark** | Deep blue-black, cyan/green/violet plane palette |
| **amber** | Retro terminal, warm amber on black |
| **matrix** | Green phosphor, classic CRT |
| **solarized** | Muted teal/blue on dark teal |

---

## Architecture Overview

```
ca_explorer_v11/
├── run.py                          Entry point
├── src/
│   ├── core/
│   │   ├── substrate_lattice.py    9D coordinate system (K, X, F × P, I, S)
│   │   ├── canon_operators.py      Viability math (ΩV, Δc*, Π, H, L_P, Γ, T)
│   │   ├── ca_engines.py           Four CA engines (F operators)
│   │   ├── integration.py          CA → Substrate → CANON unified step
│   │   └── system_manager.py       Multi-system + coupling matrix
│   ├── visualization/
│   │   ├── colors.py               4 themes × 3 plane palettes
│   │   ├── view_registry.py        Abstract ViewRenderer base
│   │   ├── physical_views.py       P-plane views
│   │   ├── informational_views.py  I-plane views
│   │   ├── canon_views.py          CANON + coupling views
│   │   └── scope_views.py          SCOPE, RADIAL, VECT, TRANSVERSE, WAVEFORM
│   ├── ui/
│   │   ├── application.py          Main application loop
│   │   ├── multi_viewport.py       N-system rendering (side-by-side / overlay)
│   │   ├── system_strip.py         System tab strip UI
│   │   ├── docking_system.py       Collapsible/resizable sidebar panels
│   │   ├── control_panel.py        Mode/theme/seed/pause controls
│   │   ├── settings_panel.py       RULE/THR/COUP/INERT/PULSE_R sliders
│   │   └── time_dial.py            Circular speed control (draggable)
│   ├── analytics/                  Entropy, FFT, curvature diagnostics
│   └── io/                         Presets, Book of Holding export
└── tests/
    └── test_full.py                59 tests across all phases
```

---

## Key Bindings Reference Card

```
SIMULATION          SYSTEMS              DISPLAY
Space  pause        =      add system    T    cycle theme
→      step once    1–6    select        O    toggle overlay
R      reseed (c)   S      settings      S    toggle settings
D      reseed (r)

DIAL                SIDEBAR              INJECTION
scroll  speed±      drag bottom  resize  LMB   paint/inject
drag    move        drag left    resize  RMB   erase/wire
                    ⟳ button     view    drag  continuous
```

---

*CA Explorer is part of the Substrate Canon ecosystem. See the whitepaper for theoretical foundations.*
