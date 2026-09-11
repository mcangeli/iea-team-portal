"""Views for the family finance domain."""

import re
import csv
from pathlib import Path
from datetime import datetime, time, timedelta
from decimal import Decimal
from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..forms import (
    AnnouncementForm, CalendarEventForm, GuardianContactForm, RiderForm,
    SeasonClassForm, SeasonMembershipForm, ShowClassForm, ShowEntryForm,
    ShowForm, ShowResultForm, SeasonScoringConfigForm, QualificationOverrideForm,
    LessonGroupForm, LessonForm, LessonAttendanceForm, ShowAvailabilityForm,
    VolunteerLogForm, VolunteerReviewForm, VolunteerRequirementForm,
    UserOnboardingForm, UserAccountEditForm, TemporaryPasswordResetForm, NotificationPreferenceForm,
    CommitteeAssignmentForm, ShowLeadAssignmentForm, ShowPlanningItemForm, ShowDayUpdateForm,
    RiderDevelopmentNoteForm, RiderAwardForm, EventRSVPForm, ActionItemForm,
    HistoricalImportUploadForm, HistoricalResultEditForm, HistoricalResultHeaderForm, HistoricalResultFormSet,
    FinancialAccountForm, FinancialCategoryForm, FinancialTransactionForm, SeasonBudgetForm,
    HomeBarnForm, MembershipDuesRateForm, FamilyChargeForm, FamilyCreditForm,
    ServiceAgreementCreditForm, FinancialAssistanceAwardForm, AssistanceClaimForm, FamilyPaymentForm,
    ShowBudgetLineForm, ReimbursementRequestForm, ReimbursementReviewForm, ShowFundingPolicyForm,
    ShowTransactionAllocationForm, FundraisingCampaignForm, FundraisingContributionForm,
    FundraisingPolicyForm,
)
from ..models import (
    Announcement, CalendarEvent, GuardianContact, Rider, RiderGuardian, Season,
    SeasonClass, SeasonMembership, SeasonScoringConfig, QualificationOverride, Show, ShowClass, ShowEntry, ShowResult, UserProfile,
    LessonGroup, Lesson, LessonAttendance, ShowAvailability, ShowDayRiderStatus, VolunteerLog, Notification,
    CommitteeAssignment, ShowLeadAssignment, ShowPlanningItem, ShowDayUpdate, RiderDevelopmentNote, RiderAward,
    EventRSVP, ActionItem, FinancialAccount, FinancialCategory, FinancialTransaction, SeasonBudget,
    HomeBarn, MembershipDuesRate, FamilyCharge, FamilyCredit, ServiceAgreementCredit,
    FinancialAssistanceAward, AssistanceClaim, FamilyPayment, ShowBudgetLine, ReimbursementRequest,
    ShowTransactionAllocation, AuditEvent, FundraisingCampaign, FundraisingContribution,
    FundraisingPolicy,
)

from .common import (
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
    _team,
    _team_scoring_rows,
    _visible_action_items,
    _visible_riders,
    _volunteer_progress_rows,
    _volunteer_requirement,
    friendly_integrity_errors,
)


from .family_finance_helpers import (
    _model_form_save_cleanly,
    _sync_assistance_transaction,
    _sync_family_payment_transaction,
)

@login_required
def finance_receivables(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    rows = []
    total_billed = total_relief = total_paid = total_balance = Decimal("0")
    if season:
        memberships = SeasonMembership.objects.filter(season=season).select_related(
            "rider", "home_barn"
        ).order_by("rider__last_name", "rider__first_name")
        for membership in memberships:
            totals = _family_account_totals(membership)
            rows.append({"membership": membership, **totals})
            total_billed += totals["billed"]
            total_relief += totals["generic_credits"] + totals["service_credits"] + totals["assistance"]
            total_paid += totals["payments"]
            total_balance += totals["balance"]
    return render(request, "portal/finance_receivables.html", {
        "season": season,
        "rows": rows,
        "total_billed": total_billed,
        "total_relief": total_relief,
        "total_paid": total_paid,
        "total_balance": total_balance,
    })

@login_required
def finance_dues_setup(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    barns = HomeBarn.objects.filter(team=team).order_by("name")
    rates = MembershipDuesRate.objects.filter(season=season).select_related("home_barn") if season else MembershipDuesRate.objects.none()
    return render(request, "portal/finance_dues_setup.html", {
        "season": season, "barns": barns, "rates": rates,
    })

@login_required
@friendly_integrity_errors
def home_barn_create(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    form = HomeBarnForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False); obj.team = team; obj.save()
        messages.success(request, "Home barn added.")
        return redirect("finance_dues_setup")
    return render(request, "portal/form.html", {"form": form, "title": "Add home barn", "eyebrow": "MEMBERSHIP DUES"})

@login_required
@friendly_integrity_errors
def home_barn_edit(request, pk):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    obj = get_object_or_404(HomeBarn, pk=pk, team=team)
    form = HomeBarnForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save(); messages.success(request, "Home barn updated."); return redirect("finance_dues_setup")
    return render(request, "portal/form.html", {"form": form, "title": f"Edit barn · {obj.name}", "eyebrow": "MEMBERSHIP DUES"})

@login_required
@friendly_integrity_errors
def dues_rate_create(request):
    team = _team(request.user); season = _active_season(team)
    _require_finance(request.user, season)
    if not season:
        messages.error(request, "Create or activate a season before setting dues.")
        return redirect("finance_dues_setup")
    form = MembershipDuesRateForm(request.POST or None, team=team, season=season)
    if form.is_valid():
        obj = form.save(commit=False); obj.season = season; obj.full_clean(); obj.save()
        messages.success(request, "Membership dues rate added.")
        return redirect("finance_dues_setup")
    return render(request, "portal/form.html", {"form": form, "title": "Add membership dues rate", "eyebrow": season.name})

@login_required
@friendly_integrity_errors
def dues_rate_edit(request, pk):
    team = _team(request.user); season = _active_season(team)
    _require_finance(request.user, season)
    obj = get_object_or_404(MembershipDuesRate.objects.select_related("season", "home_barn"), pk=pk, season__team=team)
    form = MembershipDuesRateForm(request.POST or None, instance=obj, team=team, season=obj.season)
    if form.is_valid():
        obj = form.save(commit=False); obj.full_clean(); obj.save()
        messages.success(request, "Membership dues rate updated.")
        return redirect("finance_dues_setup")
    return render(request, "portal/form.html", {"form": form, "title": f"Edit dues · {obj.home_barn.name}", "eyebrow": obj.season.name})

@login_required
@require_POST
def membership_dues_generate(request, membership_pk):
    team = _team(request.user)
    membership = get_object_or_404(
        SeasonMembership.objects.select_related("season", "rider", "home_barn"),
        pk=membership_pk, season__team=team
    )
    _require_finance(request.user, membership.season)
    if not membership.home_barn:
        messages.error(request, f"Set {membership.rider.display_name}'s home barn before generating membership dues.")
        return redirect("family_account", membership_pk=membership.pk)
    rate = MembershipDuesRate.objects.filter(season=membership.season, home_barn=membership.home_barn).first()
    if not rate:
        messages.error(request, f"No dues rate is configured for {membership.home_barn.name}.")
        return redirect("family_account", membership_pk=membership.pk)
    existing = membership.family_charges.filter(charge_type=FamilyCharge.ChargeType.MEMBERSHIP_DUES).first()
    if existing:
        messages.info(request, "This rider already has a membership-dues charge. Edit the existing charge rather than creating a duplicate.")
    else:
        FamilyCharge.objects.create(
            membership=membership,
            charge_type=FamilyCharge.ChargeType.MEMBERSHIP_DUES,
            description=f"{membership.season.name} membership dues — {membership.home_barn.name}",
            amount=rate.amount,
            charge_date=membership.season.start_date,
            due_date=rate.due_date,
            source_dues_rate=rate,
            created_by=request.user,
        )
        messages.success(request, f"Membership dues charge created from the {membership.home_barn.name} season rate.")
    return redirect("family_account", membership_pk=membership.pk)

@login_required
def family_account(request, membership_pk):
    team = _team(request.user)
    membership = get_object_or_404(
        SeasonMembership.objects.select_related("rider", "season", "home_barn"),
        pk=membership_pk, season__team=team,
    )
    if not _can_view_family_account(request.user, membership):
        raise PermissionDenied
    totals = _family_account_totals(membership)
    awards = membership.assistance_awards.prefetch_related("claims").all()
    service_agreements = membership.service_agreements.prefetch_related("required_shows").select_related("charge")
    fundraising_qs = FundraisingContribution.objects.filter(
        campaign__season=membership.season,
        beneficiary_membership=membership,
        status=FundraisingContribution.Status.POSTED,
    )
    fundraising_totals = fundraising_qs.aggregate(
        raised=Sum("amount"), family_credit=Sum("family_credit_amount")
    )
    return render(request, "portal/family_account.html", {
        "membership": membership,
        "can_finance": _can_finance(request.user, membership.season),
        "awards": awards,
        "service_agreements": service_agreements,
        "fundraising_raised": fundraising_totals["raised"] or Decimal("0"),
        "fundraising_credit": fundraising_totals["family_credit"] or Decimal("0"),
        "fundraising_team": (
            (fundraising_totals["raised"] or Decimal("0"))
            - (fundraising_totals["family_credit"] or Decimal("0"))
        ),
        **totals,
    })

@login_required
@friendly_integrity_errors
def family_charge_create(request, membership_pk):
    team = _team(request.user)
    membership = get_object_or_404(SeasonMembership.objects.select_related("season", "rider"), pk=membership_pk, season__team=team)
    _require_finance(request.user, membership.season)
    form = FamilyChargeForm(request.POST or None, membership=membership)
    if form.is_valid():
        obj = form.save(commit=False); obj.membership = membership; obj.created_by = request.user
        if not _model_form_save_cleanly(form, obj):
            return render(request, "portal/form.html", {"form": form, "title": f"Add charge · {membership.rider.display_name}", "eyebrow": "FAMILY ACCOUNT"})
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj,
            season=membership.season,
            summary=f"Added family charge for {membership.rider.display_name}",
            details={"description": obj.description, "amount": obj.amount, "status": obj.status},
        )
        messages.success(request, "Family charge added.")
        return redirect("family_account", membership_pk=membership.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"Add charge · {membership.rider.display_name}", "eyebrow": "FAMILY ACCOUNT"})

@login_required
def family_charge_edit(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(FamilyCharge.objects.select_related("membership__season", "membership__rider"), pk=pk, membership__season__team=team)
    _require_finance(request.user, obj.membership.season)
    form = FamilyChargeForm(request.POST or None, instance=obj, membership=obj.membership)
    if form.is_valid():
        obj = form.save(commit=False)
        if not _model_form_save_cleanly(form, obj):
            return render(request, "portal/form.html", {"form": form, "title": f"Edit charge · {obj.description}", "eyebrow": "FAMILY ACCOUNT"})
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj,
            season=obj.membership.season,
            summary=f"Updated family charge: {obj.description}",
            details={"amount": obj.amount, "status": obj.status},
        )
        messages.success(request, "Charge updated.")
        return redirect("family_account", membership_pk=obj.membership_id)
    return render(request, "portal/form.html", {"form": form, "title": f"Edit charge · {obj.description}", "eyebrow": "FAMILY ACCOUNT"})

@login_required
@friendly_integrity_errors
def family_credit_add(request, charge_pk):
    team = _team(request.user)
    charge = get_object_or_404(FamilyCharge.objects.select_related("membership__season", "membership__rider"), pk=charge_pk, membership__season__team=team)
    _require_finance(request.user, charge.membership.season)
    form = FamilyCreditForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False); obj.charge = charge; obj.created_by = request.user
        if not _model_form_save_cleanly(form, obj):
            return render(request, "portal/form.html", {"form": form, "title": f"Add credit · {charge.description}", "eyebrow": "FAMILY ACCOUNT"})
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj,
            season=charge.membership.season,
            summary=f"Added family credit/adjustment to {charge.description}",
            details={"amount": obj.amount, "status": obj.status, "type": obj.credit_type},
        )
        messages.success(request, "Credit/adjustment added.")
        return redirect("family_account", membership_pk=charge.membership_id)
    return render(request, "portal/form.html", {"form": form, "title": f"Add credit · {charge.description}", "eyebrow": charge.membership.rider.display_name})

@login_required
def family_credit_edit(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(
        FamilyCredit.objects.select_related("charge__membership__season", "charge__membership__rider"),
        pk=pk, charge__membership__season__team=team
    )
    _require_finance(request.user, obj.charge.membership.season)
    form = FamilyCreditForm(request.POST or None, instance=obj)
    if form.is_valid():
        obj = form.save(commit=False)
        if not _model_form_save_cleanly(form, obj):
            return render(request, "portal/form.html", {"form": form, "title": f"Edit credit · {obj.charge.description}", "eyebrow": "FAMILY ACCOUNT"})
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj,
            season=obj.charge.membership.season,
            summary=f"Updated family credit/adjustment for {obj.charge.description}",
            details={"amount": obj.amount, "status": obj.status, "type": obj.credit_type},
        )
        messages.success(request, "Credit/adjustment updated.")
        return redirect("family_account", membership_pk=obj.charge.membership_id)
    return render(request, "portal/form.html", {
        "form": form, "title": f"Edit credit · {obj.charge.description}", "eyebrow": obj.charge.membership.rider.display_name
    })

@login_required
@friendly_integrity_errors
def service_agreement_add(request, membership_pk):
    team = _team(request.user)
    membership = get_object_or_404(SeasonMembership.objects.select_related("season", "rider"), pk=membership_pk, season__team=team)
    _require_finance(request.user, membership.season)
    form = ServiceAgreementCreditForm(request.POST or None, membership=membership)
    if form.is_valid():
        obj = form.save(commit=False); obj.membership = membership; obj.created_by = request.user
        if not _model_form_save_cleanly(form, obj, save_m2m=True):
            return render(request, "portal/form.html", {"form": form, "title": f"Add service agreement · {membership.rider.display_name}", "eyebrow": "FAMILY ACCOUNT"})
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj,
            season=membership.season, summary=f"Added service agreement for {membership.rider.display_name}",
            details={"amount": obj.amount, "status": obj.status},
        )
        messages.success(request, "Service agreement saved.")
        return redirect("family_account", membership_pk=membership.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"Add service agreement · {membership.rider.display_name}", "eyebrow": "CONDITIONAL CREDIT"})

@login_required
def service_agreement_edit(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(ServiceAgreementCredit.objects.select_related("membership__season", "membership__rider"), pk=pk, membership__season__team=team)
    _require_finance(request.user, obj.membership.season)
    form = ServiceAgreementCreditForm(request.POST or None, instance=obj, membership=obj.membership)
    if form.is_valid():
        obj = form.save(commit=False)
        if not _model_form_save_cleanly(form, obj, save_m2m=True):
            return render(request, "portal/form.html", {"form": form, "title": f"Edit service agreement · {obj.membership.rider.display_name}", "eyebrow": "CONDITIONAL CREDIT"})
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj,
            season=obj.membership.season, summary=f"Updated service agreement for {obj.membership.rider.display_name}",
            details={"amount": obj.amount, "status": obj.status},
        )
        messages.success(request, "Service agreement updated.")
        return redirect("family_account", membership_pk=obj.membership_id)
    return render(request, "portal/form.html", {"form": form, "title": f"Edit service agreement · {obj.membership.rider.display_name}", "eyebrow": "CONDITIONAL CREDIT"})

@login_required
@friendly_integrity_errors
def assistance_award_add(request, membership_pk):
    team = _team(request.user)
    membership = get_object_or_404(SeasonMembership.objects.select_related("season", "rider"), pk=membership_pk, season__team=team)
    _require_finance(request.user, membership.season)
    form = FinancialAssistanceAwardForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False); obj.membership = membership; obj.created_by = request.user
        if not _model_form_save_cleanly(form, obj):
            return render(request, "portal/form.html", {"form": form, "title": f"Add assistance award · {membership.rider.display_name}", "eyebrow": "EXTERNAL ASSISTANCE"})
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj,
            season=membership.season, summary=f"Added financial assistance award for {membership.rider.display_name}",
            details={"provider": obj.provider, "approved_maximum": obj.approved_maximum, "status": obj.status},
        )
        messages.success(request, "Financial assistance award added.")
        return redirect("family_account", membership_pk=membership.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"Add assistance award · {membership.rider.display_name}", "eyebrow": "EXTERNAL ASSISTANCE"})

@login_required
def assistance_award_edit(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(FinancialAssistanceAward.objects.select_related("membership__season", "membership__rider"), pk=pk, membership__season__team=team)
    _require_finance(request.user, obj.membership.season)
    form = FinancialAssistanceAwardForm(request.POST or None, instance=obj)
    if form.is_valid():
        obj = form.save(commit=False)
        if not _model_form_save_cleanly(form, obj):
            return render(request, "portal/form.html", {"form": form, "title": f"Edit assistance award · {obj.membership.rider.display_name}", "eyebrow": "EXTERNAL ASSISTANCE"})
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj,
            season=obj.membership.season, summary=f"Updated financial assistance award for {obj.membership.rider.display_name}",
            details={"provider": obj.provider, "approved_maximum": obj.approved_maximum, "status": obj.status},
        )
        messages.success(request, "Financial assistance award updated.")
        return redirect("family_account", membership_pk=obj.membership_id)
    return render(request, "portal/form.html", {"form": form, "title": f"Edit assistance award · {obj.provider}", "eyebrow": obj.membership.rider.display_name})

@login_required
def assistance_claim_add(request, award_pk):
    team = _team(request.user)
    award = get_object_or_404(FinancialAssistanceAward.objects.select_related("membership__season", "membership__rider"), pk=award_pk, membership__season__team=team)
    _require_finance(request.user, award.membership.season)
    form = AssistanceClaimForm(request.POST or None, award=award, team=team)
    if form.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False); obj.award = award; obj.updated_by = request.user; obj.full_clean(); obj.save()
            _sync_assistance_transaction(obj, request.user)
            _audit_event(
                team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj,
                season=award.membership.season,
                summary=f"Added assistance claim for {award.membership.rider.display_name}",
                details={"status": obj.status, "requested": obj.amount_requested, "reimbursed": obj.reimbursed_amount},
            )
        messages.success(request, "Assistance claim saved.")
        return redirect("family_account", membership_pk=award.membership_id)
    return render(request, "portal/form.html", {"form": form, "title": f"Add reimbursement claim · {award.provider}", "eyebrow": award.membership.rider.display_name})

@login_required
def assistance_claim_edit(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(AssistanceClaim.objects.select_related("award__membership__season", "award__membership__rider"), pk=pk, award__membership__season__team=team)
    _require_finance(request.user, obj.award.membership.season)
    form = AssistanceClaimForm(request.POST or None, instance=obj, award=obj.award, team=team)
    if form.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False); obj.updated_by = request.user; obj.full_clean(); obj.save()
            _sync_assistance_transaction(obj, request.user)
            _audit_event(
                team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj,
                season=obj.award.membership.season,
                summary=f"Updated assistance claim for {obj.award.membership.rider.display_name}",
                details={"status": obj.status, "requested": obj.amount_requested, "reimbursed": obj.reimbursed_amount},
            )
        messages.success(request, "Assistance claim updated.")
        return redirect("family_account", membership_pk=obj.award.membership_id)
    return render(request, "portal/form.html", {"form": form, "title": f"Edit reimbursement claim · {obj.award.provider}", "eyebrow": obj.award.membership.rider.display_name})

@login_required
def family_payment_add(request, membership_pk):
    team = _team(request.user)
    membership = get_object_or_404(
        SeasonMembership.objects.select_related("season", "rider"),
        pk=membership_pk, season__team=team
    )
    _require_finance(request.user, membership.season)
    form = FamilyPaymentForm(request.POST or None, membership=membership, team=team)
    if form.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.membership = membership
            obj.created_by = request.user
            obj.full_clean()
            obj.save()
            _sync_family_payment_transaction(obj, request.user)
            _audit_event(
                team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj,
                season=membership.season,
                summary=f"Recorded family payment for {membership.rider.display_name}",
                details={"amount": obj.amount, "charge": obj.charge, "account": obj.account},
            )
        messages.success(request, "Payment recorded and posted to the team ledger.")
        return redirect("family_account", membership_pk=membership.pk)
    return render(request, "portal/form.html", {
        "form": form, "title": f"Record payment · {membership.rider.display_name}", "eyebrow": "FAMILY ACCOUNT"
    })

@login_required
def family_payment_edit(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(
        FamilyPayment.objects.select_related(
            "membership__season", "membership__rider", "charge", "financial_transaction"
        ),
        pk=pk, membership__season__team=team
    )
    _require_finance(request.user, obj.membership.season)
    if obj.status == FamilyPayment.Status.VOID:
        messages.info(request, "Voided family payments are retained for audit history and cannot be edited.")
        return redirect("family_account", membership_pk=obj.membership_id)
    form = FamilyPaymentForm(request.POST or None, instance=obj, membership=obj.membership, team=team)
    if form.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.full_clean()
            obj.save()
            _sync_family_payment_transaction(obj, request.user)
            _audit_event(
                team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj,
                season=obj.membership.season,
                summary=f"Updated family payment for {obj.membership.rider.display_name}",
                details={"amount": obj.amount, "charge": obj.charge, "account": obj.account},
            )
        messages.success(request, "Payment and linked team-ledger transaction updated.")
        return redirect("family_account", membership_pk=obj.membership_id)
    return render(request, "portal/form.html", {
        "form": form, "title": f"Edit payment · {obj.membership.rider.display_name}", "eyebrow": "FAMILY ACCOUNT"
    })

@login_required
def family_payment_delete(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(
        FamilyPayment.objects.select_related(
            "membership__season", "membership__rider", "financial_transaction"
        ),
        pk=pk, membership__season__team=team
    )
    _require_finance(request.user, obj.membership.season)
    membership_id = obj.membership_id

    if obj.status == FamilyPayment.Status.VOID:
        messages.info(request, "This family payment is already void.")
        return redirect("family_account", membership_pk=membership_id)

    if request.method == "POST":
        reason = (request.POST.get("reason") or "Voided by Treasurer").strip()
        with transaction.atomic():
            obj.status = FamilyPayment.Status.VOID
            obj.voided_at = timezone.now()
            obj.voided_by = request.user
            obj.void_reason = reason
            obj.save(update_fields=["status", "voided_at", "voided_by", "void_reason"])

            tx = obj.financial_transaction
            if tx and tx.status != FinancialTransaction.Status.VOID:
                tx.status = FinancialTransaction.Status.VOID
                tx.voided_at = timezone.now()
                tx.voided_by = request.user
                tx.void_reason = f"Family payment void: {reason}"
                tx.updated_by = request.user
                tx.save(update_fields=[
                    "status", "voided_at", "voided_by", "void_reason", "updated_by", "updated_at"
                ])

            _audit_event(
                team=team, actor=request.user, action=AuditEvent.Action.VOIDED, obj=obj,
                season=obj.membership.season,
                summary=f"Voided family payment for {obj.membership.rider.display_name}",
                details={"amount": obj.amount, "reason": reason, "transaction": tx.pk if tx else ""},
            )

        messages.success(request, "Family payment voided; the payment and ledger history were retained.")
        return redirect("family_account", membership_pk=membership_id)

    return render(request, "portal/finance_family_payment_void.html", {
        "object": obj,
        "title": "Void family payment",
    })

@login_required
@require_POST
def membership_dues_generate_all(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    if not season:
        messages.error(request, "Create or activate a season before generating membership dues.")
        return redirect("finance_dues_setup")

    created = skipped_existing = missing_barn = missing_rate = 0
    rates = {
        r.home_barn_id: r
        for r in MembershipDuesRate.objects.filter(season=season).select_related("home_barn")
    }
    memberships = SeasonMembership.objects.filter(season=season).select_related("rider", "home_barn")
    with transaction.atomic():
        for membership in memberships:
            if membership.family_charges.filter(charge_type=FamilyCharge.ChargeType.MEMBERSHIP_DUES).exists():
                skipped_existing += 1
                continue
            if not membership.home_barn_id:
                missing_barn += 1
                continue
            rate = rates.get(membership.home_barn_id)
            if not rate:
                missing_rate += 1
                continue
            FamilyCharge.objects.create(
                membership=membership,
                charge_type=FamilyCharge.ChargeType.MEMBERSHIP_DUES,
                description=f"{season.name} membership dues — {membership.home_barn.name}",
                amount=rate.amount,
                charge_date=season.start_date,
                due_date=rate.due_date,
                source_dues_rate=rate,
                created_by=request.user,
            )
            created += 1

    messages.success(
        request,
        f"Membership dues generation complete: {created} created, {skipped_existing} existing skipped, "
        f"{missing_barn} missing home barn, {missing_rate} missing dues rate."
    )
    return redirect("finance_receivables")
