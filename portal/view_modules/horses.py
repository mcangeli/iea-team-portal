from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..horse_forms import HorseCogginsForm, HorseForm, HorseSeasonProfileForm, HorseShowAssignmentForm, HorseShowAwardForm
from ..horse_models import Horse, HorseCogginsRecord, HorseSeasonProfile, HorseShowAssignment, HorseShowAward
from ..models import AuditEvent, Season, Show
from ..show_readiness_views import _can_manage_show_horses, _require_show_horse_manage
from .common import _audit_event, _can_manage, _ensure_season_open, _team


def _horse_for_user(user, pk):
    team = _team(user)
    return get_object_or_404(Horse, pk=pk, team=team)


def _require_horse_manage(user):
    if not _can_manage(user):
        raise PermissionDenied


@login_required
def horse_list(request):
    team = _team(request.user); can_manage = _can_manage(request.user)
    horses = Horse.objects.filter(team=team).prefetch_related("coggins_records", "season_profiles__season")
    status = request.GET.get("status", "active")
    if status == "inactive" and can_manage: horses = horses.filter(active=False)
    elif status == "all" and can_manage: pass
    else: horses = horses.filter(active=True)
    rows = []
    for horse in horses:
        coggins = horse.latest_coggins
        rows.append({"horse": horse, "coggins": coggins, "coggins_status": coggins.status if coggins else "missing"})
    return render(request, "portal/horse_list.html", {"rows": rows, "can_manage": can_manage, "status_filter": status})


@login_required
def horse_detail(request, pk):
    horse = _horse_for_user(request.user, pk); can_manage = _can_manage(request.user)
    if not horse.active and not can_manage: raise PermissionDenied
    return render(request, "portal/horse_detail.html", {
        "horse": horse, "can_manage": can_manage,
        "coggins_records": horse.coggins_records.all(),
        "season_profiles": horse.season_profiles.select_related("season").prefetch_related("eligible_classes"),
        "latest_coggins": horse.latest_coggins,
        "show_awards": HorseShowAward.objects.filter(assignment__horse=horse).select_related("show", "assignment").order_by("-show__show_date", "session"),
    })


@login_required
def horse_create(request):
    _require_horse_manage(request.user); team = _team(request.user)
    form = HorseForm(request.POST or None, request.FILES or None, team=team)
    if form.is_valid():
        horse = form.save(commit=False); horse.team = team; horse.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=horse, summary=f"Created horse {horse.display_name}")
        messages.success(request, f"{horse.display_name} was added to the horse registry.")
        return redirect("horse_detail", pk=horse.pk)
    return render(request, "portal/horse_form.html", {"form": form, "title": "Add horse"})


@login_required
def horse_edit(request, pk):
    _require_horse_manage(request.user); horse = _horse_for_user(request.user, pk)
    form = HorseForm(request.POST or None, request.FILES or None, instance=horse, team=horse.team)
    if form.is_valid():
        horse = form.save()
        _audit_event(team=horse.team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=horse, summary=f"Updated horse {horse.display_name}")
        messages.success(request, f"{horse.display_name} was updated.")
        return redirect("horse_detail", pk=horse.pk)
    return render(request, "portal/horse_form.html", {"form": form, "horse": horse, "title": f"Edit {horse.display_name}"})


@login_required
def horse_coggins_add(request, horse_pk):
    _require_horse_manage(request.user); horse = _horse_for_user(request.user, horse_pk)
    form = HorseCogginsForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        record = form.save(commit=False); record.horse = horse; record.full_clean(); record.save()
        _audit_event(team=horse.team, actor=request.user, action=AuditEvent.Action.CREATED, obj=record, summary=f"Added Coggins record for {horse.display_name}")
        messages.success(request, "Coggins record added."); return redirect("horse_detail", pk=horse.pk)
    return render(request, "portal/horse_coggins_form.html", {"form": form, "horse": horse, "title": f"Add Coggins — {horse.display_name}"})


@login_required
def horse_coggins_edit(request, horse_pk, pk):
    _require_horse_manage(request.user); horse = _horse_for_user(request.user, horse_pk)
    record = get_object_or_404(HorseCogginsRecord, pk=pk, horse=horse)
    form = HorseCogginsForm(request.POST or None, request.FILES or None, instance=record)
    if form.is_valid():
        record = form.save()
        _audit_event(team=horse.team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=record, summary=f"Updated Coggins record for {horse.display_name}")
        messages.success(request, "Coggins record updated."); return redirect("horse_detail", pk=horse.pk)
    return render(request, "portal/horse_coggins_form.html", {"form": form, "horse": horse, "record": record, "title": f"Edit Coggins — {horse.display_name}"})


@login_required
def horse_season_profile(request, horse_pk, season_pk=None):
    _require_horse_manage(request.user); horse = _horse_for_user(request.user, horse_pk); team = horse.team
    if season_pk: season = get_object_or_404(Season, pk=season_pk, team=team)
    elif request.method == "POST" and request.POST.get("season"): season = get_object_or_404(Season, pk=request.POST.get("season"), team=team)
    else: season = Season.objects.filter(team=team, is_active=True).order_by("-start_date").first()
    profile = HorseSeasonProfile.objects.filter(horse=horse, season=season).first() if season else None
    was_existing = bool(profile and profile.pk)
    form = HorseSeasonProfileForm(request.POST or None, instance=profile, team=team, horse=horse, initial={"season": season})
    if form.is_valid():
        profile = form.save(commit=False); profile.horse = horse; profile.save(); form.save_m2m()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.UPDATED if was_existing else AuditEvent.Action.CREATED, obj=profile, season=profile.season, summary=f"Updated season eligibility for {horse.display_name}")
        messages.success(request, f"Season eligibility saved for {profile.season.name}."); return redirect("horse_detail", pk=horse.pk)
    return render(request, "portal/horse_season_profile_form.html", {"form": form, "horse": horse, "season": season, "profile": profile, "title": f"Season eligibility — {horse.display_name}"})


@login_required
def show_horses(request, show_pk):
    team = _team(request.user); show = get_object_or_404(Show.objects.select_related("season"), pk=show_pk, team=team)
    assignments = show.horse_assignments.select_related("horse").prefetch_related("show_classes__season_class", "horse__coggins_records", "awards")
    rows = []
    for assignment in assignments:
        coggins = assignment.horse.latest_coggins
        rows.append({"assignment": assignment, "coggins": coggins, "coggins_status": coggins.status if coggins else "missing"})
    awards = show.horse_awards.select_related("assignment__horse").order_by("session")
    return render(request, "portal/show_horses.html", {
        "show": show,
        "rows": rows,
        "awards": awards,
        "can_manage": _can_manage_show_horses(request.user, show),
        "can_manage_registry": _can_manage(request.user),
    })


@login_required
def show_horse_add(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=show_pk, team=team); _require_show_horse_manage(request.user, show); _ensure_season_open(show.season)
    form = HorseShowAssignmentForm(request.POST or None, show=show)
    if form.is_valid():
        assignment = form.save(commit=False); assignment.show = show; assignment.save(); form.save_m2m()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=assignment, season=show.season, summary=f"Assigned {assignment.horse.display_name} to {show.name}")
        messages.success(request, f"{assignment.horse.display_name} was added to this show."); return redirect("show_horses", show_pk=show.pk)
    return render(request, "portal/show_horse_form.html", {"form": form, "show": show, "title": "Add horse to show"})


@login_required
def show_horse_edit(request, show_pk, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=show_pk, team=team); _require_show_horse_manage(request.user, show); _ensure_season_open(show.season)
    assignment = get_object_or_404(HorseShowAssignment, pk=pk, show=show)
    form = HorseShowAssignmentForm(request.POST or None, instance=assignment, show=show)
    if form.is_valid():
        assignment = form.save(); _audit_event(team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=assignment, season=show.season, summary=f"Updated show assignment for {assignment.horse.display_name}")
        messages.success(request, "Show horse assignment updated."); return redirect("show_horses", show_pk=show.pk)
    return render(request, "portal/show_horse_form.html", {"form": form, "show": show, "assignment": assignment, "title": f"Edit {assignment.horse.display_name}"})


@login_required
@require_POST
def show_horse_remove(request, show_pk, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=show_pk, team=team); _require_show_horse_manage(request.user, show); _ensure_season_open(show.season)
    assignment = get_object_or_404(HorseShowAssignment, pk=pk, show=show); label = assignment.horse.display_name
    _audit_event(team=team, actor=request.user, action=AuditEvent.Action.REMOVED, obj=assignment, season=show.season, summary=f"Removed {label} from {show.name}")
    assignment.delete(); messages.success(request, f"{label} was removed from this show.")
    return redirect("show_horses", show_pk=show.pk)


@login_required
def show_horse_award_add(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=show_pk, team=team); _require_show_horse_manage(request.user, show); _ensure_season_open(show.season)
    form = HorseShowAwardForm(request.POST or None, show=show)
    if form.is_valid():
        award = form.save(commit=False); award.show = show; award.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=award, season=show.season, summary=f"Recorded {award.get_session_display()} Horse of the Day for {award.horse.display_name}")
        messages.success(request, f"{award.get_session_display()} Horse of the Day recorded for {award.horse.display_name}.")
        return redirect("show_horses", show_pk=show.pk)
    return render(request, "portal/show_horse_award_form.html", {"form": form, "show": show, "title": "Record Horse of the Day"})


@login_required
def show_horse_award_edit(request, show_pk, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=show_pk, team=team); _require_show_horse_manage(request.user, show); _ensure_season_open(show.season)
    award = get_object_or_404(HorseShowAward, pk=pk, show=show)
    form = HorseShowAwardForm(request.POST or None, instance=award, show=show)
    if form.is_valid():
        award = form.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=award, season=show.season, summary=f"Updated {award.get_session_display()} Horse of the Day")
        messages.success(request, "Horse of the Day award updated.")
        return redirect("show_horses", show_pk=show.pk)
    return render(request, "portal/show_horse_award_form.html", {"form": form, "show": show, "award": award, "title": "Edit Horse of the Day"})


@login_required
@require_POST
def show_horse_award_remove(request, show_pk, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=show_pk, team=team); _require_show_horse_manage(request.user, show); _ensure_season_open(show.season)
    award = get_object_or_404(HorseShowAward, pk=pk, show=show); label = f"{award.get_session_display()} Horse of the Day — {award.horse.display_name}"
    _audit_event(team=team, actor=request.user, action=AuditEvent.Action.REMOVED, obj=award, season=show.season, summary=f"Removed {label}")
    award.delete(); messages.success(request, "Horse of the Day award removed.")
    return redirect("show_horses", show_pk=show.pk)
