# backend/settings/local.py
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Add any dev-only packages here, like django-debug-toolbar later