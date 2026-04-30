"""
SystemManager — manages N independent CA systems with color, mode, coupling.
Supports side-by-side and overlay rendering modes.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Tuple
from .ca_engines import make_engine, BinaryEngine
from .integration import UnifiedSimulation


# Predefined system colors (distinct, colorblind-friendly-ish)
SYSTEM_COLORS = [
    (0, 200, 255),    # cyan    - System 1
    (255, 140, 0),    # amber   - System 2
    (180, 60, 255),   # violet  - System 3
    (0, 230, 100),    # green   - System 4
    (255, 60, 100),   # red     - System 5
    (255, 220, 0),    # yellow  - System 6
]

MAX_SYSTEMS = 6


@dataclass
class SystemSlot:
    """One independent CA system."""
    index:   int
    name:    str
    mode:    str
    rule:    int
    color:   Tuple[int, int, int]
    engine:  object
    sim:     UnifiedSimulation
    active:  bool = True
    view:    str  = "SPACETIME"   # default view for this slot's column

    @classmethod
    def create(cls, index: int, mode: str = "binary", rule: int = 110,
               color: Optional[Tuple] = None, width: int = 300, height: int = 80) -> "SystemSlot":
        col = color or SYSTEM_COLORS[index % len(SYSTEM_COLORS)]
        if mode == "life":
            eng = make_engine("life", width=width, height=height)
        else:
            eng = make_engine(mode, width=width)
        sim = UnifiedSimulation(eng)
        return cls(
            index=index, name=f"SYS-{index+1}", mode=mode, rule=rule,
            color=col, engine=eng, sim=sim,
        )

    def set_rule(self, rule: int):
        self.rule = rule
        if hasattr(self.engine, "set_rule"):
            self.engine.set_rule(rule)

    def reseed(self, mode: str = "single"):
        self.sim.reset(seed_mode=mode)

    def step(self):
        return self.sim.step()

    def inject(self, *args, right_click: bool = False, **kwargs):
        self.sim.inject(*args, right_click=right_click, **kwargs)


class CouplingMatrix:
    """
    N×N directional coupling matrix.
    coupling[i][j] = strength that system i pushes into system j.
    """
    def __init__(self, n: int):
        self.n = n
        self.matrix = [[0.0] * n for _ in range(n)]

    def set(self, src: int, dst: int, strength: float):
        if 0 <= src < self.n and 0 <= dst < self.n and src != dst:
            self.matrix[src][dst] = max(0.0, min(1.0, strength))

    def get(self, src: int, dst: int) -> float:
        if 0 <= src < self.n and 0 <= dst < self.n:
            return self.matrix[src][dst]
        return 0.0

    def resize(self, n: int):
        old = self.matrix
        self.n = n
        self.matrix = [[0.0] * n for _ in range(n)]
        for i in range(min(len(old), n)):
            for j in range(min(len(old[i]), n)):
                self.matrix[i][j] = old[i][j]


class SystemManager:
    """Manages 1–MAX_SYSTEMS CA systems and their coupling."""

    RENDER_SIDEBYSIDE = "sidebyside"
    RENDER_OVERLAY    = "overlay"

    def __init__(self, width: int = 300, height: int = 80):
        self.width   = width
        self.height  = height
        self.slots:  List[SystemSlot] = []
        self.coupling = CouplingMatrix(0)
        self.render_mode = self.RENDER_SIDEBYSIDE
        self._selected = 0   # which system is "active" for controls

        # Start with one system
        self.add_system("binary", rule=110)

    # ------------------------------------------------------------------
    def add_system(self, mode: str = "binary", rule: int = 110,
                   color: Optional[Tuple] = None) -> Optional[SystemSlot]:
        if len(self.slots) >= MAX_SYSTEMS:
            return None
        idx  = len(self.slots)
        slot = SystemSlot.create(idx, mode=mode, rule=rule, color=color,
                                 width=self.width, height=self.height)
        self.slots.append(slot)
        self.coupling.resize(len(self.slots))
        return slot

    def remove_system(self, index: int):
        if len(self.slots) <= 1 or index >= len(self.slots):
            return
        self.slots.pop(index)
        # Re-index
        for i, s in enumerate(self.slots):
            s.index = i
            s.name  = f"SYS-{i+1}"
        self.coupling.resize(len(self.slots))
        self._selected = min(self._selected, len(self.slots) - 1)

    @property
    def selected(self) -> SystemSlot:
        return self.slots[max(0, min(self._selected, len(self.slots)-1))]

    @property
    def n(self) -> int:
        return len(self.slots)

    def select(self, index: int):
        self._selected = max(0, min(index, len(self.slots)-1))

    # ------------------------------------------------------------------
    def step_all(self, steps: int = 1):
        """Step all systems and apply coupling."""
        for _ in range(steps):
            for slot in self.slots:
                if slot.active:
                    slot.step()
            self._apply_coupling()

    def _apply_coupling(self):
        """Inject state from each src system into dst systems per coupling matrix."""
        n = self.n
        for src_idx in range(n):
            src = self.slots[src_idx]
            if not src.active:
                continue
            for dst_idx in range(n):
                if src_idx == dst_idx:
                    continue
                strength = self.coupling.get(src_idx, dst_idx)
                if strength < 0.01:
                    continue
                dst = self.slots[dst_idx]
                self._inject_coupling(src, dst, strength)

    def _inject_coupling(self, src: SystemSlot, dst: SystemSlot, strength: float):
        """Inject src's state into dst proportionally to strength."""
        src_grid = src.engine.grid
        dst_grid = dst.engine.grid

        # For 1D→1D: sample src uniformly and add to dst at same positions
        src_flat = src_grid.flatten().astype(float)
        dst_flat = dst_grid.flatten().astype(float)
        n_src    = len(src_flat)
        n_dst    = len(dst_flat)

        if n_dst == 0 or n_src == 0:
            return

        # Resample src to dst length
        indices   = (np.arange(n_dst) * n_src / n_dst).astype(int)
        src_mapped = src_flat[np.clip(indices, 0, n_src-1)]

        # Probabilistic injection: only inject where random < strength
        mask = np.random.random(n_dst) < (strength * 0.05)  # gentle coupling
        if hasattr(dst.engine, "HEAD") and not mask.any():
            return

        max_state = int(getattr(dst.engine, "LIVE", None) or
                        max(1, getattr(dst.engine, "N_STATES", 2) - 1))

        dst_new = dst_flat.copy()
        dst_new[mask] = np.clip(dst_new[mask] + src_mapped[mask] * strength,
                                0, max_state)

        # Write back (2D engines need reshape)
        try:
            dst.engine.grid[:] = dst_new.reshape(dst.engine.grid.shape).astype(dst.engine.grid.dtype)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def toggle_render_mode(self):
        if self.render_mode == self.RENDER_SIDEBYSIDE:
            self.render_mode = self.RENDER_OVERLAY
        else:
            self.render_mode = self.RENDER_SIDEBYSIDE
