from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .course_forms import ShowCourseForm
from .course_models import ShowCourse
from .models import Show
from .view_modules.common import _can_manage, _ensure_season_open, _is_show_lead, _team


def _can_view_courses(user, show):
    return _can_manage(user) or _is_show_lead(user, show)


def _require_course_view(user, show):
    if not _can_view_courses(user, show):
        raise PermissionDenied


def _require_course_manage(user):
    # Course creation/editing contains private coaching strategy, so Show Leads are
    # operational viewers in v2.1.4 while Coaches/Admins remain the editors.
    if not _can_manage(user):
        raise PermissionDenied


@login_required
def show_courses(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season", "team"), pk=show_pk, team=team)
    _require_course_view(request.user, show)
    courses = show.courses.prefetch_related("show_classes__season_class").all()
    return render(request, "portal/show_courses.html", {
        "show": show,
        "courses": courses,
        "can_manage_courses": _can_manage(request.user),
    })


@login_required
def show_course_add(request, show_pk):
    _require_course_manage(request.user)
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=show_pk, team=team)
    _ensure_season_open(show.season)
    form = ShowCourseForm(request.POST or None, request.FILES or None, show=show)
    if form.is_valid():
        course = form.save(commit=False)
        course.show = show
        course.created_by = request.user
        course.updated_by = request.user
        course.save()
        form.save_m2m()
        messages.success(request, "Course information added.")
        return redirect("show_courses", show_pk=show.pk)
    return render(request, "portal/show_course_form.html", {"show": show, "form": form, "title": "Add course information"})


@login_required
def show_course_edit(request, show_pk, course_pk):
    _require_course_manage(request.user)
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=show_pk, team=team)
    _ensure_season_open(show.season)
    course = get_object_or_404(ShowCourse, pk=course_pk, show=show)
    form = ShowCourseForm(request.POST or None, request.FILES or None, instance=course, show=show)
    if form.is_valid():
        course = form.save(commit=False)
        course.updated_by = request.user
        course.save()
        form.save_m2m()
        messages.success(request, "Course information updated.")
        return redirect("show_courses", show_pk=show.pk)
    return render(request, "portal/show_course_form.html", {"show": show, "course": course, "form": form, "title": "Edit course information"})


@login_required
@require_POST
def show_course_remove(request, show_pk, course_pk):
    _require_course_manage(request.user)
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=show_pk, team=team)
    _ensure_season_open(show.season)
    course = get_object_or_404(ShowCourse, pk=course_pk, show=show)
    course.delete()
    messages.success(request, "Course information removed.")
    return redirect("show_courses", show_pk=show.pk)
