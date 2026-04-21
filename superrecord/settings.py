"""
Django settings for CHE GOLOSO Supermarket Management System.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',') if h.strip()]

# Railway automatic domain support
if os.getenv('RAILWAY_PUBLIC_DOMAIN'):
    ALLOWED_HOSTS.append(os.getenv('RAILWAY_PUBLIC_DOMAIN'))

# Railway private networking
if os.getenv('RAILWAY_PRIVATE_DOMAIN'):
    ALLOWED_HOSTS.append(os.getenv('RAILWAY_PRIVATE_DOMAIN'))

# Railway: permitir todas las conexiones internas (proxy seguro de Railway)
if os.getenv('RAILWAY_ENVIRONMENT'):
    ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Third party apps
    'rest_framework',
    'corsheaders',
    'crispy_forms',
    'crispy_bootstrap5',
    'widget_tweaks',
    'django_extensions',
    
    # Local apps
    'accounts.apps.AccountsConfig',
    'cashregister.apps.CashregisterConfig',
    'pos.apps.PosConfig',
    'stocks.apps.StocksConfig',
    'promotions.apps.PromotionsConfig',
    'purchase.apps.PurchaseConfig',
    'expenses.apps.ExpensesConfig',
    'sales.apps.SalesConfig',
    'company.apps.CompanyConfig',
    'mercadopago.apps.MercadopagoConfig',
    'assistant.apps.AssistantConfig',
    'signage.apps.SignageConfig',
    'granel.apps.GranelConfig',
    'landing.apps.LandingConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.AjaxLoginRedirectMiddleware',
    'superrecord.middleware.NoCacheHTMLMiddleware',
]

ROOT_URLCONF = 'superrecord.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.role_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'superrecord.wsgi.application'

# Messages - map Django message tags to Bootstrap CSS classes
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL and DATABASE_URL.startswith(('postgres', 'mysql', 'sqlite')):
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Thousand separator and decimal separator for Argentina
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = '.'
DECIMAL_SEPARATOR = ','
NUMBER_GROUPING = 3

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# WhiteNoise for static files — usa hash en el nombre (pos-dark.a3f5b2.css)
# para que cada deploy invalide automaticamente la cache del navegador sin
# requerir Ctrl+Shift+R. manifest_strict=False evita crashes por referencias
# a archivos inexistentes.
# En dev (DEBUG=True) usamos el storage simple porque el runserver sirve
# static por finders y no resuelve los nombres hasheados que genera el
# manifest. En produccion usamos el storage con manifest.
if DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    STATICFILES_STORAGE = 'superrecord.storage.ForgivingManifestStaticFilesStorage'

# Cache larga para estaticos: como tienen hash en el nombre, son inmutables.
# Cuando el archivo cambia, cambia el hash, cambia la URL, y el navegador
# fetchea la nueva version automaticamente.
WHITENOISE_MAX_AGE = 31536000  # 1 año
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = []

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/Logout URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:dashboard'
LOGOUT_REDIRECT_URL = 'landing:home'

# Session settings
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CSRF settings
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Security settings for production
if not DEBUG:
    # Railway usa un reverse proxy - necesario para detectar HTTPS correctamente
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    # NO usar SECURE_SSL_REDIRECT con Railway (el proxy ya maneja HTTPS)
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
if os.getenv('RAILWAY_PUBLIC_DOMAIN'):
    CORS_ALLOWED_ORIGINS.append(f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN')}")
CORS_ALLOW_CREDENTIALS = True

# CSRF Trusted Origins for Railway
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
# Railway domains - wildcard covers all *.up.railway.app subdomains
if os.getenv('RAILWAY_ENVIRONMENT'):
    CSRF_TRUSTED_ORIGINS += [
        "https://*.up.railway.app",
        "https://*.railway.app",
    ]
if os.getenv('RAILWAY_PUBLIC_DOMAIN'):
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN')}")
if os.getenv('ALLOWED_HOSTS'):
    for host in os.getenv('ALLOWED_HOSTS').split(','):
        if host and host not in ['localhost', '127.0.0.1', 'testserver']:
            CSRF_TRUSTED_ORIGINS.append(f"https://{host}")

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}
