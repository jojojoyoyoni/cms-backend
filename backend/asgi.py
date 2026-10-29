import os
from django.core.asgi import get_asgi_application

# 1. Set the settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings.local')

# 2. Initialize Django apps (This MUST happen before importing model-related code)
django_asgi_app = get_asgi_application()

# 3. NOW we can safely import our WebSocket stuff
from channels.routing import ProtocolTypeRouter, URLRouter
from apps.notifications.middleware import JWTAuthMiddleware
from apps.notifications.routing import websocket_urlpatterns

# 4. Build the application
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})