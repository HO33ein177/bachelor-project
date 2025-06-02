# agent_hal.py
import numpy as np
import time # Corrected import from django.template.defaultfilters import time

class RFHardwareSimulator:
    def __init__(self):
        self.connected = False # Initialize connection status
        self.cosine_frequency_hz = 10e6 # Default: 10 MHz
        self.cosine_amplitude_v = 1.0   # Default: 1.0 V
        self.cosine_phase_rad = 0.0     # Default: 0 radians
        self.noise_amplitude_v = 0.1    # Default: 0.1 V

        # Default display parameters, matching common oscilloscope characteristics
        self.time_per_div_s = 0.2e-6  # Default: 0.2 µs per division
        self.num_horizontal_divisions = 10 # Standard for oscilloscopes
        self.num_time_points = 501       # Fixed number of points for acquisition (common for scopes)

        # Derived parameters (calculated in configure_cosine_wave or __init__)
        self.time_duration_s = self.time_per_div_s * self.num_horizontal_divisions
        # Default sample rate based on initial defaults
        self.sample_rate_hz = self.num_time_points / self.time_duration_s if self.time_duration_s > 0 else 500e6

        # Spectrum parameters
        self.spectrum_ref_level_dbm = 0 # Default reference level for FFT plot

        print("Mock RF Hardware Simulator (Oscilloscope Edition) initialized.")
        self.connect() # Attempt to "connect" on initialization

    def connect(self):
        """Simulates connecting to the hardware."""
        # In a real scenario, this would initialize PyVISA and open the instrument.
        # For simulation, we just set a flag.
        self.connected = True
        print("MockRF: Simulated hardware 'connected'.")
        return True

    def disconnect(self):
        """Simulates disconnecting from the hardware."""
        # In a real scenario, this would close the PyVISA instrument session.
        self.connected = False
        print("MockRF: Simulated hardware 'disconnected'.")

    def configure_cosine_wave(self, frequency_hz, amplitude_v, phase_rad=0.0,
                              time_per_div_s=0.2e-6, # New parameter passed from agent
                              num_time_points=501,    # New parameter passed from agent
                              noise_v=0.1):
        if not self.connected:
            print("MockRF: Error - Not connected for configure_cosine_wave.")
            return False

        # Update wave parameters
        self.cosine_frequency_hz = frequency_hz
        self.cosine_amplitude_v = amplitude_v
        self.cosine_phase_rad = phase_rad
        self.noise_amplitude_v = noise_v

        # Update display/acquisition parameters, ensuring consistency
        self.time_per_div_s = time_per_div_s
        self.num_time_points = num_time_points
        self.time_duration_s = self.time_per_div_s * self.num_horizontal_divisions

        # Recalculate sample rate based on updated duration and num_points
        if self.time_duration_s > 0:
            self.sample_rate_hz = self.num_time_points / self.time_duration_s
        else: # Avoid division by zero, set a default high sample rate if duration is zero
            self.sample_rate_hz = 500e6

        print(f"MockRF: Cosine configured: Freq={self.cosine_frequency_hz/1e6:.2f}MHz, Amp={self.cosine_amplitude_v:.2f}V, Noise={self.noise_amplitude_v:.2f}V")
        print(f"MockRF: Display configured: Time/Div={self.time_per_div_s*1e6:.2f}µs, Total Duration={self.time_duration_s*1e6:.2f}µs, Points={self.num_time_points}, SR={self.sample_rate_hz/1e6:.1f}MSa/s")
        return True

    def get_simulated_data(self):
        if not self.connected:
            print("MockRF: Error - Not connected for data acquisition.")
            return None

        current_num_points = self.num_time_points
        if current_num_points <= 0:
            print("MockRF: Error - Invalid number of points (<=0).")
            return None

        # --- Time Domain Data Generation ---
        time_points_s = np.linspace(0, self.time_duration_s, current_num_points, endpoint=False)
        amplitude_values = self.cosine_amplitude_v * np.cos(
            2 * np.pi * self.cosine_frequency_hz * time_points_s + self.cosine_phase_rad
        )
        amplitude_values += np.random.normal(0, self.noise_amplitude_v, current_num_points)

        # --- Frequency Domain (Spectrum) Data Generation using FFT ---
        fft_raw_output = np.fft.rfft(amplitude_values)
        fft_magnitude = np.abs(fft_raw_output) / current_num_points
        epsilon = 1e-12 # Small value to prevent log of zero
        power_spectrum_db = 20 * np.log10(fft_magnitude + epsilon)
        fft_power_dbm = power_spectrum_db - np.max(power_spectrum_db) + self.spectrum_ref_level_dbm

        fft_frequencies_hz = np.fft.rfftfreq(current_num_points, d=1.0/self.sample_rate_hz if self.sample_rate_hz > 0 else 1)
        # Ensure frequencies match the length of power data (rfft returns N/2 + 1 bins)
        fft_frequencies_hz = fft_frequencies_hz[:len(fft_power_dbm)].tolist()


        return {
            "time_s": time_points_s.tolist(),
            "amplitude_v": amplitude_values.tolist(),
            "wave_details": {
                "frequency_hz": self.cosine_frequency_hz,
                "amplitude_v": self.cosine_amplitude_v,
                "time_per_div_s": self.time_per_div_s,
                "duration_s": self.time_duration_s,
                "actual_sample_rate_hz": self.sample_rate_hz,
                "num_points_time": current_num_points,
            },
            "fft_frequencies_hz": fft_frequencies_hz,
            "fft_power_dbm": fft_power_dbm.tolist(),
            "spectrum_details": {
                "ref_level_dbm": self.spectrum_ref_level_dbm,
                "num_points_fft": len(fft_frequencies_hz),
                "fft_start_freq_hz": fft_frequencies_hz[0] if fft_frequencies_hz else 0,
                "fft_stop_freq_hz": fft_frequencies_hz[-1] if fft_frequencies_hz else 0,
            },
            "timestamp": time.time()
        }