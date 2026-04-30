"""
CANON operators — viability analysis
Variables: ΩV, Π, T, Γ, H, Δc*, L_P
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from collections import deque


# ---------------------------------------------------------------------------
# CANON state
# ---------------------------------------------------------------------------

@dataclass
class CanonState:
    """Full CANON viability snapshot at one timestep."""

    # Core viability
    Omega_V: float = 1.0       # distance to infeasibility  [0, 1]
    Delta_c_star: float = 0.0  # projected collapse margin   [0, 1]

    # Regulatory pressure
    Pi: float = 0.0            # projection force magnitude

    # History load
    H: float = 0.0             # accumulated coupling residue

    # Projection loss
    L_P: float = 0.0           # information destroyed by Π_K

    # Trajectory entropy
    Gamma: float = 0.0         # entropy of X_S (belief spread)

    # Tension
    T: float = 0.0             # ‖F(X) - Π_K(F(X))‖  (constraint tension)

    # Step
    t: int = 0

    # ------------------------------------------------------------------
    @property
    def is_viable(self) -> bool:
        return self.Omega_V > 0.05

    @property
    def collapse_risk(self) -> float:
        """0 = safe, 1 = imminent collapse."""
        return float(np.clip(1.0 - self.Omega_V - 0.1 * self.Delta_c_star, 0, 1))

    def to_dict(self) -> dict:
        return {
            "t": self.t,
            "Omega_V": self.Omega_V,
            "Delta_c_star": self.Delta_c_star,
            "Pi": self.Pi,
            "H": self.H,
            "L_P": self.L_P,
            "Gamma": self.Gamma,
            "T": self.T,
            "viable": self.is_viable,
            "collapse_risk": self.collapse_risk,
        }


# ---------------------------------------------------------------------------
# CANON operator engine
# ---------------------------------------------------------------------------

class CanonOperators:
    """
    Stateful CANON engine.  Call .update(substrate_state) each tick
    to get a fresh CanonState.
    """

    HISTORY_LEN = 256

    def __init__(self):
        self._omega_history: deque = deque(maxlen=self.HISTORY_LEN)
        self._pi_history: deque    = deque(maxlen=self.HISTORY_LEN)
        self._h_history: deque     = deque(maxlen=self.HISTORY_LEN)
        self._t = 0

    # ------------------------------------------------------------------
    def update(self, substrate) -> CanonState:
        """Compute CANON metrics from a SubstrateState."""
        from .substrate_lattice import SubstrateState, LatticeProjector

        # ΩV
        omega_v = LatticeProjector.viability_margin(substrate)

        # Π — regulatory pressure: apply F then project, measure force
        try:
            raw_next = SubstrateState(
                K_P=substrate.K_P, K_I=substrate.K_I, K_S=substrate.K_S,
                X_P=substrate.F_P(substrate.X_P.copy()),
                X_I=substrate.X_I.copy(),
                X_S=substrate.X_S.copy(),
                F_P=substrate.F_P, F_I=substrate.F_I, F_S=substrate.F_S,
                coupling_map=substrate.coupling_map,
                t=substrate.t,
            )
            proj_next = raw_next.project_to_feasible()
            pi = LatticeProjector.projection_loss(raw_next, proj_next)
            span = float(np.linalg.norm(substrate.K_P.hi - substrate.K_P.lo)) or 1.0
            pi = float(np.clip(pi / span, 0.0, 1.0))
        except Exception:
            pi = 0.0

        # H — history load (accumulated coupling residue)
        h_raw = substrate.coupling_map.residue
        # Normalise with soft cap
        h = float(1.0 - np.exp(-h_raw * 0.01))

        # L_P — projection loss at current step
        before = substrate
        after  = substrate.project_to_feasible()
        l_p    = LatticeProjector.projection_loss(before, after)
        span   = float(np.linalg.norm(substrate.K_P.hi - substrate.K_P.lo)) or 1.0
        l_p    = float(np.clip(l_p / span, 0.0, 1.0))

        # Γ — entropy of belief distribution X_S
        xs = substrate.X_S
        xs = np.maximum(xs, 1e-12)
        xs = xs / xs.sum()
        gamma = float(-np.sum(xs * np.log(xs)))
        gamma = float(np.clip(gamma / np.log(len(xs)), 0.0, 1.0))

        # T — constraint tension: ‖X - Π_K(X)‖ / span
        t_val = l_p  # re-use (identical at this step)

        # Δc* — projected collapse margin
        # Heuristic: rate of change of ΩV over last 8 steps
        self._omega_history.append(omega_v)
        if len(self._omega_history) >= 8:
            recent = list(self._omega_history)[-8:]
            trend  = (recent[-1] - recent[0]) / 8.0
            delta_c_star = float(np.clip(-trend * 20.0, 0.0, 1.0))
        else:
            delta_c_star = 0.0

        state = CanonState(
            Omega_V=omega_v,
            Delta_c_star=delta_c_star,
            Pi=pi,
            H=h,
            L_P=l_p,
            Gamma=gamma,
            T=t_val,
            t=self._t,
        )

        self._t += 1
        return state

    # ------------------------------------------------------------------
    def detect_collapse(self, history: List[CanonState]) -> Optional[int]:
        """
        Return the estimated steps-to-collapse, or None if not imminent.
        Uses linear extrapolation of ΩV trend.
        """
        if len(history) < 4:
            return None
        omegas = [s.Omega_V for s in history[-16:]]
        if len(omegas) < 2:
            return None
        trend = (omegas[-1] - omegas[0]) / len(omegas)
        if trend >= 0 or omegas[-1] <= 0:
            return None
        steps = int(-omegas[-1] / trend)
        return steps if steps < 200 else None

    # ------------------------------------------------------------------
    def reset(self):
        self._omega_history.clear()
        self._pi_history.clear()
        self._h_history.clear()
        self._t = 0
