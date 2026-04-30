"""
Restored + new scope views:
  SCOPE    — oscilloscope waveform of current CA row
  RADIAL   — time-collapsed polar cross-section (from v10)
  VECT     — vectorscope circular state display (from v10)
  TRANSVERSE — EM-TRANS style cross-section (from v10, renamed)
  WAVEFORM — 5 honest orthogonal channels: v(t) E(t) H(t) B(t) D(t)

State coloring (discrete, not gradient):
  Binary:  0=bg  1=primary
  Trinary: 0=neutral  1=warm(+/reinforce)  2=cool(-/shed)
  Wire:    0=bg  1=dim-wire  2=bright-head  3=orange-tail
  Life:    0=bg  1=live
"""

from __future__ import annotations
import pygame
import numpy as np
import math
from typing import List, Optional
from .view_registry import ViewRenderer, register_view
from .colors import ThemePalette, lerp_color
from ..core.substrate_lattice import SubstrateState
from ..core.canon_operators import CanonState


# ---------------------------------------------------------------------------
# Discrete state colorers  (called by multiple views)
# ---------------------------------------------------------------------------

def state_color(value: float, mode: str, theme: ThemePalette) -> tuple:
    """Return the correct discrete color for a cell value given the CA mode."""
    v = float(value)
    if mode == "binary":
        return theme.P.primary if v > 0.5 else theme.panel_bg

    elif mode == "trinary":
        # 0 = contain (neutral grey)  1 = reinforce (+)  2 = shed (-)
        s = round(v * 2)  # 0→0, 0.5→1, 1→2
        if s == 0:
            return (80, 80, 90)                    # contain — neutral
        elif s == 1:
            return (0, 210, 120)                   # reinforce — warm green
        else:
            return (220, 60, 60)                   # shed — cool red

    elif mode == "wire":
        s = round(v * 3)
        if s == 0:
            return theme.panel_bg                  # EMPTY
        elif s == 1:
            return (60, 60, 80)                    # WIRE — dim blue-grey
        elif s == 2:
            return (255, 220, 0)                   # HEAD — bright yellow
        else:
            return (220, 120, 0)                   # TAIL — orange

    elif mode == "life":
        return theme.P.primary if v > 0.5 else theme.panel_bg

    # Fallback
    return theme.P.cell_color(v)


def grid_to_row(engine) -> Optional[np.ndarray]:
    """Get a 1D float row from any engine type."""
    g = engine.grid
    if g.ndim == 2:
        return g[g.shape[0] // 2].astype(float)  # middle row for 2D
    return g.astype(float)


def engine_mode(engine) -> str:
    """Infer mode string from engine class."""
    cname = type(engine).__name__.lower()
    if "binary" in cname:
        return "binary"
    if "trinary" in cname:
        return "trinary"
    if "life" in cname:
        return "life"
    if "wire" in cname:
        return "wire"
    return "binary"


# ---------------------------------------------------------------------------
# SCOPE — oscilloscope waveform
# ---------------------------------------------------------------------------

@register_view
class ScopeView(ViewRenderer):
    name  = "scope"
    plane = "P"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        w, h = surface.get_width(), surface.get_height()
        surface.fill(theme.panel_bg)

        xp = substrate.X_P
        if len(xp) == 0:
            return

        n   = len(xp)
        mid = h // 2
        amp = max(10, int(h * 0.4))

        # Grid lines
        pygame.draw.line(surface, theme.panel_border, (0, mid), (w, mid), 1)
        for q in [h//4, 3*h//4]:
            pygame.draw.line(surface, theme.panel_border, (0, q), (w, q), 1)

        # Waveform — thin line connecting all cells
        pts = []
        for i in range(n):
            v = float(xp[i])
            x = int(i / max(1, n-1) * (w-1))
            y = mid - int((v - 0.5) * 2 * amp)
            y = max(0, min(h-1, y))
            pts.append((x, y))

        if len(pts) >= 2:
            color = theme.P.primary
            pygame.draw.lines(surface, color, False, pts, 1)
            # Fill below
            fill_pts = pts + [(w-1, mid), (0, mid)]
            try:
                tmp = pygame.Surface((w, h), pygame.SRCALPHA)
                pygame.draw.polygon(tmp, (*color[:3], 40), fill_pts)
                surface.blit(tmp, (0, 0))
            except Exception:
                pass

        self.label(surface, f"SCOPE  n={n}", 4, 4, theme.text, 11)
        self.draw_border(surface, theme.panel_border, 1)


# ---------------------------------------------------------------------------
# RADIAL — time-collapsed polar cross-section
# ---------------------------------------------------------------------------

@register_view
class RadialView(ViewRenderer):
    name  = "radial"
    plane = "P"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        w, h = surface.get_width(), surface.get_height()
        surface.fill(theme.panel_bg)

        history = substrate_history or []
        window  = history[-80:] if len(history) > 80 else history
        if not window:
            self.label(surface, "RADIAL: accumulating...", 4, 4, theme.text, 11)
            return

        N = len(window[0].X_P)
        if N == 0:
            return

        pos  = np.zeros(N)
        neg  = np.zeros(N)
        zero = np.zeros(N)
        w_total = 0.0

        for t_idx, state in enumerate(window):
            wt = 1.0 + (t_idx / max(1, len(window)-1)) * 0.5
            w_total += wt
            xp = state.X_P
            nn = min(N, len(xp))
            for j in range(nn):
                v = float(xp[j])
                if v > 0.67:
                    pos[j] += wt
                elif v > 0.33:
                    zero[j] += wt
                else:
                    neg[j] += wt

        if w_total > 0:
            pos /= w_total; neg /= w_total; zero /= w_total

        cx, cy = w // 2, h // 2
        base_r = min(cx, cy) * 0.25
        gain_r = min(cx, cy) * 0.65

        for j in range(N):
            ang = 2.0 * math.pi * (j / N) - math.pi / 2
            dom = pos[j] - neg[j]
            rr  = base_r + gain_r * abs(dom)
            px  = cx + int(rr * math.cos(ang))
            py  = cy + int(rr * math.sin(ang))
            if dom > 0.05:
                col = theme.P.primary
            elif dom < -0.05:
                col = theme.P.viability_lo
            else:
                col = (80, 80, 90)
            pygame.draw.circle(surface, col, (px, py), 2)

        # Reference circle
        pygame.draw.circle(surface, theme.panel_border, (cx, cy),
                           int(base_r), 1)

        txt = f"RADIAL  window={len(window)}"
        self.label(surface, txt, 4, 4, theme.text, 11)
        self.draw_border(surface, theme.panel_border, 1)


# ---------------------------------------------------------------------------
# VECT — vectorscope circular state display
# ---------------------------------------------------------------------------

@register_view
class VectView(ViewRenderer):
    name  = "vect"
    plane = "P"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        w, h = surface.get_width(), surface.get_height()
        surface.fill((8, 8, 14))

        xp = substrate.X_P
        N  = len(xp)
        if N == 0:
            return

        size    = min(w, h) - 24
        cx      = w // 2
        cy      = h // 2
        base_r  = size * 0.28
        amp_r   = size * 0.20

        # Frame
        pygame.draw.circle(surface, theme.panel_border, (cx, cy), int(size//2), 1)
        pygame.draw.circle(surface, theme.panel_border, (cx, cy), int(base_r), 1)
        pygame.draw.line(surface, theme.panel_border, (cx, cy - size//2), (cx, cy + size//2), 1)
        pygame.draw.line(surface, theme.panel_border, (cx - size//2, cy), (cx + size//2, cy), 1)

        # Trail: plot previous state with alpha for trail effect
        history = substrate_history or []
        for t_idx, state in enumerate(history[-8:]):
            alpha = int(30 + 20 * t_idx)
            xp_h  = state.X_P
            for j in range(min(N, len(xp_h))):
                v    = float(xp_h[j])
                amp  = (v - 0.5) * 2.0
                ang  = 2.0 * math.pi * (j / N) - math.pi / 2
                rr   = base_r + amp_r * amp
                px   = cx + int(rr * math.cos(ang))
                py   = cy + int(rr * math.sin(ang))
                col  = lerp_color(theme.panel_bg, theme.P.secondary, alpha / 255)
                pygame.draw.circle(surface, col, (px, py), 1)

        # Current state — bright
        pts = []
        for j in range(N):
            v    = float(xp[j])
            amp  = (v - 0.5) * 2.0
            ang  = 2.0 * math.pi * (j / N) - math.pi / 2
            rr   = base_r + amp_r * amp
            px   = cx + int(rr * math.cos(ang))
            py   = cy + int(rr * math.sin(ang))
            pts.append((px, py))
            col = (theme.P.primary if amp > 0 else
                   theme.P.viability_lo if amp < -0.1 else (80, 80, 90))
            pygame.draw.circle(surface, col, (px, py), 2)

        # Connect as polygon
        if len(pts) > 2:
            try:
                tmp = pygame.Surface((w, h), pygame.SRCALPHA)
                pygame.draw.polygon(tmp, (*theme.P.primary[:3], 30), pts)
                surface.blit(tmp, (0, 0))
            except Exception:
                pass

        self.label(surface, f"VECT  N={N}  ΩV={canon.Omega_V:.2f}", 4, 4, theme.text, 11)
        self.draw_border(surface, theme.panel_border, 1)


# ---------------------------------------------------------------------------
# TRANSVERSE — cross-section view (end-on view of wave propagation)
# ---------------------------------------------------------------------------

@register_view
class TransverseView(ViewRenderer):
    name  = "transverse"
    plane = "P"

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        w, h = surface.get_width(), surface.get_height()
        surface.fill((5, 5, 15))

        xp = substrate.X_P
        N  = len(xp)
        if N == 0:
            return

        cx, cy = w // 2, h // 2
        max_r  = min(cx, cy) - 12

        # Draw rings: each ring corresponds to a spatial zone of the CA
        n_rings = min(12, N // 4)
        for ring in range(n_rings):
            frac    = (ring + 1) / n_rings
            radius  = int(max_r * frac)
            cell_i  = int(frac * N)
            cell_i  = min(cell_i, N - 1)
            v       = float(xp[cell_i])
            intensity = v
            # Color: high value = bright ring
            col = lerp_color(theme.panel_border, theme.P.primary, intensity)
            pygame.draw.circle(surface, col, (cx, cy), radius, 2)

        # Plot current state as radial spokes
        history = substrate_history or []
        t = substrate.t * 0.15

        for j in range(0, N, max(1, N // 24)):
            v     = float(xp[j])
            amp   = v
            ang   = 2.0 * math.pi * (j / N) + t * 0.3
            r_len = int(max_r * 0.15 * amp)
            r_base = int(max_r * 0.2)
            x1 = cx + int(r_base * math.cos(ang))
            y1 = cy + int(r_base * math.sin(ang))
            x2 = cx + int((r_base + r_len) * math.cos(ang))
            y2 = cy + int((r_base + r_len) * math.sin(ang))
            if r_len > 1:
                col = lerp_color(theme.P.secondary, theme.P.primary, amp)
                pygame.draw.line(surface, col, (x1, y1), (x2, y2), 1)

        # Axes
        pygame.draw.line(surface, (50, 50, 60), (cx, 0), (cx, h), 1)
        pygame.draw.line(surface, (50, 50, 60), (0, cy), (w, cy), 1)

        self.label(surface, f"TRANSVERSE  t={substrate.t}", 4, 4, theme.text, 11)
        self.draw_border(surface, theme.panel_border, 1)


# ---------------------------------------------------------------------------
# WAVEFORM — 5 orthogonal honest channels: v(t) E(t) H(t) B(t) D(t)
# (replaces the fake EM field with lawful projections from the manifold)
# ---------------------------------------------------------------------------

@register_view
class WaveformView(ViewRenderer):
    """
    Five orthogonal diagnostic waveform channels (from Orthogonal Projection spec):
      v(t)  trajectory velocity   — how fast the system moves
      E(t)  transition energy     — cost / surprise of each step
      H(t)  novelty entropy       — windowed Shannon entropy
      B(t)  boundary proximity    — ΩV (distance to infeasibility)
      D(t)  attractor dwell       — persistence near stable states
    """
    name  = "waveform"
    plane = "CANON"

    CHANNELS = [
        ("v(t)", "velocity",    (100, 200, 255)),
        ("E(t)", "energy",      (255, 160, 60)),
        ("H(t)", "entropy",     (180, 100, 255)),
        ("B(t)", "boundary",    (60, 220, 100)),
        ("D(t)", "dwell",       (255, 220, 60)),
    ]

    def _compute_channels(self, substrate_history, canon_history):
        """Compute all 5 channels from available history."""
        n = min(len(substrate_history), len(canon_history))
        if n < 2:
            return {k: [] for _, k, _ in self.CHANNELS}

        subs = substrate_history[-n:]
        cans = canon_history[-n:]

        velocity = []
        energy   = []
        entropy  = []
        boundary = []
        dwell    = []

        prev_xp = None
        dwell_count = 0

        for i, (sub, can) in enumerate(zip(subs, cans)):
            xp = sub.X_P

            # v(t) = ||X_t - X_{t-1}||
            if prev_xp is not None and len(prev_xp) == len(xp):
                vel = float(np.linalg.norm(xp - prev_xp)) / max(1.0, len(xp))
            else:
                vel = 0.0
            velocity.append(min(1.0, vel * 4))

            # E(t) = transition energy ≈ fraction of cells that changed
            if prev_xp is not None and len(prev_xp) == len(xp):
                changed = float(np.mean(np.abs(xp - prev_xp) > 0.1))
            else:
                changed = 0.0
            energy.append(changed)

            # H(t) = windowed Shannon entropy of X_P
            flat = np.maximum(xp, 1e-9)
            flat = flat / flat.sum()
            h = float(-np.sum(flat * np.log(flat + 1e-12)) / max(1, np.log(len(flat))))
            entropy.append(min(1.0, h))

            # B(t) = boundary proximity = ΩV
            boundary.append(float(can.Omega_V))

            # D(t) = attractor dwell: low velocity over time → high dwell
            if vel < 0.05:
                dwell_count = min(dwell_count + 1, 30)
            else:
                dwell_count = max(dwell_count - 2, 0)
            dwell.append(dwell_count / 30.0)

            prev_xp = xp

        return {
            "velocity": velocity, "energy":  energy,  "entropy": entropy,
            "boundary": boundary, "dwell":   dwell,
        }

    def render(self, surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        w, h = surface.get_width(), surface.get_height()
        surface.fill(theme.panel_bg)

        channels = self._compute_channels(
            substrate_history or [], canon_history or [])

        n_ch   = len(self.CHANNELS)
        ch_h   = (h - 20) // n_ch
        label_w = 42

        for i, (sym, key, col) in enumerate(self.CHANNELS):
            y0   = 10 + i * ch_h
            data = channels.get(key, [])

            # Channel background
            bg_rect = pygame.Rect(label_w, y0, w - label_w - 4, ch_h - 2)
            pygame.draw.rect(surface, (12, 12, 20), bg_rect)
            pygame.draw.rect(surface, theme.panel_border, bg_rect, 1)

            # Zero line
            mid_y = y0 + ch_h // 2
            pygame.draw.line(surface, theme.panel_border,
                             (label_w, mid_y), (w - 4, mid_y), 1)

            # Waveform
            if len(data) >= 2:
                pts = []
                dw  = max(1, w - label_w - 4)
                for t_idx, v in enumerate(data[-(dw):]):
                    x = label_w + int(t_idx / max(1, min(len(data), dw)-1) * (dw-1))
                    y = y0 + ch_h - 2 - int(v * (ch_h - 4))
                    y = max(y0, min(y0 + ch_h - 2, y))
                    pts.append((x, y))
                if len(pts) >= 2:
                    pygame.draw.lines(surface, col, False, pts, 1)

                # Current value bar
                cur = data[-1] if data else 0.0
                bar_w_px = int(cur * (label_w - 4))
                pygame.draw.rect(surface, col, (2, y0 + 4, bar_w_px, ch_h - 8))

            # Label
            self.label(surface, sym, 2, mid_y - 6, col, 10)

        self.label(surface, "WAVEFORM  v·E·H·B·D", 4, 2, theme.text_dim, 10)
        self.draw_border(surface, theme.panel_border, 1)
