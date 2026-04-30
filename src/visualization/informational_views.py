"""
Informational plane views — X_I / K_I / F_I
Subjective plane views   — X_S / K_S / F_S
"""

from __future__ import annotations
import pygame
import numpy as np
from typing import List, Optional
import math

from .view_registry import ViewRenderer, register_view
from .colors import ThemePalette, lerp_color, gradient
from ..core.substrate_lattice import SubstrateState
from ..core.canon_operators import CanonState

_INTERP_LABELS = [
    "ordered", "chaotic", "periodic", "sparse",
    "dense", "edge-rich", "stable", "dynamic",
]


# ===========================================================================
# INFORMATIONAL PLANE
# ===========================================================================

@register_view
class StructureView(ViewRenderer):
    """X_I — FFT pattern fingerprint as bar chart."""
    name  = "structure"
    plane = "I"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        pal  = theme.I
        w, h = surface.get_width(), surface.get_height()
        surface.fill(pal.bg)

        x_i = substrate.X_I
        if len(x_i) == 0:
            return

        n      = len(x_i)
        bar_w  = max(1, w // n)
        margin = 20

        for i, v in enumerate(x_i):
            bar_h  = int((h - margin) * max(0.0, float(v)))
            color  = pal.cell_color(float(v))
            x      = i * bar_w
            pygame.draw.rect(surface, color, (x, h - margin - bar_h, bar_w - 1, bar_h))

        # Frequency axis label
        self.draw_hline(surface, h - margin, pal.grid)
        self.label(surface, "X_I  pattern spectrum", 4, 4, pal.text, 11)
        self.label(surface, "DC", 2, h - margin + 2, theme.text_dim, 10)
        self.label(surface, "HF", w - 20, h - margin + 2, pal.text, 10)

        self.draw_border(surface, theme.panel_border, 1)


@register_view
class RuleView(ViewRenderer):
    """K_I — rule table heatmap."""
    name  = "rule"
    plane = "I"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        pal  = theme.I
        w, h = surface.get_width(), surface.get_height()
        surface.fill(pal.bg)

        table = substrate.K_I.rule_table
        if len(table) == 0:
            self.label(surface, "K_I: no rule table", 4, 4, pal.text, 11)
            return

        n      = len(table)
        cell_s = max(1, min(w // n, h // 4))
        margin = (w - n * cell_s) // 2

        for i, v in enumerate(table):
            val   = int(v) / max(1, int(table.max()))
            color = pal.cell_color(val)
            pygame.draw.rect(surface, color,
                             (margin + i * cell_s, h // 2 - cell_s, cell_s - 1, cell_s * 2))

        self.label(surface, "K_I  rule table", 4, 4, pal.text, 11)
        self.draw_border(surface, theme.panel_border, 1)


@register_view
class DynamicView(ViewRenderer):
    """F_I — information entropy over time."""
    name  = "dynamic"
    plane = "I"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        pal  = theme.I
        w, h = surface.get_width(), surface.get_height()
        surface.fill(pal.bg)

        history = substrate_history or []
        gammas  = [s.X_I.std() for s in history[-w:]] if history else []
        if gammas:
            rect = pygame.Rect(4, 20, w - 8, h - 28)
            self.sparkline(surface, gammas, rect, pal.primary, bg=None)

        self.label(surface, f"F_I  X_I variance  Γ={canon.Gamma:.2f}", 4, 4, pal.text, 11)
        self.draw_border(surface, theme.panel_border, 1)


# ===========================================================================
# SUBJECTIVE PLANE
# ===========================================================================

@register_view
class BeliefView(ViewRenderer):
    """X_S — belief distribution as radial chart."""
    name  = "belief"
    plane = "S"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        pal  = theme.S
        w, h = surface.get_width(), surface.get_height()
        surface.fill(pal.bg)

        x_s = substrate.X_S
        n   = len(x_s)
        if n == 0:
            return

        cx, cy = w // 2, h // 2
        r_max  = min(cx, cy) - 24

        # Draw radial bars
        for i, v in enumerate(x_s):
            angle  = (i / n) * 2 * math.pi - math.pi / 2
            r      = int(r_max * float(v) * n)   # scale
            r      = min(r, r_max)
            color  = pal.cell_color(float(v) * n / 2.0)
            end_x  = cx + int(math.cos(angle) * r)
            end_y  = cy + int(math.sin(angle) * r)
            pygame.draw.line(surface, color, (cx, cy), (end_x, end_y), 3)

            # Label
            lx = cx + int(math.cos(angle) * (r_max + 10))
            ly = cy + int(math.sin(angle) * (r_max + 10))
            label = _INTERP_LABELS[i] if i < len(_INTERP_LABELS) else str(i)
            self.label(surface, label[:6], lx - 18, ly - 6, pal.text, 9)

        # Centre dot
        pygame.draw.circle(surface, pal.primary, (cx, cy), 4)

        self.label(surface, f"X_S belief  Γ={canon.Gamma:.2f}", 4, 4, pal.text, 11)
        self.draw_border(surface, theme.panel_border, 1)


@register_view
class InterpretationView(ViewRenderer):
    """K_S — belief constraint boundaries as gauge."""
    name  = "interpretation"
    plane = "S"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        pal  = theme.S
        w, h = surface.get_width(), surface.get_height()
        surface.fill(pal.bg)

        x_s = substrate.X_S
        n   = len(x_s)
        if n == 0:
            return

        bar_h = max(4, (h - 30) // n)
        for i, v in enumerate(x_s):
            y     = 24 + i * bar_h
            bar_w = int((w - 10) * float(v) * n)
            bar_w = min(bar_w, w - 10)
            color = pal.cell_color(float(v) * n / 2.0)
            pygame.draw.rect(surface, color, (5, y, bar_w, bar_h - 2))
            label = _INTERP_LABELS[i] if i < len(_INTERP_LABELS) else str(i)
            self.label(surface, f"{label[:8]} {v:.2f}", 5, y, pal.text, 9)

        self.label(surface, "K_S  belief bounds", 4, 4, pal.text, 11)
        self.draw_border(surface, theme.panel_border, 1)


@register_view
class MeaningEvolutionView(ViewRenderer):
    """F_S — belief distribution shift over time (most probable interpretation)."""
    name  = "meaning"
    plane = "S"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        pal  = theme.S
        w, h = surface.get_width(), surface.get_height()
        surface.fill(pal.bg)

        history = substrate_history or []
        if len(history) < 2:
            self.label(surface, "F_S: accumulating…", 4, 4, pal.text, 11)
            return

        n_interp = len(history[0].X_S)
        colors   = [pal.cell_color(i / max(1, n_interp - 1)) for i in range(n_interp)]
        steps    = history[-w:]

        # Draw stacked area chart of beliefs
        for t_idx, state in enumerate(steps):
            x   = t_idx
            acc = 0.0
            for i, v in enumerate(state.X_S):
                seg_h = int(float(v) * h)
                col   = colors[i]
                pygame.draw.line(surface, col,
                                 (x, h - int(acc * h)),
                                 (x, h - int((acc + float(v)) * h)), 1)
                acc += float(v)

        self.label(surface, f"F_S  belief evolution  t={substrate.t}", 4, 4, pal.text, 11)
        self.draw_border(surface, theme.panel_border, 1)
