# agent_hal_hardware.py
import numpy as np
import time
import pyvisa # New import for hardware communication

class RFHardwareInterface: # Renamed from RFHardwareSimulator
    def __init__(self, visa_resource_string): # Added visa_resource_string for compatibility
        # For simulation, visa_resource_string is not strictly used here, but for future hardware path
        self.rm = None # pyvisa.ResourceManager() if using hardware
        self.inst = None # For hardware
        self.visa_resource_string = visa_resource_string
        self.connected = False # Initial connection status for hardware interface

        # Default display/acquisition parameters (can be configured by frontend)
        self.time_per_div_s = 0.2e-6  # Default: 0.2 µs per division
        self.num_horizontal_divisions = 10 # Standard for oscilloscopes
        self.num_time_points = 500       # Number of points for acquisition (often fixed or queryable)
        self.time_duration_s = self.time_per_div_s * self.num_horizontal_divisions
        self.sample_rate_hz = self.num_time_points / self.time_duration_s if self.time_duration_s > 0 else 500e6

        # Parameters for configuring the physical wave (passed to scope)
        self.target_frequency_hz = 10e6
        self.target_amplitude_v = 1.0
        self.target_noise_v = 0.1 # Noise is usually from the environment/scope, not configured on scope

        # Spectrum parameters for display normalization
        self.spectrum_ref_level_dbm = 0 # Default reference level for FFT plot

        print(f"RF Hardware Interface initialized with resource: {self.visa_resource_string}")
        self.connect() # Attempt to connect on initialization

    def connect(self):
        """Connects to the physical oscilloscope via PyVISA."""
        try:
            self.rm = pyvisa.ResourceManager()
            self.inst = self.rm.open_resource(self.visa_resource_string)
            self.inst.timeout = 5000 # 5 seconds timeout for commands
            self.inst.write("*CLS") # Clear instrument status
            print(f"Hardware: Successfully connected to {self.visa_resource_string}")
            print(f"Hardware: IDN: {self.inst.query('*IDN?')}") # Query instrument identification
            self.connected = True
            return True
        except pyvisa.errors.VisaIOError as e:
            print(f"Hardware: ERROR connecting to {self.visa_resource_string}: {e}")
            self.connected = False
            return False
        except Exception as e:
            print(f"Hardware: Unexpected error during connect: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnects from the physical oscilloscope."""
        if self.inst:
            try:
                self.inst.close()
                print("Hardware: Disconnected from oscilloscope.")
            except Exception as e:
                print(f"Hardware: Error during disconnect: {e}")
        self.connected = False

    def configure_oscilloscope_settings(self, frequency_hz, amplitude_v, time_per_div_s, num_time_points, noise_v):
        """
        Sends SCPI commands to configure the physical oscilloscope.
        You will need to replace these with actual commands for your specific oscilloscope.
        """
        if not self.connected:
            print("Hardware: Not connected for configuration.")
            return False

        try:
            # Store target values (useful for later data interpretation or if scope doesn't give them back)
            self.target_frequency_hz = frequency_hz
            self.target_amplitude_v = amplitude_v
            self.target_noise_v = noise_v # Note: Noise is usually not configurable on scope

            # Update internal display/acquisition parameters for calculations
            self.time_per_div_s = time_per_div_s
            self.num_time_points = num_time_points
            self.time_duration_s = self.time_per_div_s * self.num_horizontal_divisions
            if self.time_duration_s > 0:
                self.sample_rate_hz = self.num_time_points / self.time_duration_s
            else:
                self.sample_rate_hz = 500e6 # Fallback

            print(f"Hardware: Configuring oscilloscope: Freq={self.target_frequency_hz/1e6:.2f}MHz, Amp={self.target_amplitude_v:.2f}V")
            print(f"Hardware: Display settings: Time/Div={self.time_per_div_s*1e6:.2f}µs, Total Duration={self.time_duration_s*1e6:.2f}µs, Points={self.num_time_points}, SR={self.sample_rate_hz/1e6:.1f}MSa/s")

            # --- INSERT YOUR OSCILLOSCOPE'S SCPI COMMANDS HERE ---
            # Consult your oscilloscope's programming manual for exact commands.
            # Examples (these are generic and might need adjustment):

            # 1. Set Horizontal (Time) Scale:
            self.inst.write(f"HORizontal:SCAle {self.time_per_div_s}") # Sets time per division

            # 2. Set Vertical (Voltage) Scale for Channel 1:
            # Assuming you want to display the target amplitude, you might set the scale to allow it.
            # Often, this is a fraction of the target amplitude (e.g., amplitude / 4 divisions)
            self.inst.write(f"CHANnel1:SCAle {self.target_amplitude_v / 4}") # Sets Volts per division for Channel 1

            # 3. Set Trigger (e.g., Edge Trigger on Channel 1, Rising Edge):
            self.inst.write("TRIGger:A:EDGE:SOUrce CHANnel1")
            self.inst.write("TRIGger:A:EDGE:SLOpe POSitive")
            self.inst.write("TRIGger:A:LEVel 0.0") # Set trigger level to 0V (adjust as needed)

            # 4. Set Acquisition Mode (e.g., Normal, High Res, Peak Detect):
            self.inst.write("ACQuire:MODE NORMal")

            # 5. Set Record Length (Number of Points) if controllable:
            # Not all oscilloscopes allow direct setting of points. They often derive it from timebase and sample rate.
            # If your scope supports it, use: self.inst.write(f"ACQuire:POINts {self.num_time_points}")
            # Or query the actual points after setting timebase: actual_points = int(self.inst.query("WAVeform:POINts?"))

            # 6. Set Sample Rate if controllable (often derived from timebase):
            # If your scope supports it, use: self.inst.write(f"ACQuire:SRATE {self.sample_rate_hz}")
            # ---------------------------------------------------

            return True
        except pyvisa.errors.VisaIOError as e:
            print(f"Hardware: Error configuring oscilloscope: {e}")
            return False
        except Exception as e:
            print(f"Hardware: Unexpected error during configuration: {e}")
            return False

    def get_real_time_data(self):
        """
        Acquires waveform data from the physical oscilloscope and processes it.
        You will need to replace the data acquisition and parsing with your scope's specifics.
        """
        if not self.connected:
            print("Hardware: Not connected for data acquisition.")
            return None

        try:
            # --- INSERT YOUR OSCILLOSCOPE'S DATA ACQUISITION COMMANDS HERE ---
            # Consult your oscilloscope's programming manual for exact commands and data formats.
            # This is often the most complex part (e.g., binary vs. ASCII data, preamble parsing).

            # Example common steps (adjust heavily for your scope):
            # 1. Stop acquisition (sometimes needed to read full trace)
            # self.inst.write("ACQuire:STATE STOP")

            # 2. Configure waveform source and format
            self.inst.write("DATA:SOUrce CHANnel1") # Select channel 1
            self.inst.write("DATA:ENC ASCii") # Or BINary, depends on your preference and scope capabilities
            self.inst.write("WAVeform:FORMat ASCii") # Or BYTE, WORD, etc.

            # 3. Query waveform preamble (gives scale, offset, points, time increment)
            # This information is CRUCIAL for correctly scaling the raw data.
            preamble_str = self.inst.query("WAVeform:PREamble?")
            # Example preamble parsing (adjust for your scope's format):
            # preamble_values = list(map(float, preamble_str.split(',')))
            # y_increment = preamble_values[7] # V/unit
            # y_offset = preamble_values[8]    # Vertical offset
            # x_increment = preamble_values[4] # s/point (time increment)
            # actual_num_points_acquired = int(preamble_values[2])

            # 4. Query raw waveform data
            raw_data_str = self.inst.query("WAVeform:DATA?") # For ASCII
            # For binary: raw_data_bytes = self.inst.query_binary_values("WAVeform:DATA?", datatype='B', is_single=False)

            # 5. Parse and scale the data
            # Example for ASCII (adjust based on your scope's WAV:DATA? format):
            # If it's a comma-separated list of values
            amplitude_values = np.array(list(map(float, raw_data_str.strip().split(',')))) # Adjust parsing
            # If your scope sends a header like '#9000000000' followed by data, you need to strip that.
            # amplitude_values = (amplitude_values * y_increment) + y_offset # Scale to actual voltage

            # 6. Re-enable acquisition if stopped
            # self.inst.write("ACQuire:STATE RUN")
            # ---------------------------------------------------------------

            # --- Placeholder for Actual Data Acquisition and Parsing ---
            # For demonstration, let's keep a very basic dummy data if actual scope data is not yet integrated
            # You MUST replace this with parsing your actual oscilloscope data.
            if not self.connected: # Fallback to dummy data if not connected (for testing)
                current_num_points = self.num_time_points # Use configured points
                time_points_s = np.linspace(0, self.time_duration_s, current_num_points, endpoint=False)
                amplitude_values = np.sin(2 * np.pi * self.target_frequency_hz * time_points_s) + np.random.normal(0, self.target_noise_v, current_num_points)
                # Ensure actual sample rate for FFT is consistent with the time points
                actual_sample_rate = self.sample_rate_hz # Use configured sample rate for dummy data
            else:
                # If connected, this section MUST parse real data from the scope
                # Replace with actual data from oscilloscope
                # For now, if no real data is parsed, return None to avoid errors.
                # If your parsing above is successful, populate these:
                actual_num_points_acquired = self.num_time_points # Or from preamble
                x_increment = 1.0 / self.sample_rate_hz # Or from preamble
                time_points_s = np.linspace(0, (actual_num_points_acquired - 1) * x_increment, actual_num_points_acquired).tolist()
                amplitude_values = amplitude_values.tolist() # Ensure it's a list

                # Query actual sample rate from scope if needed for FFT calculation
                actual_sample_rate = self.sample_rate_hz # Or self.inst.query("ACQuire:SRATe?")

            if not amplitude_values: # Check if parsing yielded any data
                print("Hardware: No waveform data parsed from oscilloscope.")
                return None

            # --- FFT Calculation (remains largely the same) ---
            # Ensure actual_sample_rate is correctly derived from scope data for FFT
            fft_raw_output = np.fft.rfft(np.array(amplitude_values))
            fft_magnitude = np.abs(fft_raw_output) / len(amplitude_values)
            epsilon = 1e-12
            power_spectrum_db = 20 * np.log10(fft_magnitude + epsilon)
            # You might need to calibrate spectrum_ref_level_dbm based on scope settings/units
            fft_power_dbm = power_spectrum_db - np.max(power_spectrum_db) + self.spectrum_ref_level_dbm

            fft_frequencies_hz = np.fft.rfftfreq(len(amplitude_values), d=1.0/actual_sample_rate if actual_sample_rate > 0 else 1)
            fft_frequencies_hz = fft_frequencies_hz[:len(fft_power_dbm)].tolist()

            print(f"Hardware: Acquired {len(amplitude_values)} points. SR={actual_sample_rate/1e6:.1f}MSa/s. Max FFT Freq={max(fft_frequencies_hz)/1e6:.2f}MHz")

            return {
                "time_s": time_points_s,
                "amplitude_v": amplitude_values, # This will be the main amplitude
                # No secondary amplitude from hardware by default, unless you acquire two channels
                "wave_details": {
                    "frequency_hz": self.target_frequency_hz, # Target frequency
                    "amplitude_v": self.target_amplitude_v,   # Target amplitude
                    "time_per_div_s": self.time_per_div_s,
                    "duration_s": self.time_duration_s,
                    "actual_sample_rate_hz": actual_sample_rate,
                    "num_points_time": len(amplitude_values),
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

        except pyvisa.errors.VisaIOError as e:
            print(f"Hardware: Error acquiring data from oscilloscope: {e}")
            self.connected = False # Mark as disconnected on error
            return None
        except Exception as e:
            print(f"Hardware: Generic error during data acquisition/FFT: {e}")
            return None