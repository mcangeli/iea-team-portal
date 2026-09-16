from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..forms_lessons_v340 import LessonProgramForm, LessonSeriesForm
from ..model_modules.lessons import LessonProgram, LessonSeries
from ..platform import organization_for_view_user
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
        form.save()
        messages.success(request, "Lesson series created.")
        return redirect("lesson_program_detail", pk=program.pk)
    return render(request, "portal/form.html", {"form": form, "title": "Create lesson series", "eyebrow": program.name})


@login_required
def lesson_series_edit(request, pk):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    series = get_object_or_404(LessonSeries.objects.select_related("program"), pk=pk, program__team=team)
    form = LessonSeriesForm(request.POST or None, instance=series, program=series.program)
    if form.is_valid():
        form.save()
        messages.success(request, "Lesson series updated. Existing occurrences were not silently moved.")
        return redirect("lesson_program_detail", pk=series.program_id)
    return render(request, "portal/form.html", {"form": form, "title": f"Edit {series.name}", "eyebrow": series.program.name})
