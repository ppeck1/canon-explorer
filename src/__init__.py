"""CA Explorer v11 — Substrate Lattice + CANON viability analysis."""

__version__ = "11.0.0-alpha"

from .core import (
    SubstrateState, CanonState, CanonOperators,
    BinaryEngine, TrinaryEngine, LifeEngine, WireEngine,
    make_engine, UnifiedSimulation,
)
from .visualization import get_theme, list_themes, list_views
from .ui import Application, main
