"""
Orthogonal Impulse System — a second independent CA engine
whose output can be injected into the main simulation.

This gives Paul the "orthogonality / cross-system interaction" he wants:
  - Run CA_B independently
  - Periodically sample CA_B's state and inject it as a stimulus into CA_A
  - Visualise both systems side by side in the control strip
  - Adjustable injection: position, mode (additive / XOR / pulse), rate
"""

from __future__ import annotations
import pygame
import numpy as np
import math
from typing import Optional, Callable, Any
from ..visualization.colors import ThemePalette, lerp_color


# ---- injection modes ----
INJECT_MODES = ["pulse", "additive", "xor", "replace"]


class OrthogonalSystem:
    """
    Manages a second CA engine and its interaction with the main simulation.
    """

    def __init__(self, width: int = 60):
        from ..core.ca_engines import BinaryEngine
        self.width   = width
        self.engine  = BinaryEngine(width=width, rule=30)   # rule 30 = chaotic
        self.engine.seed("random")

        self.enabled         = False
        self.inject_mode     = "pulse"
        self.inject_rate     = 0.1        # fraction of steps that trigger injection
        self.inject_position = 0.5        # 0.0–1.0 of target grid width
        self.inject_strength = 1.0
        self._step_counter   = 0
        self._step_accum     = 0.0

        # Callback: called with (position_frac, mode, grid_slice)
        self.on_inject: Optional[Callable] = None

        # Mini-view surface
        self._surface: Optional[pygame.Surface] = None
        self._rect    = pygame.Rect(0, 0, 120, 36)

    def set_rect(self, rect: pygame.Rect):
        self._rect = pygame.Rect(rect)
        self._surface = None

    # ------------------------------------------------------------------
    def step(self, dt: float, main_speed: float):
        """Advance B engine and optionally fire injection."""
        if not self.enabled:
            return

        self._step_accum += dt * main_speed * 0.5
        while self._step_accum >= 1.0:
            self._step_accum -= 1.0
            self.engine.step()
            self._step_counter += 1

            # Injection trigger
            if (self._step_counter % max(1, int(1.0 / max(0.01, self.inject_rate)))) == 0:
                self._fire_injection()

    def _fire_injection(self):
        if self.on_inject is None:
            return
        grid_slice = self.engine.grid.copy()
        self.on_inject(self.inject_position, self.inject_mode,
                       grid_slice, self.inject_strength)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, theme: ThemePalette):
        r = self._rect
        if not self.enabled:
            pygame.draw.rect(surface, theme.panel_bg, r)
            pygame.draw.rect(surface, theme.panel_border, r, 1)
            try:
                font = pygame.font.SysFont("monospace", 9)
                off  = font.render("SYS-B: off", True, theme.text_dim)
                surface.blit(off, (r.left + 2, r.centery - 5))
            except Exception:
                pass
            return

        # Background
        pygame.draw.rect(surface, theme.panel_bg, r)

        # Draw mini spacetime of engine B
        grid = self.engine.grid
        n    = len(grid)
        if n > 0:
            cell_w = max(1, r.width // n)
            pal    = theme.I
            for i, v in enumerate(grid):
                col = pal.cell_color(float(v))
                pygame.draw.rect(surface, col,
                                 (r.left + i * cell_w, r.top + 2,
                                  cell_w, r.height - 4))

        # Injection point marker
        ix = r.left + int(self.inject_position * r.width)
        pygame.draw.line(surface, theme.S.primary,
                         (ix, r.top), (ix, r.bottom), 2)

        pygame.draw.rect(surface, theme.panel_border, r, 1)

        try:
            font = pygame.font.SysFont("monospace", 9)
            txt  = font.render(f"B:{self.inject_mode[:3]} r={self.inject_rate:.1f}",
                                True, theme.text_dim)
            surface.blit(txt, (r.left + 2, r.bottom + 2))
        except Exception:
            pass

    def handle_event(self, event) -> bool:
        r = self._rect
        if event.type == pygame.MOUSEBUTTONDOWN:
            if r.collidepoint(event.pos):
                if event.button == 1:
                    # Move injection point
                    self.inject_position = (event.pos[0] - r.left) / max(1, r.width)
                    self.inject_position = max(0.0, min(1.0, self.inject_position))
                    return True
                elif event.button == 3:
                    # Right-click: cycle mode
                    idx = INJECT_MODES.index(self.inject_mode)
                    self.inject_mode = INJECT_MODES[(idx + 1) % len(INJECT_MODES)]
                    return True
        if event.type == pygame.MOUSEWHEEL and r.collidepoint(pygame.mouse.get_pos()):
            self.inject_rate = max(0.01, min(1.0, self.inject_rate + event.y * 0.05))
            return True
        return False


# ------------------------------------------------------------------
# Injection handler (attached to Application)
# ------------------------------------------------------------------

def apply_injection(main_engine: Any, position_frac: float,
                    mode: str, grid_slice: np.ndarray,
                    strength: float):
    """
    Apply CA_B's slice into CA_A at position_frac.

    Supports 1D engines (binary, trinary, wire) and 2D (life).
    """
    target = main_engine

    if hasattr(target, "height") and target.height > 1:
        # 2D — inject as a column perturbation
        cx = int(position_frac * target.width)
        n  = min(len(grid_slice), target.height)
        for y in range(n):
            v = int(grid_slice[y % len(grid_slice)])
            if mode == "additive":
                target.grid[y, cx] = min(1, target.grid[y, cx] + v)
            elif mode == "xor":
                target.grid[y, cx] ^= v
            elif mode == "replace":
                target.grid[y, cx] = v
            elif mode == "pulse":
                if v > 0:
                    target.grid[y, cx] = 1
    else:
        # 1D — inject as a region
        cw   = target.width
        cx   = int(position_frac * cw)
        n    = min(len(grid_slice), cw // 4)
        lo   = max(0, cx - n // 2)
        hi   = min(cw, lo + n)

        for i, x in enumerate(range(lo, hi)):
            v = int(grid_slice[i % len(grid_slice)])
            max_state = int(getattr(target, "LIVE", 0) or
                            max(1, getattr(target, "N_STATES", 2) - 1))
            if mode == "additive":
                target.grid[x] = min(max_state, target.grid[x] + v)
            elif mode == "xor":
                target.grid[x] ^= (v & 1)
            elif mode == "replace":
                target.grid[x] = v % (int(target.grid.max()) + 1)
            elif mode == "pulse":
                if v > 0:
                    # Use the engine's inject method if available
                    if hasattr(target, "inject"):
                        target.inject(x, radius=0, right_click=False)
                    else:
                        target.grid[x] = 1
