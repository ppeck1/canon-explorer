"""
Docking system v2 — fixes:
  • Collapse/expand toggle (stores natural_height separately)
  • Drag-resize individual panels (drag bottom edge)
  • Drag-resize whole sidebar (drag left edge)
  • Scrollable content
"""

from __future__ import annotations
import pygame
from typing import List, Optional, Tuple
from ..visualization.view_registry import ViewRenderer, list_views, instantiate_view
from ..visualization.colors import ThemePalette, lerp_color
from ..core.substrate_lattice import SubstrateState
from ..core.canon_operators import CanonState


TITLE_H  = 22
MIN_H    = 60
MIN_W    = 180
MAX_W    = 700
SPLITTER = 5


class DockPanel:
    def __init__(self, rect: pygame.Rect, view_name: str,
                 title: str = "", natural_height: int = 120):
        self.rect            = pygame.Rect(rect)
        self._natural_height = natural_height
        self.title           = title or view_name
        self.collapsed       = False
        self._dragging_bottom = False

        self._view_list  = list_views()
        self._view_index = (self._view_list.index(view_name)
                            if view_name in self._view_list else 0)
        self._view_name  = (self._view_list[self._view_index]
                            if self._view_list else view_name)
        self.title       = title or self._view_name
        self._view: Optional[ViewRenderer] = instantiate_view(self._view_name)
        self._surface: Optional[pygame.Surface] = None
        self._flash_alpha = 0

    @property
    def view_name(self) -> str:
        return self._view_name

    @property
    def content_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.rect.left, self.rect.top + TITLE_H,
            self.rect.width, max(0, self.rect.height - TITLE_H),
        )

    def _ensure_surface(self):
        cr = self.content_rect
        if cr.width <= 0 or cr.height <= 0:
            self._surface = None
            return
        if (self._surface is None
                or self._surface.get_width()  != cr.width
                or self._surface.get_height() != cr.height):
            self._surface = pygame.Surface((cr.width, cr.height))

    def toggle_collapse(self):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.rect.height = TITLE_H               # immediate visual update
        else:
            self.rect.height = self._natural_height  # restore remembered height

    def cycle_view(self, direction: int = 1):
        if not self._view_list:
            return
        self._view_index = (self._view_index + direction) % len(self._view_list)
        self._view_name  = self._view_list[self._view_index]
        self.title       = self._view_name
        self._view       = instantiate_view(self._view_name)
        self._surface    = None

    def set_view(self, name: str):
        if name in self._view_list:
            self._view_index = self._view_list.index(name)
            self._view_name  = name
            self.title       = name
            self._view       = instantiate_view(name)
            self._surface    = None

    def flash(self):
        self._flash_alpha = 200

    def render(self, screen: pygame.Surface, substrate, canon, theme,
               substrate_history=None, canon_history=None):
        try:
            font = pygame.font.SysFont("monospace", 11)
        except Exception:
            font = pygame.font.Font(None, 11)

        # Title bar - viability tinted
        title_rect = pygame.Rect(self.rect.left, self.rect.top,
                                 self.rect.width, TITLE_H)
        bar_color = lerp_color(theme.panel_bg,
                               theme.P.viability_color(canon.Omega_V), 0.2)
        pygame.draw.rect(screen, bar_color, title_rect)
        pygame.draw.rect(screen, theme.panel_border, title_rect, 1)

        arrow = "▶" if self.collapsed else "▼"
        txt = font.render(f"{arrow} {self.title}", True, theme.text)
        screen.blit(txt, (self.rect.left + 4, self.rect.top + 5))

        ar = font.render("⟳", True, theme.text_dim)
        screen.blit(ar, (self.rect.right - 14, self.rect.top + 5))

        if self.collapsed:
            return

        self._ensure_surface()
        if self._surface is None or self._view is None:
            return

        try:
            self._view.render(
                self._surface, substrate, canon, theme,
                substrate_history=substrate_history,
                canon_history=canon_history,
            )
        except Exception as e:
            self._surface.fill(theme.panel_bg)
            try:
                ef = font.render(f"! {str(e)[:38]}", True, (220, 60, 60))
                self._surface.blit(ef, (4, 4))
            except Exception:
                pass

        cr = self.content_rect
        screen.blit(self._surface, (cr.left, cr.top))

        # Flash overlay
        if self._flash_alpha > 0:
            fs = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            fs.fill((255, 220, 80, int(self._flash_alpha)))
            screen.blit(fs, self.rect.topleft)
            self._flash_alpha = max(0, self._flash_alpha - 16)

        # Bottom drag handle
        dh = pygame.Rect(self.rect.left + 20, self.rect.bottom - 3,
                         self.rect.width - 40, 3)
        pygame.draw.rect(screen, theme.panel_border, dh)

    def handle_event(self, event) -> Tuple[bool, bool]:
        """Returns (consumed, needs_reflow)."""
        bottom_zone = pygame.Rect(self.rect.left, self.rect.bottom - 6,
                                  self.rect.width, 10)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.collapsed and bottom_zone.collidepoint(event.pos):
                self._dragging_bottom = True
                return True, False

            title_rect = pygame.Rect(self.rect.left, self.rect.top,
                                     self.rect.width, TITLE_H)
            if title_rect.collidepoint(event.pos):
                arrow_rect = pygame.Rect(self.rect.right - 20, self.rect.top,
                                         20, TITLE_H)
                if arrow_rect.collidepoint(event.pos):
                    self.cycle_view(1)
                else:
                    self.toggle_collapse()
                return True, True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging_bottom:
                self._dragging_bottom = False
                return True, True

        elif event.type == pygame.MOUSEMOTION:
            if self._dragging_bottom:
                new_h = max(MIN_H + TITLE_H, event.pos[1] - self.rect.top)
                self.rect.height     = new_h
                self._natural_height = new_h
                return True, True

        return False, False


class DockLayout:
    def __init__(self, rect: pygame.Rect, theme: ThemePalette):
        self.rect   = pygame.Rect(rect)
        self.theme  = theme
        self.panels: List[DockPanel] = []
        self._scroll_y     = 0
        self._drag_sidebar = False
        self._drag_start_x = 0
        self._drag_start_w = 0

    def add_panel(self, view_name: str, title: str = "",
                  height: int = 120) -> DockPanel:
        r = pygame.Rect(self.rect.left, self.rect.top, self.rect.width, height)
        p = DockPanel(r, view_name, title, natural_height=height)
        self.panels.append(p)
        self.reflow()
        return p

    def reflow(self):
        y = self.rect.top - self._scroll_y
        for p in self.panels:
            p.rect.left  = self.rect.left
            p.rect.width = self.rect.width
            p.rect.top   = y
            if p.collapsed:
                p.rect.height = TITLE_H
            y += p.rect.height + 2

    def _total_h(self) -> int:
        return sum(p.rect.height + 2 for p in self.panels)

    def render(self, screen, substrate, canon,
               substrate_history=None, canon_history=None):
        pygame.draw.rect(screen, self.theme.panel_bg, self.rect)
        old_clip = screen.get_clip()
        screen.set_clip(self.rect)

        for p in self.panels:
            if p.rect.bottom < self.rect.top or p.rect.top > self.rect.bottom:
                continue
            p.render(screen, substrate, canon, self.theme,
                     substrate_history=substrate_history,
                     canon_history=canon_history)

        screen.set_clip(old_clip)

        # Left-edge drag handle
        handle_col = (self.theme.P.primary if self._drag_sidebar
                      else self.theme.panel_border)
        pygame.draw.rect(screen, handle_col,
                         pygame.Rect(self.rect.left, self.rect.top,
                                     SPLITTER, self.rect.height))

        # Scrollbar
        total_h = self._total_h()
        if total_h > self.rect.height:
            sb_h = max(20, self.rect.height * self.rect.height // total_h)
            sb_y = self.rect.top + (self._scroll_y
                                    * (self.rect.height - sb_h)
                                    // max(1, total_h - self.rect.height))
            pygame.draw.rect(screen, self.theme.panel_border,
                             pygame.Rect(self.rect.right - 6, sb_y, 5, sb_h))

    def handle_event(self, event) -> bool:
        left_edge = pygame.Rect(self.rect.left - 5, self.rect.top,
                                SPLITTER + 6, self.rect.height)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if left_edge.collidepoint(event.pos):
                self._drag_sidebar  = True
                self._drag_start_x  = event.pos[0]
                self._drag_start_w  = self.rect.width
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._drag_sidebar:
                self._drag_sidebar = False
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self._drag_sidebar:
                dx      = self._drag_start_x - event.pos[0]
                new_w   = max(MIN_W, min(MAX_W, self._drag_start_w + dx))
                shift   = new_w - self.rect.width
                self.rect.left  -= shift
                self.rect.width  = new_w
                self.reflow()
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEWE)
                return True
            if left_edge.collidepoint(event.pos):
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEWE)

        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                total_h    = self._total_h()
                max_scroll = max(0, total_h - self.rect.height)
                self._scroll_y = max(0, min(max_scroll,
                                            self._scroll_y - event.y * 24))
                self.reflow()
                return True

        for p in self.panels:
            consumed, needs_reflow = p.handle_event(event)
            if consumed:
                if needs_reflow:
                    self.reflow()
                return True

        return False

    def set_theme(self, theme: ThemePalette):
        self.theme = theme

    def flash_all(self):
        for p in self.panels:
            p.flash()
