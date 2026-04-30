"""
Multi-system viewport — renders N systems side-by-side or as overlay.
Each system gets its own column; 2D Life uses numpy surfarray for speed.
State coloring is discrete (not gradient) per mode.
"""
from __future__ import annotations
import pygame
import numpy as np
import math
from typing import List, Optional, Tuple

from ..core.system_manager import SystemManager, SystemSlot
from ..visualization.colors import ThemePalette, lerp_color
from ..visualization.scope_views import state_color, engine_mode


def _render_slot_1d(surface: pygame.Surface, slot: SystemSlot,
                    theme: ThemePalette, show_history: bool = True):
    """Spacetime strip for 1D engines — numpy-accelerated."""
    w, h = surface.get_width(), surface.get_height()
    mode = engine_mode(slot.engine)
    hist = slot.sim.substrate_history

    if not hist:
        surface.fill(theme.panel_bg)
        return

    n_rows = min(h, len(hist))
    if n_rows == 0:
        surface.fill(theme.panel_bg)
        return

    n_col = len(hist[0].X_P)
    if n_col == 0:
        surface.fill(theme.panel_bg)
        return

    cw = max(1, w // n_col)

    # Build pixel array efficiently
    pixel_arr = np.zeros((w, h, 3), dtype=np.uint8)
    # Fill bg
    bg = theme.panel_bg
    pixel_arr[:, :, 0] = bg[0]
    pixel_arr[:, :, 1] = bg[1]
    pixel_arr[:, :, 2] = bg[2]

    for row_idx, state in enumerate(hist[-n_rows:]):
        y = h - n_rows + row_idx
        if y < 0 or y >= h:
            continue
        xp = state.X_P
        n = min(n_col, len(xp))
        for i in range(n):
            v   = float(xp[i])
            col = state_color(v, mode, theme)
            x0  = i * cw
            x1  = min(w, x0 + cw)
            if col != theme.panel_bg:
                pixel_arr[x0:x1, y] = col

    try:
        surf = pygame.surfarray.make_surface(pixel_arr)
        surface.blit(surf, (0, 0))
    except Exception:
        # Fallback: slow pixel loop
        surface.fill(theme.panel_bg)
        for row_idx, state in enumerate(hist[-n_rows:]):
            y = h - n_rows + row_idx
            xp = state.X_P
            for i in range(min(n_col, len(xp))):
                v   = float(xp[i])
                col = state_color(v, mode, theme)
                if cw == 1:
                    surface.set_at((i, y), col)
                else:
                    pygame.draw.rect(surface, col, (i*cw, y, cw, 1))

    # Current generation line
    pygame.draw.line(surface, slot.color, (0, h-2), (w, h-2), 2)


def _render_slot_2d(surface: pygame.Surface, slot: SystemSlot,
                    theme: ThemePalette):
    """
    2D grid (Life) — numpy surfarray path for full speed.
    No Python loops over cells.
    """
    engine = slot.engine
    w, h   = surface.get_width(), surface.get_height()
    grid   = engine.grid

    rows, cols = grid.shape
    cw = max(1, w // cols)
    ch = max(1, h // rows)

    # Build full pixel array via numpy broadcast
    # live cells → slot.color, dead → bg
    live_mask = (grid > 0)   # shape (rows, cols)

    # Create RGB arrays
    r = np.where(live_mask, slot.color[0], theme.panel_bg[0]).astype(np.uint8)
    g = np.where(live_mask, slot.color[1], theme.panel_bg[1]).astype(np.uint8)
    b = np.where(live_mask, slot.color[2], theme.panel_bg[2]).astype(np.uint8)

    # Stack to (rows, cols, 3) then scale to screen size
    rgb = np.stack([r, g, b], axis=2)

    if cw == 1 and ch == 1 and rgb.shape[:2] == (h, w):
        # Perfect fit — direct surfarray
        try:
            # surfarray expects (width, height, 3)
            surf = pygame.surfarray.make_surface(rgb.transpose(1, 0, 2))
            surface.blit(surf, (0, 0))
            return
        except Exception:
            pass

    # Scale up via numpy repeat
    rgb_up = np.repeat(np.repeat(rgb, ch, axis=0), cw, axis=1)
    rgb_up = rgb_up[:h, :w]   # crop to surface size

    try:
        surf = pygame.surfarray.make_surface(
            rgb_up.transpose(1, 0, 2).astype(np.uint8))
        surface.blit(surf, (0, 0))
    except Exception:
        # Final fallback
        surface.fill(theme.panel_bg)
        for r_idx in range(rows):
            for c_idx in range(cols):
                if grid[r_idx, c_idx]:
                    pygame.draw.rect(surface, slot.color,
                                     (c_idx*cw, r_idx*ch, cw-1, ch-1))


def _render_slot_hud(surface: pygame.Surface, slot: SystemSlot,
                     theme: ThemePalette):
    """Draw name, step, CANON metrics as HUD overlay on a slot surface."""
    try:
        font  = pygame.font.SysFont("monospace", 11)
        canon = slot.sim.current_canon
        txt   = font.render(
            f"{slot.name}  t={slot.sim.t}  "
            f"ΩV={canon.Omega_V:.2f}  Γ={canon.Gamma:.2f}",
            True, slot.color,
        )
        # Semi-transparent bg for readability
        bg_surf = pygame.Surface((txt.get_width() + 8, txt.get_height() + 4),
                                  pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 120))
        surface.blit(bg_surf, (2, 2))
        surface.blit(txt, (4, 4))
    except Exception:
        pass


class MultiSystemViewport:
    """
    Renders 1–N systems in side-by-side columns or overlay blend.
    No flash effects.
    """

    def render(self, surface: pygame.Surface, manager: SystemManager,
               theme: ThemePalette):
        active = [s for s in manager.slots if s.active]
        if not active:
            surface.fill(theme.panel_bg)
            return

        if manager.render_mode == SystemManager.RENDER_SIDEBYSIDE:
            self._render_sidebyside(surface, active, theme)
        else:
            self._render_overlay(surface, active, theme)

    def _render_sidebyside(self, surface, slots: list, theme: ThemePalette):
        w, h   = surface.get_width(), surface.get_height()
        n      = len(slots)
        slot_w = w // n

        for i, slot in enumerate(slots):
            x0   = i * slot_w
            # Account for last slot getting remainder pixels
            sw   = slot_w if i < n-1 else w - x0
            sub  = pygame.Surface((sw, h))

            e = slot.engine
            if hasattr(e, "height") and e.height > 1:
                _render_slot_2d(sub, slot, theme)
            else:
                _render_slot_1d(sub, slot, theme)

            _render_slot_hud(sub, slot, theme)

            surface.blit(sub, (x0, 0))

            # Separator
            if i < n - 1:
                pygame.draw.line(surface, slot.color,
                                 (x0 + sw, 0), (x0 + sw, h), 1)

    def _render_overlay(self, surface, slots: list, theme: ThemePalette):
        """Blend all systems into one surface. Dead cells = bg; live = color blend."""
        w, h = surface.get_width(), surface.get_height()
        surface.fill(theme.panel_bg)

        for slot in slots:
            tmp = pygame.Surface((w, h), pygame.SRCALPHA)
            tmp.fill((0, 0, 0, 0))

            sub = pygame.Surface((w, h))
            e   = slot.engine
            if hasattr(e, "height") and e.height > 1:
                _render_slot_2d(sub, slot, theme)
            else:
                _render_slot_1d(sub, slot, theme)

            # Alpha-blend with 50% opacity per layer
            tmp.blit(sub, (0, 0))
            tmp.set_alpha(180 // len(slots))
            surface.blit(tmp, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # HUD for all
        try:
            font = pygame.font.SysFont("monospace", 10)
            x = 4
            for slot in slots:
                canon = slot.sim.current_canon
                txt = font.render(
                    f"{slot.name}  ΩV={canon.Omega_V:.2f}", True, slot.color)
                surface.blit(txt, (x, 4))
                x += txt.get_width() + 12
        except Exception:
            pass
