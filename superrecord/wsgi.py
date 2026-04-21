"""
WSGI config for CHE GOLOSO project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')

application = get_wsgi_application()
