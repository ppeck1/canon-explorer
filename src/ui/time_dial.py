"""
TimeDial v2 — larger, freely draggable, scroll-resizable.
"""

from __future__ import annotations
import pygame
import math
from typing import Optional, Tuple
from ..visualization.colors import ThemePalette, lerp_color


class TimeDial:
    MIN_SPEED = 0.1
    MAX_SPEED = 100.0     # raised from 10x to 100x
    NEUTRAL   = 1.0
    MIN_R     = 28
    MAX_R     = 90
    DEFAULT_R = 52        # larger default

    def __init__(self, cx: int, cy: int, radius: int = DEFAULT_R):
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self._angle   = self._speed_to_angle(self.NEUTRAL)
        self._dragging_needle  = False
        self._dragging_body    = False
        self._drag_body_offset = (0, 0)

    @property
    def speed(self) -> float:
        return self._angle_to_speed(self._angle)

    @speed.setter
    def speed(self, v: float):
        self._angle = self._speed_to_angle(
            max(self.MIN_SPEED, min(self.MAX_SPEED, v)))

    @staticmethod
    def _speed_to_angle(speed: float) -> float:
        t = (math.log(speed) - math.log(TimeDial.MIN_SPEED)) / \
            (math.log(TimeDial.MAX_SPEED) - math.log(TimeDial.MIN_SPEED))
        return -math.pi + t * math.pi   # -π (slow) … 0 (fast)

    @staticmethod
    def _angle_to_speed(angle: float) -> float:
        t = (angle + math.pi) / math.pi
        t = max(0.0, min(1.0, t))
        return TimeDial.MIN_SPEED * (TimeDial.MAX_SPEED / TimeDial.MIN_SPEED) ** t

    def _hit_needle(self, pos) -> bool:
        """Is pos near the needle/dial face?"""
        dx = pos[0] - self.cx
        dy = pos[1] - self.cy
        return math.hypot(dx, dy) <= self.radius + 10

    def _hit_body(self, pos) -> bool:
        """Is pos in the drag-move grab zone (centre circle)?"""
        dx = pos[0] - self.cx
        dy = pos[1] - self.cy
        return math.hypot(dx, dy) <= self.radius * 0.45

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._hit_body(event.pos):
                self._dragging_body    = True
                self._drag_body_offset = (event.pos[0] - self.cx,
                                          event.pos[1] - self.cy)
                return True
            if self._hit_needle(event.pos):
                self._dragging_needle = True
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging_needle or self._dragging_body:
                self._dragging_needle = False
                self._dragging_body   = False
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self._dragging_body:
                self.cx = event.pos[0] - self._drag_body_offset[0]
                self.cy = event.pos[1] - self._drag_body_offset[1]
                return True
            if self._dragging_needle:
                dx = event.pos[0] - self.cx
                dy = event.pos[1] - self.cy
                angle = math.atan2(dy, dx)
                # Clamp to upper semicircle: -π .. 0
                angle = max(-math.pi, min(0.0, angle))
                self._angle = angle
                return True

        elif event.type == pygame.MOUSEWHEEL:
            if self._hit_needle(pygame.mouse.get_pos()):
                # Scroll wheel: resize the dial
                if event.x != 0:
                    self.radius = max(self.MIN_R,
                                      min(self.MAX_R, self.radius + event.x * 4))
                else:
                    factor = 1.25 if event.y > 0 else 1 / 1.25
                    self.speed = self.speed * factor
                return True

        return False

    def draw(self, surface: pygame.Surface, theme: ThemePalette):
        r   = self.radius
        cx, cy = self.cx, self.cy
        speed  = self.speed

        # Shadow
        pygame.draw.circle(surface, (0, 0, 0), (cx + 3, cy + 3), r)

        # Background
        pygame.draw.circle(surface, theme.panel_bg, (cx, cy), r)

        # Speed arc
        t = (math.log(speed) - math.log(self.MIN_SPEED)) / \
            (math.log(self.MAX_SPEED) - math.log(self.MIN_SPEED))
        arc_color = lerp_color(theme.P.viability_lo, theme.P.viability_hi, t)

        arc_thick = max(3, r // 7)
        sweep_deg = int(t * 180)
        if sweep_deg > 0:
            pygame.draw.arc(
                surface, arc_color,
                (cx - r + arc_thick, cy - r + arc_thick,
                 (r - arc_thick) * 2, (r - arc_thick) * 2),
                math.pi, math.pi + self._angle + math.pi,
                arc_thick,
            )

        # Outer ring
        pygame.draw.circle(surface, theme.panel_border, (cx, cy), r, 2)

        # Tick marks
        try:
            font = pygame.font.SysFont("monospace", max(7, r // 6))
        except Exception:
            font = pygame.font.Font(None, max(7, r // 6))

        for speed_tick in [0.1, 0.25, 1.0, 5.0, 25.0, 100.0]:
            if speed_tick > self.MAX_SPEED:
                continue
            a    = self._speed_to_angle(speed_tick)
            ir   = r - arc_thick - 2
            tx   = cx + int(math.cos(a) * ir)
            ty   = cy + int(math.sin(a) * ir)
            pygame.draw.circle(surface, theme.panel_border, (tx, ty), 2)
            # Label outermost ticks
            if speed_tick in (0.1, 1.0, 100.0):
                lx = cx + int(math.cos(a) * (r + 8))
                ly = cy + int(math.sin(a) * (r + 8))
                lbl = f"{int(speed_tick) if speed_tick >= 1 else speed_tick}x"
                lt  = font.render(lbl, True, theme.text_dim)
                surface.blit(lt, (lx - lt.get_width() // 2,
                                  ly - lt.get_height() // 2))

        # Needle
        nx = cx + int(math.cos(self._angle) * (r - arc_thick - 4))
        ny = cy + int(math.sin(self._angle) * (r - arc_thick - 4))
        pygame.draw.line(surface, arc_color, (cx, cy), (nx, ny), 2)

        # Centre hub (drag target)
        hub_r = max(5, r // 5)
        pygame.draw.circle(surface, theme.panel_bg, (cx, cy), hub_r)
        pygame.draw.circle(surface, arc_color,      (cx, cy), hub_r, 2)

        # Speed text
        try:
            sf  = pygame.font.SysFont("monospace", max(9, r // 4))
            stxt = sf.render(f"{speed:.1f}×", True, arc_color)
            surface.blit(stxt, (cx - stxt.get_width() // 2, cy + r + 4))
        except Exception:
            pass

        # Drag hint when moving
        if self._dragging_body:
            pygame.draw.circle(surface, arc_color, (cx, cy), r + 3, 1)
