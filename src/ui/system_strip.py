"""
System strip — UI bar showing all active systems as tabs,
with add/remove, per-system mode/rule/color controls.
"""
from __future__ import annotations
import pygame
from typing import List, Optional, Callable, Tuple
from ..core.system_manager import SystemManager, SYSTEM_COLORS, MAX_SYSTEMS
from ..visualization.colors import ThemePalette, lerp_color


STRIP_H = 36   # height of the system strip


class SystemStrip:
    def __init__(self, rect: pygame.Rect, theme: ThemePalette,
                 manager: SystemManager):
        self.rect    = pygame.Rect(rect)
        self.theme   = theme
        self.manager = manager

        self.on_select:      Optional[Callable] = None
        self.on_add:         Optional[Callable] = None
        self.on_remove:      Optional[Callable] = None
        self.on_mode_change: Optional[Callable] = None
        self.on_overlay_toggle: Optional[Callable] = None

        self._slot_rects: List[pygame.Rect] = []
        self._close_rects: List[pygame.Rect] = []

    def _build_rects(self):
        self._slot_rects  = []
        self._close_rects = []
        x   = self.rect.left + 4
        y   = self.rect.top + 4
        h   = self.rect.height - 8
        tab_w = 90

        for i, slot in enumerate(self.manager.slots):
            r = pygame.Rect(x, y, tab_w, h)
            self._slot_rects.append(r)
            # Close button (top-right of tab, small)
            cr = pygame.Rect(r.right - 12, r.top + 2, 10, 10)
            self._close_rects.append(cr)
            x += tab_w + 2

        # "+" button
        self._add_rect = pygame.Rect(x, y, 28, h)
        # Overlay toggle button
        self._overlay_rect = pygame.Rect(x + 32, y, 60, h)

    def draw(self, surface: pygame.Surface):
        self._build_rects()
        pygame.draw.rect(surface, self.theme.panel_bg, self.rect)
        pygame.draw.rect(surface, self.theme.panel_border, self.rect, 1)

        try:
            font  = pygame.font.SysFont("monospace", 10)
            font2 = pygame.font.SysFont("monospace", 9)
        except Exception:
            font  = pygame.font.Font(None, 10)
            font2 = pygame.font.Font(None, 9)

        for i, slot in enumerate(self.manager.slots):
            r   = self._slot_rects[i]
            sel = (i == self.manager._selected)

            bg = lerp_color(self.theme.panel_bg, slot.color, 0.3 if sel else 0.12)
            pygame.draw.rect(surface, bg, r, border_radius=4)
            border_col = slot.color if sel else self.theme.panel_border
            pygame.draw.rect(surface, border_col, r, 1, border_radius=4)

            # System name + mode
            txt = font.render(slot.name, True, slot.color)
            surface.blit(txt, (r.left + 4, r.top + 3))
            sub = font2.render(f"{slot.mode[:3].upper()} r{slot.rule}", True,
                               self.theme.text_dim)
            surface.blit(sub, (r.left + 4, r.top + 14))

            # Close X (only if >1 system)
            if len(self.manager.slots) > 1:
                cr = self._close_rects[i]
                xt = font2.render("×", True, self.theme.text_dim)
                surface.blit(xt, (cr.left, cr.top))

        # Add button
        if len(self.manager.slots) < MAX_SYSTEMS:
            pygame.draw.rect(surface, self.theme.panel_bg, self._add_rect, border_radius=3)
            pygame.draw.rect(surface, self.theme.panel_border, self._add_rect, 1, border_radius=3)
            plus = font.render("+", True, self.theme.P.primary)
            surface.blit(plus, (self._add_rect.centerx - plus.get_width()//2,
                                 self._add_rect.centery - plus.get_height()//2))

        # Overlay toggle
        mode_lbl = "OVERLAY" if self.manager.render_mode == "overlay" else "SIDE-BY"
        pygame.draw.rect(surface, self.theme.panel_bg, self._overlay_rect, border_radius=3)
        pygame.draw.rect(surface, self.theme.panel_border, self._overlay_rect, 1, border_radius=3)
        ot = font2.render(mode_lbl, True, self.theme.P.accent)
        surface.blit(ot, (self._overlay_rect.centerx - ot.get_width()//2,
                           self._overlay_rect.centery - ot.get_height()//2))

    def handle_event(self, event) -> bool:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        self._build_rects()

        for i, r in enumerate(self._slot_rects):
            if r.collidepoint(event.pos):
                # Check close button
                if (len(self.manager.slots) > 1 and
                        self._close_rects[i].collidepoint(event.pos)):
                    self.manager.remove_system(i)
                    if self.on_remove:
                        self.on_remove(i)
                else:
                    self.manager.select(i)
                    if self.on_select:
                        self.on_select(i)
                return True

        if (len(self.manager.slots) < MAX_SYSTEMS and
                self._add_rect.collidepoint(event.pos)):
            if self.on_add:
                self.on_add()
            return True

        if self._overlay_rect.collidepoint(event.pos):
            self.manager.toggle_render_mode()
            if self.on_overlay_toggle:
                self.on_overlay_toggle()
            return True

        return False

    def set_theme(self, theme: ThemePalette):
        self.theme = theme
