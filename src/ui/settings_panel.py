"""
Settings panel — RULE / THR / COUP / INERT / PULSE_R sliders
(restored from v9.8.6, adapted for v11)

Also hosts the Orthogonal System controls.
"""

from __future__ import annotations
import pygame
from typing import Optional, Callable, Dict, Any
from ..visualization.colors import ThemePalette, lerp_color


class Slider:
    """Horizontal slider with label and live value display."""

    def __init__(self, label: str, value: float, lo: float, hi: float,
                 step: float = 0.0, integer: bool = False,
                 callback: Optional[Callable] = None):
        self.label    = label
        self.value    = value
        self.lo       = lo
        self.hi       = hi
        self.step     = step
        self.integer  = integer
        self.callback = callback
        self.rect     = pygame.Rect(0, 0, 100, 16)
        self._dragging = False

    def set_rect(self, rect: pygame.Rect):
        self.rect = pygame.Rect(rect)

    def _clamp(self, v: float) -> float:
        v = max(self.lo, min(self.hi, v))
        if self.step > 0:
            v = round(v / self.step) * self.step
        if self.integer:
            v = round(v)
        return v

    def _t(self) -> float:
        return (self.value - self.lo) / max(1e-9, self.hi - self.lo)

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._dragging = True
                self._set_from_x(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging:
                self._dragging = False
                return True
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            self._set_from_x(event.pos[0])
            return True
        return False

    def _set_from_x(self, x: int):
        t   = (x - self.rect.left) / max(1, self.rect.width)
        new = self._clamp(self.lo + t * (self.hi - self.lo))
        if new != self.value:
            self.value = new
            if self.callback:
                self.callback(new)

    def draw(self, surface: pygame.Surface, theme: ThemePalette,
             label_w: int = 70, val_w: int = 40):
        r = self.rect
        try:
            font = pygame.font.SysFont("monospace", 11)
        except Exception:
            font = pygame.font.Font(None, 11)

        # Label
        lt = font.render(self.label, True, theme.text)
        surface.blit(lt, (r.left, r.centery - lt.get_height() // 2))

        # Track
        track = pygame.Rect(r.left + label_w, r.top + r.height // 2 - 2,
                            r.width - label_w - val_w, 4)
        pygame.draw.rect(surface, theme.panel_border, track)
        # Fill
        fill_w = int(track.width * self._t())
        fill_c = lerp_color(theme.P.secondary, theme.P.primary, self._t())
        if fill_w > 0:
            pygame.draw.rect(surface, fill_c,
                             pygame.Rect(track.left, track.top, fill_w, track.height))
        # Thumb
        thumb_x = track.left + fill_w
        pygame.draw.rect(surface, theme.P.accent,
                         pygame.Rect(thumb_x - 3, r.top + 1, 6, r.height - 2))

        # Value
        val_str = (f"{int(self.value)}" if self.integer
                   else f"{self.value:.2f}")
        vt = font.render(val_str, True, theme.P.primary)
        surface.blit(vt, (r.right - val_w + 2, r.centery - vt.get_height() // 2))


class SettingsPanel:
    """
    Collapsible settings strip below the control bar.
    Contains: RULE, THR, COUP, INERT, PULSE_R sliders
    + Orthogonal system controls.
    """

    HEIGHT_OPEN   = 72
    HEIGHT_CLOSED = 0

    def __init__(self, rect: pygame.Rect, theme: ThemePalette):
        self.rect    = pygame.Rect(rect)
        self.theme   = theme
        self.visible = True

        # Slider values (defaults matching v9.8.6 screenshot)
        self._vals: Dict[str, float] = {
            "RULE":    110.0,
            "THR":     1.20,
            "COUP":    1.00,
            "INERT":   0.25,
            "PULSE_R": 3.0,
        }

        # Callbacks → wired by Application
        self.callbacks: Dict[str, Optional[Callable]] = {
            k: None for k in self._vals
        }

        self._sliders: Dict[str, Slider] = {}
        self._build_sliders()

    def _build_sliders(self):
        specs = [
            ("RULE",    0,   255,  1.0,  True),
            ("THR",     0.1, 3.0,  0.05, False),
            ("COUP",    0.0, 2.0,  0.05, False),
            ("INERT",   0.0, 1.0,  0.05, False),
            ("PULSE_R", 1,   10,   1.0,  True),
        ]
        for key, lo, hi, step, integer in specs:
            def make_cb(k):
                def cb(v):
                    self._vals[k] = v
                    if self.callbacks.get(k):
                        self.callbacks[k](v)
                return cb
            self._sliders[key] = Slider(
                key, self._vals[key], lo, hi,
                step=step, integer=integer,
                callback=make_cb(key),
            )

    def get(self, key: str) -> float:
        return self._vals.get(key, 0.0)

    def set(self, key: str, value: float):
        if key in self._sliders:
            self._sliders[key].value = value
            self._vals[key] = value

    def layout(self, full_width: int, y_top: int, sidebar_left: int):
        self.rect = pygame.Rect(0, y_top, sidebar_left, self.HEIGHT_OPEN)
        if not self.visible:
            self.rect.height = 0
            return

        n      = len(self._sliders)
        margin = 6
        sw     = (self.rect.width - margin * 2) // n
        sy     = y_top + 8

        for i, (key, slider) in enumerate(self._sliders.items()):
            slider.set_rect(pygame.Rect(
                margin + i * sw, sy, sw - 4, 20
            ))

    def draw(self, surface: pygame.Surface):
        if not self.visible or self.rect.height == 0:
            return
        pygame.draw.rect(surface, self.theme.panel_bg, self.rect)
        pygame.draw.rect(surface, self.theme.panel_border, self.rect, 1)

        for slider in self._sliders.values():
            slider.draw(surface, self.theme)

        try:
            font = pygame.font.SysFont("monospace", 10)
            tip  = font.render(
                "Tip: left-click grid to inject  |  right-click to erase/wire  "
                "|  scroll dial to change speed  |  drag dial to move it",
                True, self.theme.text_dim,
            )
            surface.blit(tip, (8, self.rect.bottom - 18))
        except Exception:
            pass

    def handle_event(self, event) -> bool:
        if not self.visible:
            return False
        for slider in self._sliders.values():
            if slider.handle_event(event):
                return True
        return False

    def set_theme(self, theme: ThemePalette):
        self.theme = theme
        for s in self._sliders.values():
            pass  # theme is accessed at draw time
