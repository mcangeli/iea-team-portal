"""Compatibility view namespace.

v2.0.0 organizes implementations by domain under portal.view_modules while
preserving portal.views.<name> for URL configuration and external imports.
"""

from .view_modules.common import *
from .view_modules.roster_helpers import *
from .view_modules.dashboards import *
from .view_modules.roster import *
from .view_modules.season_setup_catalog_ui import season_class_create
from .view_modules.communications_helpers import *
from .view_modules.communications import *
from .view_modules.competitions_helpers import *
from .view_modules.competitions import *
from .view_modules.show_day_helpers import *
from .view_modules.show_day import *
from .view_modules.scoring import *
from .view_modules.show_planning_helpers import *
from .view_modules.show_planning import *
from .view_modules.lessons_helpers import *
from .view_modules.lessons import *
from .view_modules.history_helpers import *
from .view_modules.history import *
from .view_modules.administration_helpers import *
from .view_modules.administration import *
from .view_modules.finance_core_helpers import *
from .view_modules.finance_core import *
from .view_modules.family_finance_helpers import *
from .view_modules.family_finance import *
from .view_modules.fundraising_helpers import *
from .view_modules.fundraising import *
from .view_modules.finance_reports_helpers import *
from .view_modules.finance_reports import *
from .view_modules.show_finance_helpers import *
from .view_modules.show_finance import *

# v3.2.3 compatibility refinements intentionally override legacy roster
# implementations while preserving the public portal.views names.
from .view_modules.roster_v323 import (
    rider_list,
    rider_detail,
    rider_guardian_add,
    rider_guardian_edit,
    rider_guardian_link,
    rider_guardian_unlink,
)
