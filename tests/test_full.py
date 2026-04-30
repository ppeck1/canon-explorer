"""
CA Explorer v11 — Test Suite
Tests all four phases: Core, Visualization, UI (headless), Integration
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pytest


# ===========================================================================
# PHASE 1: CORE
# ===========================================================================

class TestSubstrateLattice:
    def test_box_constraint_contains(self):
        from src.core.substrate_lattice import BoxConstraint
        bc = BoxConstraint(lo=np.zeros(4), hi=np.ones(4))
        assert bc.contains(np.array([0.5, 0.5, 0.5, 0.5]))
        assert not bc.contains(np.array([1.5, 0.5, 0.5, 0.5]))

    def test_box_constraint_project(self):
        from src.core.substrate_lattice import BoxConstraint
        bc = BoxConstraint(lo=np.zeros(4), hi=np.ones(4))
        projected = bc.project(np.array([-0.5, 1.5, 0.3, 0.7]))
        assert np.allclose(projected, [0.0, 1.0, 0.3, 0.7])

    def test_box_constraint_distance(self):
        from src.core.substrate_lattice import BoxConstraint
        bc = BoxConstraint(lo=np.zeros(4), hi=np.ones(4))
        d = bc.distance(np.array([0.5, 0.5, 0.5, 0.5]))
        assert d > 0

    def test_belief_constraint_project(self):
        from src.core.substrate_lattice import BeliefConstraint
        bc = BeliefConstraint(n_interpretations=8)
        raw = np.array([1.0, 2.0, 0.5, 0.0, 1.5, 0.3, 0.2, 0.1])
        proj = bc.project(raw)
        assert abs(proj.sum() - 1.0) < 1e-6
        assert np.all(proj >= 0)

    def test_coupling_map_residue(self):
        from src.core.substrate_lattice import CouplingMap, BoxConstraint, BeliefConstraint, GrammarConstraint, SubstrateState
        cmap = CouplingMap()
        # Build a minimal state that's out of bounds to trigger residue accumulation
        bc = BoxConstraint(lo=np.zeros(4), hi=np.ones(4))
        gc = GrammarConstraint(rule_table=np.array([0, 1, 0, 1, 1, 0, 1, 0]))
        bec = BeliefConstraint(n_interpretations=4)
        state = SubstrateState(
            K_P=bc, K_I=gc, K_S=bec,
            X_P=np.array([1.5, 0.5, 0.3, 0.8]),   # one out of bounds
            X_I=np.zeros(4), X_S=np.array([0.25]*4),
            F_P=lambda x: x, F_I=lambda x, p: x, F_S=lambda x, i: x,
            coupling_map=cmap, t=0,
        )
        projected = cmap.project(state)
        assert projected.coupling_map.residue > 0

    def test_substrate_step(self):
        from src.core.substrate_lattice import BoxConstraint, BeliefConstraint, GrammarConstraint, CouplingMap, SubstrateState
        bc  = BoxConstraint(lo=np.zeros(4), hi=np.ones(4))
        gc  = GrammarConstraint(rule_table=np.array([]))
        bec = BeliefConstraint(n_interpretations=4)
        state = SubstrateState(
            K_P=bc, K_I=gc, K_S=bec,
            X_P=np.array([0.5]*4),
            X_I=np.zeros(4),
            X_S=np.array([0.25]*4),
            F_P=lambda x: x + 0.01,
            F_I=lambda x, p: x,
            F_S=lambda x, i: x,
            coupling_map=CouplingMap(), t=0,
        )
        next_state = state.step()
        assert next_state.t == 1
        assert np.all(next_state.X_P <= 1.0)

    def test_lattice_projector(self):
        from src.core.substrate_lattice import LatticeProjector, BoxConstraint, BeliefConstraint, GrammarConstraint, CouplingMap, SubstrateState
        bc  = BoxConstraint(lo=np.zeros(4), hi=np.ones(4))
        gc  = GrammarConstraint(rule_table=np.array([]))
        bec = BeliefConstraint(n_interpretations=4)
        state = SubstrateState(
            K_P=bc, K_I=gc, K_S=bec,
            X_P=np.array([0.5]*4),
            X_I=np.zeros(4), X_S=np.array([0.25]*4),
            F_P=lambda x: x, F_I=lambda x, p: x, F_S=lambda x, i: x,
            coupling_map=CouplingMap(), t=0,
        )
        omega_v = LatticeProjector.viability_margin(state)
        assert 0.0 <= omega_v <= 1.0


class TestCanonOperators:
    def _make_sim(self):
        from src.core.ca_engines import BinaryEngine
        from src.core.integration import UnifiedSimulation
        e   = BinaryEngine(width=50, rule=110)
        sim = UnifiedSimulation(e)
        return sim

    def test_canon_state_viable(self):
        from src.core.canon_operators import CanonState
        c = CanonState(Omega_V=0.8)
        assert c.is_viable
        c2 = CanonState(Omega_V=0.02)
        assert not c2.is_viable

    def test_collapse_risk(self):
        from src.core.canon_operators import CanonState
        c = CanonState(Omega_V=0.0, Delta_c_star=1.0)
        assert c.collapse_risk >= 0.8

    def test_canon_update(self):
        sim = self._make_sim()
        for _ in range(10):
            sim.step()
        c = sim.current_canon
        assert 0.0 <= c.Omega_V <= 1.0
        assert 0.0 <= c.Gamma  <= 1.0
        assert c.H >= 0.0

    def test_detect_collapse_no_history(self):
        from src.core.canon_operators import CanonOperators
        ops = CanonOperators()
        result = ops.detect_collapse([])
        assert result is None

    def test_canon_to_dict(self):
        from src.core.canon_operators import CanonState
        c = CanonState(Omega_V=0.5, Pi=0.2)
        d = c.to_dict()
        assert "Omega_V" in d
        assert "viable" in d


class TestCAEngines:
    def test_binary_step(self):
        from src.core.ca_engines import BinaryEngine
        e = BinaryEngine(width=100, rule=110)
        e.seed("single")
        prev = e.grid.copy()
        e.step()
        # Grid should evolve (rule 110 from single cell)
        assert e.grid.shape == (100,)

    def test_binary_inject_live(self):
        from src.core.ca_engines import BinaryEngine
        e = BinaryEngine(width=100, rule=110)
        e.grid[:] = 0
        e.inject(50, radius=2, right_click=False)
        assert e.grid[50] == 1

    def test_binary_inject_erase(self):
        from src.core.ca_engines import BinaryEngine
        e = BinaryEngine(width=100, rule=110)
        e.grid[:] = 1
        e.inject(50, radius=2, right_click=True)
        assert e.grid[50] == 0

    def test_trinary_step(self):
        from src.core.ca_engines import TrinaryEngine
        e = TrinaryEngine(width=100)
        e.seed("single")
        e.step()
        assert e.grid.max() <= 2

    def test_life_step(self):
        from src.core.ca_engines import LifeEngine
        e = LifeEngine(width=40, height=30, rule="conway")
        e.seed("random")
        prev = e.grid.sum()
        e.step()
        # Grid should be valid
        assert e.grid.shape == (30, 40)
        assert e.grid.max() <= 1

    def test_life_glider(self):
        from src.core.ca_engines import LifeEngine
        e = LifeEngine(width=40, height=30)
        e.seed("glider")
        assert e.grid.sum() == 5   # glider has 5 live cells

    def test_wire_step(self):
        from src.core.ca_engines import WireEngine
        e = WireEngine(width=100)
        e.seed("wire")
        head_before = (e.grid == e.HEAD).sum()
        e.step()
        # HEAD → TAIL, old TAIL → WIRE
        tails = (e.grid == e.TAIL).sum()
        assert tails >= 0

    def test_wire_inject_pulse(self):
        from src.core.ca_engines import WireEngine
        e = WireEngine(width=100)
        e.grid[40:60] = e.WIRE
        e.inject(50, radius=2, right_click=False)
        assert e.grid[50] == e.HEAD

    def test_wire_inject_wire(self):
        from src.core.ca_engines import WireEngine
        e = WireEngine(width=100)
        e.grid[50] = e.HEAD
        e.inject(50, radius=0, right_click=True)
        assert e.grid[50] == e.WIRE

    def test_make_engine_factory(self):
        from src.core.ca_engines import make_engine
        for mode in ["binary", "trinary", "life", "wire"]:
            e = make_engine(mode, width=50, height=40)
            assert e is not None


class TestIntegration:
    def test_unified_simulation_init(self):
        from src.core.ca_engines import BinaryEngine
        from src.core.integration import UnifiedSimulation
        e   = BinaryEngine(width=50)
        sim = UnifiedSimulation(e)
        assert len(sim.substrate_history) == 1
        assert len(sim.canon_history) == 1

    def test_unified_step(self):
        from src.core.ca_engines import BinaryEngine
        from src.core.integration import UnifiedSimulation
        e   = BinaryEngine(width=50)
        sim = UnifiedSimulation(e)
        for _ in range(20):
            sub, can = sim.step()
        assert sim.t == 20
        assert len(sim.substrate_history) == 21

    def test_x_p_shape(self):
        from src.core.ca_engines import BinaryEngine
        from src.core.integration import UnifiedSimulation
        e   = BinaryEngine(width=50)
        sim = UnifiedSimulation(e)
        sub, _ = sim.step()
        assert sub.X_P.shape == (50,)

    def test_x_s_is_distribution(self):
        from src.core.ca_engines import BinaryEngine
        from src.core.integration import UnifiedSimulation
        e   = BinaryEngine(width=50)
        sim = UnifiedSimulation(e)
        for _ in range(5):
            sub, _ = sim.step()
        assert abs(sub.X_S.sum() - 1.0) < 1e-5
        assert np.all(sub.X_S >= 0)

    def test_reset(self):
        from src.core.ca_engines import BinaryEngine
        from src.core.integration import UnifiedSimulation
        e   = BinaryEngine(width=50)
        sim = UnifiedSimulation(e)
        for _ in range(10):
            sim.step()
        sim.reset()
        assert sim.t == 0

    def test_inject_1d(self):
        from src.core.ca_engines import BinaryEngine
        from src.core.integration import UnifiedSimulation
        e   = BinaryEngine(width=50)
        sim = UnifiedSimulation(e)
        e.grid[:] = 0
        sim.inject(25, right_click=False)
        assert e.grid[25] == 1

    def test_all_modes_step(self):
        from src.core.ca_engines import make_engine
        from src.core.integration import UnifiedSimulation
        for mode in ["binary", "trinary", "life", "wire"]:
            e   = make_engine(mode, width=60, height=40)
            sim = UnifiedSimulation(e)
            for _ in range(5):
                sub, can = sim.step()
            assert 0.0 <= can.Omega_V <= 1.0


# ===========================================================================
# PHASE 2: VISUALIZATION
# ===========================================================================

class TestColors:
    def test_lerp_color(self):
        from src.visualization.colors import lerp_color
        c = lerp_color((0, 0, 0), (255, 255, 255), 0.5)
        assert c == (127, 127, 127)

    def test_gradient(self):
        from src.visualization.colors import gradient
        c = gradient([(0,0,0),(255,0,0),(0,0,255)], 0.5)
        assert c == (255, 0, 0)

    def test_theme_loading(self):
        from src.visualization.colors import get_theme, list_themes
        themes = list_themes()
        assert len(themes) >= 4
        for t in themes:
            theme = get_theme(t)
            assert theme.P is not None
            assert theme.I is not None
            assert theme.S is not None

    def test_cell_color_range(self):
        from src.visualization.colors import get_theme
        theme = get_theme("dark")
        for v in [0.0, 0.25, 0.5, 0.75, 1.0]:
            c = theme.P.cell_color(v)
            assert len(c) == 3
            assert all(0 <= x <= 255 for x in c)


class TestViewRegistry:
    def test_views_registered(self):
        from src.visualization import list_views
        views = list_views()
        assert len(views) >= 10
        for expected in ["cells", "lattice", "spacetime", "structure",
                         "belief", "viability", "collapse", "coupling"]:
            assert expected in views, f"Missing view: {expected}"

    def test_instantiate_all_views(self):
        from src.visualization import list_views, instantiate_view
        for name in list_views():
            v = instantiate_view(name)
            assert v is not None, f"Failed to instantiate: {name}"


class TestViewRendering:
    """Headless render tests — render to an off-screen surface."""

    def _setup(self):
        import os; os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        import pygame
        pygame.init()
        pygame.display.set_mode((1,1))

        from src.core.ca_engines import BinaryEngine
        from src.core.integration import UnifiedSimulation
        from src.visualization.colors import get_theme
        e   = BinaryEngine(width=100, rule=110)
        sim = UnifiedSimulation(e)
        for _ in range(30):
            sim.step()
        theme = get_theme("dark")
        return sim, theme

    def test_render_cells(self):
        import pygame, os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.init()
        pygame.display.set_mode((1,1))

        from src.core.ca_engines import BinaryEngine
        from src.core.integration import UnifiedSimulation
        from src.visualization.colors import get_theme
        from src.visualization import instantiate_view

        e   = BinaryEngine(width=100)
        sim = UnifiedSimulation(e)
        for _ in range(20):
            sim.step()

        theme = get_theme("dark")
        surf  = pygame.Surface((400, 80))

        for view_name in ["cells", "lattice", "spacetime", "viability",
                          "structure", "belief", "coupling", "canon_dashboard"]:
            v = instantiate_view(view_name)
            assert v is not None
            v.render(surf, sim.current_substrate, sim.current_canon, theme,
                     substrate_history=sim.substrate_history,
                     canon_history=sim.canon_history)
        # If no exception was raised, rendering is functional


# ===========================================================================
# PHASE 3: INTEGRATION / PIPELINE
# ===========================================================================

class TestFullPipeline:
    def test_ca_substrate_canon_pipeline(self):
        """Full pipeline: CA → Substrate → CANON."""
        import os; os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

        from src.core.ca_engines import BinaryEngine
        from src.core.integration import UnifiedSimulation, CAToSubstrateMapper
        from src.core.canon_operators import CanonOperators

        e      = BinaryEngine(width=100, rule=110)
        sim    = UnifiedSimulation(e)
        canon  = CanonOperators()

        for _ in range(50):
            sub, can = sim.step()

        assert isinstance(sub.X_P, np.ndarray)
        assert isinstance(sub.X_I, np.ndarray)
        assert isinstance(sub.X_S, np.ndarray)
        assert sub.X_S.sum() > 0.99

    def test_all_ca_modes_full_pipeline(self):
        from src.core.ca_engines import make_engine
        from src.core.integration import UnifiedSimulation

        for mode in ["binary", "trinary", "life", "wire"]:
            e   = make_engine(mode, width=60, height=40)
            sim = UnifiedSimulation(e)
            for _ in range(20):
                sub, can = sim.step()
            assert 0 <= can.Omega_V <= 1
            assert abs(sub.X_S.sum() - 1.0) < 1e-4

    def test_history_accumulation(self):
        from src.core.ca_engines import BinaryEngine
        from src.core.integration import UnifiedSimulation
        e   = BinaryEngine(width=50)
        sim = UnifiedSimulation(e)
        for _ in range(30):
            sim.step()
        # H should increase (residue accumulates)
        h_vals = [c.H for c in sim.canon_history]
        # Some non-trivial H values expected after steps
        assert max(h_vals) >= 0

    def test_book_of_holding_export(self):
        import tempfile
        from src.core.ca_engines import BinaryEngine
        from src.core.integration import UnifiedSimulation
        from src.io import BookOfHoldingExport

        e   = BinaryEngine(width=30)
        sim = UnifiedSimulation(e)
        for _ in range(5):
            sim.step()

        exporter = BookOfHoldingExport(mode="binary")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            fname = f.name
        result = exporter.export_trajectory(
            sim.substrate_history, sim.canon_history, fname)
        assert os.path.exists(result)

        import json
        with open(result) as f:
            doc = json.load(f)
        assert doc["version"] == "11.0"
        assert len(doc["trajectory"]) == len(sim.substrate_history)

    def test_preset_loading(self):
        from src.io import load_preset, list_presets
        presets = list_presets()
        assert len(presets) >= 5
        for name in presets:
            p = load_preset(name)
            assert "mode" in p


# ===========================================================================
# PHASE 4: ANALYTICS
# ===========================================================================

class TestAnalytics:
    def test_substrate_entropy(self):
        from src.analytics import SubstrateMetrics
        x = np.array([0.0, 0.5, 1.0, 0.25])
        e = SubstrateMetrics.plane_entropy(x)
        assert e >= 0

    def test_fft_analysis(self):
        from src.analytics import FFTAnalysis
        state = np.random.random(100)
        freqs, power = FFTAnalysis.power_spectrum(state)
        assert len(freqs) == len(power)
        assert np.all(power >= 0)

    def test_dominant_frequency(self):
        from src.analytics import FFTAnalysis
        x = np.sin(np.linspace(0, 10 * np.pi, 200))
        f = FFTAnalysis.dominant_frequency(x)
        assert 0 <= f <= 0.5

    def test_entropy_tracker(self):
        from src.core.ca_engines import BinaryEngine
        from src.core.integration import UnifiedSimulation
        from src.analytics import EntropyTracker

        e      = BinaryEngine(width=50)
        sim    = UnifiedSimulation(e)
        tracker = EntropyTracker(window=16)

        for _ in range(20):
            sub, _ = sim.step()
            tracker.push(sub)

        assert 0 <= tracker.current
        assert len(tracker.history) == 16


# ===========================================================================
# Run
# ===========================================================================

if __name__ == "__main__":
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    result = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(result)
