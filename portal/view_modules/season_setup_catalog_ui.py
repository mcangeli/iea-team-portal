"""Compatibility routing for catalog-backed Season Setup UI.

The existing season_class_create URL now serves the catalog-aware SeasonClass
editor, which supports both official IEA selection and deliberate manual/special
classes. Adding ?catalog=1 continues to open the whole-season rulebook/discipline
synchronization workflow without changing historical URLs.
"""

from .iea_catalog_admin import iea_catalog_configuration
from .roster import season_class_create as legacy_season_class_create


def season_class_create(request, *args, **kwargs):
    if request.GET.get("catalog") == "1" or request.POST.get("catalog_mode") == "1":
        return iea_catalog_configuration(request)
    return legacy_season_class_create(request, *args, **kwargs)
