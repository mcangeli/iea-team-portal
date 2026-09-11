from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from ..horse_forms import HorseCogginsForm, HorseForm, HorseSeasonProfileForm
from ..horse_models import Horse, HorseCogginsRecord, HorseSeasonProfile
from ..models import AuditEvent, Season
from .common import _audit_event, _can_manage, _team


def _horse_for_user(user, pk):
    team = _team(user)
    return get_object_or_404(Horse, pk=pk, team=team)


def _require_horse_manage(user):
    if not _can_manage(user):
        raise PermissionDenied


@login_required
def horse_list(request):
    team = _team(request.user)
    can_manage = _can_manage(request.user)
    horses = Horse.objects.filter(team=team).prefetch_related("coggins_records", "season_profiles__season")

    status = request.GET.get("status", "active")
    if status == "inactive" and can_manage:
        horses = horses.filter(active=False)
    elif status == "all" and can_manage:
        pass
    else:
        horses = horses.filter(active=True)

    rows = []
    for horse in horses:
        coggins = horse.latest_coggins
        rows.append({
            "horse": horse,
            "coggins": coggins,
            "coggins_status": coggins.status if coggins else "missing",
        })

    return render(request, "portal/horse_list.html", {
        "rows": rows,
        "can_manage": can_manage,
        "status_filter": status,
    })


@login_required
def horse_detail(request, pk):
    horse = _horse_for_user(request.user, pk)
    can_manage = _can_manage(request.user)
    if not horse.active and not can_manage:
        raise PermissionDenied
    coggins_records = horse.coggins_records.all()
    season_profiles = horse.season_profiles.select_related("season").prefetch_related("eligible_classes")
    return render(request, "portal/horse_detail.html", {
        "horse": horse,
        "can_manage": can_manage,
        "coggins_records": coggins_records,
        "season_profiles": season_profiles,
        "latest_coggins": horse.latest_coggins,
    })


@login_required
def horse_create(request):
    _require_horse_manage(request.user)
    team = _team(request.user)
    if request.method == "POST":
        form = HorseForm(request.POST, request.FILES, team=team)
        if form.is_valid():
            horse = form.save(commit=False)
            horse.team = team
            horse.save()
            _audit_event(
                team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=horse,
                summary=f"Created horse {horse.display_name}",
            )
            messages.success(request, f"{horse.display_name} was added to the horse registry.")
            return redirect("horse_detail", pk=horse.pk)
    else:
        form = HorseForm(team=team)
    return render(request, "portal/horse_form.html", {"form": form, "title": "Add horse"})


@login_required
def horse_edit(request, pk):
    _require_horse_manage(request.user)
    horse = _horse_for_user(request.user, pk)
    if request.method == "POST":
        form = HorseForm(request.POST, request.FILES, instance=horse, team=horse.team)
        if form.is_valid():
            horse = form.save()
            _audit_event(
                team=horse.team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=horse,
                summary=f"Updated horse {horse.display_name}",
            )
            messages.success(request, f"{horse.display_name} was updated.")
            return redirect("horse_detail", pk=horse.pk)
    else:
        form = HorseForm(instance=horse, team=horse.team)
    return render(request, "portal/horse_form.html", {
        "form": form, "horse": horse, "title": f"Edit {horse.display_name}",
    })


@login_required
def horse_coggins_add(request, horse_pk):
    _require_horse_manage(request.user)
    horse = _horse_for_user(request.user, horse_pk)
    if request.method == "POST":
        form = HorseCogginsForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save(commit=False)
            record.horse = horse
            record.full_clean()
            record.save()
            _audit_event(
                team=horse.team, actor=request.user, action=AuditEvent.Action.CREATED, obj=record,
                summary=f"Added Coggins record for {horse.display_name}",
            )
            messages.success(request, "Coggins record added.")
            return redirect("horse_detail", pk=horse.pk)
    else:
        form = HorseCogginsForm()
    return render(request, "portal/horse_coggins_form.html", {
        "form": form, "horse": horse, "title": f"Add Coggins — {horse.display_name}",
    })


@login_required
def horse_coggins_edit(request, horse_pk, pk):
    _require_horse_manage(request.user)
    horse = _horse_for_user(request.user, horse_pk)
    record = get_object_or_404(HorseCogginsRecord, pk=pk, horse=horse)
    if request.method == "POST":
        form = HorseCogginsForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            record = form.save()
            _audit_event(
                team=horse.team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=record,
                summary=f"Updated Coggins record for {horse.display_name}",
            )
            messages.success(request, "Coggins record updated.")
            return redirect("horse_detail", pk=horse.pk)
    else:
        form = HorseCogginsForm(instance=record)
    return render(request, "portal/horse_coggins_form.html", {
        "form": form, "horse": horse, "record": record,
        "title": f"Edit Coggins — {horse.display_name}",
    })


@login_required
def horse_season_profile(request, horse_pk, season_pk=None):
    _require_horse_manage(request.user)
    horse = _horse_for_user(request.user, horse_pk)
    team = horse.team

    season = None
    if season_pk:
        season = get_object_or_404(Season, pk=season_pk, team=team)
    elif request.method == "POST" and request.POST.get("season"):
        season = get_object_or_404(Season, pk=request.POST.get("season"), team=team)
    else:
        season = Season.objects.filter(team=team, is_active=True).order_by("-start_date").first()

    profile = None
    if season:
        profile = HorseSeasonProfile.objects.filter(horse=horse, season=season).first()

    if request.method == "POST":
        was_existing = bool(profile and profile.pk)
        form = HorseSeasonProfileForm(request.POST, instance=profile, team=team, horse=horse)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.horse = horse
            profile.save()
            form.save_m2m()
            _audit_event(
                team=team, actor=request.user,
                action=AuditEvent.Action.UPDATED if was_existing else AuditEvent.Action.CREATED,
                obj=profile, season=profile.season,
                summary=f"Updated season eligibility for {horse.display_name}",
            )
            messages.success(request, f"Season eligibility saved for {profile.season.name}.")
            return redirect("horse_detail", pk=horse.pk)
    else:
        form = HorseSeasonProfileForm(instance=profile, team=team, horse=horse, initial={"season": season})

    return render(request, "portal/horse_season_profile_form.html", {
        "form": form, "horse": horse, "season": season, "profile": profile,
        "title": f"Season eligibility — {horse.display_name}",
    })
