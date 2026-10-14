"""
Configurações da loja de brownies.
Lê segredos do .env (nunca versionado).
"""

from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-apenas-local')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'loja',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'loja.contexto.carrinho',          # contador do carrinho em toda página
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Cuiaba'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==========================================
# Pagamento — Mercado Pago
# ==========================================
MP_ACCESS_TOKEN     = config('MP_ACCESS_TOKEN', default='')
MP_PUBLIC_KEY       = config('MP_PUBLIC_KEY', default='')
MP_WEBHOOK_SECRET   = config('MP_WEBHOOK_SECRET', default='')

# URL pública do site (o Mercado Pago precisa dela para o webhook e retorno)
SITE_URL = config('SITE_URL', default='http://localhost:8000')

# ==========================================
# Dados da loja (aparecem no site)
# ==========================================
LOJA_NOME       = config('LOJA_NOME', default='Brownie da Casa')
LOJA_WHATSAPP   = config('LOJA_WHATSAPP', default='')
LOJA_EMAIL      = config('LOJA_EMAIL', default='')

# Frete: valor fixo por enquanto (trocar por cálculo real depois)
FRETE_VALOR     = config('FRETE_VALOR', default='10.00')
FRETE_GRATIS_ACIMA = config('FRETE_GRATIS_ACIMA', default='80.00')
