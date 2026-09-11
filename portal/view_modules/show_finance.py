"""Views for the show finance domain."""

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


from .show_finance_helpers import (
    _require_adult_finance_participant,
    _show_finance_totals,
)

@login_required
def show_finance(request, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=pk, team=team)
    _require_finance(request.user, show.season)
    totals = _show_finance_totals(show)
    reimbursements = show.reimbursement_requests.select_related("requested_by","category","payment_account")
    return render(request, "portal/show_finance.html", {
        "show": show, **totals, "reimbursements": reimbursements,
        "funding_policy": show.season.show_fee_policy_for(show.competition_level),
        "funding_policy_label": dict(Season.ShowFeePolicy.choices).get(show.season.show_fee_policy_for(show.competition_level)),
    })

@login_required
def show_budget_add(request, show_pk):
    team = _team(request.user); show = get_object_or_404(Show, pk=show_pk, team=team)
    _require_finance(request.user, show.season)
    form = ShowBudgetLineForm(request.POST or None, show=show)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.show = show
        obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj,
            season=show.season,
            summary=f"Added show budget item: {obj.description}",
            details={"show": show, "scope": obj.scope, "category": obj.category, "amount": obj.amount},
        )
        messages.success(request, "Show budget line added.")
        return redirect("show_finance", pk=show.pk)
    return render(request,"portal/form.html",{"form":form,"title":"Add show budget line","eyebrow":show.name})

@login_required
def show_budget_edit(request, pk):
    team=_team(request.user); line=get_object_or_404(ShowBudgetLine.objects.select_related("show"),pk=pk,show__team=team)
    _require_finance(request.user,line.show.season)
    form=ShowBudgetLineForm(request.POST or None,instance=line,show=line.show)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.show = line.show
        obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj,
            season=line.show.season,
            summary=f"Updated show budget item: {obj.description}",
            details={"show": line.show, "scope": obj.scope, "category": obj.category, "amount": obj.amount},
        )
        messages.success(request, "Show budget line updated.")
        return redirect("show_finance", pk=line.show_id)
    return render(request,"portal/form.html",{"form":form,"title":"Edit show budget line","eyebrow":line.show.name})

@login_required
def show_family_charges_generate(request, pk):
    team=_team(request.user); show=get_object_or_404(Show.objects.select_related("season"),pk=pk,team=team)
    _require_finance(request.user,show.season)
    policy=show.season.show_fee_policy_for(show.competition_level)
    riders=Rider.objects.filter(show_entries__show_class__show=show).distinct().order_by("last_name","first_name")
    memberships=SeasonMembership.objects.filter(season=show.season,rider__in=riders).select_related("rider")
    if request.method=="POST":
        if policy in {Season.ShowFeePolicy.INCLUDED, Season.ShowFeePolicy.PACKAGE}:
            messages.error(request,"This season marks these show fees as covered by dues or a season package. Change the funding policy or use Manual / mixed before creating family charges.")
            return redirect("show_finance",pk=show.pk)
        amount_raw=request.POST.get("amount","0")
        description=(request.POST.get("description") or f"{show.name} show fee").strip()
        due_date=request.POST.get("due_date") or None
        try: amount=Decimal(amount_raw)
        except Exception: amount=Decimal("0")
        selected=set(request.POST.getlist("membership"))
        if amount <= 0:
            messages.error(request,"Enter a show fee greater than zero.")
        else:
            created=skipped=0
            for membership in memberships:
                if str(membership.pk) not in selected: continue
                exists=FamilyCharge.objects.filter(membership=membership,show=show,charge_type=FamilyCharge.ChargeType.SHOW_FEE).exists()
                if exists: skipped+=1; continue
                FamilyCharge.objects.create(membership=membership,show=show,charge_type=FamilyCharge.ChargeType.SHOW_FEE,
                    description=description,amount=amount,due_date=due_date,created_by=request.user)
                created+=1
            messages.success(request,f"Created {created} family show charge{'s' if created != 1 else ''}; skipped {skipped} existing charge{'s' if skipped != 1 else ''}.")
            return redirect("show_finance",pk=show.pk)
    return render(request,"portal/show_family_charges.html",{
        "show":show,"memberships":memberships,"policy":policy,
        "policy_label":dict(Season.ShowFeePolicy.choices).get(policy),
        "default_amount":show.season.default_rider_show_fee,
    })

@login_required
def show_funding_policy(request):
    _require_manage(request.user); team=_team(request.user); season=_active_season(team)
    if not season:
        messages.error(request,"Create or activate a season first."); return redirect("season_setup")
    form=ShowFundingPolicyForm(request.POST or None,instance=season)
    if form.is_valid():
        form.save(); messages.success(request,"Show funding policy updated."); return redirect("season_setup")
    return render(request,"portal/form.html",{"form":form,"title":"Show funding policy","eyebrow":season.name})

@login_required
def finance_transaction_allocations(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(
        FinancialTransaction.objects.select_related("season", "account", "category"),
        pk=pk, team=team,
    )
    _require_finance(request.user, obj.season)
    allocations = obj.show_allocations.select_related("show", "budget_line").all()
    allocated = allocations.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    remaining = obj.amount - allocated
    return render(request, "portal/finance_transaction_allocations.html", {
        "transaction": obj,
        "allocations": allocations,
        "allocated": allocated,
        "remaining": remaining,
    })

@login_required
@friendly_integrity_errors
def finance_transaction_allocation_add(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(FinancialTransaction, pk=pk, team=team)
    _require_finance(request.user, obj.season)
    if obj.status != FinancialTransaction.Status.POSTED:
        messages.error(request, "Voided transactions cannot receive show allocations.")
        return redirect("finance_transaction_allocations", pk=obj.pk)
    allocated = obj.show_allocations.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    remaining = obj.amount - allocated
    form = ShowTransactionAllocationForm(
        request.POST or None, transaction=obj,
        initial={"amount": remaining if remaining > 0 else None},
    )
    if form.is_valid():
        allocation = form.save(commit=False)
        allocation.transaction = obj
        allocation.full_clean()
        allocation.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.ALLOCATED, obj=allocation,
            summary=f"Allocated {allocation.amount} to {allocation.show.name}",
            details={
                "transaction": obj.pk, "scope": allocation.scope,
                "budget_item": allocation.budget_line or "", "amount": allocation.amount,
            },
        )
        messages.success(request, "Show allocation added.")
        return redirect("finance_transaction_allocations", pk=obj.pk)
    return render(request, "portal/form.html", {
        "form": form,
        "title": "Allocate transaction to show",
        "eyebrow": obj.description,
    })

@login_required
@friendly_integrity_errors
def finance_transaction_allocation_edit(request, allocation_pk):
    team = _team(request.user)
    allocation = get_object_or_404(
        ShowTransactionAllocation.objects.select_related("transaction", "show"),
        pk=allocation_pk, transaction__team=team,
    )
    obj = allocation.transaction
    _require_finance(request.user, obj.season)
    if obj.status != FinancialTransaction.Status.POSTED:
        messages.error(request, "Allocations on voided transactions cannot be edited.")
        return redirect("finance_transaction_allocations", pk=obj.pk)
    form = ShowTransactionAllocationForm(
        request.POST or None, instance=allocation, transaction=obj
    )
    if form.is_valid():
        item = form.save(commit=False)
        item.transaction = obj
        item.full_clean()
        item.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=item,
            summary=f"Updated show allocation for {item.show.name}",
            details={
                "transaction": obj.pk, "scope": item.scope,
                "budget_item": item.budget_line or "", "amount": item.amount,
            },
        )
        messages.success(request, "Show allocation updated.")
        return redirect("finance_transaction_allocations", pk=obj.pk)
    return render(request, "portal/form.html", {
        "form": form,
        "title": "Edit show allocation",
        "eyebrow": obj.description,
    })

@login_required
def finance_transaction_allocation_delete(request, allocation_pk):
    team = _team(request.user)
    allocation = get_object_or_404(
        ShowTransactionAllocation.objects.select_related("transaction", "show"),
        pk=allocation_pk, transaction__team=team,
    )
    obj = allocation.transaction
    _require_finance(request.user, obj.season)
    if request.method == "POST":
        allocation_label = str(allocation)
        allocation_id = allocation.pk
        allocation_amount = allocation.amount
        allocation_show = allocation.show
        allocation.delete()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.REMOVED,
            season=obj.season, entity_type="ShowTransactionAllocation",
            entity_id=allocation_id, entity_label=allocation_label,
            summary=f"Removed show allocation from {allocation_show.name}",
            details={"transaction": obj.pk, "amount": allocation_amount, "show": allocation_show},
        )
        messages.success(request, "Show allocation removed. The ledger transaction itself was not changed.")
        return redirect("finance_transaction_allocations", pk=obj.pk)
    return render(request, "portal/confirm_delete.html", {
        "object": allocation,
        "title": "Remove show allocation",
        "message": "This removes only the reporting allocation. It does not delete or void the underlying payment.",
    })

@login_required
def reimbursement_list(request):
    _require_adult_finance_participant(request.user)
    team = _team(request.user)
    base = ReimbursementRequest.objects.filter(team=team).select_related(
        "season", "show", "requested_by", "category"
    )

    is_admin = request.user.is_superuser or (
        hasattr(request.user, "profile") and request.user.profile.role == UserProfile.Role.ADMIN
    )
    finance_season_ids = _finance_season_ids(request.user, team)
    can_review_any = is_admin or bool(finance_season_ids)

    if is_admin:
        qs = base.filter(Q(status__gt="") & (Q(status__in=[
            ReimbursementRequest.Status.SUBMITTED,
            ReimbursementRequest.Status.APPROVED,
            ReimbursementRequest.Status.REJECTED,
            ReimbursementRequest.Status.PAID,
        ]) | Q(requested_by=request.user)))
    elif finance_season_ids:
        qs = base.filter(
            Q(requested_by=request.user)
            | (
                Q(season_id__in=finance_season_ids)
                & ~Q(status=ReimbursementRequest.Status.DRAFT)
            )
        ).distinct()
    else:
        qs = base.filter(requested_by=request.user)

    selected_status = request.GET.get("status", "")
    selected_season = request.GET.get("season", "")
    selected_show = request.GET.get("show", "")
    q = request.GET.get("q", "").strip()

    valid_statuses = {x[0] for x in ReimbursementRequest.Status.choices}
    if selected_status in valid_statuses:
        qs = qs.filter(status=selected_status)
    else:
        selected_status = ""
    if selected_season.isdigit():
        qs = qs.filter(season_id=int(selected_season))
    else:
        selected_season = ""
    if selected_show.isdigit():
        qs = qs.filter(show_id=int(selected_show))
    else:
        selected_show = ""
    if q:
        qs = qs.filter(
            Q(description__icontains=q)
            | Q(payee_name__icontains=q)
            | Q(category__name__icontains=q)
            | Q(show__name__icontains=q)
            | Q(requested_by__first_name__icontains=q)
            | Q(requested_by__last_name__icontains=q)
        )

    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))
    params = {
        "status": selected_status, "season": selected_season,
        "show": selected_show, "q": q,
    }
    return render(request, "portal/reimbursement_list.html", {
        "requests": page.object_list, "page_obj": page, "can_finance": can_review_any,
        "selected_status": selected_status, "selected_season": selected_season,
        "selected_show": selected_show, "q": q,
        "filter_query": urlencode({k: v for k, v in params.items() if v}),
        "statuses": ReimbursementRequest.Status.choices,
        "seasons": Season.objects.filter(team=team).order_by("-start_date"),
        "shows": Show.objects.filter(team=team).order_by("-show_date", "name"),
    })

@login_required
def reimbursement_create(request):
    _require_adult_finance_participant(request.user)
    team = _team(request.user)
    form = ReimbursementRequestForm(
        request.POST or None, request.FILES or None, team=team, user=request.user
    )
    if form.is_valid():
        obj = form.save(commit=False)
        obj.team = team
        obj.requested_by = request.user
        action = request.POST.get("action", "submit")
        if action == "draft":
            obj.status = ReimbursementRequest.Status.DRAFT
            obj.submitted_at = None
        else:
            obj.status = ReimbursementRequest.Status.SUBMITTED
            obj.submitted_at = timezone.now()
        obj.full_clean()
        obj.save()
        _audit_event(
            team=team, actor=request.user,
            action=AuditEvent.Action.CREATED if obj.status == ReimbursementRequest.Status.DRAFT else AuditEvent.Action.SUBMITTED,
            obj=obj, season=obj.season,
            summary=(
                f"Saved reimbursement draft: {obj.description}"
                if obj.status == ReimbursementRequest.Status.DRAFT
                else f"Submitted reimbursement: {obj.description}"
            ),
            details={"amount": obj.amount, "show": obj.show or "", "category": obj.category},
        )
        messages.success(
            request,
            "Reimbursement saved as a draft." if obj.status == ReimbursementRequest.Status.DRAFT
            else "Reimbursement request submitted for Treasurer review."
        )
        return redirect("reimbursement_list")
    return render(request, "portal/reimbursement_form.html", {
        "form": form, "title": "New reimbursement", "eyebrow": "TEAM EXPENSE"
    })

@login_required
def reimbursement_edit(request, pk):
    _require_adult_finance_participant(request.user)
    team = _team(request.user)
    obj = get_object_or_404(ReimbursementRequest, pk=pk, team=team, requested_by=request.user)
    if obj.status != ReimbursementRequest.Status.DRAFT:
        messages.error(request, "Only draft reimbursements can be edited by the submitter.")
        return redirect("reimbursement_list")

    form = ReimbursementRequestForm(
        request.POST or None, request.FILES or None, instance=obj, team=team, user=request.user
    )
    if form.is_valid():
        item = form.save(commit=False)
        action = request.POST.get("action", "draft")
        if action == "submit":
            item.status = ReimbursementRequest.Status.SUBMITTED
            item.submitted_at = timezone.now()
        else:
            item.status = ReimbursementRequest.Status.DRAFT
            item.submitted_at = None
        item.full_clean()
        item.save()
        _audit_event(
            team=team, actor=request.user,
            action=AuditEvent.Action.SUBMITTED if item.status == ReimbursementRequest.Status.SUBMITTED else AuditEvent.Action.UPDATED,
            obj=item, season=item.season,
            summary=(
                f"Submitted reimbursement: {item.description}"
                if item.status == ReimbursementRequest.Status.SUBMITTED
                else f"Updated reimbursement draft: {item.description}"
            ),
            details={"amount": item.amount, "show": item.show or "", "category": item.category},
        )
        messages.success(
            request,
            "Reimbursement submitted for Treasurer review."
            if item.status == ReimbursementRequest.Status.SUBMITTED
            else "Reimbursement draft updated."
        )
        return redirect("reimbursement_list")
    return render(request, "portal/reimbursement_form.html", {
        "form": form, "title": "Edit reimbursement draft", "eyebrow": "TEAM EXPENSE"
    })

@login_required
@require_POST
def reimbursement_submit(request, pk):
    _require_adult_finance_participant(request.user)
    team = _team(request.user)
    obj = get_object_or_404(ReimbursementRequest, pk=pk, team=team, requested_by=request.user)
    if obj.status != ReimbursementRequest.Status.DRAFT:
        messages.error(request, "Only draft reimbursements can be submitted.")
        return redirect("reimbursement_list")
    obj.status = ReimbursementRequest.Status.SUBMITTED
    obj.submitted_at = timezone.now()
    obj.full_clean()
    obj.save(update_fields=["status", "submitted_at"])
    _audit_event(
        team=team, actor=request.user, action=AuditEvent.Action.SUBMITTED, obj=obj,
        season=obj.season, summary=f"Submitted reimbursement: {obj.description}",
        details={"amount": obj.amount},
    )
    messages.success(request, "Reimbursement submitted for Treasurer review.")
    return redirect("reimbursement_list")

@login_required
def reimbursement_review(request, pk):
    _require_adult_finance_participant(request.user)
    team = _team(request.user)
    obj = get_object_or_404(ReimbursementRequest, pk=pk, team=team)
    _require_finance(request.user, obj.season)
    if obj.status == ReimbursementRequest.Status.DRAFT:
        raise PermissionDenied("Draft reimbursements are private to the submitter.")

    previous_status = obj.status
    form = ReimbursementReviewForm(request.POST or None, instance=obj, team=team)
    if form.is_valid():
        item = form.save(commit=False)
        allowed = {
            ReimbursementRequest.Status.SUBMITTED: {
                ReimbursementRequest.Status.SUBMITTED,
                ReimbursementRequest.Status.APPROVED,
                ReimbursementRequest.Status.REJECTED,
            },
            ReimbursementRequest.Status.APPROVED: {
                ReimbursementRequest.Status.APPROVED,
                ReimbursementRequest.Status.REJECTED,
                ReimbursementRequest.Status.PAID,
            },
            ReimbursementRequest.Status.REJECTED: {
                ReimbursementRequest.Status.REJECTED,
                ReimbursementRequest.Status.SUBMITTED,
            },
            ReimbursementRequest.Status.PAID: {ReimbursementRequest.Status.PAID},
        }
        if item.status not in allowed.get(previous_status, {item.status}):
            form.add_error(
                "status",
                f"Cannot change reimbursement from {obj.get_status_display()} to {item.get_status_display()}.",
            )
        if form.errors:
            return render(request, "portal/form.html", {
                "form": form, "title": f"Review reimbursement · {obj.payee_name}", "eyebrow": "TREASURER"
            })

        item.reviewed_by = request.user
        item.reviewed_at = timezone.now()
        item.full_clean()

        if item.status == ReimbursementRequest.Status.PAID:
            if item.financial_transaction_id:
                tx = item.financial_transaction
                tx.transaction_date = item.paid_date
                tx.account = item.payment_account
                tx.category = item.category
                tx.amount = item.amount
                tx.payee = item.payee_name
                tx.description = item.description
                tx.show = item.show
                tx.show_finance_scope = item.show_finance_scope
                tx.updated_by = request.user
                tx.full_clean()
                tx.save()
            else:
                tx = FinancialTransaction(
                    team=item.team, season=item.season, transaction_date=item.paid_date,
                    kind=FinancialTransaction.Kind.EXPENSE, account=item.payment_account,
                    category=item.category, amount=item.amount, payee=item.payee_name,
                    description=item.description, show=item.show,
                    show_finance_scope=item.show_finance_scope,
                    notes=f"Reimbursement request #{item.pk}",
                    created_by=request.user, updated_by=request.user,
                )
                tx.full_clean()
                tx.save()
                item.financial_transaction = tx

        item.save()

        if item.status == ReimbursementRequest.Status.PAID and item.financial_transaction_id:
            if item.show_id and item.show_finance_scope:
                allocation_note = f"From reimbursement request #{item.pk}"
                reimbursement_allocation = ShowTransactionAllocation.objects.filter(
                    transaction=item.financial_transaction,
                    notes=allocation_note,
                ).first()
                if reimbursement_allocation:
                    reimbursement_allocation.show = item.show
                    reimbursement_allocation.scope = item.show_finance_scope
                    reimbursement_allocation.amount = item.amount
                    reimbursement_allocation.full_clean()
                    reimbursement_allocation.save()
                else:
                    reimbursement_allocation = ShowTransactionAllocation(
                        transaction=item.financial_transaction,
                        show=item.show,
                        scope=item.show_finance_scope,
                        amount=item.amount,
                        notes=allocation_note,
                    )
                    reimbursement_allocation.full_clean()
                    reimbursement_allocation.save()

        action_map = {
            ReimbursementRequest.Status.SUBMITTED: AuditEvent.Action.SUBMITTED,
            ReimbursementRequest.Status.APPROVED: AuditEvent.Action.APPROVED,
            ReimbursementRequest.Status.REJECTED: AuditEvent.Action.REJECTED,
            ReimbursementRequest.Status.PAID: AuditEvent.Action.PAID,
        }
        _audit_event(
            team=team, actor=request.user, action=action_map[item.status], obj=item,
            season=item.season,
            summary=f"Reimbursement {item.get_status_display().lower()}: {item.description}",
            details={
                "from_status": previous_status, "to_status": item.status,
                "amount": item.amount, "reviewer": request.user,
                "ledger_transaction": item.financial_transaction_id or "",
            },
        )
        messages.success(request, "Reimbursement request updated.")
        return redirect("reimbursement_list")
    return render(request, "portal/form.html", {
        "form": form, "title": f"Review reimbursement · {obj.payee_name}", "eyebrow": "TREASURER"
    })

@login_required
def reimbursement_receipt(request, pk):
    _require_adult_finance_participant(request.user)
    team=_team(request.user); obj=get_object_or_404(ReimbursementRequest,pk=pk,team=team)
    season=obj.season
    if obj.requested_by_id != request.user.id and not _can_finance(request.user,season):
        raise PermissionDenied
    if not obj.receipt: raise Http404("No receipt attached.")
    return FileResponse(obj.receipt.open("rb"),as_attachment=True,filename=Path(obj.receipt.name).name)
