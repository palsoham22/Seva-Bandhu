import os
import django

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seva_bandhu.settings')

# 🔥 THIS WAS MISSING
django.setup()
from django.contrib.auth.models import User

if not User.objects.filter(username="admin").exists():

    User.objects.create_superuser(

        username="admin",
        email="admin@gmail.com",
        password="123456"
    )

    print("✅ SUPERUSER CREATED")

# HTTP app
django_asgi_app = get_asgi_application()

# Import AFTER setup
import core.routing

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            core.routing.websocket_urlpatterns
        )
    ),
})
