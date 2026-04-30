"""
CA Explorer v11.2 — Multi-system application
• N systems side-by-side or overlay
• Restored SCOPE/RADIAL/VECT/TRANSVERSE/WAVEFORM views
• Fast Life rendering via numpy surfarray
• Discrete state colors
• No impulse flash on sidebar panels
• Settings sliders restored
"""

from __future__ import annotations
import sys, math, time
import pygame
import numpy as np
from typing import Optional, Tuple, List

from ..core.ca_engines import make_engine
from ..core.integration import UnifiedSimulation
from ..core.system_manager import SystemManager, SYSTEM_COLORS
from ..visualization.colors import get_theme, list_themes, ThemePalette
from ..visualization.view_registry import list_views
from .docking_system import DockLayout
from .control_panel import ControlPanel
from .settings_panel import SettingsPanel
from .time_dial import TimeDial
from .multi_viewport import MultiSystemViewport
from .system_strip import SystemStrip, STRIP_H


WIN_W   = 1440
WIN_H   = 900
CTRL_H  = 44
DOCK_W  = 300
FPS_CAP = 120


class Application:
    VERSION = "11.2.0"

    def __init__(self, width: int = WIN_W, height: int = WIN_H):
        pygame.init()
        pygame.font.init()
        self.width  = width
        self.height = height
        self.screen = pygame.display.set_mode(
            (width, height), pygame.RESIZABLE)
        pygame.display.set_caption(
            f"CA Explorer v{self.VERSION} — Substrate Lattice + CANON")

        self._theme_name = "dark"
        self.theme = get_theme(self._theme_name)

        # Multi-system manager (starts with 1 system)
        self.manager = SystemManager(width=300, height=80)

        self.clock        = pygame.time.Clock()
        self._paused      = False
        self._step_once   = False
        self._speed       = 1.0
        self._step_accum  = 0.0
        self._settings_visible = True
        self._frame       = 0

        self.viewport = MultiSystemViewport()
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        settings_h = SettingsPanel.HEIGHT_OPEN if self._settings_visible else 0
        sidebar_left = self.width - self.dock.rect.width if hasattr(self, "dock") else self.width - DOCK_W

        # Control strip
        self.controls = ControlPanel(
            pygame.Rect(0, 0, self.width, CTRL_H), self.theme)
        self.controls.on_mode_change     = self._change_mode
        self.controls.on_seed            = self._reseed_selected
        self.controls.on_theme_change    = self._change_theme
        self.controls.on_pause_toggle    = self._toggle_pause
        self.controls.on_step            = lambda: setattr(self, "_step_once", True)
        self.controls.on_settings_toggle = self._toggle_settings
        self.controls.on_ortho_toggle    = self._add_system   # repurposed

        # System strip (below control)
        self.system_strip = SystemStrip(
            pygame.Rect(0, CTRL_H, self.width - DOCK_W, STRIP_H),
            self.theme, self.manager)
        self.system_strip.on_add    = self._add_system
        self.system_strip.on_select = lambda i: self._update_controls_for_selected()
        self.system_strip.on_remove = lambda i: None

        # Settings panel
        settings_top = CTRL_H + STRIP_H
        self.settings = SettingsPanel(
            pygame.Rect(0, settings_top, self.width - DOCK_W,
                        SettingsPanel.HEIGHT_OPEN), self.theme)
        self.settings.visible = self._settings_visible
        self._wire_settings()

        # Dock sidebar
        dock_left = self.width - DOCK_W
        dock_rect = pygame.Rect(dock_left, CTRL_H, DOCK_W, self.height - CTRL_H)
        if not hasattr(self, "dock"):
            self.dock = DockLayout(dock_rect, self.theme)
            self.dock.add_panel("viability",       "ΩV Viability",    height=100)
            self.dock.add_panel("collapse",        "Δc* Collapse",    height=80)
            self.dock.add_panel("history",         "H History",       height=80)
            self.dock.add_panel("waveform",        "WAVEFORM v·E·H·B·D", height=160)
            self.dock.add_panel("vect",            "VECT",            height=160)
            self.dock.add_panel("radial",          "RADIAL",          height=160)
            self.dock.add_panel("belief",          "X_S Belief",      height=140)
            self.dock.add_panel("canon_dashboard", "CANON",           height=90)
        else:
            self.dock.rect = dock_rect
        self.dock.reflow()

        # Time dial
        if not hasattr(self, "dial"):
            self.dial = TimeDial(cx=dock_left - 70, cy=CTRL_H // 2 + 8)
        else:
            self.dial.cx = dock_left - 70

    def _main_top(self) -> int:
        settings_h = SettingsPanel.HEIGHT_OPEN if self._settings_visible else 0
        return CTRL_H + STRIP_H + settings_h

    def _main_rect(self) -> pygame.Rect:
        top = self._main_top()
        return pygame.Rect(0, top, self.dock.rect.left, self.height - top)

    # ------------------------------------------------------------------
    def _wire_settings(self):
        sel = self.manager.selected
        self.settings.set("RULE", float(getattr(sel.engine, "rule", 110)))
        self._pulse_radius = int(self.settings.get("PULSE_R"))

        def on_rule(v):
            self.manager.selected.set_rule(int(v))
        def on_coup(v):
            n = self.manager.n
            for i in range(n):
                for j in range(n):
                    if i != j:
                        self.manager.coupling.set(i, j, v * 0.5)
        def on_pulse_r(v):
            self._pulse_radius = int(v)

        self.settings.callbacks["RULE"]    = on_rule
        self.settings.callbacks["COUP"]    = on_coup
        self.settings.callbacks["PULSE_R"] = on_pulse_r

    def _update_controls_for_selected(self):
        sel = self.manager.selected
        self.settings.set("RULE", float(getattr(sel.engine, "rule", 110)))

    # ------------------------------------------------------------------
    def _add_system(self):
        modes = ["binary", "trinary", "life", "wire"]
        n = self.manager.n
        mode = modes[n % len(modes)]
        rules = [30, 110, 90, 150]
        rule = rules[n % len(rules)]
        self.manager.add_system(mode=mode, rule=rule)

    def _change_mode(self, mode: str):
        sel = self.manager.selected
        old_idx = sel.index
        # Recreate the engine on the selected slot
        from ..core.system_manager import SystemSlot
        new = SystemSlot.create(old_idx, mode=mode, rule=sel.rule,
                                color=sel.color, width=300, height=80)
        self.manager.slots[old_idx] = new
        self.manager.coupling.resize(self.manager.n)
        self._wire_settings()

    def _reseed_selected(self, mode: str = "single"):
        self.manager.selected.reseed(mode)

    def _change_theme(self, name: str):
        self._theme_name = name
        self.theme = get_theme(name)
        self.dock.set_theme(self.theme)
        self.controls.set_theme(self.theme)
        self.settings.set_theme(self.theme)
        self.system_strip.set_theme(self.theme)

    def _toggle_pause(self):
        self._paused = not self._paused

    def _toggle_settings(self):
        self._settings_visible = not self._settings_visible
        self.settings.visible  = self._settings_visible

    # ------------------------------------------------------------------
    def _inject_at(self, pos: Tuple[int, int], right_click: bool,
                   target_slot_idx: Optional[int] = None):
        mr = self._main_rect()
        if not mr.collidepoint(pos):
            return

        rx = pos[0] - mr.left
        ry = pos[1] - mr.top

        n      = len([s for s in self.manager.slots if s.active])
        slot_w = mr.width // max(1, n)

        # Which system column is clicked?
        col_idx = min(rx // max(1, slot_w), n - 1)
        active  = [s for s in self.manager.slots if s.active]
        if col_idx >= len(active):
            return

        if target_slot_idx is not None:
            slot = self.manager.slots[target_slot_idx]
        else:
            slot = active[col_idx]

        e = slot.engine
        # x within this column
        col_x = rx - col_idx * slot_w
        r     = self._pulse_radius

        if hasattr(e, "height") and e.height > 1:
            cx = int(col_x / max(1, slot_w) * e.width)
            cy = int(ry    / max(1, mr.height) * e.height)
            slot.inject(cx, cy, radius=r, right_click=right_click)
        else:
            cx = int(col_x / max(1, slot_w) * e.width)
            slot.inject(cx, radius=r, right_click=right_click)

    # ------------------------------------------------------------------
    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                k = event.key
                if k == pygame.K_ESCAPE:
                    return False
                elif k == pygame.K_SPACE:
                    self._toggle_pause()
                    self.controls._paused = self._paused
                    self.controls._pause_btn.label = "▶" if self._paused else "⏸"
                elif k == pygame.K_RIGHT:
                    self._step_once = True
                elif k == pygame.K_r:
                    self._reseed_selected("single")
                elif k == pygame.K_d:
                    self._reseed_selected("random")
                elif k == pygame.K_t:
                    themes = list_themes()
                    idx = (themes.index(self._theme_name)+1) % len(themes)
                    self._change_theme(themes[idx])
                elif k == pygame.K_s:
                    self._toggle_settings()
                elif k == pygame.K_o:
                    self.manager.toggle_render_mode()
                elif k == pygame.K_PLUS or k == pygame.K_EQUALS:
                    self._add_system()
                # System select 1-6
                elif pygame.K_1 <= k <= pygame.K_6:
                    idx = k - pygame.K_1
                    if idx < self.manager.n:
                        self.manager.select(idx)
                        self._update_controls_for_selected()

            if event.type == pygame.VIDEORESIZE:
                self.width, self.height = event.w, event.h
                self.screen = pygame.display.set_mode(
                    (self.width, self.height), pygame.RESIZABLE)
                self.dock.rect.left  = self.width - self.dock.rect.width
                self.dock.rect.height = self.height - CTRL_H
                self.dock.reflow()

            # Mouse
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if self._main_rect().collidepoint(event.pos):
                        self._inject_at(event.pos, right_click=False)
                elif event.button == 3:
                    if self._main_rect().collidepoint(event.pos):
                        self._inject_at(event.pos, right_click=True)

            if event.type == pygame.MOUSEMOTION:
                if event.buttons[0] and self._main_rect().collidepoint(event.pos):
                    self._inject_at(event.pos, right_click=False)
                elif event.buttons[2] and self._main_rect().collidepoint(event.pos):
                    self._inject_at(event.pos, right_click=True)

            if self.dial.handle_event(event):
                self._speed = self.dial.speed
                continue
            if self.controls.handle_event(event):
                continue
            if self.settings.visible and self.settings.handle_event(event):
                continue
            if self.system_strip.handle_event(event):
                continue
            self.dock.handle_event(event)

        return True

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if self._paused and not self._step_once:
            return

        if self._step_once:
            steps = 1
            self._step_once = False
        else:
            self._step_accum += self._speed * dt
            burst = max(1, min(80, int(self._speed * 4)))
            steps = min(int(self._step_accum), burst)
            self._step_accum -= steps

        if steps > 0:
            self.manager.step_all(steps)

        self._frame += 1

    # ------------------------------------------------------------------
    def render(self):
        self.screen.fill(self.theme.bg_app)
        settings_h = SettingsPanel.HEIGHT_OPEN if self._settings_visible else 0

        # Main multi-system viewport
        mr = self._main_rect()
        if mr.width > 0 and mr.height > 0:
            main_surf = pygame.Surface((mr.width, mr.height))
            try:
                self.viewport.render(main_surf, self.manager, self.theme)
            except Exception as ex:
                main_surf.fill(self.theme.panel_bg)
                try:
                    f = pygame.font.SysFont("monospace", 11)
                    main_surf.blit(f.render(str(ex), True, (200,60,60)), (4,4))
                except Exception:
                    pass
            self.screen.blit(main_surf, (mr.left, mr.top))

        # Use selected system's CANON for sidebar
        sel = self.manager.selected
        self.dock.rect.height = self.height - CTRL_H
        self.dock.render(
            self.screen,
            sel.sim.current_substrate,
            sel.sim.current_canon,
            substrate_history=sel.sim.substrate_history,
            canon_history=sel.sim.canon_history,
        )

        # Control strip
        self.controls.rect.width = self.width
        self.controls.draw(self.screen)

        # System strip
        self.system_strip.rect = pygame.Rect(0, CTRL_H,
                                              self.dock.rect.left, STRIP_H)
        self.system_strip.draw(self.screen)

        # Settings panel
        if self._settings_visible:
            self.settings.layout(self.width, CTRL_H + STRIP_H,
                                  self.dock.rect.left)
            self.settings.draw(self.screen)

        # Time dial
        self.dial.draw(self.screen, self.theme)

        # Status bar
        try:
            fps  = self.clock.get_fps()
            font = pygame.font.SysFont("monospace", 10)
            info = font.render(
                f"v{self.VERSION}  fps={fps:.0f}  "
                f"{self.manager.n}sys  {self.manager.render_mode}  "
                f"{self._speed:.1f}×  t={sel.sim.t}  "
                f"O=overlay  +=add  1-6=select",
                True, self.theme.text_dim)
            self.screen.blit(info, (4, self.height - 14))
        except Exception:
            pass

        pygame.display.flip()

    # ------------------------------------------------------------------
    def run(self):
        prev = time.perf_counter()
        while True:
            now  = time.perf_counter()
            dt   = min(now - prev, 0.1)
            prev = now
            if not self.handle_events():
                break
            self.update(dt)
            self.render()
            self.clock.tick(FPS_CAP)
        pygame.quit()


def main():
    Application().run()

if __name__ == "__main__":
    main()
