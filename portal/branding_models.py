"""Compatibility exports for the relocated branding model.

New model-registration code lives under ``portal.model_modules``. Keep this
module as a stable import path while the rest of the application is migrated.
"""

from .model_modules.branding import TeamBranding

__all__ = ["TeamBranding"]
