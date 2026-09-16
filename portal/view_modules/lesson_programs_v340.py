from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..forms_lessons_v340 import IEALessonSeriesForm, LessonAttendanceRecordForm, LessonCancelForm, LessonEnrollmentForm, LessonParticipantAssignmentForm, LessonProgramForm, LessonRescheduleForm, LessonSeriesForm
from ..model_modules.lessons import IEALessonSeriesContext, LessonAssignment, LessonAttendanceRecord, LessonEnrollment, LessonOccurrence, LessonProgram, LessonSeries
from ..models import SeasonMembership
from ..platform import active_period_for_organization, organization_for_view_user
from ..services.lesson_operations import materialize_lesson_series
from ..services.lesson_preparation import prepare_lesson_occurrence
from ..services.lesson_scheduling import cancel_lesson_occurrence, reschedule_lesson_occurrence
from .common import _can_manage, _require_manage


def _barn_programs(team): return LessonProgram.objects.filter(team=team).exclude(series__iea_context__isnull=False).distinct()
def _occurrence_for_team(team, pk): return get_object_or_404(LessonOccurrence.objects.select_related("series__program", "series__iea_context__season", "instructor").prefetch_related("attendance_records__person", "assignments__person", "assignments__horse"), pk=pk, series__program__team=team)

@login_required
def lesson_program_list(request):
    team=organization_for_view_user(request.user); programs=_barn_programs(team).prefetch_related("series").order_by("name")
    return render(request,"portal/lesson_program_list.html",{"programs":programs,"can_manage":_can_manage(request.user)})

@login_required
def lesson_program_detail(request,pk):
    team=organization_for_view_user(request.user); program=get_object_or_404(_barn_programs(team).prefetch_related("series__enrollments","series__occurrences"),pk=pk)
    return render(request,"portal/lesson_program_detail.html",{"program":program,"barn_series":program.series.filter(iea_context__isnull=True),"can_manage":_can_manage(request.user)})

@login_required
def lesson_program_create(request):
    _require_manage(request.user); team=organization_for_view_user(request.user); form=LessonProgramForm(request.POST or None,team=team)
    if form.is_valid():
        program=form.save(); messages.success(request,"Barn lesson program created."); return redirect("lesson_program_detail",pk=program.pk)
    return render(request,"portal/form.html",{"form":form,"title":"Create barn lesson program","eyebrow":"BARN LESSON PROGRAM"})

@login_required
def lesson_program_edit(request,pk):
    _require_manage(request.user); team=organization_for_view_user(request.user); program=get_object_or_404(_barn_programs(team),pk=pk); form=LessonProgramForm(request.POST or None,instance=program,team=team)
    if form.is_valid(): form.save(); messages.success(request,"Barn lesson program updated."); return redirect("lesson_program_detail",pk=program.pk)
    return render(request,"portal/form.html",{"form":form,"title":f"Edit {program.name}","eyebrow":"BARN LESSON PROGRAM"})

@login_required
def lesson_series_create(request,program_pk):
    _require_manage(request.user); team=organization_for_view_user(request.user); program=get_object_or_404(_barn_programs(team),pk=program_pk); form=LessonSeriesForm(request.POST or None,program=program)
    if form.is_valid(): series=form.save(); messages.success(request,"Barn lesson series created."); return redirect("lesson_series_detail",pk=series.pk)
    return render(request,"portal/form.html",{"form":form,"title":"Create barn lesson series","eyebrow":program.name})

@login_required
def iea_lesson_list(request):
    team=organization_for_view_user(request.user); season=active_period_for_organization(team); contexts=IEALessonSeriesContext.objects.none(); legacy_upcoming=[]; legacy_recent=[]
    if season:
        contexts=IEALessonSeriesContext.objects.filter(season=season).select_related("series__program").order_by("team_level","series__name")
        legacy_lessons=season.lessons.select_related("group","coach").prefetch_related("attendance__rider")
        legacy_upcoming=legacy_lessons.filter(starts_at__gte=timezone.now()).order_by("starts_at"); legacy_recent=legacy_lessons.filter(starts_at__lt=timezone.now()).order_by("-starts_at")[:12]
    return render(request,"portal/iea_lesson_list.html",{"season":season,"futures_contexts":contexts.filter(team_level=SeasonMembership.TeamLevel.FUTURES),"upper_contexts":contexts.filter(team_level=SeasonMembership.TeamLevel.UPPER),"legacy_upcoming":legacy_upcoming,"legacy_recent":legacy_recent,"can_manage":_can_manage(request.user)})

@login_required
def iea_lesson_series_create(request):
    _require_manage(request.user); team=organization_for_view_user(request.user); season=active_period_for_organization(team)
    if not season: raise PermissionDenied("An active IEA season is required before creating team lessons.")
    program,_=LessonProgram.objects.get_or_create(team=team,name="IEA Team Lessons",defaults={"description":"IEA team instruction managed by season and team level."}); form=IEALessonSeriesForm(request.POST or None,program=program,season=season)
    if form.is_valid(): series=form.save(); messages.success(request,f"{series.iea_context.get_team_level_display()} lesson series created."); return redirect("lesson_series_detail",pk=series.pk)
    return render(request,"portal/form.html",{"form":form,"title":"Create IEA team lesson series","eyebrow":season.name})

@login_required
def lesson_series_detail(request,pk):
    team=organization_for_view_user(request.user); series=get_object_or_404(LessonSeries.objects.select_related("program","instructor").prefetch_related("enrollments__person","occurrences__attendance_records","occurrences__assignments"),pk=pk,program__team=team); occurrences=series.occurrences.order_by("starts_at"); now=timezone.now(); context=series.iea_context if series.is_iea_series else None
    return render(request,"portal/lesson_series_detail.html",{"series":series,"iea_context":context,"enrollments":series.enrollments.select_related("person").order_by("person__last_name","person__first_name") if not context else [],"upcoming_occurrences":occurrences.filter(starts_at__gte=now),"past_occurrences":occurrences.filter(starts_at__lt=now).order_by("-starts_at")[:12],"can_manage":_can_manage(request.user)})

@login_required
def lesson_series_edit(request,pk):
    _require_manage(request.user); team=organization_for_view_user(request.user); series=get_object_or_404(LessonSeries.objects.select_related("program"),pk=pk,program__team=team); form=LessonSeriesForm(request.POST or None,instance=series,program=series.program)
    if form.is_valid(): form.save(); messages.success(request,"Lesson series updated. Existing occurrences were not silently moved."); return redirect("lesson_series_detail",pk=series.pk)
    return render(request,"portal/form.html",{"form":form,"title":f"Edit {series.name}","eyebrow":series.program.name})

@login_required
def lesson_enrollment_create(request,series_pk):
    _require_manage(request.user); team=organization_for_view_user(request.user); series=get_object_or_404(LessonSeries.objects.select_related("program"),pk=series_pk,program__team=team)
    if series.is_iea_series: raise PermissionDenied("IEA team lesson rosters are managed by season team membership.")
    form=LessonEnrollmentForm(request.POST or None,series=series)
    if form.is_valid(): enrollment=form.save(); messages.success(request,f"{enrollment.person} added to {series.name}."); return redirect("lesson_series_detail",pk=series.pk)
    return render(request,"portal/form.html",{"form":form,"title":"Add enrollment","eyebrow":series.name})

@login_required
def lesson_enrollment_edit(request,pk):
    _require_manage(request.user); team=organization_for_view_user(request.user); enrollment=get_object_or_404(LessonEnrollment.objects.select_related("series__program","person"),pk=pk,series__program__team=team); form=LessonEnrollmentForm(request.POST or None,instance=enrollment,series=enrollment.series)
    if form.is_valid(): form.save(); messages.success(request,"Lesson enrollment updated."); return redirect("lesson_series_detail",pk=enrollment.series_id)
    return render(request,"portal/form.html",{"form":form,"title":f"Edit enrollment · {enrollment.person}","eyebrow":enrollment.series.name})

@login_required
def lesson_series_generate(request,pk):
    _require_manage(request.user); team=organization_for_view_user(request.user); series=get_object_or_404(LessonSeries.objects.select_related("program"),pk=pk,program__team=team)
    if request.method!="POST": return redirect("lesson_series_detail",pk=series.pk)
    start_date=max(timezone.localdate(),series.start_date) if series.start_date else timezone.localdate(); end_date=series.end_date or (start_date+timedelta(weeks=12)); result=materialize_lesson_series(series,start_date,end_date); messages.success(request,f"Schedule ready: {len(result.generation.created)} occurrence(s) created and {len(result.prepared)} prepared."); return redirect("lesson_series_detail",pk=series.pk)

@login_required
def lesson_occurrence_detail(request,pk):
    team=organization_for_view_user(request.user); occurrence=_occurrence_for_team(team,pk); context=occurrence.series.iea_context if occurrence.series.is_iea_series else None
    return render(request,"portal/lesson_occurrence_detail.html",{"occurrence":occurrence,"iea_context":context,"attendance":occurrence.attendance_records.select_related("person").order_by("person__last_name","person__first_name"),"assignments":occurrence.assignments.select_related("person","horse").order_by("role","person__last_name"),"can_manage":_can_manage(request.user)})

@login_required
def lesson_occurrence_prepare(request,pk):
    _require_manage(request.user); team=organization_for_view_user(request.user); occurrence=_occurrence_for_team(team,pk)
    if request.method=="POST":
        result=prepare_lesson_occurrence(occurrence); messages.success(request,f"Roster ready: {len(result.attendance_created)} attendance and {len(result.assignments_created)} assignment record(s) added.")
    return redirect("lesson_occurrence_detail",pk=pk)

@login_required
def lesson_attendance_edit(request,pk):
    _require_manage(request.user); team=organization_for_view_user(request.user); record=get_object_or_404(LessonAttendanceRecord.objects.select_related("occurrence__series__program","person"),pk=pk,occurrence__series__program__team=team); form=LessonAttendanceRecordForm(request.POST or None,instance=record)
    if form.is_valid(): form.save(); messages.success(request,f"Attendance updated for {record.person}."); return redirect("lesson_occurrence_detail",pk=record.occurrence_id)
    return render(request,"portal/form.html",{"form":form,"title":f"Attendance · {record.person}","eyebrow":record.occurrence.title})

@login_required
def lesson_assignment_edit(request,pk):
    _require_manage(request.user); team=organization_for_view_user(request.user); assignment=get_object_or_404(LessonAssignment.objects.select_related("occurrence__series__program","person","horse"),pk=pk,role=LessonAssignment.Role.PARTICIPANT,occurrence__series__program__team=team); form=LessonParticipantAssignmentForm(request.POST or None,instance=assignment,occurrence=assignment.occurrence)
    if form.is_valid(): form.save(); messages.success(request,f"Horse assignment updated for {assignment.person}."); return redirect("lesson_occurrence_detail",pk=assignment.occurrence_id)
    return render(request,"portal/form.html",{"form":form,"title":f"Horse assignment · {assignment.person}","eyebrow":assignment.occurrence.title})

@login_required
def lesson_occurrence_complete(request,pk):
    _require_manage(request.user); team=organization_for_view_user(request.user); occurrence=_occurrence_for_team(team,pk)
    if request.method=="POST":
        if occurrence.status==LessonOccurrence.Status.CANCELLED: messages.error(request,"A cancelled lesson cannot be completed.")
        else: occurrence.status=LessonOccurrence.Status.COMPLETED; occurrence.full_clean(); occurrence.save(update_fields=["status","updated_at"]); messages.success(request,"Lesson marked complete.")
    return redirect("lesson_occurrence_detail",pk=pk)

@login_required
def lesson_occurrence_cancel(request,pk):
    _require_manage(request.user); team=organization_for_view_user(request.user); occurrence=_occurrence_for_team(team,pk); form=LessonCancelForm(request.POST or None,initial={"notes":occurrence.notes})
    if request.method=="POST" and form.is_valid():
        try: cancel_lesson_occurrence(occurrence,notes=form.cleaned_data["notes"]); messages.success(request,"Lesson cancelled."); return redirect("lesson_occurrence_detail",pk=pk)
        except ValidationError as exc: form.add_error(None,exc)
    return render(request,"portal/form.html",{"form":form,"title":f"Cancel {occurrence.title}","eyebrow":"LESSON OCCURRENCE"})

@login_required
def lesson_occurrence_reschedule(request,pk):
    _require_manage(request.user); team=organization_for_view_user(request.user); occurrence=_occurrence_for_team(team,pk); initial={"starts_at":timezone.localtime(occurrence.starts_at).strftime("%Y-%m-%dT%H:%M"),"ends_at":timezone.localtime(occurrence.ends_at).strftime("%Y-%m-%dT%H:%M") if occurrence.ends_at else "","notes":occurrence.notes}; form=LessonRescheduleForm(request.POST or None,initial=initial)
    if request.method=="POST" and form.is_valid():
        try: reschedule_lesson_occurrence(occurrence,starts_at=form.cleaned_data["starts_at"],ends_at=form.cleaned_data["ends_at"],notes=form.cleaned_data["notes"]); messages.success(request,"Lesson rescheduled. Its original recurrence slot remains protected."); return redirect("lesson_occurrence_detail",pk=pk)
        except ValidationError as exc: form.add_error(None,exc)
    return render(request,"portal/form.html",{"form":form,"title":f"Reschedule {occurrence.title}","eyebrow":"LESSON OCCURRENCE"})
