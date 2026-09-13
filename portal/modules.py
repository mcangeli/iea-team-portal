"""ArenaLine platform module registry and enablement helpers.

v2.9 keeps every existing module enabled by default.  This module establishes a
single application boundary for module metadata and future organization-level
enablement without changing the current Team tenancy model or database schema.
"""

from collections.abc import Iterable


ARENA_MODULES = {
    "core": {"label": "Core", "scope": "platform"},
    "people": {"label": "People & Families", "scope": "platform"},
    "horses": {"label": "Horses", "scope": "platform"},
    "competition_iea": {"label": "IEA Competition", "scope": "competition"},
    "operations": {"label": "Operations", "scope": "platform"},
    "finance": {"label": "Finance", "scope": "platform"},
    "communications": {"label": "Communications", "scope": "platform"},
}

DEFAULT_ENABLED_MODULES = tuple(ARENA_MODULES.keys())


def resolve_enabled_modules(module_ids: Iterable[str] | None = None) -> tuple[str, ...]:
    """Return valid enabled modules in registry order.

    Passing ``None`` preserves current ArenaLine behavior by enabling every
    registered module.  An explicit iterable is supported as the stable service
    boundary future organization configuration can call into; unknown IDs are
    ignored rather than leaking invalid module names into templates.

    ``core`` is always present because it owns the authenticated shell,
    organization context, and shared platform services.
    """

    if module_ids is None:
        return DEFAULT_ENABLED_MODULES

    requested = set(module_ids)
    requested.add("core")
    return tuple(module_id for module_id in ARENA_MODULES if module_id in requested)


def module_is_enabled(module_id: str, enabled_modules: Iterable[str] | None = None) -> bool:
    """Return whether a registered module is enabled for the supplied module set."""

    if module_id not in ARENA_MODULES:
        return False
    return module_id in resolve_enabled_modules(enabled_modules)
