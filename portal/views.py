"""Compatibility view namespace.

v2.0.0 organizes implementations by domain under portal.view_modules while
preserving portal.views.<name> for URL configuration and external imports.
"""

from .view_modules.common import *
from .view_modules.common import (
    FINANCE_AUDIT_ENTITY_TYPES, HISTORICAL_IMPORT_HEADERS, TEAM_LEVELS,
    _active_committee_roles, _active_season, _announcement_recipients,
    _assistance_report_rows, _audit_event, _audit_value, _can_coordinate_team,
    _can_edit_show_schedule_class, _can_finance, _can_manage, _can_manage_points,
    _can_plan_show, _can_view_family_account, _can_view_private_rider,
    _ensure_season_open, _family_account_totals, _finance_season_ids, _is_admin,
    _is_non_team_scoring_class, _is_rider_account, _is_show_lead, _personal_riders,
    _planning_item_visible_to_user, _qualification_rows, _receivable_report_rows,
    _require_finance, _require_manage, _rider_class_point_rows, _selected_team,
    _show_planning_allowed_levels, _show_schedule_edit_levels, _team,
    _team_scoring_rows, _visible_action_items, _visible_riders,
    _volunteer_progress_rows, _volunteer_requirement, friendly_integrity_errors,
)
from .view_modules.roster_helpers import *
from .view_modules.roster_helpers import _team_roster, _visible_announcements
from .view_modules.dashboards import *
from .view_modules.roster import *
from .view_modules.roster import season_class_create as legacy_season_class_create
from .view_modules.season_setup_catalog_ui import season_class_create
from .view_modules.communications_helpers import *
from .view_modules.communications_helpers import _deliver_announcement
from .view_modules.communications import *
from .view_modules.competitions_helpers import *
from .view_modules.competitions_helpers import _sync_show_calendar
from .view_modules.competitions import *
from .view_modules.show_day_helpers import *
from .view_modules.show_day_helpers import (
    _can_publish_show_update, _can_update_show_day_rider_status, _deliver_show_update,
    _parse_schedule_time, _rider_team_level_for_show, _shift_schedule_time,
    _show_day_operational_levels, _show_day_operational_user,
    _show_day_participating_riders, _show_update_allowed_audiences,
    _show_update_family_user_ids, _show_update_recipients, _visible_show_day_updates,
)
from .view_modules.show_day import *
from .view_modules.scoring import *
from .view_modules.show_planning_helpers import *
from .view_modules.show_planning_helpers import _can_manage_planning_item
from .view_modules.show_planning import *
from .view_modules.lessons_helpers import *
from .view_modules.lessons_helpers import _seed_lesson_attendance, _sync_lesson_calendar
from .view_modules.lessons import *
from .view_modules.lesson_programs_v340 import *
from .view_modules.history_helpers import *
from .view_modules.history_helpers import (
    _accessiea_show_column, _accessiea_split_name, _accessiea_team_level,
    _historical_import_bootstrap_counts, _historical_import_commit,
    _historical_import_preview, _historical_import_preview_accessiea,
    _historical_import_preview_standard, _history_import_date, _history_import_decimal,
    _history_import_int, _history_import_level, _history_import_norm,
    _history_import_track, _season_archive_readiness, _season_rider_summary,
)
from .view_modules.history import *
from .view_modules.administration_helpers import *
from .view_modules.administration_helpers import _can_manage_user
from .view_modules.administration import *
from .view_modules.finance_core_helpers import *
from .view_modules.finance_core_helpers import _finance_account_rows
from .view_modules.finance_core import *
from .view_modules.family_finance_helpers import *
from .view_modules.family_finance_helpers import _model_form_save_cleanly, _sync_assistance_transaction, _sync_family_payment_transaction
from .view_modules.family_finance import *
from .view_modules.fundraising_helpers import *
from .view_modules.fundraising_helpers import _fundraising_policy, _sync_fundraising_contribution
from .view_modules.fundraising import *
from .view_modules.finance_reports_helpers import *
from .view_modules.finance_reports_helpers import _budget_report_rows, _csv_response, _finance_report_season
from .view_modules.finance_reports import *
from .view_modules.show_finance_helpers import *
from .view_modules.show_finance_helpers import _require_adult_finance_participant, _show_finance_totals
from .view_modules.show_finance import *
from .view_modules.finance_v350 import *

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
