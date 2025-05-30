"""
ASGI config for finalProject project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
import os
from channels.auth import AuthMiddlewareStack # Optional: for user auth in consumers
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator # Security
from django.core.asgi import get_asgi_application

# Import routing from your app (we'll create this next)
import users.routing # Make sure this import path is correct

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finalProject.settings')

# Initialize Django ASGI application early to ensure AppRegistry is populated
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    "http": django_asgi_app,

    # WebSocket chat handler
    "websocket": AllowedHostsOriginValidator( # Basic security
        AuthMiddlewareStack( # Optional: access request.user in consumer
            URLRouter(
                users.routing.websocket_urlpatterns # Point to your app's routing
            )
        )
    ),
})