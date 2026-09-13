"""Compatibility routing for catalog-backed Season Setup UI.

The existing season_class_create URL remains the manual/special-case workflow.
Adding ?catalog=1 opens the official IEA catalog configuration workflow without
changing historical URLs or removing manual class creation.
"""

from .iea_catalog_admin import iea_catalog_configuration
from .roster import season_class_create as legacy_season_class_create


def season_class_create(request, *args, **kwargs):
    if request.GET.get("catalog") == "1" or request.POST.get("catalog_mode") == "1":
        return iea_catalog_configuration(request)
    return legacy_season_class_create(request, *args, **kwargs)
