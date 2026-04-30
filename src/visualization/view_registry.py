"""
View registry — abstract ViewRenderer base + catalog of all registered views.
"""

from __future__ import annotations
import pygame
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Type, List, Optional
from ..core.substrate_lattice import SubstrateState
from ..core.canon_operators import CanonState
from .colors import ThemePalette, gradient, lerp_color


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class ViewRenderer(ABC):
    """Base class for every view panel."""

    name: str = "unnamed"
    plane: str = "P"    # "P", "I", "S", or "CANON"

    def __init__(self):
        self._font_cache: Dict[int, pygame.font.Font] = {}

    def font(self, size: int) -> pygame.font.Font:
        if size not in self._font_cache:
            try:
                self._font_cache[size] = pygame.font.SysFont("monospace", size)
            except Exception:
                self._font_cache[size] = pygame.font.Font(None, size)
        return self._font_cache[size]

    def label(self, surface: pygame.Surface, text: str, x: int, y: int,
              color, size: int = 12):
        f = self.font(size)
        surf = f.render(text, True, color)
        surface.blit(surf, (x, y))

    @abstractmethod
    def render(
        self,
        surface: pygame.Surface,
        substrate: SubstrateState,
        canon: CanonState,
        theme: ThemePalette,
        substrate_history: Optional[List[SubstrateState]] = None,
        canon_history: Optional[List[CanonState]] = None,
    ):
        pass

    def draw_border(self, surface: pygame.Surface, color, width: int = 1):
        r = surface.get_rect()
        pygame.draw.rect(surface, color, r, width)

    def draw_hline(self, surface: pygame.Surface, y: int, color, x0: int = 0, x1: int = -1):
        if x1 < 0:
            x1 = surface.get_width()
        pygame.draw.line(surface, color, (x0, y), (x1, y))

    def sparkline(
        self, surface: pygame.Surface,
        values: List[float],
        rect: pygame.Rect,
        color,
        bg=None,
        y_range: tuple = (0.0, 1.0),
        fill: bool = True,
    ):
        if not values:
            return
        if bg:
            pygame.draw.rect(surface, bg, rect)
        lo, hi = y_range
        span = hi - lo or 1.0
        w, h = rect.width, rect.height
        pts = []
        for i, v in enumerate(values):
            x = rect.left + int(i / max(1, len(values) - 1) * w)
            y = rect.bottom - int((v - lo) / span * h)
            pts.append((x, y))
        if fill and len(pts) > 1:
            poly = pts + [(pts[-1][0], rect.bottom), (pts[0][0], rect.bottom)]
            fill_color = (*color[:3], 60)
            tmp = pygame.Surface((w, h), pygame.SRCALPHA)
            off = [(p[0] - rect.left, p[1] - rect.top) for p in poly]
            pygame.draw.polygon(tmp, fill_color, off)
            surface.blit(tmp, rect.topleft)
        if len(pts) > 1:
            pygame.draw.lines(surface, color, False, pts, 1)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_VIEW_REGISTRY: Dict[str, Type[ViewRenderer]] = {}


def register_view(cls: Type[ViewRenderer]) -> Type[ViewRenderer]:
    _VIEW_REGISTRY[cls.name] = cls
    return cls


def get_view(name: str) -> Optional[Type[ViewRenderer]]:
    return _VIEW_REGISTRY.get(name)


def list_views() -> List[str]:
    return sorted(_VIEW_REGISTRY.keys())


def instantiate_view(name: str) -> Optional[ViewRenderer]:
    cls = get_view(name)
    return cls() if cls else None
