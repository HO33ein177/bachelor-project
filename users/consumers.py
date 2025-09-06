# users/consumers.py
import json

import requests
from channels.generic.websocket import AsyncWebsocketConsumer

# Define a group name clients will join
NETWORK_DATA_GROUP_NAME = 'network_data_group'
AGENT_API_URL = "http://127.0.0.1:8001" # Agent's own API (different port from Django)
# AGENT_API_URL = "http://192.168.227.137:8001" # Agent's own API (different port from Django)

RF_SPECTRUM_GROUP_NAME = 'rf_spectrum_group'
# AGENT_CONTROL_API_URL = "http://127.0.0.1:8001" # Agent's own API
AGENT_CONTROL_API_URL = "http://192.168.137.114:8001" # Agent's own API



class NetworkDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Print the client's scope information for more details
        client_info = self.scope.get('client', 'N/A')
        print(f"Consumer: WebSocket CONNECTING from {client_info}, channel: {self.channel_name}")
        try:
            await self.channel_layer.group_add(
                NETWORK_DATA_GROUP_NAME,
                self.channel_name
            )
            print(f"Consumer: Successfully ADDED to group '{NETWORK_DATA_GROUP_NAME}', channel: {self.channel_name}")

            await self.accept() # Try to accept the connection
            print(f"Consumer: WebSocket ACCEPTED from {client_info}, channel: {self.channel_name}")

        except Exception as e:
            print(f"Consumer: ERROR in connect method for channel {self.channel_name}: {e}")
            await self.close() # Close the connection if an error occurs


    async def disconnect(self, close_code):
        client_info = self.scope.get('client', 'N/A')
        print(f"Consumer: WebSocket DISCONNECTED from {client_info}, code: {close_code}, channel: {self.channel_name}")
        try:
            await self.channel_layer.group_discard(
                NETWORK_DATA_GROUP_NAME,
                self.channel_name
            )
            print(f"Consumer: Successfully REMOVED from group '{NETWORK_DATA_GROUP_NAME}', channel: {self.channel_name}")
        except Exception as e:
            print(f"Consumer: ERROR in disconnect method for channel {self.channel_name}: {e}")

    async def receive(self, text_data):
        """
        Called when a message is received from the WebSocket client (browser).
        """
        client_info = self.scope.get('client', 'N/A')
        print(f"Consumer: Received command from {client_info}: {text_data}")
        try:
            data = json.loads(text_data)
            command = data.get('command')
            status_message = "Unknown command received."

            if command == 'start_capture':
                print("Consumer: Relaying START command to agent...")
                try:
                    requests.post(f"{AGENT_API_URL}/start", timeout=3)
                    status_message = "Capture started by agent."
                except requests.exceptions.RequestException as e:
                    print(f"Consumer: Error sending START to agent: {e}")
                    status_message = "Error starting agent."
            elif command == 'stop_capture':
                print("Consumer: Relaying STOP command to agent...")
                try:
                    requests.post(f"{AGENT_API_URL}/stop", timeout=3)
                    status_message = "Capture stopped by agent."
                except requests.exceptions.RequestException as e:
                    print(f"Consumer: Error sending STOP to agent: {e}")
                    status_message = "Error stopping agent."

            # Send a status update back to the client
            await self.send(text_data=json.dumps({
                'type': 'status_update',
                'message': status_message
            }))

        except json.JSONDecodeError:
            print("Consumer: Received invalid JSON command from client.")
        except Exception as e:
            print(f"Consumer: Error in receive method: {e}")

    async def network_data_message(self, event):
        """
        Handles messages sent over the channel layer to the group.
        This method name ('network_data_message') corresponds to the 'type'
        in the channel_layer.group_send call from the HTTP view.
        """
        message_data = event['message']
        print(f"Sending message to WebSocket {self.channel_name}: {message_data}")

        # Send message data to the WebSocket client (browser)
        await self.send(text_data=json.dumps({
            'type': 'network_data',
            'payload': message_data
        }))
        message_data = event['message']
        # print(f"Consumer: Sending data to WebSocket {self.channel_name}: {message_data}") # Optional: can be very verbose
        try:
            await self.send(text_data=json.dumps({
                'type': 'network_data',
                'payload': message_data
            }))
        except Exception as e:
            print(f"Consumer: Error sending data to WebSocket {self.channel_name}: {e}")


# users/consumers.py
# ... (imports remain mostly the same) ...
class RFSpectrumConsumer(AsyncWebsocketConsumer):
    # ... (connect, disconnect methods are the same) ...
    async def connect(self):
        client_info = self.scope.get('client', 'N/A')
        print(f"RFSpectrumConsumer: WebSocket CONNECTING from {client_info}, channel: {self.channel_name}")
        try:
            await self.channel_layer.group_add(
                RF_SPECTRUM_GROUP_NAME,  # Make sure this group name is correct
                self.channel_name
            )
            print(
                f"RFSpectrumConsumer: Successfully ADDED to group '{RF_SPECTRUM_GROUP_NAME}', channel: {self.channel_name}")
            await self.accept()
            print(f"RFSpectrumConsumer: WebSocket ACCEPTED from {client_info}, channel: {self.channel_name}")
            await self.send(text_data=json.dumps(
                {'type': 'status_update', 'message': 'Connected to RF Time Domain Server.'}))  # Updated message
        except Exception as e:
            print(f"RFSpectrumConsumer: ERROR in connect method for channel {self.channel_name}: {e}")
            await self.close()

    async def disconnect(self, close_code):
        client_info = self.scope.get('client', 'N/A')
        print(
            f"RFSpectrumConsumer: WebSocket DISCONNECTED from {client_info}, code: {close_code}, channel: {self.channel_name}")
        try:
            await self.channel_layer.group_discard(
                RF_SPECTRUM_GROUP_NAME,
                self.channel_name
            )
            print(
                f"RFSpectrumConsumer: Successfully REMOVED from group '{RF_SPECTRUM_GROUP_NAME}', channel: {self.channel_name}")
        except Exception as e:
            print(f"RFSpectrumConsumer: ERROR in disconnect method for channel {self.channel_name}: {e}")

    async def receive(self, text_data):
        client_info = self.scope.get('client', 'N/A')
        print(f"RFSpectrumConsumer: Received command from {client_info}: {text_data}")
        status_message = "Command processed."
        command_processed_successfully = True
        try:
            data = json.loads(text_data)
            command_type = data.get('command_type')
            command = data.get('command')
            params = data.get('params', {})

            if command_type == 'rf_control':  # Keep this for start/stop
                endpoint = None
                payload = None  # For POST body
                if command == 'start_simulation':  # Renamed from start_rf_scan
                    endpoint = f"{AGENT_CONTROL_API_URL}/start_simulation"
                    status_message = "Simulation started by agent."
                elif command == 'stop_simulation':  # Renamed from stop_rf_scan
                    endpoint = f"{AGENT_CONTROL_API_URL}/stop_simulation"
                    status_message = "Simulation stopped by agent."
                # Remove configure_rf_scan and set_sim_signals as they were spectrum specific
                # Add new command for cosine configuration
                elif command == 'configure_cosine':
                    endpoint = f"{AGENT_CONTROL_API_URL}/configure_cosine"
                    # params should now include time_per_div_s and num_time_points
                    # e.g., params = {'frequency_hz': ..., 'amplitude_v': ..., 'time_per_div_s': ..., 'num_time_points': ...}
                    payload = params
                    status_message = "Cosine wave & display parameters sent to agent."
                else:
                    status_message = f"Unknown RF command: {command}"
                    command_processed_successfully = False

                if endpoint:
                    try:
                        response = requests.post(endpoint, json=payload, timeout=5)
                        response.raise_for_status()
                        agent_response = response.json()
                        print(
                            f"RFSpectrumConsumer: Command '{command}' sent to agent. Agent response: {agent_response}")
                        # If agent indicates an error in its own response, reflect that
                        if agent_response.get('error'):
                            status_message = f"Agent error: {agent_response.get('error')}"
                            command_processed_successfully = False
                        elif agent_response.get('status'):
                            status_message = f"Agent: {agent_response.get('status')}"


                    except requests.exceptions.RequestException as e:
                        print(f"RFSpectrumConsumer: Error sending '{command}' to agent: {e}")
                        status_message = f"Error relaying '{command}' to agent."
                        command_processed_successfully = False
            else:
                status_message = f"Unknown command type: {command_type}"
                command_processed_successfully = False

        # ... (rest of the error handling and response sending is the same) ...
        except json.JSONDecodeError:
            print("RFSpectrumConsumer: Received invalid JSON command from client.")
            status_message = "Invalid command format."
            command_processed_successfully = False
        except Exception as e:
            print(f"RFSpectrumConsumer: Error in receive method: {e}")
            status_message = "Error processing command."
            command_processed_successfully = False

        await self.send(text_data=json.dumps({
            'type': 'command_response' if command_processed_successfully else 'error_response',
            'message': status_message
        }))

    async def rf_spectrum_update(self, event):  # This method name is tied to the 'type' in group_send
        rf_data = event['message']
        print(f"RFSpectrumConsumer: Sending RF (Time Domain) data to WebSocket {self.channel_name}: {rf_data}")
        try:
            await self.send(text_data=json.dumps({
                'type': 'rf_simulated_data', # More generic type now
                'payload': rf_data
            }))
        except Exception as e:
            print(f"RFSpectrumConsumer: Error sending RF Time Domain data to WebSocket {self.channel_name}: {e}")