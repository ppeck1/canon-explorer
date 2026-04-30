"""
IO — presets, export, Book of Holding trajectory format.
"""

from __future__ import annotations
import json
import os
import time
from typing import List, Optional, Dict, Any

from ..core.substrate_lattice import SubstrateState
from ..core.canon_operators import CanonState


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

PRESETS: Dict[str, Dict] = {
    "bacterial_lifecycle": {
        "mode": "life",
        "width": 120,
        "height": 80,
        "rule": "conway",
        "seed": "random",
        "seed_density": 0.35,
        "description": "Conway Life — models birth/survival dynamics of a bacterial colony",
    },
    "empire_collapse": {
        "mode": "binary",
        "width": 300,
        "rule": 110,
        "seed": "single",
        "description": "Rule 110 — edge-of-chaos dynamics analogous to complex civilisation growth",
    },
    "musical_composition": {
        "mode": "trinary",
        "width": 300,
        "rule": 777,
        "seed": "gradient",
        "description": "Trinary CA — three-state patterns analogous to musical harmonic progressions",
    },
    "stable_system": {
        "mode": "binary",
        "width": 300,
        "rule": 4,
        "seed": "random",
        "description": "Rule 4 — highly stable, low entropy system for CANON baseline",
    },
    "hidden_failure": {
        "mode": "binary",
        "width": 300,
        "rule": 30,
        "seed": "single",
        "description": "Rule 30 — chaotic rule; viability degrades unpredictably",
    },
}


def load_preset(name: str) -> Optional[Dict]:
    return PRESETS.get(name)


def list_presets() -> List[str]:
    return list(PRESETS.keys())


# ---------------------------------------------------------------------------
# Screenshot export
# ---------------------------------------------------------------------------

def export_screenshot(surface, directory: str = ".", prefix: str = "ca_explorer") -> str:
    """Save a pygame Surface as PNG. Returns filename."""
    try:
        import pygame
        os.makedirs(directory, exist_ok=True)
        ts       = int(time.time())
        filename = os.path.join(directory, f"{prefix}_{ts}.png")
        pygame.image.save(surface, filename)
        return filename
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Book of Holding export
# ---------------------------------------------------------------------------

class BookOfHoldingExport:
    """
    Export substrate + CANON trajectory as JSON.

    Format:
    {
        "version": "11.0",
        "mode": "binary",
        "trajectory": [
            {
                "t": 0,
                "K": { "P": [lo, hi], "I": "rule_table", "S": n_interp },
                "X": { "P": [...], "I": [...], "S": [...] },
                "canon": { "omega_v": 0.8, ... }
            },
            ...
        ]
    }
    """

    def __init__(self, mode: str = "unknown"):
        self.mode = mode

    def export_trajectory(
        self,
        substrate_history: List[SubstrateState],
        canon_history: List[CanonState],
        filename: str = "trajectory.json",
    ) -> str:
        trajectory = []
        for sub, can in zip(substrate_history, canon_history):
            entry = {
                "t": sub.t,
                "K": {
                    "P": {
                        "lo": sub.K_P.lo.tolist(),
                        "hi": sub.K_P.hi.tolist(),
                    },
                    "S": {"n_interpretations": sub.K_S.n_interpretations},
                },
                "X": {
                    "P": sub.X_P.tolist(),
                    "I": sub.X_I.tolist(),
                    "S": sub.X_S.tolist(),
                },
                "coupling_residue": sub.coupling_map.residue,
                "canon": can.to_dict(),
            }
            trajectory.append(entry)

        doc = {
            "version": "11.0",
            "mode": self.mode,
            "exported_at": int(time.time()),
            "n_steps": len(trajectory),
            "trajectory": trajectory,
        }

        with open(filename, "w") as f:
            json.dump(doc, f, indent=2)

        return filename
