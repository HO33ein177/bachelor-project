# agent.py
import requests
import json
import threading
import time
from flask import Flask, request as flask_request, jsonify

from agent_hal import RFHardwareSimulator  # Assuming agent_hal.py is in the same directory

# --- Configuration ---
DJANGO_SIM_DATA_API_ENDPOINT = "http://127.0.0.1:8000/users/api/receive_rf_data/"  # We can reuse this endpoint
AGENT_CONTROL_API_PORT = 8001

# --- Global state for RF simulation ---
sim_active = False
sim_thread = None
sim_interval_seconds = 0.1  # How often to generate and send a new trace (faster for waveform)


def send_to_django_backend(endpoint, data_payload):
    try:
        response = requests.post(endpoint, json=data_payload, timeout=3)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Agent: Error sending data to {endpoint}: {e}", end='\r')


def simulation_loop():
    """Periodically gets a simulated trace and sends it to Django if active."""
    global sim_active
    print("Agent: Simulation Loop Thread started.")
    while sim_active:
        # Calls the renamed method in the simulator
        sim_data = RFHardwareSimulator.get_simulated_data() # UPDATED
        if sim_data:
            send_to_django_backend(DJANGO_SIM_DATA_API_ENDPOINT, sim_data)
        time.sleep(sim_interval_seconds)  # Keep this delay reasonable
        print("Agent: Simulation Loop Thread finished.")


# --- Flask App for Agent Control API ---
agent_api_app = Flask(__name__)


@agent_api_app.route('/start_simulation', methods=['POST'])
def handle_start_simulation():
    global sim_active, sim_thread
    if sim_active and sim_thread and sim_thread.is_alive():
        return jsonify({"status": "Simulation already active"}), 200

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
        # Convert to float, provide defaults if keys are missing
        freq_hz = float(data.get('frequency_hz', RFHardwareSimulator.cosine_frequency_hz))
        amp_v = float(data.get('amplitude_v', RFHardwareSimulator.cosine_amplitude_v))
        duration_s = float(data.get('duration_s', RFHardwareSimulator.time_duration_s))
        sample_rate_hz = float(data.get('sample_rate_hz', RFHardwareSimulator.sample_rate_hz))
        noise_v = float(data.get('noise_v', RFHardwareSimulator.noise_amplitude_v))

        success = RFHardwareSimulator.configure_cosine_wave(
            frequency_hz=freq_hz,
            amplitude_v=amp_v,
            duration_s=duration_s,
            sample_rate_hz=sample_rate_hz,
            noise_v=noise_v
        )
        if success:
            return jsonify({"status": "Cosine wave parameters configured"}), 200
        else:
            return jsonify({"error": "Failed to configure cosine wave (device not connected?)"}), 500
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
    print("Agent script finished.")


@agent_api_app.route('/configure_cosine', methods=['POST'])
def handle_configure_cosine():
    data = flask_request.get_json()
    if not data: # ... (error check) ...
        return jsonify({"error": "Missing JSON payload"}), 400

    try:
        freq_hz = float(data.get('frequency_hz', RFHardwareSimulator.cosine_frequency_hz))
        amp_v = float(data.get('amplitude_v', RFHardwareSimulator.cosine_amplitude_v))
        # New parameters for oscilloscope-like control
        time_per_div_s = float(data.get('time_per_div_s', RFHardwareSimulator.time_per_div_s))
        num_time_points = int(data.get('num_time_points', RFHardwareSimulator.num_time_points))
        noise_v = float(data.get('noise_v', RFHardwareSimulator.noise_amplitude_v))

        success = RFHardwareSimulator.configure_cosine_wave(
            frequency_hz=freq_hz,
            amplitude_v=amp_v,
            time_per_div_s=time_per_div_s, # Pass new param
            num_time_points=num_time_points, # Pass new param
            noise_v=noise_v
        )
        # ... (rest of success/error handling) ...
        if success:
            return jsonify({"status": "Cosine wave & display parameters configured"}), 200
        else:
            return jsonify({"error": "Failed to configure (device not connected?)"}), 500
    except ValueError:
        return jsonify({"error": "Invalid data type for parameters."}), 400
    except Exception as e:
        print(f"Agent API: Error in /configure_cosine: {e}")
        return jsonify({"error": "Internal server error"}), 500