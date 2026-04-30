"""
Control panel v2 — mode/theme/seed buttons, tight layout.
Settings sliders now live in SettingsPanel below.
"""

from __future__ import annotations
import pygame
from typing import Optional, Callable, List
from ..visualization.colors import ThemePalette


class Button:
    def __init__(self, rect, label, active=False, tooltip=""):
        self.rect    = pygame.Rect(rect)
        self.label   = label
        self.active  = active
        self.tooltip = tooltip
        self._hover  = False

    def draw(self, surface, theme):
        try:
            font = pygame.font.SysFont("monospace", 11)
        except Exception:
            font = pygame.font.Font(None, 11)

        if self.active:
            bg, fg = theme.P.primary, theme.panel_bg
        elif self._hover:
            bg, fg = theme.panel_border, theme.text
        else:
            bg, fg = theme.panel_bg, theme.text_dim

        pygame.draw.rect(surface, bg, self.rect, border_radius=3)
        pygame.draw.rect(surface, theme.panel_border, self.rect, 1, border_radius=3)
        t = font.render(self.label, True, fg)
        surface.blit(t, (self.rect.centerx - t.get_width() // 2,
                         self.rect.centery - t.get_height() // 2))

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class ControlPanel:
    HEIGHT = 44
    MODES  = ["binary", "trinary", "life", "wire"]

    def __init__(self, rect, theme):
        self.rect    = pygame.Rect(rect)
        self.theme   = theme
        self._mode   = "binary"
        self._paused = False

        self.on_mode_change:   Optional[Callable] = None
        self.on_seed:          Optional[Callable] = None
        self.on_theme_change:  Optional[Callable] = None
        self.on_pause_toggle:  Optional[Callable] = None
        self.on_step:          Optional[Callable] = None
        self.on_settings_toggle: Optional[Callable] = None
        self.on_ortho_toggle:  Optional[Callable] = None

        self._build()

    def _build(self):
        x  = self.rect.left + 6
        y  = self.rect.top + 8
        h  = 26
        bw = 54

        self._mode_btns: List[Button] = []
        for m in self.MODES:
            b = Button((x, y, bw, h), m, active=(m == self._mode),
                        tooltip=f"Switch to {m} CA")
            self._mode_btns.append(b)
            x += bw + 2

        x += 8

        self._seed_btns = [
            Button((x,     y, 58, h), "reseed",  tooltip="Reseed centre"),
            Button((x+60,  y, 58, h), "random",  tooltip="Random seed"),
        ]
        x += 124

        self._theme_btns: List[Button] = []
        for t in ["dark", "amber", "matrix", "solarized"]:
            b = Button((x, y, 70, h), t, tooltip=f"{t} theme")
            self._theme_btns.append(b)
            x += 72

        x += 8
        self._pause_btn = Button((x, y, 36, h), "⏸", tooltip="Space = pause")
        x += 38
        self._step_btn  = Button((x, y, 36, h), "›|", tooltip="→ = step once")
        x += 38

        self._settings_btn = Button((x, y, 72, h), "settings",
                                     tooltip="Toggle settings sliders")
        x += 74
        self._ortho_btn = Button((x, y, 58, h), "SYS-B",
                                  tooltip="Orthogonal impulse system")

    def draw(self, surface):
        pygame.draw.rect(surface, self.theme.panel_bg, self.rect)
        pygame.draw.rect(surface, self.theme.panel_border, self.rect, 1)

        for b in self._mode_btns + self._seed_btns + self._theme_btns:
            b.draw(surface, self.theme)
        self._pause_btn.draw(surface, self.theme)
        self._step_btn.draw(surface, self.theme)
        self._settings_btn.draw(surface, self.theme)
        self._ortho_btn.draw(surface, self.theme)

    def handle_event(self, event) -> bool:
        for b in self._mode_btns:
            if b.handle_event(event):
                self._mode = b.label
                for x in self._mode_btns:
                    x.active = (x.label == self._mode)
                if self.on_mode_change:
                    self.on_mode_change(self._mode)
                return True

        for b in self._seed_btns:
            if b.handle_event(event):
                if self.on_seed:
                    self.on_seed("random" if b.label == "random" else "single")
                return True

        for b in self._theme_btns:
            if b.handle_event(event):
                if self.on_theme_change:
                    self.on_theme_change(b.label)
                return True

        if self._pause_btn.handle_event(event):
            self._paused = not self._paused
            self._pause_btn.label = "▶" if self._paused else "⏸"
            if self.on_pause_toggle:
                self.on_pause_toggle()
            return True

        if self._step_btn.handle_event(event):
            if self.on_step:
                self.on_step()
            return True

        if self._settings_btn.handle_event(event):
            if self.on_settings_toggle:
                self.on_settings_toggle()
            return True

        if self._ortho_btn.handle_event(event):
            if self.on_ortho_toggle:
                self.on_ortho_toggle()
            return True

        return False

    def set_theme(self, theme):
        self.theme = theme

    @property
    def is_paused(self):
        return self._paused
