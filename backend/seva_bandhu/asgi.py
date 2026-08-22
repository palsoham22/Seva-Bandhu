import os
import django

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seva_bandhu.settings')

# 🔥 THIS WAS MISSING
django.setup()
from django.contrib.auth.models import User

admin_username = os.environ.get('DJANGO_ADMIN_USERNAME')
admin_email = os.environ.get('DJANGO_ADMIN_EMAIL')
admin_password = os.environ.get('DJANGO_ADMIN_PASSWORD')
if admin_username and admin_email and admin_password and not User.objects.filter(username=admin_username).exists():
    User.objects.create_superuser(
        username=admin_username,
        email=admin_email,
        password=admin_password,
    )
    print("SUPERUSER CREATED")

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
