# agent_hal.py
import numpy as np
import time
import pyvisa

class RFHardwareSimulator: # Or RFHardwareInterface if you're using the hardware version
    def __init__(self, visa_resource_string=None): # Added visa_resource_string for compatibility
        # For simulation, visa_resource_string is not strictly used here, but for future hardware path
        self.rm = None # pyvisa.ResourceManager() if using hardware
        self.inst = None # For hardware
        self.visa_resource_string = visa_resource_string
        self.connected = True # Always connected for simulator, False for hardware initially

        # --- Main Wave Parameters ---
        self.cosine_frequency_hz = 10e6 # Default: 10 MHz
        self.cosine_amplitude_v = 1.0   # Default: 1.0 V
        self.cosine_phase_rad = 0.0     # Default: 0 radians
        self.noise_amplitude_v = 0.1    # Default: 0.1 V (applied to main wave)

        # --- SECOND WAVE Parameters ---
        self.cosine2_frequency_hz = 20e6 # Default: 20 MHz
        self.cosine2_amplitude_v = 0.5   # Default: 0.5 V
        self.cosine2_phase_rad = np.pi/4 # Default: 45 degrees phase shift

        # Default display/acquisition parameters (can be configured by frontend)
        self.time_per_div_s = 0.2e-6  # Default: 0.2 µs per division
        self.num_horizontal_divisions = 10 # Standard for oscilloscopes
        self.num_time_points = 1000       # Number of points for acquisition (common for scopes)
        self.time_duration_s = self.time_per_div_s * self.num_horizontal_divisions
        self.sample_rate_hz = self.num_time_points / self.time_duration_s if self.time_duration_s > 0 else 500e6

        # Spectrum parameters for display normalization
        self.spectrum_ref_level_dbm = 0 # Default reference level for FFT plot

        print("Mock RF Hardware Simulator (Oscilloscope Edition) initialized.")
        # self.connect() # Removed as it's always connected for simulator, or called explicitly for hardware

    def connect(self):
        """Simulates connecting to the hardware (or explicitly connects if hardware)."""
        # For simulator, this just confirms connected
        self.connected = True
        print("MockRF: Simulated hardware 'connected'.")
        return True

    def disconnect(self):
        """Simulates disconnecting from the hardware (or explicitly disconnects if hardware)."""
        self.connected = False
        print("MockRF: Simulated hardware 'disconnected'.")

    def configure_cosine_wave(self, frequency_hz, amplitude_v, phase_rad=0.0,
                              frequency_hz2=None, amplitude_v2=None, phase_rad2=np.pi/4, # New params for second wave
                              time_per_div_s=0.2e-6, num_time_points=1000, noise_v=0.1):

        if not self.connected:
            print("MockRF: Error - Not connected for configure_cosine_wave.")
            return False

        # Updated Main Wave parameters
        self.cosine_frequency_hz = frequency_hz
        self.cosine_amplitude_v = amplitude_v
        self.cosine_phase_rad = phase_rad
        self.noise_amplitude_v = noise_v

        # Updated Second Wave parameters
        self.cosine2_frequency_hz = frequency_hz2 if frequency_hz2 is not None else self.cosine2_frequency_hz
        self.cosine2_amplitude_v = amplitude_v2 if amplitude_v2 is not None else self.cosine2_amplitude_v
        self.cosine2_phase_rad = phase_rad2

        # Updated display/acquisition parameters
        self.time_per_div_s = time_per_div_s
        self.num_time_points = num_time_points
        self.time_duration_s = self.time_per_div_s * self.num_horizontal_divisions
        if self.time_duration_s > 0:
            self.sample_rate_hz = self.num_time_points / self.time_duration_s
        else:
            self.sample_rate_hz = 500e6

        print(f"MockRF: Main Wave: Freq={self.cosine_frequency_hz/1e6:.2f}MHz, Amp={self.cosine_amplitude_v:.2f}V, Noise={self.noise_amplitude_v:.2f}V")
        print(f"MockRF: Second Wave: Freq={self.cosine2_frequency_hz/1e6:.2f}MHz, Amp={self.cosine2_amplitude_v:.2f}V")
        print(f"MockRF: Display: Time/Div={self.time_per_div_s*1e6:.2f}µs, Total Duration={self.time_duration_s*1e6:.2f}µs, Points={self.num_time_points}, SR={self.sample_rate_hz/1e6:.1f}MSa/s")
        return True

    def get_simulated_data(self):
        """Generates two separate simulated traces for the time domain."""
        if not self.connected:
            print("MockRF: Error - Not connected for data acquisition.")
            return None

        current_num_points = self.num_time_points
        if current_num_points <= 0:
            print("MockRF: Error - Invalid number of points (<=0).")
            return None

        time_points_s = np.linspace(0, self.time_duration_s, current_num_points, endpoint=False)

        # --- Main Wave Generation ---
        amplitude_values_main = self.cosine_amplitude_v * np.cos(
            2 * np.pi * self.cosine_frequency_hz * time_points_s + self.cosine_phase_rad
        )
        amplitude_values_main += np.random.normal(0, self.noise_amplitude_v, current_num_points)

        # --- Secondary Wave Generation ---
        amplitude_values_secondary = self.cosine2_amplitude_v * np.cos(
            2 * np.pi * self.cosine2_frequency_hz * time_points_s + self.cosine2_phase_rad
        )

        # --- FFT Calculation (still based on MAIN wave for simplicity as per request) ---
        fft_raw_output = np.fft.rfft(amplitude_values_main)
        fft_magnitude = np.abs(fft_raw_output) / current_num_points
        epsilon = 1e-12
        power_spectrum_db = 20 * np.log10(fft_magnitude + epsilon)
        fft_power_dbm = power_spectrum_db - np.max(power_spectrum_db) + self.spectrum_ref_level_dbm

        fft_frequencies_hz = np.fft.rfftfreq(current_num_points, d=1.0/self.sample_rate_hz if self.sample_rate_hz > 0 else 1)
        fft_frequencies_hz = fft_frequencies_hz[:len(fft_power_dbm)].tolist()

        return {
            "time_s": time_points_s.tolist(),
            "amplitude_v_main": amplitude_values_main.tolist(),
            "amplitude_v_secondary": amplitude_values_secondary.tolist(),
            "wave_details": {
                "frequency_hz": self.cosine_frequency_hz,
                "amplitude_v": self.cosine_amplitude_v,
                "frequency_hz2": self.cosine2_frequency_hz,
                "amplitude_v2": self.cosine2_amplitude_v,
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