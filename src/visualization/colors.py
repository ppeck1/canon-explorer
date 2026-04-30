"""
Color palette system
Four built-in themes × three plane palettes (P / I / S)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Dict, List
import numpy as np

Color = Tuple[int, int, int]


def lerp_color(a: Color, b: Color, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def gradient(colors: List[Color], t: float) -> Color:
    """Multi-stop gradient, t in [0, 1]."""
    if len(colors) == 1:
        return colors[0]
    n = len(colors) - 1
    scaled = t * n
    idx    = int(scaled)
    frac   = scaled - idx
    idx    = min(idx, n - 1)
    return lerp_color(colors[idx], colors[idx + 1], frac)


# ---------------------------------------------------------------------------
@dataclass
class PlanePalette:
    """Colors for a single substrate plane."""
    bg:        Color
    primary:   Color
    secondary: Color
    accent:    Color
    text:      Color
    grid:      Color
    viability_hi: Color    # ΩV high (good)
    viability_lo: Color    # ΩV low  (danger)

    def cell_color(self, value: float) -> Color:
        """value in [0, 1]"""
        return gradient([self.bg, self.primary, self.accent], value)

    def viability_color(self, omega_v: float) -> Color:
        return lerp_color(self.viability_lo, self.viability_hi, omega_v)


@dataclass
class ThemePalette:
    """A complete theme with palettes for all three planes."""
    name: str
    P: PlanePalette    # Physical
    I: PlanePalette    # Informational
    S: PlanePalette    # Subjective
    bg_app:    Color   # Application background
    panel_bg:  Color
    panel_border: Color
    text:      Color
    text_dim:  Color

    def plane(self, name: str) -> PlanePalette:
        return {"P": self.P, "I": self.I, "S": self.S}[name]


# ---------------------------------------------------------------------------
# Built-in themes
# ---------------------------------------------------------------------------

THEMES: Dict[str, ThemePalette] = {}

# --- DARK (default) ---
THEMES["dark"] = ThemePalette(
    name="dark",
    P=PlanePalette(
        bg=(10, 10, 20),
        primary=(0, 180, 255),
        secondary=(0, 100, 180),
        accent=(0, 255, 200),
        text=(200, 220, 255),
        grid=(30, 40, 60),
        viability_hi=(0, 220, 120),
        viability_lo=(220, 40, 40),
    ),
    I=PlanePalette(
        bg=(10, 20, 10),
        primary=(80, 220, 80),
        secondary=(40, 140, 40),
        accent=(180, 255, 80),
        text=(200, 255, 200),
        grid=(20, 40, 20),
        viability_hi=(80, 255, 80),
        viability_lo=(200, 80, 40),
    ),
    S=PlanePalette(
        bg=(20, 10, 25),
        primary=(200, 80, 255),
        secondary=(120, 40, 180),
        accent=(255, 160, 255),
        text=(230, 200, 255),
        grid=(40, 20, 50),
        viability_hi=(180, 100, 255),
        viability_lo=(220, 40, 80),
    ),
    bg_app=(8, 8, 12),
    panel_bg=(16, 16, 24),
    panel_border=(40, 50, 80),
    text=(200, 210, 230),
    text_dim=(100, 110, 140),
)

# --- SOLARIZED ---
THEMES["solarized"] = ThemePalette(
    name="solarized",
    P=PlanePalette(
        bg=(0, 43, 54),
        primary=(38, 139, 210),
        secondary=(42, 161, 152),
        accent=(133, 153, 0),
        text=(131, 148, 150),
        grid=(7, 54, 66),
        viability_hi=(133, 153, 0),
        viability_lo=(220, 50, 47),
    ),
    I=PlanePalette(
        bg=(7, 54, 66),
        primary=(42, 161, 152),
        secondary=(133, 153, 0),
        accent=(181, 137, 0),
        text=(147, 161, 161),
        grid=(0, 43, 54),
        viability_hi=(100, 200, 100),
        viability_lo=(211, 54, 130),
    ),
    S=PlanePalette(
        bg=(7, 54, 66),
        primary=(211, 54, 130),
        secondary=(108, 113, 196),
        accent=(181, 137, 0),
        text=(147, 161, 161),
        grid=(0, 43, 54),
        viability_hi=(42, 161, 152),
        viability_lo=(220, 50, 47),
    ),
    bg_app=(0, 43, 54),
    panel_bg=(7, 54, 66),
    panel_border=(88, 110, 117),
    text=(131, 148, 150),
    text_dim=(88, 110, 117),
)

# --- AMBER (retro terminal) ---
THEMES["amber"] = ThemePalette(
    name="amber",
    P=PlanePalette(
        bg=(20, 10, 0),
        primary=(255, 160, 0),
        secondary=(200, 100, 0),
        accent=(255, 220, 80),
        text=(255, 180, 60),
        grid=(40, 20, 0),
        viability_hi=(255, 220, 0),
        viability_lo=(180, 40, 0),
    ),
    I=PlanePalette(
        bg=(15, 10, 0),
        primary=(200, 130, 0),
        secondary=(160, 90, 0),
        accent=(255, 200, 60),
        text=(220, 160, 40),
        grid=(30, 15, 0),
        viability_hi=(200, 200, 40),
        viability_lo=(160, 30, 0),
    ),
    S=PlanePalette(
        bg=(20, 10, 0),
        primary=(255, 100, 20),
        secondary=(180, 60, 0),
        accent=(255, 180, 40),
        text=(240, 160, 40),
        grid=(35, 18, 0),
        viability_hi=(255, 180, 0),
        viability_lo=(200, 20, 0),
    ),
    bg_app=(10, 5, 0),
    panel_bg=(18, 9, 0),
    panel_border=(80, 40, 0),
    text=(220, 150, 40),
    text_dim=(120, 70, 0),
)

# --- MATRIX (green phosphor) ---
THEMES["matrix"] = ThemePalette(
    name="matrix",
    P=PlanePalette(
        bg=(0, 8, 0),
        primary=(0, 220, 0),
        secondary=(0, 140, 0),
        accent=(120, 255, 120),
        text=(0, 200, 0),
        grid=(0, 24, 0),
        viability_hi=(0, 255, 80),
        viability_lo=(200, 40, 0),
    ),
    I=PlanePalette(
        bg=(0, 6, 0),
        primary=(0, 180, 0),
        secondary=(0, 100, 0),
        accent=(80, 220, 80),
        text=(0, 160, 0),
        grid=(0, 18, 0),
        viability_hi=(0, 220, 60),
        viability_lo=(160, 30, 0),
    ),
    S=PlanePalette(
        bg=(0, 10, 0),
        primary=(0, 200, 60),
        secondary=(0, 120, 40),
        accent=(100, 255, 100),
        text=(0, 180, 40),
        grid=(0, 22, 0),
        viability_hi=(0, 240, 100),
        viability_lo=(180, 40, 20),
    ),
    bg_app=(0, 4, 0),
    panel_bg=(0, 10, 0),
    panel_border=(0, 60, 0),
    text=(0, 200, 0),
    text_dim=(0, 100, 0),
)

DEFAULT_THEME = "dark"


def get_theme(name: str) -> ThemePalette:
    return THEMES.get(name, THEMES[DEFAULT_THEME])


def list_themes() -> List[str]:
    return list(THEMES.keys())
