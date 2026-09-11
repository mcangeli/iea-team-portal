from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_VERSION = (BASE_DIR / "VERSION").read_text(encoding="utf-8").strip() if (BASE_DIR / "VERSION").exists() else "dev"
PORTAL_REPOSITORY_URL = os.getenv("PORTAL_REPOSITORY_URL", "https://github.com/mcangeli/iea-team-portal").rstrip("/")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
ALLOWED_HOSTS = [x.strip() for x in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if x.strip()]

if not DEBUG:
    production_errors = []
    if not SECRET_KEY or SECRET_KEY == "unsafe-dev-key-change-me" or len(SECRET_KEY) < 32:
        production_errors.append("DJANGO_SECRET_KEY must be set to a strong value of at least 32 characters.")
    if not POSTGRES_PASSWORD or POSTGRES_PASSWORD == "change-me":
        production_errors.append("POSTGRES_PASSWORD must be set and may not use the default placeholder.")
    if not ALLOWED_HOSTS:
        production_errors.append("DJANGO_ALLOWED_HOSTS must contain at least one hostname.")
    if production_errors:
        raise ImproperlyConfigured(
            "Unsafe or incomplete production configuration:\n- " + "\n- ".join(production_errors)
        )
else:
    SECRET_KEY = SECRET_KEY or "unsafe-dev-key-change-me"
    POSTGRES_PASSWORD = POSTGRES_PASSWORD or "change-me"
    ALLOWED_HOSTS = ALLOWED_HOSTS or ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "portal",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "portal.middleware.ForcePasswordChangeMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages", "portal.context_processors.portal_context",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.getenv("POSTGRES_DB", "iea_team"), "USER": os.getenv("POSTGRES_USER", "iea_team"),
    "PASSWORD": POSTGRES_PASSWORD, "HOST": os.getenv("POSTGRES_HOST", "db"),
    "PORT": os.getenv("POSTGRES_PORT", "5432"),
}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-us"; TIME_ZONE = os.getenv("TIME_ZONE", "America/New_York"); USE_I18N = True; USE_TZ = True
STATIC_URL = "/static/"; STATIC_ROOT = BASE_DIR / "staticfiles"; STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"; MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = "/"; LOGOUT_REDIRECT_URL = "/accounts/login/"
SESSION_COOKIE_SECURE = os.getenv("SECURE_COOKIES", "1") == "1"
CSRF_COOKIE_SECURE = os.getenv("SECURE_COOKIES", "1") == "1"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

DEFAULT_TEMP_PASSWORD = os.getenv("DEFAULT_TEMP_PASSWORD", "")

# Optional SMTP delivery. If EMAIL_HOST is blank, communications remain in-app only.
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "0") == "1"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "team-portal@localhost")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST else "django.core.mail.backends.console.EmailBackend"
