"""
Physical plane views — projections of X_P / K_P / F_P
"""

from __future__ import annotations
import pygame
import numpy as np
from typing import List, Optional

from .view_registry import ViewRenderer, register_view
from .colors import ThemePalette, lerp_color, gradient
from ..core.substrate_lattice import SubstrateState
from ..core.canon_operators import CanonState


# ---------------------------------------------------------------------------
# Cells View  — raw X_P
# ---------------------------------------------------------------------------

@register_view
class CellsView(ViewRenderer):
    name  = "cells"
    plane = "P"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        pal  = theme.P
        w, h = surface.get_width(), surface.get_height()
        surface.fill(pal.bg)

        x_p = substrate.X_P
        n   = len(x_p)
        if n == 0:
            return

        cell_w = max(1, w // n)
        for i, v in enumerate(x_p):
            color = pal.cell_color(float(v))
            pygame.draw.rect(surface, color, (i * cell_w, 0, cell_w, h))

        # Overlay viability tint on border
        v_color = pal.viability_color(canon.Omega_V)
        self.draw_border(surface, v_color, 2)

        # Label
        self.label(surface, f"X_P  ΩV={canon.Omega_V:.2f}", 4, 4, pal.text, 11)


# ---------------------------------------------------------------------------
# Lattice View  — X_P with K_P constraint overlay
# ---------------------------------------------------------------------------

@register_view
class LatticeView(ViewRenderer):
    name  = "lattice"
    plane = "P"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        pal  = theme.P
        w, h = surface.get_width(), surface.get_height()
        surface.fill(pal.bg)

        x_p = substrate.X_P
        k_lo = substrate.K_P.lo
        k_hi = substrate.K_P.hi
        n    = len(x_p)
        if n == 0:
            return

        cell_w = max(1, w // n)
        bar_h  = max(2, int(h * 0.1))

        # Draw cells
        for i, v in enumerate(x_p):
            color = pal.cell_color(float(v))
            pygame.draw.rect(surface, color, (i * cell_w, bar_h, cell_w, h - bar_h))

        # K_P constraint boundaries as top bar
        for i in range(n):
            lo_v = float(k_lo[i]) if i < len(k_lo) else 0.0
            hi_v = float(k_hi[i]) if i < len(k_hi) else 1.0
            # Color code: tight constraint = red tint, loose = green
            constraint_tightness = 1.0 - (hi_v - lo_v)
            bar_color = lerp_color(pal.viability_hi, pal.viability_lo, constraint_tightness)
            pygame.draw.rect(surface, bar_color, (i * cell_w, 0, cell_w, bar_h - 1))

        self.draw_border(surface, theme.panel_border, 1)
        self.label(surface, f"Lattice X_P|K_P  Π={canon.Pi:.2f}", 4, bar_h + 2, pal.text, 11)


# ---------------------------------------------------------------------------
# Spacetime View  — F_P evolution strip (time × space)
# ---------------------------------------------------------------------------

@register_view
class SpacetimeView(ViewRenderer):
    name  = "spacetime"
    plane = "P"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        pal  = theme.P
        w, h = surface.get_width(), surface.get_height()
        surface.fill(pal.bg)

        history = substrate_history or []
        n_rows  = min(h, len(history))
        if n_rows == 0:
            self.label(surface, "spacetime: accumulating…", 4, 4, pal.text, 11)
            return

        # Most recent row at bottom
        for row_idx, state in enumerate(history[-n_rows:]):
            y     = h - n_rows + row_idx
            x_p   = state.X_P
            n_col = len(x_p)
            if n_col == 0:
                continue
            cell_w = max(1, w // n_col)
            for i, v in enumerate(x_p):
                color = pal.cell_color(float(v))
                surface.set_at((i * cell_w, y), color)
                if cell_w > 1:
                    pygame.draw.line(surface, color, (i * cell_w, y), ((i+1)*cell_w - 1, y))

        self.draw_border(surface, theme.panel_border, 1)
        self.label(surface, f"Spacetime  t={substrate.t}", 4, 4, pal.text, 11)
