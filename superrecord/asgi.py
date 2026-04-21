"""
ASGI config for CHE GOLOSO project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')

application = get_asgi_application()
