"""
Integration layer — CA ↔ Substrate ↔ CANON

Unified step loop:
  CA.step()  →  map_ca_to_substrate()  →  CANON.update()  →  Views
"""

from __future__ import annotations
import numpy as np
from typing import Any, List, Optional, Tuple, Union

from .substrate_lattice import (
    SubstrateState, BoxConstraint, GrammarConstraint, BeliefConstraint,
    CouplingMap, LatticeProjector,
)
from .canon_operators import CanonOperators, CanonState
from .ca_engines import BinaryEngine, TrinaryEngine, LifeEngine, WireEngine


# ---------------------------------------------------------------------------
# Pattern fingerprint (X_I)
# ---------------------------------------------------------------------------

def _extract_patterns(grid: np.ndarray, n_buckets: int = 16) -> np.ndarray:
    """
    Compress a 1D or 2D CA grid into a fixed-size pattern fingerprint.
    Uses spatial frequency bucketing of a flattened normalised signal.
    """
    flat = grid.flatten().astype(np.float32)
    if len(flat) == 0:
        return np.zeros(n_buckets, dtype=np.float32)
    # FFT magnitude spectrum (low-frequency summary)
    fft = np.abs(np.fft.rfft(flat, n=max(len(flat), n_buckets * 2)))
    bucket_size = max(1, len(fft) // n_buckets)
    buckets = np.array([
        fft[i * bucket_size:(i + 1) * bucket_size].mean()
        for i in range(n_buckets)
    ], dtype=np.float32)
    norm = buckets.max() or 1.0
    return buckets / norm


# ---------------------------------------------------------------------------
# Belief / interpretation field (X_S)
# ---------------------------------------------------------------------------

_INTERPRETATIONS = [
    "ordered",      # low entropy, structured
    "chaotic",      # high entropy
    "periodic",     # dominant frequency
    "sparse",       # few live cells
    "dense",        # many live cells
    "edge-rich",    # many state transitions
    "stable",       # low change rate
    "dynamic",      # high change rate
]
N_INTERP = len(_INTERPRETATIONS)


def _compute_belief(
    grid: np.ndarray,
    prev_grid: Optional[np.ndarray],
    pattern: np.ndarray,
) -> np.ndarray:
    """Compute a probability distribution over interpretations."""
    flat  = grid.flatten().astype(np.float32)
    n     = len(flat)
    mx    = flat.max() or 1.0
    norm  = flat / mx

    density   = float(norm.mean())
    transitions = int(np.sum(np.abs(np.diff(flat.astype(int))) > 0))
    edge_ratio = transitions / max(1, n - 1)

    if prev_grid is not None:
        change_rate = float(np.mean(np.abs(
            grid.flatten().astype(float) - prev_grid.flatten().astype(float)
        ) > 0))
    else:
        change_rate = 0.5

    # Low-frequency dominance → periodic
    if len(pattern) > 1:
        periodic_score = float(pattern[1:4].mean()) / (float(pattern[0]) + 1e-6)
    else:
        periodic_score = 0.0

    from scipy.stats import entropy as scipy_entropy
    try:
        hist, _ = np.histogram(norm, bins=8, range=(0, 1))
        hist = hist.astype(float) + 1e-6
        ent = float(scipy_entropy(hist / hist.sum()))
        max_ent = np.log(8)
        ent_norm = ent / max_ent
    except Exception:
        ent_norm = 0.5

    beliefs = np.array([
        1.0 - ent_norm,            # ordered
        ent_norm,                  # chaotic
        min(1.0, periodic_score),  # periodic
        1.0 - density,             # sparse
        density,                   # dense
        edge_ratio,                # edge-rich
        1.0 - change_rate,         # stable
        change_rate,               # dynamic
    ], dtype=np.float32)

    beliefs = np.maximum(beliefs, 1e-6)
    return beliefs / beliefs.sum()


# ---------------------------------------------------------------------------
# CA → Substrate mapper
# ---------------------------------------------------------------------------

class CAToSubstrateMapper:
    """Converts a CA engine's current state into a SubstrateState."""

    def __init__(self, ca_engine: Any, coupling: Optional[CouplingMap] = None):
        self.engine  = ca_engine
        self.coupling = coupling or CouplingMap()
        self._prev_grid: Optional[np.ndarray] = None
        self._prev_substrate: Optional[SubstrateState] = None

    # ---- constraint builders ----
    def _physical_constraints(self) -> BoxConstraint:
        e = self.engine
        flat = e.flat()
        lo = np.zeros_like(flat)
        hi = np.ones_like(flat)
        return BoxConstraint(lo=lo, hi=hi)

    def _grammar_constraint(self) -> GrammarConstraint:
        e = self.engine
        if hasattr(e, "_rule_table"):
            return GrammarConstraint(rule_table=e._rule_table.copy())
        return GrammarConstraint(rule_table=np.array([]))

    def _belief_constraint(self) -> BeliefConstraint:
        return BeliefConstraint(n_interpretations=N_INTERP)

    # ---- dynamics wrappers ----
    def _make_F_P(self):
        """Return a function that steps the physical state."""
        e = self.engine
        def F_P(x: np.ndarray) -> np.ndarray:
            # We drive from the engine; x is used for viability check only
            return x.copy()
        return F_P

    def _make_F_I(self):
        def F_I(x_i: np.ndarray, x_p: np.ndarray) -> np.ndarray:
            return _extract_patterns(x_p)
        return F_I

    def _make_F_S(self):
        mapper = self
        def F_S(x_s: np.ndarray, x_i: np.ndarray) -> np.ndarray:
            # Soft update: 80% prior, 20% new reading
            new_xs = _compute_belief(
                mapper.engine.grid,
                mapper._prev_grid,
                x_i,
            )
            blended = 0.8 * x_s + 0.2 * new_xs
            blended = np.maximum(blended, 1e-6)
            return blended / blended.sum()
        return F_S

    # ---- main mapper ----
    def map_state(self, t: int = 0) -> SubstrateState:
        e = self.engine
        x_p = e.flat()
        x_i = _extract_patterns(e.grid)
        x_s = _compute_belief(e.grid, self._prev_grid, x_i)

        if self._prev_substrate is not None:
            # Keep coupling residue from previous step
            coupling = self._prev_substrate.coupling_map
        else:
            coupling = self.coupling

        substrate = SubstrateState(
            K_P=self._physical_constraints(),
            K_I=self._grammar_constraint(),
            K_S=self._belief_constraint(),
            X_P=x_p,
            X_I=x_i,
            X_S=x_s,
            F_P=self._make_F_P(),
            F_I=self._make_F_I(),
            F_S=self._make_F_S(),
            coupling_map=coupling,
            t=t,
        )
        return substrate

    def advance(self, t: int = 0) -> SubstrateState:
        """Step the engine and return a new SubstrateState."""
        self._prev_grid = self.engine.grid.copy()
        self.engine.step()
        substrate = self.map_state(t)
        self._prev_substrate = substrate
        return substrate


# ---------------------------------------------------------------------------
# Unified step coordinator
# ---------------------------------------------------------------------------

class UnifiedSimulation:
    """
    Top-level object that owns:
      - CA engine
      - CA→Substrate mapper
      - CANON operators
      - History buffers
    """

    MAX_HISTORY = 512

    def __init__(self, ca_engine: Any):
        self.engine  = ca_engine
        self.mapper  = CAToSubstrateMapper(ca_engine)
        self.canon   = CanonOperators()

        self.substrate_history: List[SubstrateState] = []
        self.canon_history:     List[CanonState]     = []
        self.t = 0

        # Initialise with current state
        s = self.mapper.map_state(t=0)
        c = self.canon.update(s)
        self.substrate_history.append(s)
        self.canon_history.append(c)

    # ------------------------------------------------------------------
    def step(self) -> Tuple[SubstrateState, CanonState]:
        """Advance one timestep."""
        self.t += 1
        substrate = self.mapper.advance(t=self.t)
        canon     = self.canon.update(substrate)

        self.substrate_history.append(substrate)
        self.canon_history.append(canon)

        # Trim history
        if len(self.substrate_history) > self.MAX_HISTORY:
            self.substrate_history.pop(0)
            self.canon_history.pop(0)

        return substrate, canon

    @property
    def current_substrate(self) -> SubstrateState:
        return self.substrate_history[-1]

    @property
    def current_canon(self) -> CanonState:
        return self.canon_history[-1]

    def reset(self, seed_mode: str = "default"):
        """Reseed engine and reset history."""
        if hasattr(self.engine, "seed"):
            self.engine.seed(mode=seed_mode if seed_mode != "default" else
                             ("single" if hasattr(self.engine, "rule") else "random"))
        self.mapper  = CAToSubstrateMapper(self.engine, coupling=CouplingMap())
        self.canon.reset()
        self.substrate_history.clear()
        self.canon_history.clear()
        self.t = 0
        s = self.mapper.map_state(t=0)
        c = self.canon.update(s)
        self.substrate_history.append(s)
        self.canon_history.append(c)

    def inject(self, *args, right_click: bool = False, **kwargs):
        """Forward injection to engine."""
        self.engine.inject(*args, right_click=right_click, **kwargs)
