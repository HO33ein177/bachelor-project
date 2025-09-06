# users/routing.py
from django.urls import re_path
from . import consumers # We'll create this next

websocket_urlpatterns = [
    # Define a URL pattern for WebSocket connections
    # Example: ws://yourdomain/ws/network_data/
    re_path(r'ws/network_data/$', consumers.NetworkDataConsumer.as_asgi()),
# --- For RF Spectrum Data --- ADD THIS ---
    re_path(r'^ws/rf_spectrum/$', consumers.RFSpectrumConsumer.as_asgi(), name='ws_rf_spectrum'),
]