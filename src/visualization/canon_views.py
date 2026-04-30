"""
CANON diagnostic views  — ΩV, Δc*, H, L_P, Π
Coupling views          — cross-plane influence network
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


# ---------------------------------------------------------------------------
# Helper: mini gauge (arc)
# ---------------------------------------------------------------------------

def _draw_arc_gauge(
    surface: pygame.Surface,
    cx: int, cy: int, r: int,
    value: float,       # 0-1
    color_hi, color_lo,
    bg_color,
    label: str,
    font,
    thickness: int = 6,
):
    """Semi-circular arc gauge."""
    start_deg = 180
    end_deg   = 0
    pygame.draw.arc(surface, bg_color,
                    (cx - r, cy - r, r * 2, r * 2),
                    math.radians(end_deg), math.radians(start_deg), thickness)
    sweep = int(value * 180)
    if sweep > 0:
        color = lerp_color(color_lo, color_hi, value)
        pygame.draw.arc(surface, color,
                        (cx - r, cy - r, r * 2, r * 2),
                        math.radians(start_deg - sweep), math.radians(start_deg),
                        thickness)
    # Needle
    angle = math.radians(180 - value * 180)
    nx = cx + int(math.cos(angle) * (r - thickness))
    ny = cy - int(math.sin(angle) * (r - thickness))
    pygame.draw.line(surface, color_hi, (cx, cy), (nx, ny), 2)
    pygame.draw.circle(surface, color_hi, (cx, cy), 3)
    # Label
    txt = font.render(f"{label} {value:.2f}", True, color_hi)
    surface.blit(txt, (cx - txt.get_width() // 2, cy + 6))


# ===========================================================================
# Viability Margin View  ΩV
# ===========================================================================

@register_view
class ViabilityMarginView(ViewRenderer):
    name  = "viability"
    plane = "CANON"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        pal  = theme.P
        w, h = surface.get_width(), surface.get_height()
        surface.fill(theme.panel_bg)

        history = canon_history or []
        omegas  = [c.Omega_V for c in history[-w:]]

        # Sparkline
        rect = pygame.Rect(4, 30, w - 8, h - 50)
        self.sparkline(surface, omegas, rect, pal.viability_hi,
                       y_range=(0.0, 1.0), fill=True)

        # Current value bar
        bar_w = int((w - 8) * canon.Omega_V)
        color = pal.viability_color(canon.Omega_V)
        pygame.draw.rect(surface, color, (4, h - 18, bar_w, 12))
        pygame.draw.rect(surface, theme.panel_border, (4, h - 18, w - 8, 12), 1)

        # Danger threshold line
        thresh_x = 4 + int((w - 8) * 0.05)
        pygame.draw.line(surface, pal.viability_lo, (thresh_x, h - 22), (thresh_x, h - 14), 2)

        self.label(surface, f"ΩV  Viability Margin  {canon.Omega_V:.3f}", 4, 4, pal.text, 12)
        if not canon.is_viable:
            self.label(surface, "⚠ INFEASIBLE", w // 2 - 30, h // 2, pal.viability_lo, 13)

        self.draw_border(surface, theme.panel_border, 1)


# ===========================================================================
# Collapse Margin View  Δc*
# ===========================================================================

@register_view
class CollapseMarginView(ViewRenderer):
    name  = "collapse"
    plane = "CANON"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        pal  = theme.P
        w, h = surface.get_width(), surface.get_height()
        surface.fill(theme.panel_bg)

        history = canon_history or []
        deltas  = [c.Delta_c_star for c in history[-w:]]

        rect = pygame.Rect(4, 30, w - 8, h - 50)
        self.sparkline(surface, deltas, rect, (220, 80, 40),
                       y_range=(0.0, 1.0), fill=True)

        bar_w = int((w - 8) * canon.Delta_c_star)
        pygame.draw.rect(surface, (220, 80, 40), (4, h - 18, bar_w, 12))
        pygame.draw.rect(surface, theme.panel_border, (4, h - 18, w - 8, 12), 1)

        self.label(surface, f"Δc*  Collapse Margin  {canon.Delta_c_star:.3f}", 4, 4, (220, 160, 100), 12)
        self.draw_border(surface, theme.panel_border, 1)


# ===========================================================================
# History Load View  H
# ===========================================================================

@register_view
class HistoryLoadView(ViewRenderer):
    name  = "history"
    plane = "CANON"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        pal  = theme.I
        w, h = surface.get_width(), surface.get_height()
        surface.fill(theme.panel_bg)

        history = canon_history or []
        loads   = [c.H for c in history[-w:]]

        rect = pygame.Rect(4, 30, w - 8, h - 50)
        self.sparkline(surface, loads, rect, pal.primary, y_range=(0.0, 1.0))

        # H gauge bar
        bar_w = int((w - 8) * canon.H)
        hue   = lerp_color((40, 200, 80), (200, 40, 40), canon.H)
        pygame.draw.rect(surface, hue, (4, h - 18, bar_w, 12))
        pygame.draw.rect(surface, theme.panel_border, (4, h - 18, w - 8, 12), 1)

        self.label(surface, f"H  History Load  {canon.H:.3f}", 4, 4, pal.text, 12)
        self.draw_border(surface, theme.panel_border, 1)


# ===========================================================================
# Projection Loss View  L_P
# ===========================================================================

@register_view
class ProjectionLossView(ViewRenderer):
    name  = "projection_loss"
    plane = "CANON"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        pal  = theme.S
        w, h = surface.get_width(), surface.get_height()
        surface.fill(theme.panel_bg)

        history = canon_history or []
        losses  = [c.L_P for c in history[-w:]]

        rect = pygame.Rect(4, 30, w - 8, h - 50)
        self.sparkline(surface, losses, rect, pal.primary, y_range=(0.0, 1.0))

        bar_w = int((w - 8) * min(1.0, canon.L_P))
        pygame.draw.rect(surface, pal.primary, (4, h - 18, bar_w, 12))
        pygame.draw.rect(surface, theme.panel_border, (4, h - 18, w - 8, 12), 1)

        self.label(surface, f"L_P  Projection Loss  {canon.L_P:.3f}", 4, 4, pal.text, 12)
        self.draw_border(surface, theme.panel_border, 1)


# ===========================================================================
# CANON Dashboard  — all metrics at a glance
# ===========================================================================

@register_view
class CanonDashboardView(ViewRenderer):
    name  = "canon_dashboard"
    plane = "CANON"

    _METRICS = ["Omega_V", "Delta_c_star", "Pi", "H", "L_P", "Gamma", "T"]
    _LABELS  = ["ΩV", "Δc*", "Π", "H", "L_P", "Γ", "T"]

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        w, h = surface.get_width(), surface.get_height()
        surface.fill(theme.panel_bg)

        n = len(self._METRICS)
        col_w = w // n
        font = self.font(10)

        for i, (metric, lbl) in enumerate(zip(self._METRICS, self._LABELS)):
            v     = float(getattr(canon, metric, 0.0))
            x     = i * col_w + col_w // 2
            color = lerp_color(theme.P.viability_lo, theme.P.viability_hi, v)

            # Vertical bar
            bar_h = int((h - 40) * v)
            pygame.draw.rect(surface, color, (i * col_w + 4, h - 24 - bar_h, col_w - 8, bar_h))
            pygame.draw.rect(surface, theme.panel_border, (i * col_w + 4, 20, col_w - 8, h - 44), 1)

            # Label
            txt = font.render(lbl, True, theme.text)
            surface.blit(txt, (x - txt.get_width() // 2, 6))
            val_txt = font.render(f"{v:.2f}", True, color)
            surface.blit(val_txt, (x - val_txt.get_width() // 2, h - 20))

        self.label(surface, "CANON  Diagnostic Dashboard", 4, h - 12,
                   theme.text_dim, 10)
        self.draw_border(surface, theme.panel_border, 1)


# ===========================================================================
# Coupling Graph View  — cross-plane influence network
# ===========================================================================

@register_view
class CouplingGraphView(ViewRenderer):
    name  = "coupling"
    plane = "CANON"

    _PLANES = ["P", "I", "S"]
    _POSITIONS = {
        "P": (0.2, 0.5),
        "I": (0.8, 0.5),
        "S": (0.5, 0.15),
    }
    _COLORS = {
        "P": (0, 180, 255),
        "I": (80, 220, 80),
        "S": (200, 80, 255),
    }

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        w, h = surface.get_width(), surface.get_height()
        surface.fill(theme.panel_bg)

        cmap = substrate.coupling_map

        def pt(plane):
            fx, fy = self._POSITIONS[plane]
            return int(fx * w), int(fy * h)

        # Draw edges
        for src in self._PLANES:
            for dst in self._PLANES:
                if src == dst:
                    continue
                weight = cmap.get(src, dst)
                if weight < 0.01:
                    continue
                p0 = pt(src)
                p1 = pt(dst)
                alpha = int(255 * weight)
                edge_color = (*self._COLORS[src][:3],)
                edge_color = tuple(int(c * weight) for c in edge_color)
                pygame.draw.line(surface, edge_color, p0, p1, max(1, int(weight * 4)))
                # Arrow head (midpoint)
                mx = (p0[0] + p1[0]) // 2
                my = (p0[1] + p1[1]) // 2
                pygame.draw.circle(surface, edge_color, (mx, my), 3)

        # Draw nodes
        for plane in self._PLANES:
            px, py = pt(plane)
            color  = self._COLORS[plane]
            pygame.draw.circle(surface, color, (px, py), 18, 2)
            pygame.draw.circle(surface, color, (px, py), 4)
            self.label(surface, plane, px - 4, py - 6, color, 14)

        # Residue
        res = substrate.coupling_map.residue
        self.label(surface, f"H residue {res:.1f}", 4, h - 18, theme.text_dim, 10)
        self.label(surface, "Coupling Graph  P↔I↔S", 4, 4, theme.text, 11)
        self.draw_border(surface, theme.panel_border, 1)


# ===========================================================================
# Plane Interaction View  — P↔I↔S flows as Sankey-style bars
# ===========================================================================

@register_view
class PlaneInteractionView(ViewRenderer):
    name  = "plane_interaction"
    plane = "CANON"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        w, h = surface.get_width(), surface.get_height()
        surface.fill(theme.panel_bg)

        cmap   = substrate.coupling_map
        planes = ["P", "I", "S"]
        colors = [(0, 180, 255), (80, 220, 80), (200, 80, 255)]
        col_w  = w // 3

        for i, (src, sc) in enumerate(zip(planes, colors)):
            x = i * col_w
            # Incoming sum
            incoming = sum(cmap.get(dst, src) for dst in planes if dst != src)
            # Outgoing sum
            outgoing = sum(cmap.get(src, dst) for dst in planes if dst != src)

            bar_in  = int((h - 50) * min(1.0, incoming / 2.0))
            bar_out = int((h - 50) * min(1.0, outgoing / 2.0))

            # Incoming bar (darker)
            col_in = tuple(c // 2 for c in sc)
            pygame.draw.rect(surface, col_in,
                             (x + 4, h - 30 - bar_in, col_w // 2 - 4, bar_in))
            # Outgoing bar
            pygame.draw.rect(surface, sc,
                             (x + col_w // 2, h - 30 - bar_out, col_w // 2 - 4, bar_out))

            self.label(surface, src, x + col_w // 2 - 4, 8, sc, 14)
            self.label(surface, "in", x + 4, h - 26, col_in, 9)
            self.label(surface, "out", x + col_w // 2, h - 26, sc, 9)

        self.label(surface, "Plane Interactions", 4, h - 14, theme.text_dim, 10)
        self.draw_border(surface, theme.panel_border, 1)
