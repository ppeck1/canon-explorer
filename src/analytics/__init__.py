"""
Analytics — substrate metrics, FFT analysis, entropy.
"""

from __future__ import annotations
import numpy as np
from typing import List, Optional, Tuple
from ..core.substrate_lattice import SubstrateState
from ..core.canon_operators import CanonState


# ---------------------------------------------------------------------------
# Substrate metrics
# ---------------------------------------------------------------------------

class SubstrateMetrics:
    """Diagnostic metrics for the 9D substrate lattice."""

    @staticmethod
    def plane_entropy(x: np.ndarray) -> float:
        """Shannon entropy of a normalised state vector."""
        flat = x.flatten().astype(float)
        if flat.max() == flat.min():
            return 0.0
        hist, _ = np.histogram(flat, bins=16)
        hist = hist.astype(float) + 1e-9
        hist /= hist.sum()
        return float(-np.sum(hist * np.log2(hist)))

    @staticmethod
    def lattice_distance(s1: SubstrateState, s2: SubstrateState) -> float:
        """L2 distance between two substrate physical states."""
        return float(np.linalg.norm(s1.X_P - s2.X_P))

    @staticmethod
    def belief_divergence(s1: SubstrateState, s2: SubstrateState) -> float:
        """KL-divergence between two belief distributions."""
        p = np.maximum(s1.X_S, 1e-12)
        q = np.maximum(s2.X_S, 1e-12)
        p /= p.sum()
        q /= q.sum()
        return float(np.sum(p * np.log(p / q)))

    @staticmethod
    def trajectory_curvature(history: List[SubstrateState]) -> float:
        """Curvature of X_P trajectory (second derivative norm)."""
        if len(history) < 3:
            return 0.0
        a, b, c = history[-3].X_P, history[-2].X_P, history[-1].X_P
        accel = c - 2 * b + a
        return float(np.linalg.norm(accel))


# ---------------------------------------------------------------------------
# FFT analysis
# ---------------------------------------------------------------------------

class FFTAnalysis:
    """Frequency-domain analysis of CA state."""

    @staticmethod
    def power_spectrum(state: np.ndarray, n_bins: int = 32) -> Tuple[np.ndarray, np.ndarray]:
        """Return (frequencies, power) for a 1D CA state."""
        flat  = state.flatten().astype(float)
        fft   = np.fft.rfft(flat)
        power = np.abs(fft) ** 2
        freqs = np.fft.rfftfreq(len(flat))
        # Bin into n_bins buckets
        bins  = np.array_split(power, min(n_bins, len(power)))
        bin_p = np.array([b.mean() for b in bins])
        bin_f = np.linspace(0, 0.5, len(bin_p))
        return bin_f, bin_p

    @staticmethod
    def dominant_frequency(state: np.ndarray) -> float:
        """Return the dominant spatial frequency (0..0.5)."""
        flat  = state.flatten().astype(float)
        fft   = np.fft.rfft(flat)
        power = np.abs(fft) ** 2
        freqs = np.fft.rfftfreq(len(flat))
        if len(freqs) < 2:
            return 0.0
        # Ignore DC
        return float(freqs[1:][np.argmax(power[1:])])

    @staticmethod
    def spectral_entropy(state: np.ndarray) -> float:
        """Entropy of the power spectrum."""
        _, power = FFTAnalysis.power_spectrum(state)
        power = np.maximum(power, 1e-12)
        power = power / power.sum()
        return float(-np.sum(power * np.log2(power)))


# ---------------------------------------------------------------------------
# Entropy tracker
# ---------------------------------------------------------------------------

class EntropyTracker:
    """Track rolling entropy of X_P over time."""

    def __init__(self, window: int = 64):
        self.window  = window
        self._buffer: List[float] = []

    def push(self, state: SubstrateState):
        e = SubstrateMetrics.plane_entropy(state.X_P)
        self._buffer.append(e)
        if len(self._buffer) > self.window:
            self._buffer.pop(0)

    @property
    def current(self) -> float:
        return self._buffer[-1] if self._buffer else 0.0

    @property
    def trend(self) -> float:
        if len(self._buffer) < 4:
            return 0.0
        return float(np.polyfit(range(len(self._buffer)), self._buffer, 1)[0])

    @property
    def history(self) -> List[float]:
        return list(self._buffer)
