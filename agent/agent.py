# agent.py
import requests
import json
import threading
import time
from flask import Flask, request as flask_request, jsonify

from agent_hal import RFHardwareSimulator # Or agent_hal_hardware if you're using that version

# --- Configuration ---
# Ensure this points to your Django server (your laptop's IP if agent is on Pi, or 127.0.0.1 if both are on laptop)
DJANGO_SIM_DATA_API_ENDPOINT = "http://127.0.0.1:8000/users/api/receive_rf_data/"
AGENT_CONTROL_API_PORT = 8001

# --- Global state for RF simulation ---
sim_active = False
sim_thread = None
sim_interval_seconds = 0.1

# --- Global instance of the hardware simulator ---
# If using the hardware version, remember to put your VISA descriptor here
rf_simulator_instance = RFHardwareSimulator()

def send_to_django_backend(endpoint, data_payload):
    try:
        response = requests.post(endpoint, json=data_payload, timeout=10) # Increased timeout
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Agent: Error sending data to {endpoint}: {e}", end='\r')


def simulation_loop():
    """Periodically gets a simulated trace and sends it to Django if active."""
    global sim_active
    print("Agent: Simulation Loop Thread started.")
    while sim_active:
        sim_data = rf_simulator_instance.get_simulated_data()
        if sim_data:
            send_to_django_backend(DJANGO_SIM_DATA_API_ENDPOINT, sim_data)
        time.sleep(sim_interval_seconds)
    print("Agent: Simulation Loop Thread finished.")


# --- Flask App for Agent Control API ---
agent_api_app = Flask(__name__)


@agent_api_app.route('/start_simulation', methods=['POST'])
def handle_start_simulation():
    global sim_active, sim_thread
    if sim_active and sim_thread and sim_thread.is_alive():
        return jsonify({"status": "Simulation already active"}), 200

    # Ensure simulator is connected if it has a connect method (for hardware HAL)
    if hasattr(rf_simulator_instance, 'connected') and not rf_simulator_instance.connected:
        print("Agent API: Attempting to connect simulator...")
        if not rf_simulator_instance.connect():
            return jsonify({"status": "Error: Could not connect to simulator/hardware."}), 500

    sim_active = True
    sim_thread = threading.Thread(target=simulation_loop, daemon=True)
    sim_thread.start()
    print("Agent API: Simulation started.")
    return jsonify({"status": "Simulation started"}), 200


@agent_api_app.route('/stop_simulation', methods=['POST'])
def handle_stop_simulation():
    global sim_active, sim_thread
    print("Agent API: Simulation stop command received.")
    sim_active = False
    if sim_thread and sim_thread.is_alive():
        sim_thread.join(timeout=sim_interval_seconds + 0.5)
    sim_thread = None
    print("Agent API: Simulation stopped.")
    return jsonify({"status": "Simulation stopped"}), 200


@agent_api_app.route('/configure_cosine', methods=['POST'])
def handle_configure_cosine():
    data = flask_request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON payload"}), 400

    try:
        # Extract parameters for MAIN wave
        freq_hz_input = float(data.get('frequency_hz', rf_simulator_instance.cosine_frequency_hz))
        amp_v_input = float(data.get('amplitude_v', rf_simulator_instance.cosine_amplitude_v))

        # Extract parameters for SECONDARY wave
        freq_hz2_input = float(data.get('frequency_hz2', rf_simulator_instance.cosine2_frequency_hz)) # New param
        amp_v2_input = float(data.get('amplitude_v2', rf_simulator_instance.cosine2_amplitude_v))     # New param

        # Extract other common parameters
        duration_s_input = float(data.get('duration_s', rf_simulator_instance.time_duration_s))
        sample_rate_hz_input = float(data.get('sample_rate_hz', rf_simulator_instance.sample_rate_hz))
        noise_v_input = float(data.get('noise_v', rf_simulator_instance.noise_amplitude_v))

        # Calculate number of points based on desired total duration and sample rate
        calculated_num_time_points = int(duration_s_input * sample_rate_hz_input)
        if calculated_num_time_points <= 0:
            calculated_num_time_points = rf_simulator_instance.num_time_points

        # Calculate time_per_div_s for HAL configuration
        configured_time_per_div_s = duration_s_input / rf_simulator_instance.num_horizontal_divisions

        # Call configure_cosine_wave on the simulator instance with new parameters
        success = rf_simulator_instance.configure_cosine_wave(
            frequency_hz=freq_hz_input,
            amplitude_v=amp_v_input,
            frequency_hz2=freq_hz2_input, # Pass new param
            amplitude_v2=amp_v2_input,   # Pass new param
            time_per_div_s=configured_time_per_div_s,
            num_time_points=calculated_num_time_points,
            noise_v=noise_v_input
        )
        if success:
            return jsonify({"status": "Cosine wave & display parameters configured"}), 200
        else:
            return jsonify({"error": "Failed to configure cosine wave (simulator error)"}), 500
    except ValueError:
        return jsonify({"error": "Invalid data type for parameters."}), 400
    except Exception as e:
        print(f"Agent API: Error in /configure_cosine: {e}")
        return jsonify({"error": "Internal server error"}), 500


def run_agent_control_api():
    print(f"Agent Control API server starting on http://127.0.0.1:{AGENT_CONTROL_API_PORT}")
    agent_api_app.run(host='0.0.0.0', port=AGENT_CONTROL_API_PORT, debug=False, use_reloader=False)


if __name__ == '__main__':
    print("Agent starting... Simulation is initially STOPPED.")
    api_thread = threading.Thread(target=run_agent_control_api, daemon=True)
    api_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nAgent: Ctrl+C detected, stopping agent services...")
        sim_active = False
        if sim_thread and sim_thread.is_alive():
            sim_thread.join(timeout=2)
        if hasattr(rf_simulator_instance, 'disconnect'): # Call disconnect if method exists
            rf_simulator_instance.disconnect()
    print("Agent script finished.")