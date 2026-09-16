from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..forms_lessons_v340 import LessonEnrollmentForm, LessonProgramForm, LessonSeriesForm
from ..model_modules.lessons import LessonEnrollment, LessonOccurrence, LessonProgram, LessonSeries
from ..platform import organization_for_view_user
from ..services.lesson_operations import materialize_lesson_series
from .common import _can_manage, _require_manage


@login_required
def lesson_program_list(request):
    team = organization_for_view_user(request.user)
    programs = LessonProgram.objects.filter(team=team).prefetch_related("series").order_by("name")
    return render(request, "portal/lesson_program_list.html", {
        "programs": programs,
        "can_manage": _can_manage(request.user),
    })


@login_required
def lesson_program_detail(request, pk):
    team = organization_for_view_user(request.user)
    program = get_object_or_404(
        LessonProgram.objects.prefetch_related("series__enrollments", "series__occurrences"),
        pk=pk,
        team=team,
    )
    return render(request, "portal/lesson_program_detail.html", {
        "program": program,
        "can_manage": _can_manage(request.user),
    })


@login_required
def lesson_program_create(request):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    form = LessonProgramForm(request.POST or None, team=team)
    if form.is_valid():
        program = form.save()
        messages.success(request, "Lesson program created.")
        return redirect("lesson_program_detail", pk=program.pk)
    return render(request, "portal/form.html", {"form": form, "title": "Create lesson program", "eyebrow": "LESSON PROGRAM"})


@login_required
def lesson_program_edit(request, pk):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    program = get_object_or_404(LessonProgram, pk=pk, team=team)
    form = LessonProgramForm(request.POST or None, instance=program, team=team)
    if form.is_valid():
        form.save()
        messages.success(request, "Lesson program updated.")
        return redirect("lesson_program_detail", pk=program.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"Edit {program.name}", "eyebrow": "LESSON PROGRAM"})


@login_required
def lesson_series_create(request, program_pk):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    program = get_object_or_404(LessonProgram, pk=program_pk, team=team)
    form = LessonSeriesForm(request.POST or None, program=program)
    if form.is_valid():
        series = form.save()
        messages.success(request, "Lesson series created.")
        return redirect("lesson_series_detail", pk=series.pk)
    return render(request, "portal/form.html", {"form": form, "title": "Create lesson series", "eyebrow": program.name})


@login_required
def lesson_series_detail(request, pk):
    team = organization_for_view_user(request.user)
    series = get_object_or_404(
        LessonSeries.objects.select_related("program", "instructor").prefetch_related(
            "enrollments__person", "occurrences__attendance_records", "occurrences__assignments"
        ),
        pk=pk,
        program__team=team,
    )
    occurrences = series.occurrences.order_by("starts_at")
    now = timezone.now()
    return render(request, "portal/lesson_series_detail.html", {
        "series": series,
        "enrollments": series.enrollments.select_related("person").order_by("person__last_name", "person__first_name"),
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
    enrollment = get_object_or_404(
        LessonEnrollment.objects.select_related("series__program", "person"), pk=pk, series__program__team=team
    )
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
    messages.success(
        request,
        f"Schedule ready: {len(result.generation.created)} occurrence(s) created and {len(result.prepared)} prepared.",
    )
    return redirect("lesson_series_detail", pk=series.pk)


@login_required
def lesson_occurrence_detail(request, pk):
    team = organization_for_view_user(request.user)
    occurrence = get_object_or_404(
        LessonOccurrence.objects.select_related("series__program", "instructor").prefetch_related(
            "attendance_records__person", "assignments__person", "assignments__horse"
        ),
        pk=pk,
        series__program__team=team,
    )
    return render(request, "portal/lesson_occurrence_detail.html", {
        "occurrence": occurrence,
        "attendance": occurrence.attendance_records.select_related("person").order_by("person__last_name", "person__first_name"),
        "assignments": occurrence.assignments.select_related("person", "horse").order_by("role", "person__last_name"),
        "can_manage": _can_manage(request.user),
    })
