"""
Substrate Lattice — 9D coordinate system
X_{t+1} = Π_K(F(X_t))

Three planes × three layers:
  P (Physical):     K_P, X_P, F_P
  I (Informational): K_I, X_I, F_I
  S (Subjective):   K_S, X_S, F_S
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple, Dict, Any
from copy import deepcopy


# ---------------------------------------------------------------------------
# Constraint objects
# ---------------------------------------------------------------------------

@dataclass
class BoxConstraint:
    """Axis-aligned box in R^n: lo ≤ x ≤ hi"""
    lo: np.ndarray
    hi: np.ndarray

    def contains(self, x: np.ndarray) -> bool:
        return bool(np.all(x >= self.lo) and np.all(x <= self.hi))

    def project(self, x: np.ndarray) -> np.ndarray:
        return np.clip(x, self.lo, self.hi)

    def distance(self, x: np.ndarray) -> float:
        """Minimum distance from x to the constraint boundary."""
        if not self.contains(x):
            return 0.0
        d_lo = x - self.lo
        d_hi = self.hi - x
        return float(np.min(np.minimum(d_lo, d_hi)))


@dataclass
class GrammarConstraint:
    """Informational plane constraint: rule table + allowed transitions."""
    rule_table: np.ndarray          # shape (n_states, n_neighbors) → state
    allowed_patterns: Optional[np.ndarray] = None   # explicit allowed configs

    def contains(self, x: Any) -> bool:
        return True   # soft constraint — measured via projection loss

    def project(self, x: Any) -> Any:
        return x      # no-op; actual enforcement in F_I


@dataclass
class BeliefConstraint:
    """Subjective plane constraint: belief distribution must be a valid pdf."""
    n_interpretations: int = 8

    def contains(self, x: np.ndarray) -> bool:
        return bool(
            x.shape == (self.n_interpretations,)
            and np.all(x >= 0)
            and abs(x.sum() - 1.0) < 1e-6
        )

    def project(self, x: np.ndarray) -> np.ndarray:
        x = np.maximum(x, 0.0)
        s = x.sum()
        if s < 1e-12:
            return np.ones(self.n_interpretations) / self.n_interpretations
        return x / s

    def distance(self, x: np.ndarray) -> float:
        return 1.0 if self.contains(x) else 0.0


# ---------------------------------------------------------------------------
# Coupling map
# ---------------------------------------------------------------------------

@dataclass
class CouplingMap:
    """
    Cross-plane influence weights.
    coupling[src_plane][dst_plane] ∈ [0, 1]
    """
    weights: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "P": {"P": 1.0, "I": 0.3, "S": 0.1},
        "I": {"P": 0.2, "I": 1.0, "S": 0.3},
        "S": {"P": 0.05, "I": 0.2, "S": 1.0},
    })

    # Residue accumulator (becomes H in CANON)
    residue: float = 0.0

    def get(self, src: str, dst: str) -> float:
        return self.weights.get(src, {}).get(dst, 0.0)

    def project(self, state: "SubstrateState") -> "SubstrateState":
        """Π_K: project each plane to its feasible region."""
        X_P = state.K_P.project(state.X_P)
        X_I = state.K_I.project(state.X_I)
        X_S = state.K_S.project(state.X_S)

        # Measure projection loss → accumulate residue
        loss_P = float(np.linalg.norm(state.X_P - X_P))
        loss_I = 0.0   # grammar projection is identity
        loss_S = float(np.linalg.norm(state.X_S - X_S))
        new_residue = self.residue + loss_P + loss_I + loss_S

        new_map = CouplingMap(weights=deepcopy(self.weights), residue=new_residue)

        return SubstrateState(
            K_P=state.K_P, K_I=state.K_I, K_S=state.K_S,
            X_P=X_P, X_I=X_I, X_S=X_S,
            F_P=state.F_P, F_I=state.F_I, F_S=state.F_S,
            coupling_map=new_map,
            t=state.t,
        )


# ---------------------------------------------------------------------------
# Core state
# ---------------------------------------------------------------------------

@dataclass
class SubstrateState:
    """9D state in the Substrate Lattice."""

    # --- Constraint layer ---
    K_P: BoxConstraint
    K_I: GrammarConstraint
    K_S: BeliefConstraint

    # --- State layer ---
    X_P: np.ndarray          # physical state (CA grid flattened)
    X_I: np.ndarray          # informational state (pattern fingerprint)
    X_S: np.ndarray          # subjective belief distribution

    # --- Dynamic layer ---
    F_P: Callable            # physical update rule
    F_I: Callable            # informational rewrite
    F_S: Callable            # subjective evolution

    # --- Cross-plane ---
    coupling_map: CouplingMap

    # --- Time ---
    t: int = 0

    # ------------------------------------------------------------------
    def project_to_feasible(self) -> "SubstrateState":
        """Π_K: enforce constraints on all planes."""
        return self.coupling_map.project(self)

    def step(self) -> "SubstrateState":
        """X_{t+1} = Π_K(F(X_t))"""
        # Apply dynamics on each plane
        X_P_next = self.F_P(self.X_P)
        X_I_next = self.F_I(self.X_I, self.X_P)
        X_S_next = self.F_S(self.X_S, X_I_next)

        next_state = SubstrateState(
            K_P=self.K_P, K_I=self.K_I, K_S=self.K_S,
            X_P=X_P_next, X_I=X_I_next, X_S=X_S_next,
            F_P=self.F_P, F_I=self.F_I, F_S=self.F_S,
            coupling_map=self.coupling_map,
            t=self.t + 1,
        )
        return next_state.project_to_feasible()

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "t": self.t,
            "X_P": self.X_P.tolist(),
            "X_I": self.X_I.tolist(),
            "X_S": self.X_S.tolist(),
            "coupling_residue": self.coupling_map.residue,
        }


# ---------------------------------------------------------------------------
# Projector utility (standalone)
# ---------------------------------------------------------------------------

class LatticeProjector:
    """Utility for projecting states and measuring distances."""

    @staticmethod
    def viability_margin(state: SubstrateState) -> float:
        """
        ΩV: minimum distance from any plane's state to its constraint boundary.
        Normalised to [0, 1].
        """
        d_P = state.K_P.distance(state.X_P)
        d_S = state.K_S.distance(state.X_S)
        # Normalise by the diagonal of K_P
        span = float(np.linalg.norm(state.K_P.hi - state.K_P.lo)) or 1.0
        omega_v = min(d_P / span, d_S)
        return float(np.clip(omega_v, 0.0, 1.0))

    @staticmethod
    def projection_loss(before: SubstrateState, after: SubstrateState) -> float:
        """L_P: L2 distance between pre- and post-projection physical state."""
        return float(np.linalg.norm(before.X_P - after.X_P))
