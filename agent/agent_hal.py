"""Lightweight RF hardware simulator.

This module provides a minimal stand‑in for the oscilloscope used by the
project.  It generates a noisy sine wave and performs a very small FFT using
only the Python standard library so that it can run in environments where
`numpy` and other scientific packages are unavailable.  The structure of the
returned payload mirrors the JSON expected by ``receive_rf_data_view`` in the
``users`` Django app.
"""

from __future__ import annotations

import math
import random
import time
from typing import Dict, List, Tuple
class RFHardwareSimulator:
    """Produce mock RF data for the agent.
    The simulator generates a single sine wave with configurable frequency and
       amplitude.  Each call to :meth:`get_simulated_data` returns time‑domain data
       and a very small FFT so that the front‑end charts can be exercised without
       access to the real oscilloscope.
       """

    def __init__(self) -> None:
        self.connected = True

        # Default waveform parameters
        self.cosine_frequency_hz = 1_000.0  # 1 kHz
        self.cosine_amplitude_v = 1.0
        self.noise_amplitude_v = 0.05

        # Acquisition settings
        self.num_horizontal_divisions = 10
        self.num_time_points = 256
        self.sample_rate_hz = 10_000.0  # 10 kSa/s
        self.time_duration_s = self.num_time_points / self.sample_rate_hz
        self.time_per_div_s = self.time_duration_s / self.num_horizontal_divisions

        # Spectrum display parameters
        self.spectrum_ref_level_dbm = 0.0

    # ------------------------------------------------------------------
    # Configuration helpers
    def connect(self) -> bool:
        self.connected = True
        return True
    def disconnect(self) -> None:
        self.connected = False

    def configure_cosine_wave(
            self,
            frequency_hz: float,
            amplitude_v: float,
            time_per_div_s: float = 0.001,
            num_time_points: int = 256,
            noise_v: float = 0.05,
            **_ignored: object,
    ) -> bool:
        """Update basic waveform settings.

        Additional keyword arguments are accepted for API compatibility but are
        ignored by this lightweight simulator.
        """
        if not self.connected:
            self.cosine_frequency_hz = frequency_hz
            self.cosine_amplitude_v = amplitude_v
            self.noise_amplitude_v = noise_v
            self.time_per_div_s = time_per_div_s
            self.num_time_points = max(1, num_time_points)
            self.time_duration_s = self.time_per_div_s * self.num_horizontal_divisions
            self.sample_rate_hz = self.num_time_points / self.time_duration_s

            return True
# ------------------------------------------------------------------
    def _compute_fft(self, samples: List[float]) -> Tuple[List[float], List[float]]:
        """Return FFT magnitudes in dBm using a naive DFT implementation."""

        n = len(samples)
        freqs: List[float] = []
        powers: List[float] = []
        for k in range(n // 2 + 1):
            re = 0.0
            im = 0.0
            for i, x in enumerate(samples):
                angle = 2 * math.pi * k * i / n
                re += x * math.cos(angle)
                im -= x * math.sin(angle)
            mag = math.hypot(re, im) / n
            power_db = 20 * math.log10(mag + 1e-12)
            freqs.append(k * self.sample_rate_hz / n)
            powers.append(power_db)
        return freqs, powers

    def get_simulated_data(self) -> Dict[str, object]:
        if not self.connected:
            return {}
# Generate time axis and noisy sine wave
        time_points = [i / self.sample_rate_hz for i in range(self.num_time_points)]
        amplitudes = [
            self.cosine_amplitude_v * math.sin(2 * math.pi * self.cosine_frequency_hz * t)
            + self.noise_amplitude_v * random.uniform(-1, 1)
            for t in time_points
        ]
        fft_freqs, fft_dbm = self._compute_fft(amplitudes)

        return {
            "time_s": time_points,
            "amplitude_v": amplitudes,
            "wave_details": {
                "frequency_hz": self.cosine_frequency_hz,
                "amplitude_v": self.cosine_amplitude_v,
                "time_per_div_s": self.time_per_div_s,
                "duration_s": self.time_duration_s,
                "actual_sample_rate_hz": self.sample_rate_hz,
                "num_points_time": self.num_time_points,
            },
            "fft_frequencies_hz": fft_freqs,
            "fft_power_dbm": fft_dbm,
            "spectrum_details": {
                "ref_level_dbm": self.spectrum_ref_level_dbm,
                "num_points_fft": len(fft_freqs),
                "fft_start_freq_hz": fft_freqs[0] if fft_freqs else 0.0,
                "fft_stop_freq_hz": fft_freqs[-1] if fft_freqs else 0.0,
            },
            "timestamp": time.time(),
        }
