# agent.py
import requests
import json
import threading
import time
from flask import Flask, request as flask_request, jsonify

from agent_hal_hardware import RFHardwareInterface # Changed import and class name

# --- Configuration ---
# Ensure this points to your Django server (your laptop's IP if agent is on Pi, or 127.0.0.1 if both are on laptop)
DJANGO_SIM_DATA_API_ENDPOINT = "http://127.0.0.1:8000/users/api/receive_rf_data/"
AGENT_CONTROL_API_PORT = 8001

# --- Global state for RF acquisition ---
sim_active = False # Renamed from sim_active as it's now hardware acquisition
acquisition_thread = None # Renamed from sim_thread

# Interval at which data is acquired and sent to Django
acquisition_interval_seconds = 0.1

# --- Global instance of the hardware interface ---
# IMPORTANT: Replace 'YOUR_OSCILLOSCOPE_VISA_DESCRIPTOR' with the actual string
# obtained from rm.list_resources() on your Raspberry Pi (e.g., 'USB0::XXXX::YYYY::SN::0::INSTR')
rf_hardware_interface = RFHardwareInterface('YOUR_OSCILLOSCOPE_VISA_DESCRIPTOR')

def send_to_django_backend(endpoint, data_payload):
    try:
        response = requests.post(endpoint, json=data_payload, timeout=10) # Increased timeout
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Agent: Error sending data to {endpoint}: {e}", end='\r')


def acquisition_loop(): # Renamed from simulation_loop
    """Periodically acquires data from hardware and sends it to Django if active."""
    global sim_active, acquisition_thread # Use sim_active to control loop exit
    print("Agent: Hardware Acquisition Loop Thread started.")
    while sim_active: # Loop controlled by sim_active
        # Call the method to get real data from the hardware interface
        real_data = rf_hardware_interface.get_real_time_data()
        if real_data:
            # Ensure the payload includes the main amplitude, and if secondary is needed, add it here too.
            # For a single channel scope, it's just 'amplitude_v'.
            # If you configure get_real_time_data to return amplitude_v_main and amplitude_v_secondary,
            # ensure your views.py also looks for those. For now, it returns 'amplitude_v' from scope.
            send_to_django_backend(DJANGO_SIM_DATA_API_ENDPOINT, real_data)
        else:
            print("Agent: No data acquired from hardware. Retrying...")
        time.sleep(acquisition_interval_seconds)
    print("Agent: Hardware Acquisition Loop Thread finished.")


# --- Flask App for Agent Control API ---
agent_api_app = Flask(__name__)


@agent_api_app.route('/start_simulation', methods=['POST'])
def handle_start_acquisition(): # Renamed from handle_start_simulation
    global sim_active, acquisition_thread
    if sim_active and acquisition_thread and acquisition_thread.is_alive():
        return jsonify({"status": "Hardware acquisition already active"}), 200

    # Attempt to connect to hardware before starting loop if not connected
    if not rf_hardware_interface.connected:
        print("Agent API: Attempting to connect to hardware...")
        if not rf_hardware_interface.connect():
            return jsonify({"status": "Error: Could not connect to oscilloscope."}), 500

    sim_active = True
    acquisition_thread = threading.Thread(target=acquisition_loop, daemon=True) # Changed target
    acquisition_thread.start()
    print("Agent API: Hardware acquisition started.")
    return jsonify({"status": "Hardware acquisition started"}), 200


@agent_api_app.route('/stop_simulation', methods=['POST']) # Renamed from handle_stop_simulation
def handle_stop_acquisition():
    global sim_active, acquisition_thread
    print("Agent API: Hardware acquisition stop command received.")
    sim_active = False
    if acquisition_thread and acquisition_thread.is_alive():
        acquisition_thread.join(timeout=acquisition_interval_seconds + 0.5)
    acquisition_thread = None
    print("Agent API: Hardware acquisition stopped.")
    return jsonify({"status": "Hardware acquisition stopped"}), 200


@agent_api_app.route('/configure_cosine', methods=['POST']) # This route will now configure the physical scope
def handle_configure_oscilloscope(): # Renamed from handle_configure_cosine
    data = flask_request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON payload"}), 400

    try:
        # Extract parameters from the received JSON payload
        freq_hz_input = float(data.get('frequency_hz', rf_hardware_interface.target_frequency_hz))
        amp_v_input = float(data.get('amplitude_v', rf_hardware_interface.target_amplitude_v))
        duration_s_input = float(data.get('duration_s', rf_hardware_interface.time_duration_s))
        sample_rate_hz_input = float(data.get('sample_rate_hz', rf_hardware_interface.sample_rate_hz))
        noise_v_input = float(data.get('noise_v', rf_hardware_interface.target_noise_v))

        # Frontend also sends freq_hz2 and amplitude_v2 for secondary wave,
        # but a typical single-channel scope will only configure/acquire one main signal.
        # If your scope supports multiple channels or signal generation for a second wave,
        # you'll need to adapt this part. For now, focus on primary signal.
        freq_hz2_input = float(data.get('frequency_hz2', 0)) # Default to 0 for second wave if not used by scope
        amp_v2_input = float(data.get('amplitude_v2', 0))     # Default to 0 for second wave if not used by scope


        # Calculate number of points based on desired total duration and sample rate
        calculated_num_time_points = int(duration_s_input * sample_rate_hz_input)
        if calculated_num_time_points <= 0:
            calculated_num_time_points = rf_hardware_interface.num_time_points

        # Calculate time_per_div_s that hardware interface expects for its configuration
        configured_time_per_div_s = duration_s_input / rf_hardware_interface.num_horizontal_divisions

        # Call the configure_oscilloscope_settings method on the hardware instance
        success = rf_hardware_interface.configure_oscilloscope_settings( # Changed method call
            frequency_hz=freq_hz_input,
            amplitude_v=amp_v_input,
            time_per_div_s=configured_time_per_div_s,
            num_time_points=calculated_num_time_points,
            noise_v=noise_v_input
            # Add parameters for secondary channel/signal if your scope supports generating/acquiring two independent signals.
            # Example: channel2_amplitude=amp_v2_input, channel2_frequency=freq_hz2_input
        )
        if success:
            return jsonify({"status": "Oscilloscope parameters configured"}), 200
        else:
            return jsonify({"error": "Failed to configure oscilloscope (connection or command error)"}), 500
    except ValueError:
        return jsonify({"error": "Invalid data type for parameters."}), 400
    except Exception as e:
        print(f"Agent API: Error in /configure_cosine: {e}")
        return jsonify({"error": "Internal server error"}), 500


def run_agent_control_api():
    print(f"Agent Control API server starting on http://127.0.0.1:{AGENT_CONTROL_API_PORT}")
    agent_api_app.run(host='0.0.0.0', port=AGENT_CONTROL_API_PORT, debug=False, use_reloader=False)


if __name__ == '__main__':
    print("Agent starting... Hardware acquisition is initially STOPPED.")
    api_thread = threading.Thread(target=run_agent_control_api, daemon=True)
    api_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nAgent: Ctrl+C detected, stopping agent services...")
        sim_active = False
        if acquisition_thread and acquisition_thread.is_alive():
            acquisition_thread.join(timeout=2)
        if rf_hardware_interface.connected: # Only try to disconnect if connected
            rf_hardware_interface.disconnect()
    print("Agent script finished.")