"""v3.2.3 compatibility refinements for rider roster, profile, and family linking."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from portal.forms import GuardianContactForm
from portal.model_modules.people import LegacyPersonLink, OrganizationRoleAssignment, Person, PersonRelationship
from portal.models import GuardianContact, Rider, RiderGuardian, SeasonMembership
from portal.people_compat import (
    end_rider_guardian_relationship,
    ensure_guardian_contact_for_person,
    ensure_guardian_person,
    ensure_rider_person,
    sync_rider_guardian_link,
)
from portal.people_services import can_view_private_rider
from portal.platform import active_period_for_organization, organization_for_view_user
from portal.public_profiles import public_profiles_for_riders
from portal.view_modules.common import (
    _can_manage, _require_manage, _selected_team,
    _volunteer_progress_rows,
)
from portal.view_modules.roster_helpers import _team_roster


def _attach_public_profiles(riders):
    rows = list(riders)
    profiles = public_profiles_for_riders(rows)
    for rider in rows:
        rider.public_profile = profiles.get(rider.pk)
    return rows


@login_required
def rider_list(request):
    team = organization_for_view_user(request.user)
    season = active_period_for_organization(team)
    qs = _team_roster(request.user, team)
    if season:
        # The card template reads this compatibility attribute from Rider.
        # Populate it from the Person-native path when available, then fill
        # legacy-only memberships during the v3.9 transition.
        qs = qs.prefetch_related(
            "iea_participant_bridge__season_memberships__classes",
            Prefetch(
                "memberships",
                queryset=SeasonMembership.objects.filter(season=season).select_related(
                    "season", "iea_participant__person"
                ).prefetch_related("classes"),
                to_attr="active_season_memberships",
            ),
        )
    selected = _selected_team(request)
    if season:
        # Prefer Person-native season participation, while retaining legacy-only
        # rows until the v3.9 compatibility closeout.
        futures = _attach_public_profiles(qs.filter(
            Q(iea_participant_bridge__season_memberships__season=season, iea_participant_bridge__season_memberships__team_level=SeasonMembership.TeamLevel.FUTURES)
            | Q(memberships__season=season, memberships__iea_participant__isnull=True, memberships__team_level=SeasonMembership.TeamLevel.FUTURES)
        ).distinct())
        upper = _attach_public_profiles(qs.filter(
            Q(iea_participant_bridge__season_memberships__season=season, iea_participant_bridge__season_memberships__team_level=SeasonMembership.TeamLevel.UPPER)
            | Q(memberships__season=season, memberships__iea_participant__isnull=True, memberships__team_level=SeasonMembership.TeamLevel.UPPER)
        ).distinct())
        assigned_ids = SeasonMembership.objects.filter(season=season).values_list("rider_id", flat=True)
        unassigned = _attach_public_profiles(qs.exclude(pk__in=assigned_ids).distinct())
    else:
        futures = []; upper = []; unassigned = _attach_public_profiles(qs)
    riders = _attach_public_profiles(qs)
    return render(request, "portal/rider_list.html", {
        "riders": riders, "futures": futures, "upper": upper, "unassigned": unassigned,
        "season": season, "can_manage": _can_manage(request.user), "selected_team": selected,
    })


def _canonical_family_rows(rider):
    """Return active parent/guardian relationships from People for profile display.

    Legacy records are attached only as compatibility action targets. They are
    not the source of the displayed name, contact data, relationship label, or
    primary-contact state.
    """
    rider_bridge = LegacyPersonLink.objects.filter(rider=rider).select_related("person").first()
    if not rider_bridge:
        return []
    relationships = PersonRelationship.objects.filter(
        to_person=rider_bridge.person,
        relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        active=True,
        from_person__active=True,
    ).select_related("from_person", "from_person__user", "from_person__legacy_identity").order_by(
        "-primary_contact", "from_person__last_name", "from_person__first_name"
    )
    rows = []
    for relationship in relationships:
        person = relationship.from_person
        guardian = None
        legacy_link = None
        try:
            guardian = person.legacy_identity.guardian
        except (LegacyPersonLink.DoesNotExist, AttributeError):
            guardian = None
        if guardian:
            legacy_link = RiderGuardian.objects.filter(rider=rider, guardian=guardian).first()
        rows.append({
            "relationship": relationship,
            "person": person,
            "guardian": guardian,
            "legacy_link": legacy_link,
        })
    return rows


@login_required
def rider_detail(request, pk):
    team = organization_for_view_user(request.user)
    rider = get_object_or_404(Rider, pk=pk, team=team)
    private_view = can_view_private_rider(request.user, rider)
    active_season = active_period_for_organization(team)
    try:
        participant = rider.iea_participant_bridge
    except AttributeError:
        participant = None
    # v3.9 prefers Person-native IEA history when the participant bridge exists.
    # Legacy-only memberships remain visible during the compatibility window so
    # historical data and pre-v3.9 fixtures are not silently dropped.
    if participant:
        memberships = list(
            participant.season_memberships.select_related(
                "season", "iea_participant__person"
            ).prefetch_related("classes")
        )
    else:
        memberships = list(
            rider.memberships.select_related("season").prefetch_related("classes")
        )
    current_membership = next((m for m in memberships if active_season and m.season_id == active_season.id), None)
    historical_memberships = [m for m in memberships if not active_season or m.season_id != active_season.id]
    historical_memberships.sort(key=lambda m: (m.season.start_date, m.season.id), reverse=True)

    entries = rider.show_entries.filter(result__isnull=False)
    if active_season:
        entries = entries.filter(show_class__show__season=active_season)
    season_points = entries.aggregate(total=Sum("result__points"))["total"] or 0

    lesson_history = rider.lesson_attendance.none()
    volunteer_progress = None
    if active_season and private_view:
        lesson_history = rider.lesson_attendance.filter(lesson__season=active_season).select_related("lesson").order_by("-lesson__starts_at")[:10]
        progress_rows = _volunteer_progress_rows(active_season, Rider.objects.filter(pk=rider.pk))
        volunteer_progress = progress_rows[0] if progress_rows else None

    return render(request, "portal/rider_detail.html", {
        "rider": rider, "season_points": season_points, "can_manage": _can_manage(request.user),
        "active_season": active_season, "current_membership": current_membership,
        "historical_memberships": historical_memberships, "lesson_history": lesson_history,
        "volunteer_progress": volunteer_progress, "private_view": private_view,
        "family_rows": _canonical_family_rows(rider) if private_view else [],
    })


@login_required
def rider_guardian_add(request, pk):
    """Compatibility entry point: new family members are created through People."""
    _require_manage(request.user); team = organization_for_view_user(request.user)
    get_object_or_404(Rider, pk=pk, team=team)
    messages.info(request, "Parents and guardians are now created as People. Add the Person once, then link the family relationship.")
    return redirect("person_create")


@login_required
def rider_guardian_edit(request, pk, guardian_pk):
    """Compatibility entry point for legacy Rider/Guardian family edit URLs."""
    _require_manage(request.user); team = organization_for_view_user(request.user)
    rider = get_object_or_404(Rider, pk=pk, team=team)
    link = get_object_or_404(
        RiderGuardian.objects.select_related("guardian"),
        rider=rider,
        guardian_id=guardian_pk,
        guardian__team=team,
    )
    rider_person = ensure_rider_person(rider)
    guardian_person = ensure_guardian_person(link.guardian)
    relationship = PersonRelationship.objects.filter(
        from_person=guardian_person,
        to_person=rider_person,
        relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        active=True,
    ).first()
    if relationship is None:
        relationship = sync_rider_guardian_link(link)
    messages.info(request, "Family relationships are now managed on the Person record.")
    return redirect(
        "person_relationship_edit",
        pk=guardian_person.pk,
        relationship_pk=relationship.pk,
    )

def _family_link_candidates(team, rider_person, linked_person_ids):
    """Return existing People plus unmigrated login accounts as one simple picker."""
    rows = []
    people = Person.objects.filter(team=team, active=True).exclude(pk=rider_person.pk).exclude(pk__in=linked_person_ids).select_related("user", "user__profile").order_by("last_name", "first_name")
    for person in people:
        role = person.user.profile.get_role_display() if person.user_id and hasattr(person.user, "profile") else "Person"
        rows.append({"value": f"person:{person.pk}", "name": person.display_name, "email": person.email or (person.user.email if person.user_id else ""), "role": role, "has_login": bool(person.user_id)})

    users = User.objects.filter(profile__team=team, is_active=True, arena_person__isnull=True).select_related("profile").order_by("last_name", "first_name", "username")
    for user in users:
        name = user.get_full_name().strip() or user.username
        rows.append({"value": f"user:{user.pk}", "name": name, "email": user.email, "role": user.profile.get_role_display(), "has_login": True})
    return rows


def _person_for_family_selection(selection, team):
    """Resolve a People record or migrate an existing organization login on demand."""
    try:
        kind, raw_id = selection.split(":", 1)
        object_id = int(raw_id)
    except (ValueError, AttributeError):
        raise ValidationError("Choose an existing person or login account.")

    if kind == "person":
        return get_object_or_404(Person, pk=object_id, team=team, active=True)
    if kind != "user":
        raise ValidationError("Choose an existing person or login account.")

    user = get_object_or_404(User.objects.select_related("profile"), pk=object_id, profile__team=team, is_active=True)
    try:
        return user.arena_person
    except Person.DoesNotExist:
        return Person.objects.create(
            team=team,
            user=user,
            first_name=user.first_name or user.username,
            last_name=user.last_name,
            email=user.email,
            active=True,
        )


@login_required
def rider_guardian_link(request, rider_pk):
    _require_manage(request.user); team = organization_for_view_user(request.user)
    rider = get_object_or_404(Rider, pk=rider_pk, team=team); rider_person = ensure_rider_person(rider)
    linked_person_ids = set(PersonRelationship.objects.filter(
        to_person=rider_person,
        relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        active=True,
    ).values_list("from_person_id", flat=True))
    candidates = _family_link_candidates(team, rider_person, linked_person_ids)
    if request.method == "POST":
        selection = request.POST.get("person")
        if not selection:
            messages.error(request, "Choose an existing person or login account."); return redirect("rider_guardian_link", rider_pk=rider.pk)
        relationship = (request.POST.get("relationship") or "Parent/Guardian").strip(); primary_contact = request.POST.get("primary_contact") == "on"
        try:
            with transaction.atomic():
                parent_person = _person_for_family_selection(selection, team)
                if parent_person.pk == rider_person.pk:
                    raise ValidationError("A rider cannot be their own parent/guardian relationship.")
                relationship_obj, _created = PersonRelationship.objects.get_or_create(
                    from_person=parent_person,
                    to_person=rider_person,
                    relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
                    defaults={"label": relationship, "primary_contact": primary_contact, "active": True},
                )
                relationship_obj.label = relationship
                relationship_obj.primary_contact = primary_contact
                relationship_obj.active = True
                relationship_obj.end_date = None
                relationship_obj.full_clean()
                relationship_obj.save(update_fields=["label", "primary_contact", "active", "end_date"])
                OrganizationRoleAssignment.objects.get_or_create(
                    team=team,
                    person=parent_person,
                    role=OrganizationRoleAssignment.Role.PARENT_GUARDIAN,
                    active=True,
                )
        except ValidationError as exc:
            messages.error(request, str(exc)); return redirect("rider_guardian_link", rider_pk=rider.pk)
        messages.success(request, f"{parent_person.display_name} linked to {rider_person} as {relationship}."); return redirect("rider_detail", pk=rider.pk)
    return render(request, "portal/rider_guardian_link.html", {"rider": rider, "people": candidates})


@login_required
@require_POST
def rider_guardian_unlink(request, rider_pk, link_pk):
    """Compatibility endpoint for stale legacy unlink submissions.

    Canonical family relationships are Person-native. This endpoint only accepts
    an existing legacy RiderGuardian link, ends the corresponding canonical
    relationship, and removes the compatibility row.
    """
    _require_manage(request.user); team = organization_for_view_user(request.user)
    rider = get_object_or_404(Rider, pk=rider_pk, team=team)
    link = get_object_or_404(
        RiderGuardian.objects.select_related("guardian"),
        pk=link_pk,
        rider=rider,
        guardian__team=team,
    )
    guardian = link.guardian
    rider_person = ensure_rider_person(rider)
    guardian_person = ensure_guardian_person(guardian)
    relationship = PersonRelationship.objects.filter(
        from_person=guardian_person,
        to_person=rider_person,
        relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        active=True,
    ).first()
    with transaction.atomic():
        if relationship is not None:
            relationship.active = False
            relationship.end_date = timezone.localdate()
            relationship.save(update_fields=["active", "end_date"])
        link.delete()
        if guardian.user_id:
            still_linked = RiderGuardian.objects.filter(
                rider=rider,
                guardian__user_id=guardian.user_id,
            ).exists()
            if not still_linked:
                rider.guardians.remove(guardian.user)
    messages.success(
        request,
        f"{guardian_person.display_name} unlinked from {rider_person.display_name}; both Person records were kept.",
    )
    return redirect("rider_detail", pk=rider.pk)
