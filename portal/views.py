"""Compatibility view namespace.



v2.0.0 organizes implementations by domain under portal.view_modules while

preserving portal.views.<name> for URL configuration and external imports.

"""



from .view_modules.common import (
    FINANCE_AUDIT_ENTITY_TYPES,
    HISTORICAL_IMPORT_HEADERS,
    TEAM_LEVELS,
    _active_committee_roles,
    _active_season,
    _announcement_recipients,
    _assistance_report_rows,
    _audit_event,
    _audit_value,
    _can_coordinate_team,
    _can_edit_show_schedule_class,
    _can_finance,
    _can_manage,
    _can_manage_points,
    _can_plan_show,
    _can_view_family_account,
    _can_view_private_rider,
    _ensure_season_open,
    _family_account_totals,
    _finance_season_ids,
    _is_admin,
    _is_non_team_scoring_class,
    _is_rider_account,
    _is_show_lead,
    _personal_riders,
    _planning_item_visible_to_user,
    _qualification_rows,
    _receivable_report_rows,
    _require_finance,
    _require_manage,
    _rider_class_point_rows,
    _selected_team,
    _show_planning_allowed_levels,
    _show_schedule_edit_levels,
    _team,
    _team_scoring_rows,
    _visible_action_items,
    _visible_riders,
    _volunteer_progress_rows,
    _volunteer_requirement,
    friendly_integrity_errors,
)

from .view_modules.roster_helpers import (
    _team_roster,
    _visible_announcements,
)

from .view_modules.roster import (
    dashboard,
    my_team,
    rider_list,
    rider_export,
    rider_detail,
    rider_create,
    rider_edit,
    rider_membership_edit,
    rider_guardian_add,
    rider_guardian_edit,
    parent_list,
    parent_export,
    season_setup,
    season_class_create,
    season_class_edit,
    rider_guardian_link,
    rider_guardian_unlink,
)

from .view_modules.communications_helpers import (
    _deliver_announcement,
)

from .view_modules.communications import (
    event_rsvp,
    action_item_list,
    action_item_create,
    action_item_edit,
    action_item_claim,
    action_item_complete,
    calendar,
    event_create,
    event_edit,
    event_delete,
    announcement_create,
    notification_list,
    notification_read,
    notification_read_all,
    notification_preferences,
)

from .view_modules.competitions_helpers import (
    _sync_show_calendar,
)

from .view_modules.competitions import (
    show_list,
    show_detail,
    show_create,
    show_edit,
    show_delete,
    show_class_create,
    show_class_edit,
    show_class_delete,
    show_entry_create,
    show_entry_edit,
    show_entry_delete,
    show_result_edit,
)

from .view_modules.show_day_helpers import (
    _can_publish_show_update,
    _can_update_show_day_rider_status,
    _deliver_show_update,
    _parse_schedule_time,
    _rider_team_level_for_show,
    _shift_schedule_time,
    _show_day_operational_levels,
    _show_day_operational_user,
    _show_day_participating_riders,
    _show_update_allowed_audiences,
    _show_update_family_user_ids,
    _show_update_recipients,
    _visible_show_day_updates,
)

from .view_modules.show_day import (
    my_show_day,
    show_day_dashboard,
    show_day_rider_status_update,
    show_schedule,
    show_day_updates,
    show_day_update_add,
    show_day_update_edit,
    show_day_update_retract,
    show_week_summary,
    show_week_summary_send,
)

from .view_modules.scoring import (
    standings,
    scoring_settings,
    qualification_override_edit,
    standings_export,
    point_rider_set,
)

from .view_modules.show_planning_helpers import (
    _can_manage_planning_item,
)

from .view_modules.show_planning import (
    show_planning,
    show_planning_seed_defaults,
    show_lead_add,
    show_planning_item_add,
    show_planning_item_edit,
    show_planning_item_claim,
    show_planning_item_complete,
)

from .view_modules.lessons_helpers import (
    _seed_lesson_attendance,
    _sync_lesson_calendar,
)

from .view_modules.lessons import (
    lesson_list,
    lesson_group_list,
    lesson_group_create,
    lesson_group_edit,
    lesson_create,
    lesson_detail,
    lesson_edit,
    lesson_delete,
    lesson_attendance_edit,
    show_availability,
    show_availability_edit,
    volunteer_dashboard,
    volunteer_submit,
    volunteer_review,
    volunteer_requirements,
    volunteer_export,
)

from .view_modules.history_helpers import (
    _accessiea_show_column,
    _accessiea_split_name,
    _accessiea_team_level,
    _historical_import_bootstrap_counts,
    _historical_import_commit,
    _historical_import_preview,
    _historical_import_preview_accessiea,
    _historical_import_preview_standard,
    _history_import_date,
    _history_import_decimal,
    _history_import_int,
    _history_import_level,
    _history_import_norm,
    _history_import_track,
    _season_archive_readiness,
    _season_rider_summary,
)

from .view_modules.history import (
    season_archive,
    season_history_entry,
    season_history_import,
    season_history_import_template,
    season_archive_readiness,
    season_review,
    season_close,
    season_reopen,
    rider_history,
    historical_result_edit,
    historical_result_delete,
    historical_results_add,
    rider_summary_print,
    development_note_add,
    award_list,
    award_add,
    team_record_book,
)

from .view_modules.administration_helpers import (
    _can_manage_user,
)

from .view_modules.administration import (
    committee_list,
    committee_assignment_create,
    committee_assignment_edit,
    user_list,
    user_create,
    user_edit,
    user_reset_password,
    password_change_required,
    audit_log,
)

from .view_modules.finance_core_helpers import (
    _finance_account_rows,
)

from .view_modules.finance_core import (
    finance_audit_log,
    finance_dashboard,
    finance_transaction_list,
    finance_transaction_create,
    finance_transaction_edit,
    finance_transaction_delete,
    finance_transaction_export,
    finance_accounts,
    finance_account_create,
    finance_account_edit,
    finance_category_create,
    finance_category_edit,
    finance_budget,
    finance_budget_create,
    finance_budget_edit,
    finance_receipt_download,
)

from .view_modules.family_finance_helpers import (
    _model_form_save_cleanly,
    _sync_assistance_transaction,
    _sync_family_payment_transaction,
)

from .view_modules.family_finance import (
    finance_receivables,
    finance_dues_setup,
    home_barn_create,
    home_barn_edit,
    dues_rate_create,
    dues_rate_edit,
    membership_dues_generate,
    family_account,
    family_charge_create,
    family_charge_edit,
    family_credit_add,
    family_credit_edit,
    service_agreement_add,
    service_agreement_edit,
    assistance_award_add,
    assistance_award_edit,
    assistance_claim_add,
    assistance_claim_edit,
    family_payment_add,
    family_payment_edit,
    family_payment_delete,
    membership_dues_generate_all,
)

from .view_modules.fundraising_helpers import (
    _fundraising_policy,
    _sync_fundraising_contribution,
)

from .view_modules.fundraising import (
    fundraising_policy_edit,
    family_fundraising,
    fundraising_dashboard,
    fundraising_campaign_create,
    fundraising_campaign_edit,
    fundraising_campaign_detail,
    fundraising_contribution_add,
    fundraising_contribution_edit,
    fundraising_contribution_void,
    fundraising_campaign_export,
)

from .view_modules.finance_reports_helpers import (
    _budget_report_rows,
    _csv_response,
    _finance_report_season,
)

from .view_modules.finance_reports import (
    finance_reports,
    finance_report_budget,
    finance_report_receivables,
    finance_report_assistance,
    finance_report_category,
    finance_report_budget_export,
    finance_report_receivables_export,
    finance_report_assistance_export,
    finance_report_category_export,
)

from .view_modules.show_finance_helpers import (
    _require_adult_finance_participant,
    _show_finance_totals,
)

from .view_modules.show_finance import (
    show_finance,
    show_budget_add,
    show_budget_edit,
    show_family_charges_generate,
    show_funding_policy,
    finance_transaction_allocations,
    finance_transaction_allocation_add,
    finance_transaction_allocation_edit,
    finance_transaction_allocation_delete,
    reimbursement_list,
    reimbursement_create,
    reimbursement_edit,
    reimbursement_submit,
    reimbursement_review,
    reimbursement_receipt,
)
