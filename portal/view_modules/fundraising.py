"""Views for the fundraising domain."""

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


from .fundraising_helpers import (
    _fundraising_policy,
    _sync_fundraising_contribution,
)

@login_required
def fundraising_policy_edit(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    if not season:
        messages.error(request, "Create or activate a season before setting a fundraising policy.")
        return redirect("fundraising_dashboard")
    policy = _fundraising_policy(season)
    form = FundraisingPolicyForm(request.POST or None, instance=policy, season=season)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.season = season
        obj.updated_by = request.user
        obj.full_clean()
        obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED,
            obj=obj, season=season,
            summary=f"Updated fundraising policy for {season.name}",
            details={
                "model": obj.model,
                "default_family_credit_percent": obj.default_family_credit_percent,
                "participation_optional": obj.participation_optional,
                "allowed_charge_types": ", ".join(obj.allowed_charge_types or []),
            },
        )
        messages.success(request, "Fundraising policy updated.")
        return redirect("fundraising_dashboard")
    return render(request, "portal/form.html", {
        "form": form,
        "title": f"Fundraising policy · {season.name}",
        "eyebrow": "FUNDRAISING POLICY",
    })

@login_required
def family_fundraising(request, membership_pk):
    team = _team(request.user)
    membership = get_object_or_404(
        SeasonMembership.objects.select_related("rider", "season"),
        pk=membership_pk, season__team=team,
    )
    if not _can_view_family_account(request.user, membership):
        raise PermissionDenied

    policy = _fundraising_policy(membership.season)
    contributions = (
        FundraisingContribution.objects.filter(
            campaign__team=team,
            campaign__season=membership.season,
            beneficiary_membership=membership,
            status=FundraisingContribution.Status.POSTED,
        )
        .select_related("campaign", "family_charge")
        .order_by("-received_date", "-created_at")
    )

    rows = []
    total_raised = total_credit = Decimal("0")
    for contribution in contributions:
        rows.append({
            "campaign": contribution.campaign,
            "date": contribution.received_date,
            "amount": contribution.amount,
            "family_credit": contribution.family_credit_amount,
            "team_retained": contribution.team_retained_amount,
            "family_charge": contribution.family_charge,
        })
        total_raised += contribution.amount
        total_credit += contribution.family_credit_amount or Decimal("0")

    return render(request, "portal/family_fundraising.html", {
        "membership": membership,
        "policy": policy,
        "rows": rows,
        "total_raised": total_raised,
        "total_credit": total_credit,
        "total_team": total_raised - total_credit,
    })

@login_required
def fundraising_dashboard(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)

    campaigns = FundraisingCampaign.objects.filter(team=team).select_related("season")
    selected_season = request.GET.get("season", "")
    if selected_season == "all":
        pass
    elif selected_season.isdigit():
        campaigns = campaigns.filter(season_id=int(selected_season))
    else:
        selected_season = str(season.pk) if season else "all"
        if season:
            campaigns = campaigns.filter(season=season)

    campaign_rows = []
    total_raised = total_family_credit = total_retained = Decimal("0")
    for campaign in campaigns:
        raised = campaign.posted_total
        family_credit = campaign.family_credit_total
        retained = raised - family_credit
        campaign_rows.append({
            "campaign": campaign,
            "raised": raised,
            "family_credit": family_credit,
            "retained": retained,
        })
        total_raised += raised
        total_family_credit += family_credit
        total_retained += retained

    return render(request, "portal/fundraising_dashboard.html", {
        "policy": _fundraising_policy(season),
        "campaign_rows": campaign_rows,
        "seasons": Season.objects.filter(team=team).order_by("-start_date"),
        "selected_season": selected_season,
        "total_raised": total_raised,
        "total_family_credit": total_family_credit,
        "total_retained": total_retained,
    })

@login_required
def fundraising_campaign_create(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    if not season:
        messages.error(request, "Create or activate a season before creating a fundraising campaign.")
        return redirect("fundraising_dashboard")
    form = FundraisingCampaignForm(request.POST or None)
    if not request.method == "POST" and season:
        form.fields["start_date"].initial = timezone.localdate()
    if form.is_valid():
        obj = form.save(commit=False)
        obj.team = team
        obj.season = season
        obj.created_by = request.user
        obj.full_clean()
        obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj,
            season=season, summary=f"Created fundraising campaign: {obj.name}",
            details={"goal": obj.goal_amount, "status": obj.status},
        )
        messages.success(request, "Fundraising campaign created.")
        return redirect("fundraising_campaign_detail", pk=obj.pk)
    return render(request, "portal/form.html", {
        "form": form, "title": "New fundraising campaign", "eyebrow": "FUNDRAISING"
    })

@login_required
def fundraising_campaign_edit(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(FundraisingCampaign, pk=pk, team=team)
    _require_finance(request.user, obj.season)
    form = FundraisingCampaignForm(request.POST or None, instance=obj)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.team = team
        obj.full_clean()
        obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj,
            season=obj.season, summary=f"Updated fundraising campaign: {obj.name}",
            details={"goal": obj.goal_amount, "status": obj.status},
        )
        messages.success(request, "Fundraising campaign updated.")
        return redirect("fundraising_campaign_detail", pk=obj.pk)
    return render(request, "portal/form.html", {
        "form": form, "title": f"Edit fundraiser · {obj.name}", "eyebrow": "FUNDRAISING"
    })

@login_required
def fundraising_campaign_detail(request, pk):
    team = _team(request.user)
    campaign = get_object_or_404(FundraisingCampaign.objects.select_related("season"), pk=pk, team=team)
    _require_finance(request.user, campaign.season)
    contributions = campaign.contributions.select_related(
        "beneficiary_membership__rider", "family_charge", "account", "category",
        "financial_transaction", "family_credit"
    )
    posted = contributions.filter(status=FundraisingContribution.Status.POSTED)
    totals = posted.aggregate(
        raised=Sum("amount"),
        family_credit=Sum("family_credit_amount"),
    )
    raised = totals["raised"] or Decimal("0")
    family_credit = totals["family_credit"] or Decimal("0")
    return render(request, "portal/fundraising_campaign_detail.html", {
        "campaign": campaign,
        "contributions": contributions,
        "raised": raised,
        "family_credit": family_credit,
        "retained": raised - family_credit,
    })

@login_required
def fundraising_contribution_add(request, campaign_pk):
    team = _team(request.user)
    campaign = get_object_or_404(FundraisingCampaign, pk=campaign_pk, team=team)
    _require_finance(request.user, campaign.season)
    if campaign.status == FundraisingCampaign.Status.CLOSED:
        messages.error(request, "Closed fundraising campaigns cannot receive new contributions.")
        return redirect("fundraising_campaign_detail", pk=campaign.pk)

    policy = _fundraising_policy(campaign.season)
    form = FundraisingContributionForm(request.POST or None, campaign=campaign, policy=policy)
    if not request.method == "POST":
        form.fields["received_date"].initial = timezone.localdate()
    if form.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.campaign = campaign
            obj.created_by = request.user
            obj.status = FundraisingContribution.Status.POSTED
            obj.full_clean()
            obj.save()
            _sync_fundraising_contribution(obj, request.user)
            _audit_event(
                team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj,
                season=campaign.season,
                summary=f"Recorded fundraising contribution to {campaign.name}",
                details={
                    "donor": obj.donor_name or "Anonymous", "amount": obj.amount,
                    "family_credit": obj.family_credit_amount,
                    "beneficiary": obj.beneficiary_membership or "",
                },
            )
        messages.success(request, "Fundraising contribution recorded and posted to the team ledger.")
        return redirect("fundraising_campaign_detail", pk=campaign.pk)
    return render(request, "portal/form.html", {
        "form": form, "title": f"Add contribution · {campaign.name}", "eyebrow": "FUNDRAISING"
    })

@login_required
def fundraising_contribution_edit(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(
        FundraisingContribution.objects.select_related(
            "campaign__season", "family_credit", "family_charge", "beneficiary_membership__rider"
        ),
        pk=pk, campaign__team=team,
    )
    _require_finance(request.user, obj.campaign.season)
    if obj.status == FundraisingContribution.Status.VOID:
        messages.info(request, "Voided fundraising contributions are retained for audit history and cannot be edited.")
        return redirect("fundraising_campaign_detail", pk=obj.campaign_id)

    policy = _fundraising_policy(obj.campaign.season)
    form = FundraisingContributionForm(
        request.POST or None, instance=obj, campaign=obj.campaign, policy=policy
    )
    if form.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.campaign = obj.campaign
            obj.full_clean()
            obj.save()
            _sync_fundraising_contribution(obj, request.user)
            _audit_event(
                team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj,
                season=obj.campaign.season,
                summary=f"Updated fundraising contribution to {obj.campaign.name}",
                details={
                    "donor": obj.donor_name or "Anonymous", "amount": obj.amount,
                    "family_credit": obj.family_credit_amount,
                    "beneficiary": obj.beneficiary_membership or "",
                },
            )
        messages.success(request, "Fundraising contribution and linked finance records updated.")
        return redirect("fundraising_campaign_detail", pk=obj.campaign_id)
    return render(request, "portal/form.html", {
        "form": form, "title": f"Edit contribution · {obj.campaign.name}", "eyebrow": "FUNDRAISING"
    })

@login_required
def fundraising_contribution_void(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(
        FundraisingContribution.objects.select_related(
            "campaign__season", "financial_transaction", "family_credit"
        ),
        pk=pk, campaign__team=team,
    )
    _require_finance(request.user, obj.campaign.season)
    if obj.status == FundraisingContribution.Status.VOID:
        messages.info(request, "This fundraising contribution is already void.")
        return redirect("fundraising_campaign_detail", pk=obj.campaign_id)

    if request.method == "POST":
        reason = (request.POST.get("reason") or "Voided by Treasurer").strip()
        with transaction.atomic():
            obj.status = FundraisingContribution.Status.VOID
            obj.voided_at = timezone.now()
            obj.voided_by = request.user
            obj.void_reason = reason
            obj.save(update_fields=["status", "voided_at", "voided_by", "void_reason", "updated_at"])

            if obj.financial_transaction_id:
                tx = obj.financial_transaction
                if tx.status != FinancialTransaction.Status.VOID:
                    tx.status = FinancialTransaction.Status.VOID
                    tx.voided_at = timezone.now()
                    tx.voided_by = request.user
                    tx.void_reason = f"Fundraising contribution void: {reason}"
                    tx.updated_by = request.user
                    tx.save(update_fields=[
                        "status", "voided_at", "voided_by", "void_reason", "updated_by", "updated_at"
                    ])

            if obj.family_credit_id:
                credit = obj.family_credit
                credit.status = FamilyCredit.Status.CANCELLED
                credit.notes = f"{credit.notes}\nFundraising contribution #{obj.pk} voided: {reason}".strip()
                credit.save(update_fields=["status", "notes"])

            _audit_event(
                team=team, actor=request.user, action=AuditEvent.Action.VOIDED, obj=obj,
                season=obj.campaign.season,
                summary=f"Voided fundraising contribution to {obj.campaign.name}",
                details={"amount": obj.amount, "reason": reason},
            )
        messages.success(request, "Fundraising contribution voided; ledger and family-credit history were retained.")
        return redirect("fundraising_campaign_detail", pk=obj.campaign_id)

    return render(request, "portal/fundraising_contribution_void.html", {
        "object": obj, "title": "Void fundraising contribution"
    })

@login_required
def fundraising_campaign_export(request, pk):
    team = _team(request.user)
    campaign = get_object_or_404(FundraisingCampaign, pk=pk, team=team)
    _require_finance(request.user, campaign.season)
    response = HttpResponse(content_type="text/csv")
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "-", campaign.name).strip("-").lower() or "fundraiser"
    response["Content-Disposition"] = f'attachment; filename="{safe_name}-contributions.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Date", "Status", "Donor", "Amount", "Rider / Family", "Family credit",
        "Team retained", "Account", "Category", "Method", "Reference", "Notes",
    ])
    for row in campaign.contributions.select_related(
        "beneficiary_membership__rider", "account", "category"
    ):
        writer.writerow([
            row.received_date, row.get_status_display(), row.donor_name or "Anonymous", row.amount,
            row.beneficiary_membership.rider if row.beneficiary_membership_id else "",
            row.family_credit_amount, row.team_retained_amount,
            row.account.name, row.category.name, row.method, row.reference, row.notes,
        ])
    return response
