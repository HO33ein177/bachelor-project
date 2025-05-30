# agent_hal.py
import numpy as np
from django.template.defaultfilters import time


class RFHardwareSimulator:
    def __init__(self):
        # ... (existing parameters like cosine_frequency_hz, cosine_amplitude_v, etc.) ...
        self.time_per_div_s = 0.2e-6 # Default: 0.2 µs per division
        self.num_horizontal_divisions = 10 # Standard for oscilloscopes
        self.num_time_points = 501 # Keep this somewhat fixed for now, or calculate based on sample rate
        # self.sample_rate_hz is still important for Nyquist & FFT

        # Calculate initial time_duration_s based on time_per_div_s
        self.time_duration_s = self.time_per_div_s * self.num_horizontal_divisions
        # Adjust sample_rate_hz based on new duration and fixed points, or vice-versa
        # For simplicity, let's say sample_rate determines num_points for a given duration
        self.sample_rate_hz = self.num_time_points / self.time_duration_s if self.time_duration_s > 0 else 500e6

        # ... (rest of __init__)
        print("Mock RF Hardware Simulator (Oscilloscope Edition) initialized.")
        self.connect()

    # Update configure_cosine_wave to also accept/use time_per_div
    def configure_cosine_wave(self, frequency_hz, amplitude_v, phase_rad=0.0,
                              time_per_div_s=0.2e-6, # New parameter
                              num_time_points=501,    # Can also be a parameter
                              noise_v=0.1):
        if not self.connected:
            print("MockRF: Error - Not connected for configure_cosine_wave.")
            return False
        self.cosine_frequency_hz = frequency_hz
        self.cosine_amplitude_v = amplitude_v
        self.cosine_phase_rad = phase_rad

        self.time_per_div_s = time_per_div_s
        self.num_time_points = num_time_points # Allow GUI to set preferred points
        self.time_duration_s = self.time_per_div_s * self.num_horizontal_divisions

        # Adjust sample rate based on new duration and num_points
        if self.time_duration_s > 0:
            self.sample_rate_hz = self.num_time_points / self.time_duration_s
        else: # Avoid division by zero, set a default if duration is zero
            self.sample_rate_hz = 500e6 # A default high sample rate

        self.noise_amplitude_v = noise_v
        print(f"MockRF: Cosine configured: Freq={self.cosine_frequency_hz/1e6:.2f}MHz, Amp={self.cosine_amplitude_v:.2f}V")
        print(f"MockRF: Display configured: Time/Div={self.time_per_div_s*1e6:.2f}µs, Total Duration={self.time_duration_s*1e6:.2f}µs, Points={self.num_time_points}, SR={self.sample_rate_hz/1e6:.1f}MSa/s")
        return True

    def get_simulated_data(self): # Name kept from previous step
        if not self.connected: # ... (error check) ...
            return None

        # Ensure num_points is consistent with what sample_rate and duration imply
        # Or, recalculate num_points here based on current self.time_duration_s and self.sample_rate_hz
        # For simplicity, we'll use self.num_time_points set during configuration.
        # If self.sample_rate_hz was fixed, then num_points would be self.time_duration_s * self.sample_rate_hz

        current_num_points = self.num_time_points
        if current_num_points <= 0:
            print("MockRF: Error - Invalid number of points (<=0).")
            return None

        # --- Time Domain Data Generation ---
        # time_duration_s is now derived from time_per_div_s
        time_points_s = np.linspace(0, self.time_duration_s, current_num_points, endpoint=False)
        amplitude_values = self.cosine_amplitude_v * np.cos(
            2 * np.pi * self.cosine_frequency_hz * time_points_s + self.cosine_phase_rad
        )
        amplitude_values += np.random.normal(0, self.noise_amplitude_v, current_num_points)

        # --- Frequency Domain (Spectrum) Data Generation using FFT ---
        fft_raw_output = np.fft.rfft(amplitude_values)
        fft_magnitude = np.abs(fft_raw_output) / current_num_points
        epsilon = 1e-12
        power_spectrum_db = 20 * np.log10(fft_magnitude + epsilon)
        fft_power_dbm = power_spectrum_db - np.max(power_spectrum_db) + self.spectrum_ref_level_dbm

        # Sample rate used for FFT freq calculation is self.sample_rate_hz
        fft_frequencies_hz = np.fft.rfftfreq(current_num_points, d=1.0/self.sample_rate_hz if self.sample_rate_hz > 0 else 1)


        # print(f"MockRF: Acquired simulated data (Time Points: {current_num_points}, FFT Bins: {len(fft_frequencies_hz)})...")

        return {
            "time_s": time_points_s.tolist(),
            "amplitude_v": amplitude_values.tolist(),
            "wave_details": {
                "frequency_hz": self.cosine_frequency_hz,
                "amplitude_v": self.cosine_amplitude_v,
                "time_per_div_s": self.time_per_div_s, # Send this to frontend
                "duration_s": self.time_duration_s,
                "actual_sample_rate_hz": self.sample_rate_hz,
                "num_points_time": current_num_points,
            },
            "fft_frequencies_hz": fft_frequencies_hz.tolist(),
            "fft_power_dbm": fft_power_dbm.tolist(),
            "spectrum_details": {
                "ref_level_dbm": self.spectrum_ref_level_dbm,
                "num_points_fft": len(fft_frequencies_hz),
                "fft_start_freq_hz": fft_frequencies_hz[0] if len(fft_frequencies_hz) > 0 else 0,
                "fft_stop_freq_hz": fft_frequencies_hz[-1] if len(fft_frequencies_hz) > 0 else 0,
            },
            "timestamp": time.time()
        }
# ... (rest of the class: rf_device_simulator instance) ...