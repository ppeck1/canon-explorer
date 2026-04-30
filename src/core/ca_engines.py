"""
CA Engines — F operators
Four engine types: Binary (1D ECA), Trinary (1D), Life (2D), Wire (1D Wireworld)

Each engine exposes:
  .grid          — current state (numpy array)
  .step()        — advance one generation
  .seed(mode)    — randomise / preset initial condition
  .inject(pos, radius, right_click=False)  — user stimulus
  .width / .height
"""

from __future__ import annotations
import numpy as np
from typing import Optional, Tuple, List
from collections import deque


# ---------------------------------------------------------------------------
# Binary Engine  (1D Elementary Cellular Automaton)
# ---------------------------------------------------------------------------

class BinaryEngine:
    DEAD = 0
    LIVE = 1

    def __init__(self, width: int = 200, rule: int = 110):
        self.width  = width
        self.height = 1
        self.rule   = rule
        self._rule_table = self._build_rule_table(rule)
        self.grid   = np.zeros(width, dtype=np.uint8)
        self.seed()

    # ---- rule table ----
    @staticmethod
    def _build_rule_table(rule: int) -> np.ndarray:
        table = np.zeros(8, dtype=np.uint8)
        for i in range(8):
            table[i] = (rule >> i) & 1
        return table

    def set_rule(self, rule: int):
        self.rule = rule
        self._rule_table = self._build_rule_table(rule)

    # ---- lifecycle ----
    def seed(self, mode: str = "single"):
        g = np.zeros(self.width, dtype=np.uint8)
        if mode == "single":
            g[self.width // 2] = 1
        elif mode == "random":
            g[:] = np.random.randint(0, 2, self.width, dtype=np.uint8)
        elif mode == "block":
            c = self.width // 2
            g[c-2:c+3] = 1
        self.grid = g

    def step(self) -> np.ndarray:
        g  = self.grid
        w  = self.width
        left   = np.roll(g, 1)
        right  = np.roll(g, -1)
        idx    = (left * 4 + g * 2 + right).astype(np.uint8)
        self.grid = self._rule_table[idx]
        return self.grid.copy()

    def inject(self, pos: int, radius: int = 1, right_click: bool = False):
        lo = max(0, pos - radius)
        hi = min(self.width, pos + radius + 1)
        self.grid[lo:hi] = 0 if right_click else 1

    # ---- flat accessor for substrate ----
    def flat(self) -> np.ndarray:
        return self.grid.astype(np.float32)

    def density(self) -> float:
        return float(self.grid.mean())


# ---------------------------------------------------------------------------
# Trinary Engine  (1D, 3 states)
# ---------------------------------------------------------------------------

class TrinaryEngine:
    N_STATES = 3

    def __init__(self, width: int = 200, rule: int = 777):
        self.width  = width
        self.height = 1
        self.rule   = rule
        self._rule_table = self._build_rule_table(rule)
        self.grid   = np.zeros(width, dtype=np.uint8)
        self.seed()

    @staticmethod
    def _build_rule_table(rule: int) -> np.ndarray:
        # 3^3 = 27 possible neighbourhood patterns
        table = np.zeros(27, dtype=np.uint8)
        r = rule
        for i in range(27):
            table[i] = r % 3
            r //= 3
        return table

    def set_rule(self, rule: int):
        self.rule = rule
        self._rule_table = self._build_rule_table(rule)

    def seed(self, mode: str = "single"):
        g = np.zeros(self.width, dtype=np.uint8)
        if mode == "single":
            g[self.width // 2] = 1
        elif mode == "random":
            g[:] = np.random.randint(0, 3, self.width, dtype=np.uint8)
        elif mode == "gradient":
            g[:] = np.arange(self.width) % 3
        self.grid = g

    def step(self) -> np.ndarray:
        g    = self.grid
        left = np.roll(g, 1)
        rgt  = np.roll(g, -1)
        idx  = (left * 9 + g * 3 + rgt).astype(np.int32)
        self.grid = self._rule_table[idx]
        return self.grid.copy()

    def inject(self, pos: int, radius: int = 1, right_click: bool = False):
        lo = max(0, pos - radius)
        hi = min(self.width, pos + radius + 1)
        if right_click:
            self.grid[lo:hi] = 0
        else:
            self.grid[lo:hi] = (self.grid[lo:hi] + 1) % 3

    def flat(self) -> np.ndarray:
        return (self.grid / 2.0).astype(np.float32)

    def density(self) -> float:
        return float(self.grid.mean() / 2.0)


# ---------------------------------------------------------------------------
# Life Engine  (2D Conway / Variants)
# ---------------------------------------------------------------------------

class LifeEngine:
    DEAD = 0
    LIVE = 1

    # (birth, survival) pairs for well-known rules
    RULES = {
        "conway":    ([3], [2, 3]),
        "highlife":  ([3, 6], [2, 3]),
        "day&night": ([3, 6, 7, 8], [3, 4, 6, 7, 8]),
        "seeds":     ([2], []),
        "replicator":([1, 3, 5, 7], [1, 3, 5, 7]),
    }

    def __init__(self, width: int = 80, height: int = 60, rule: str = "conway"):
        self.width  = width
        self.height = height
        self.set_rule(rule)
        self.grid = np.zeros((height, width), dtype=np.uint8)
        self.seed()

    def set_rule(self, rule: str):
        self.rule_name = rule
        birth, survive = self.RULES.get(rule, self.RULES["conway"])
        self._birth   = set(birth)
        self._survive = set(survive)

    def seed(self, mode: str = "random", density: float = 0.35):
        g = np.zeros((self.height, self.width), dtype=np.uint8)
        if mode == "random":
            g[:] = (np.random.random((self.height, self.width)) < density).astype(np.uint8)
        elif mode == "glider":
            cx, cy = self.width // 2, self.height // 2
            pattern = [(0,1),(1,2),(2,0),(2,1),(2,2)]
            for dx, dy in pattern:
                g[(cy+dy) % self.height, (cx+dx) % self.width] = 1
        elif mode == "blank":
            pass
        self.grid = g

    def step(self) -> np.ndarray:
        from scipy.ndimage import convolve
        kernel = np.array([[1,1,1],[1,0,1],[1,1,1]], dtype=np.uint8)
        # Use manual sum for speed without scipy dep check
        g = self.grid
        nbrs = (
            np.roll(np.roll(g,  1, 0),  1, 1) + np.roll(g,  1, 0) +
            np.roll(np.roll(g,  1, 0), -1, 1) + np.roll(g,  0, 0) * 0 +   # skip centre
            np.roll(np.roll(g, -1, 0),  1, 1) + np.roll(g, -1, 0) +
            np.roll(np.roll(g, -1, 0), -1, 1) +
            np.roll(g,  1, 1) + np.roll(g, -1, 1)
        )
        born    = (g == 0) & np.isin(nbrs, list(self._birth))
        survive = (g == 1) & np.isin(nbrs, list(self._survive))
        self.grid = (born | survive).astype(np.uint8)
        return self.grid.copy()

    def inject(self, x: int, y: int, radius: int = 2, right_click: bool = False):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                ny = (y + dy) % self.height
                nx = (x + dx) % self.width
                if right_click:
                    self.grid[ny, nx] = 0
                else:
                    self.grid[ny, nx] = 1

    def flat(self) -> np.ndarray:
        return self.grid.flatten().astype(np.float32)

    def density(self) -> float:
        return float(self.grid.mean())


# ---------------------------------------------------------------------------
# Wire Engine  (1D Wireworld)
# ---------------------------------------------------------------------------

class WireEngine:
    EMPTY  = 0
    WIRE   = 1
    HEAD   = 2   # electron head
    TAIL   = 3   # electron tail

    def __init__(self, width: int = 200):
        self.width  = width
        self.height = 1
        self.grid   = np.zeros(width, dtype=np.uint8)
        self._scheduled: List[Tuple[int, int]] = []   # (position, delay)
        self.seed()

    # ---- preset circuit patterns ----
    PRESETS = {
        "wire":      lambda w: _wire_preset(w),
        "oscillator":lambda w: _oscillator_preset(w),
        "clock":     lambda w: _clock_preset(w),
    }

    def seed(self, mode: str = "wire"):
        g = np.zeros(self.width, dtype=np.uint8)
        if mode == "wire":
            g[10:self.width-10] = self.WIRE
            g[20] = self.HEAD
            g[21] = self.TAIL
        elif mode == "oscillator":
            # Simple loop
            seg = self.width // 3
            g[seg:2*seg] = self.WIRE
            g[seg] = self.HEAD
            g[seg+1] = self.TAIL
        elif mode == "random":
            g[:] = np.random.choice(
                [self.EMPTY, self.WIRE],
                size=self.width,
                p=[0.3, 0.7]
            )
            # Seed a few heads
            wire_positions = np.where(g == self.WIRE)[0]
            if len(wire_positions) > 0:
                for pos in np.random.choice(wire_positions, min(3, len(wire_positions)), replace=False):
                    g[pos] = self.HEAD
        self.grid = g
        self._scheduled = []

    def step(self) -> np.ndarray:
        g = self.grid.copy()
        w = self.width
        new_g = np.zeros(w, dtype=np.uint8)

        for x in range(w):
            cell = g[x]
            if cell == self.EMPTY:
                new_g[x] = self.EMPTY
            elif cell == self.HEAD:
                new_g[x] = self.TAIL
            elif cell == self.TAIL:
                new_g[x] = self.WIRE
            elif cell == self.WIRE:
                # Count electron heads in neighbourhood
                left_h  = 1 if g[(x-1) % w] == self.HEAD else 0
                right_h = 1 if g[(x+1) % w] == self.HEAD else 0
                n_heads = left_h + right_h
                if n_heads == 1 or n_heads == 2:
                    new_g[x] = self.HEAD
                else:
                    new_g[x] = self.WIRE

        # Process scheduled pulses
        remaining = []
        for pos, delay in self._scheduled:
            if delay <= 0:
                if 0 <= pos < w and new_g[pos] == self.WIRE:
                    new_g[pos] = self.HEAD
            else:
                remaining.append((pos, delay - 1))
        self._scheduled = remaining

        self.grid = new_g
        return self.grid.copy()

    def inject(self, pos: int, radius: int = 3, right_click: bool = False):
        """
        Left-click:  inject energy pulse (staggered electron heads).
        Right-click: create wire segment (erases electrons, writes WIRE).
        """
        if right_click:
            # Write WIRE (erase electrons)
            lo = max(0, pos - radius)
            hi = min(self.width, pos + radius + 1)
            for x in range(lo, hi):
                if self.grid[x] != self.EMPTY:
                    self.grid[x] = self.WIRE
        else:
            # Energy pulse: staggered heads on wire
            self._inject_pulse(pos, radius)

    def _inject_pulse(self, pos: int, radius: int):
        """Create a wave of electron heads spreading from pos."""
        for i in range(-radius, radius + 1):
            target = pos + i
            if 0 <= target < self.width:
                delay = abs(i) * 2
                if delay == 0:
                    if self.grid[target] in (self.WIRE, self.HEAD):
                        self.grid[target] = self.HEAD
                else:
                    self._scheduled.append((target, delay))

    def flat(self) -> np.ndarray:
        return (self.grid / 3.0).astype(np.float32)

    def density(self) -> float:
        """Fraction of cells that are electron heads."""
        return float(np.sum(self.grid == self.HEAD) / max(1, np.sum(self.grid != self.EMPTY)))


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_engine(mode: str, width: int = 200, height: int = 60, **kwargs):
    mode = mode.lower()
    if mode == "binary":
        return BinaryEngine(width=width, rule=kwargs.get("rule", 110))
    elif mode == "trinary":
        return TrinaryEngine(width=width, rule=kwargs.get("rule", 777))
    elif mode == "life":
        return LifeEngine(width=width, height=height, rule=kwargs.get("rule", "conway"))
    elif mode in ("wire", "wireworld"):
        return WireEngine(width=width)
    else:
        raise ValueError(f"Unknown CA mode: {mode!r}")
