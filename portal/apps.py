from django.apps import AppConfig


class PortalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portal"

    def import_models(self):
        super().import_models()
        from . import lifecycle_models  # noqa: F401
        from .model_modules import branding  # noqa: F401
        from . import horse_models  # noqa: F401
        from . import hoofprint_models  # noqa: F401
        from . import show_readiness_models  # noqa: F401
        from . import course_models  # noqa: F401
        from . import post_show_horse_models  # noqa: F401
        from . import host_show_models  # noqa: F401

    def ready(self):
        import portal.signals  # noqa: F401
