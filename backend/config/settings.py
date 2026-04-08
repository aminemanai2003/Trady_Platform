"""Django settings for FX Alpha Platform backend."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "corsheaders",
    # Auth token support
    "rest_framework.authtoken",
    # Local apps
    "data",
    "signals",
    "agents",
    "analytics",
    "scheduling",
    "ocr",
    "notifications",
    "face_auth",
    "rag_tutor",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database — connects to existing PostgreSQL from Data Acquisition
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "forex_metadata"),
        "USER": os.getenv("POSTGRES_USER", "dataminds"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "dataminds_secure_password"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

# Direct database settings for core.database module
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "forex_metadata")
POSTGRES_USER = os.getenv("POSTGRES_USER", "dataminds")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "dataminds_secure_password")

# InfluxDB settings (existing from Data Acquisition)
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "my-super-secret-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "forex_org")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "forex_data")

# Direct InfluxDB settings for core.database module
INFLUX_URL = INFLUXDB_URL
INFLUX_TOKEN = INFLUXDB_TOKEN
INFLUX_ORG = INFLUXDB_ORG
INFLUX_BUCKET = INFLUXDB_BUCKET

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "300/minute",
        "login": "5/minute",        # brute-force guard on login endpoint
        "otp_request": "5/10m",     # max OTP sends per 10 min per user
        "otp_verify": "10/10m",     # max verify attempts per 10 min per IP
        "face_enroll": "5/hour",    # enrollment attempts per hour per user
        "face_verify": "10/10m",    # face verification attempts per 10 min per IP
        "twofa_verify_setup": "5/10m",  # 2FA setup verification attempts per 10 min per user
    },
}

# CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True   # allow cookies to be forwarded by the Next.js proxy

# LLM / Agent settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Session security ──────────────────────────────────────────────────────────
SESSION_COOKIE_HTTPONLY = True   # JS cannot read the session cookie
SESSION_COOKIE_SAMESITE = "Lax" # CSRF mitigation for cross-site requests
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS-only in production
# 2FA pending session expires in 10 minutes if the user never completes OTP
SESSION_COOKIE_AGE = 600

# ── Email (Gmail SMTP) ────────────────────────────────────────────────────────
# All values come from environment variables — never hardcoded.
GMAIL_USER = os.getenv("GMAIL_USER", "")
# Note: use a Google App Password, not your account password.
# https://myaccount.google.com/apppasswords
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# ── Twilio (SMS) ──────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID",   "")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN",    "")
TWILIO_PHONE_NUMBER  = os.getenv("TWILIO_PHONE_NUMBER",  "")

# ── Face authentication ─────────────────────────────────────────────────────────────
# 32-byte URL-safe base64 Fernet key.  Generate with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FACE_EMBEDDING_KEY = os.getenv("FACE_EMBEDDING_KEY", "")
# Cosine distance threshold — lower = stricter (default 0.40)
FACE_SIMILARITY_THRESHOLD = float(os.getenv("FACE_SIMILARITY_THRESHOLD", "0.40"))
