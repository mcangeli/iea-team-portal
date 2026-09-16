from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..forms_lessons_v340 import IEALessonSeriesForm, LessonEnrollmentForm, LessonProgramForm, LessonSeriesForm
from ..model_modules.lessons import IEALessonSeriesContext, LessonEnrollment, LessonOccurrence, LessonProgram, LessonSeries
from ..models import SeasonMembership
from ..platform import active_period_for_organization, organization_for_view_user
from ..services.lesson_operations import materialize_lesson_series
from .common import _can_manage, _require_manage


def _barn_programs(team):
    return LessonProgram.objects.filter(team=team).exclude(series__iea_context__isnull=False).distinct()


@login_required
def lesson_program_list(request):
    team = organization_for_view_user(request.user)
    programs = _barn_programs(team).prefetch_related("series").order_by("name")
    return render(request, "portal/lesson_program_list.html", {"programs": programs, "can_manage": _can_manage(request.user)})


@login_required
def lesson_program_detail(request, pk):
    team = organization_for_view_user(request.user)
    program = get_object_or_404(_barn_programs(team).prefetch_related("series__enrollments", "series__occurrences"), pk=pk)
    barn_series = program.series.filter(iea_context__isnull=True)
    return render(request, "portal/lesson_program_detail.html", {"program": program, "barn_series": barn_series, "can_manage": _can_manage(request.user)})


@login_required
def lesson_program_create(request):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    form = LessonProgramForm(request.POST or None, team=team)
    if form.is_valid():
        program = form.save()
        messages.success(request, "Barn lesson program created.")
        return redirect("lesson_program_detail", pk=program.pk)
    return render(request, "portal/form.html", {"form": form, "title": "Create barn lesson program", "eyebrow": "BARN LESSON PROGRAM"})


@login_required
def lesson_program_edit(request, pk):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    program = get_object_or_404(_barn_programs(team), pk=pk)
    form = LessonProgramForm(request.POST or None, instance=program, team=team)
    if form.is_valid():
        form.save()
        messages.success(request, "Barn lesson program updated.")
        return redirect("lesson_program_detail", pk=program.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"Edit {program.name}", "eyebrow": "BARN LESSON PROGRAM"})


@login_required
def lesson_series_create(request, program_pk):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    program = get_object_or_404(_barn_programs(team), pk=program_pk)
    form = LessonSeriesForm(request.POST or None, program=program)
    if form.is_valid():
        series = form.save()
        messages.success(request, "Barn lesson series created.")
        return redirect("lesson_series_detail", pk=series.pk)
    return render(request, "portal/form.html", {"form": form, "title": "Create barn lesson series", "eyebrow": program.name})


@login_required
def iea_lesson_list(request):
    team = organization_for_view_user(request.user)
    season = active_period_for_organization(team)
    contexts = IEALessonSeriesContext.objects.none()
    if season:
        contexts = IEALessonSeriesContext.objects.filter(season=season).select_related("series__program").order_by("team_level", "series__name")
    return render(request, "portal/iea_lesson_list.html", {
        "season": season,
        "futures_contexts": contexts.filter(team_level=SeasonMembership.TeamLevel.FUTURES),
        "upper_contexts": contexts.filter(team_level=SeasonMembership.TeamLevel.UPPER),
        "can_manage": _can_manage(request.user),
    })


@login_required
def iea_lesson_series_create(request):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    season = active_period_for_organization(team)
    if not season:
        raise PermissionDenied("An active IEA season is required before creating team lessons.")
    program, _ = LessonProgram.objects.get_or_create(team=team, name="IEA Team Lessons", defaults={"description": "IEA team instruction managed by season and team level."})
    form = IEALessonSeriesForm(request.POST or None, program=program, season=season)
    if form.is_valid():
        series = form.save()
        messages.success(request, f"{series.iea_context.get_team_level_display()} lesson series created.")
        return redirect("lesson_series_detail", pk=series.pk)
    return render(request, "portal/form.html", {"form": form, "title": "Create IEA team lesson series", "eyebrow": season.name})


@login_required
def lesson_series_detail(request, pk):
    team = organization_for_view_user(request.user)
    series = get_object_or_404(LessonSeries.objects.select_related("program", "instructor").prefetch_related("enrollments__person", "occurrences__attendance_records", "occurrences__assignments"), pk=pk, program__team=team)
    occurrences = series.occurrences.order_by("starts_at")
    now = timezone.now()
    context = series.iea_context if series.is_iea_series else None
    return render(request, "portal/lesson_series_detail.html", {
        "series": series,
        "iea_context": context,
        "enrollments": series.enrollments.select_related("person").order_by("person__last_name", "person__first_name") if not context else [],
        "upcoming_occurrences": occurrences.filter(starts_at__gte=now),
        "past_occurrences": occurrences.filter(starts_at__lt=now).order_by("-starts_at")[:12],
        "can_manage": _can_manage(request.user),
    })


@login_required
def lesson_series_edit(request, pk):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    series = get_object_or_404(LessonSeries.objects.select_related("program"), pk=pk, program__team=team)
    form = LessonSeriesForm(request.POST or None, instance=series, program=series.program)
    if form.is_valid():
        form.save()
        messages.success(request, "Lesson series updated. Existing occurrences were not silently moved.")
        return redirect("lesson_series_detail", pk=series.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"Edit {series.name}", "eyebrow": series.program.name})


@login_required
def lesson_enrollment_create(request, series_pk):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    series = get_object_or_404(LessonSeries.objects.select_related("program"), pk=series_pk, program__team=team)
    if series.is_iea_series:
        raise PermissionDenied("IEA team lesson rosters are managed by season team membership.")
    form = LessonEnrollmentForm(request.POST or None, series=series)
    if form.is_valid():
        enrollment = form.save()
        messages.success(request, f"{enrollment.person} added to {series.name}.")
        return redirect("lesson_series_detail", pk=series.pk)
    return render(request, "portal/form.html", {"form": form, "title": "Add enrollment", "eyebrow": series.name})


@login_required
def lesson_enrollment_edit(request, pk):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    enrollment = get_object_or_404(LessonEnrollment.objects.select_related("series__program", "person"), pk=pk, series__program__team=team)
    form = LessonEnrollmentForm(request.POST or None, instance=enrollment, series=enrollment.series)
    if form.is_valid():
        form.save()
        messages.success(request, "Lesson enrollment updated.")
        return redirect("lesson_series_detail", pk=enrollment.series_id)
    return render(request, "portal/form.html", {"form": form, "title": f"Edit enrollment · {enrollment.person}", "eyebrow": enrollment.series.name})


@login_required
def lesson_series_generate(request, pk):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    series = get_object_or_404(LessonSeries.objects.select_related("program"), pk=pk, program__team=team)
    if request.method != "POST":
        return redirect("lesson_series_detail", pk=series.pk)
    start_date = max(timezone.localdate(), series.start_date) if series.start_date else timezone.localdate()
    end_date = series.end_date or (start_date + timedelta(weeks=12))
    result = materialize_lesson_series(series, start_date, end_date)
    messages.success(request, f"Schedule ready: {len(result.generation.created)} occurrence(s) created and {len(result.prepared)} prepared.")
    return redirect("lesson_series_detail", pk=series.pk)


@login_required
def lesson_occurrence_detail(request, pk):
    team = organization_for_view_user(request.user)
    occurrence = get_object_or_404(LessonOccurrence.objects.select_related("series__program", "instructor").prefetch_related("attendance_records__person", "assignments__person", "assignments__horse"), pk=pk, series__program__team=team)
    return render(request, "portal/lesson_occurrence_detail.html", {
        "occurrence": occurrence,
        "attendance": occurrence.attendance_records.select_related("person").order_by("person__last_name", "person__first_name"),
        "assignments": occurrence.assignments.select_related("person", "horse").order_by("role", "person__last_name"),
        "can_manage": _can_manage(request.user),
    })
