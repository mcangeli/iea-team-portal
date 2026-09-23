from calendar import monthrange
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..forms_lesson_resources import LessonResourceAssignmentForm, LessonResourceReleaseForm
from ..forms_lessons_v340 import IEALessonOccurrenceForm, IEALessonSeriesForm, LessonAttendanceRecordForm, LessonCancelForm, LessonEnrollmentForm, LessonParticipantAssignmentForm, LessonProgramForm, LessonRescheduleForm, LessonSeriesForm
from ..model_modules.facilities import ResourceReservation
from ..model_modules.lessons import IEALessonOccurrenceParticipant, IEALessonSeriesContext, LessonAssignment, LessonAttendanceRecord, LessonEnrollment, LessonOccurrence, LessonProgram, LessonSeries
from ..models import SeasonMembership
from ..model_modules.finance import FinanceDomain, ReceivableBillingRule, ReceivableCharge
from ..services.finance_access import allowed_finance_domains
from ..services.finance_account_resolution import resolve_participant_account
from ..services.lesson_billing import BILLABLE_ATTENDANCE, bill_lesson_occurrence
from ..platform import active_period_for_organization, organization_for_view_user
from ..services.lesson_completion import complete_lesson_occurrence
from ..services.lesson_operations import materialize_lesson_series
from ..services.lesson_permissions import can_manage_lesson_occurrence, can_manage_lesson_series, is_barn_lesson_manager, is_iea_lesson_manager, require_barn_lesson_manager, require_iea_lesson_manager, require_lesson_occurrence_manager
from ..services.lesson_preparation import prepare_lesson_occurrence
from ..services.lesson_scheduling import cancel_lesson_occurrence, reschedule_lesson_occurrence
from ..services.lesson_resources import LESSON_OCCURRENCE_SOURCE, assign_lesson_resource, current_lesson_resource_reservation, release_lesson_resource


def _barn_programs(team):
    # A program belongs in the Barn workspace when it is empty or contains at
    # least one Barn series. Pure IEA containers stay in the Team Lessons
    # workspace, while an accidental/legacy mixed container does not hide its
    # Barn series from Barn operations.
    return LessonProgram.objects.filter(team=team).filter(
        Q(series__isnull=True) | Q(series__iea_context__isnull=True)
    ).distinct()

def _occurrence_for_team(team, pk): return get_object_or_404(LessonOccurrence.objects.select_related("series__program", "series__iea_context__season", "instructor").prefetch_related("attendance_records__person", "assignments__person", "assignments__horse"), pk=pk, series__program__team=team)
def _require_series_manager(user, series):
    if not can_manage_lesson_series(user, series):
        if series.is_iea_series: require_iea_lesson_manager(user)
        require_barn_lesson_manager(user)

@login_required
def lesson_program_list(request):
    team=organization_for_view_user(request.user); programs=_barn_programs(team).prefetch_related("series").order_by("name")
    return render(request,"portal/lesson_program_list.html",{"programs":programs,"can_manage":is_barn_lesson_manager(request.user)})

@login_required
def lesson_program_detail(request,pk):
    team=organization_for_view_user(request.user); program=get_object_or_404(_barn_programs(team).prefetch_related("series__enrollments","series__occurrences"),pk=pk)
    return render(request,"portal/lesson_program_detail.html",{"program":program,"barn_series":program.series.filter(iea_context__isnull=True),"can_manage":is_barn_lesson_manager(request.user)})

@login_required
def lesson_program_create(request):
    require_barn_lesson_manager(request.user); team=organization_for_view_user(request.user); form=LessonProgramForm(request.POST or None,team=team)
    if form.is_valid(): program=form.save(); messages.success(request,"Barn lesson program created."); return redirect("lesson_program_detail",pk=program.pk)
    return render(request,"portal/form.html",{"form":form,"title":"Create barn lesson program","eyebrow":"BARN LESSON PROGRAM"})

@login_required
def lesson_program_edit(request,pk):
    require_barn_lesson_manager(request.user); team=organization_for_view_user(request.user); program=get_object_or_404(_barn_programs(team),pk=pk); form=LessonProgramForm(request.POST or None,instance=program,team=team)
    if form.is_valid(): form.save(); messages.success(request,"Barn lesson program updated."); return redirect("lesson_program_detail",pk=program.pk)
    return render(request,"portal/form.html",{"form":form,"title":f"Edit {program.name}","eyebrow":"BARN LESSON PROGRAM"})

@login_required
def lesson_series_create(request,program_pk):
    require_barn_lesson_manager(request.user); team=organization_for_view_user(request.user); program=get_object_or_404(_barn_programs(team),pk=program_pk); form=LessonSeriesForm(request.POST or None,program=program)
    if form.is_valid(): series=form.save(); messages.success(request,"Barn lesson series created."); return redirect("lesson_series_detail",pk=series.pk)
    return render(request,"portal/form.html",{"form":form,"title":"Create barn lesson series","eyebrow":program.name})

@login_required
def iea_lesson_list(request):
    team=organization_for_view_user(request.user); season=active_period_for_organization(team); contexts=IEALessonSeriesContext.objects.none(); legacy_upcoming=[]; legacy_recent=[]; month_occurrences=[]; month_cursor=timezone.localdate().replace(day=1)
    requested_month=request.GET.get("month","")
    if requested_month:
        try: month_cursor=date.fromisoformat(f"{requested_month}-01")
        except ValueError: pass
    if season:
        contexts=IEALessonSeriesContext.objects.filter(season=season).select_related("series__program").order_by("team_level","series__name")
        legacy_lessons=season.lessons.select_related("group","coach").prefetch_related("attendance__rider"); legacy_upcoming=legacy_lessons.filter(starts_at__gte=timezone.now()).order_by("starts_at"); legacy_recent=legacy_lessons.filter(starts_at__lt=timezone.now()).order_by("-starts_at")[:12]
        month_end=month_cursor.replace(day=monthrange(month_cursor.year,month_cursor.month)[1])
        month_occurrences=LessonOccurrence.objects.filter(series__iea_context__season=season,starts_at__date__range=(month_cursor,month_end)).select_related("series__program","instructor").prefetch_related("iea_participants").order_by("starts_at")
    previous_month=(month_cursor-timedelta(days=1)).replace(day=1)
    next_month=(month_cursor.replace(day=monthrange(month_cursor.year,month_cursor.month)[1])+timedelta(days=1)).replace(day=1)
    return render(request,"portal/iea_lesson_list.html",{"season":season,"futures_contexts":contexts.filter(team_level=SeasonMembership.TeamLevel.FUTURES),"upper_contexts":contexts.filter(team_level=SeasonMembership.TeamLevel.UPPER),"legacy_upcoming":legacy_upcoming,"legacy_recent":legacy_recent,"month_occurrences":month_occurrences,"month_cursor":month_cursor,"previous_month":previous_month,"next_month":next_month,"can_manage":is_iea_lesson_manager(request.user)})


@login_required
def iea_lesson_occurrence_create(request):
    require_iea_lesson_manager(request.user)
    team = organization_for_view_user(request.user)
    season = active_period_for_organization(team)
    if not season:
        raise PermissionDenied("An active IEA season is required before scheduling team lessons.")
    program, _ = LessonProgram.objects.get_or_create(
        team=team,
        name="IEA Team Lessons",
        defaults={"description": "IEA team instruction scheduled by individual occurrence."},
    )
    series, _ = LessonSeries.objects.get_or_create(
        program=program,
        name="IEA Team Lessons",
        defaults={"active": True},
    )
    context, _ = IEALessonSeriesContext.objects.get_or_create(
        series=series,
        defaults={"season": season, "team_level": IEALessonSeriesContext.TeamLevel.MIXED},
    )
    if context.season_id != season.id or context.team_level != IEALessonSeriesContext.TeamLevel.MIXED:
        context.season = season
        context.team_level = IEALessonSeriesContext.TeamLevel.MIXED
        context.full_clean()
        context.save()
    form = IEALessonOccurrenceForm(
        request.POST or None,
        team=team,
        season=season,
        series=series,
    )
    if form.is_valid():
        resource_space = form.cleaned_data.get("resource_space")
        try:
            with transaction.atomic():
                occurrence = form.save()
                if resource_space:
                    assign_lesson_resource(occurrence, resource_space)
        except ValidationError as exc:
            validation_messages = []
            if hasattr(exc, "message_dict"):
                for field_messages in exc.message_dict.values():
                    validation_messages.extend(field_messages)
            else:
                validation_messages.extend(exc.messages)
            form.add_error("resource_space", " ".join(validation_messages))
        else:
            location_suffix = f" in {resource_space.name}" if resource_space else ""
            messages.success(
                request,
                f"{occurrence.title} scheduled with {occurrence.iea_participants.count()} rider(s){location_suffix}.",
            )
            return redirect("lesson_occurrence_detail", pk=occurrence.pk)
    return render(request, "portal/iea_lesson_occurrence_form.html", {"form": form, "season": season})

@login_required
def iea_lesson_series_create(request):
    require_iea_lesson_manager(request.user); team=organization_for_view_user(request.user); season=active_period_for_organization(team)
    if not season: raise PermissionDenied("An active IEA season is required before creating team lessons.")
    program,_=LessonProgram.objects.get_or_create(team=team,name="IEA Team Lessons",defaults={"description":"IEA team instruction managed by season and team level."}); form=IEALessonSeriesForm(request.POST or None,program=program,season=season)
    if form.is_valid(): series=form.save(); messages.success(request,f"{series.iea_context.get_team_level_display()} lesson series created."); return redirect("lesson_series_detail",pk=series.pk)
    return render(request,"portal/form.html",{"form":form,"title":"Create IEA team lesson series","eyebrow":season.name})

@login_required
def lesson_series_detail(request,pk):
    team=organization_for_view_user(request.user); series=get_object_or_404(LessonSeries.objects.select_related("program","instructor").prefetch_related("enrollments__person","occurrences__attendance_records","occurrences__assignments"),pk=pk,program__team=team); occurrences=series.occurrences.order_by("starts_at"); now=timezone.now(); context=series.iea_context if series.is_iea_series else None
    return render(request,"portal/lesson_series_detail.html",{"series":series,"iea_context":context,"enrollments":series.enrollments.select_related("person").order_by("person__last_name","person__first_name") if not context else [],"upcoming_occurrences":occurrences.filter(starts_at__gte=now),"past_occurrences":occurrences.filter(starts_at__lt=now).order_by("-starts_at")[:12],"can_manage":can_manage_lesson_series(request.user,series)})

@login_required
def lesson_series_edit(request,pk):
    team=organization_for_view_user(request.user); series=get_object_or_404(LessonSeries.objects.select_related("program","iea_context__season"),pk=pk,program__team=team); _require_series_manager(request.user,series)
    if series.is_iea_series:
        form=IEALessonSeriesForm(request.POST or None,instance=series,program=series.program,season=series.iea_context.season)
    else:
        form=LessonSeriesForm(request.POST or None,instance=series,program=series.program)
    if form.is_valid(): form.save(); messages.success(request,"Lesson series updated. Existing occurrences were not silently moved."); return redirect("lesson_series_detail",pk=series.pk)
    return render(request,"portal/form.html",{"form":form,"title":f"Edit {series.name}","eyebrow":series.program.name})

@login_required
def lesson_enrollment_create(request,series_pk):
    team=organization_for_view_user(request.user); series=get_object_or_404(LessonSeries.objects.select_related("program"),pk=series_pk,program__team=team); require_barn_lesson_manager(request.user)
    if series.is_iea_series: raise PermissionDenied("IEA team lesson rosters are managed by season team membership.")
    form=LessonEnrollmentForm(request.POST or None,series=series)
    if form.is_valid(): enrollment=form.save(); messages.success(request,f"{enrollment.person} added to {series.name}."); return redirect("lesson_series_detail",pk=series.pk)
    return render(request,"portal/form.html",{"form":form,"title":"Add enrollment","eyebrow":series.name})

@login_required
def lesson_enrollment_edit(request,pk):
    team=organization_for_view_user(request.user); enrollment=get_object_or_404(LessonEnrollment.objects.select_related("series__program","person"),pk=pk,series__program__team=team); require_barn_lesson_manager(request.user); form=LessonEnrollmentForm(request.POST or None,instance=enrollment,series=enrollment.series)
    if form.is_valid(): form.save(); messages.success(request,"Lesson enrollment updated."); return redirect("lesson_series_detail",pk=enrollment.series_id)
    return render(request,"portal/form.html",{"form":form,"title":f"Edit enrollment · {enrollment.person}","eyebrow":enrollment.series.name})

@login_required
def lesson_series_generate(request,pk):
    team=organization_for_view_user(request.user); series=get_object_or_404(LessonSeries.objects.select_related("program"),pk=pk,program__team=team); _require_series_manager(request.user,series)
    if request.method!="POST": return redirect("lesson_series_detail",pk=series.pk)
    start_date=max(timezone.localdate(),series.start_date) if series.start_date else timezone.localdate(); end_date=series.end_date or (start_date+timedelta(weeks=12)); result=materialize_lesson_series(series,start_date,end_date); messages.success(request,f"Schedule ready: {len(result.generation.created)} occurrence(s) created and {len(result.prepared)} prepared."); return redirect("lesson_series_detail",pk=series.pk)

def _lesson_billing_preview(occurrence, rule):
    rows=[]
    for attendance in occurrence.attendance_records.select_related("person").order_by("person__last_name","person__first_name"):
        state="not_billable"; account=None
        if attendance.status in BILLABLE_ATTENDANCE:
            try: account=resolve_participant_account(attendance.person,finance_domain=rule.account.finance_domain)
            except ValidationError: state="ambiguous"
            else:
                if account is None: state="no_account"
                elif account.pk != rule.account_id: state="different_account"
                elif ReceivableCharge.objects.filter(billing_rule=rule,generation_key=f"service:lesson_attendance:{occurrence.pk}:{attendance.person_id}").exists(): state="already_billed"
                else: state="ready"
        rows.append({"attendance":attendance,"account":account,"state":state})
    return rows

@login_required
def lesson_occurrence_detail(request,pk):
    team=organization_for_view_user(request.user); occurrence=_occurrence_for_team(team,pk); context=occurrence.series.iea_context if occurrence.series.is_iea_series else None
    domains=allowed_finance_domains(request.user,team)
    domain=FinanceDomain.IEA if occurrence.series.is_iea_series else FinanceDomain.GENERAL
    rules=ReceivableBillingRule.objects.none()
    if domain in domains and occurrence.status==LessonOccurrence.Status.COMPLETED:
        participant_account_ids=set()
        for attendance in occurrence.attendance_records.select_related("person"):
            if attendance.status not in BILLABLE_ATTENDANCE: continue
            try: account=resolve_participant_account(attendance.person,finance_domain=domain)
            except ValidationError: continue
            if account is not None: participant_account_ids.add(account.pk)
        rules=ReceivableBillingRule.objects.filter(account__team=team,account__finance_domain=domain,account_id__in=participant_account_ids,cadence=ReceivableBillingRule.Cadence.SERVICE,active=True).select_related("account").order_by("description","account__name")
    selected_rule=None; billing_rows=[]
    requested_rule=request.GET.get("billing_rule")
    if requested_rule and rules.filter(pk=requested_rule).exists():
        selected_rule=rules.get(pk=requested_rule); billing_rows=_lesson_billing_preview(occurrence,selected_rule)
    resource_reservation=current_lesson_resource_reservation(occurrence); resource_history=ResourceReservation.objects.filter(source_type=LESSON_OCCURRENCE_SOURCE,source_id=occurrence.pk).select_related("space__facility").order_by("created_at","id")
    return render(request,"portal/lesson_occurrence_detail.html",{"occurrence":occurrence,"resource_reservation":resource_reservation,"resource_history":resource_history,"iea_context":context,"attendance":occurrence.attendance_records.select_related("person").order_by("person__last_name","person__first_name"),"assignments":occurrence.assignments.select_related("person","horse").order_by("role","person__last_name"),"can_manage":can_manage_lesson_occurrence(request.user,occurrence),"billing_rules":rules,"selected_billing_rule":selected_rule,"billing_rows":billing_rows})

@login_required
def lesson_occurrence_bill(request,pk):
    team=organization_for_view_user(request.user); occurrence=_occurrence_for_team(team,pk)
    if request.method!="POST": return redirect("lesson_occurrence_detail",pk=pk)
    domain=FinanceDomain.IEA if occurrence.series.is_iea_series else FinanceDomain.GENERAL
    if domain not in allowed_finance_domains(request.user,team): raise PermissionDenied
    rule=get_object_or_404(ReceivableBillingRule.objects.select_related("account"),pk=request.POST.get("billing_rule"),account__team=team,account__finance_domain=domain,cadence=ReceivableBillingRule.Cadence.SERVICE,active=True)
    try:
        result=bill_lesson_occurrence(occurrence=occurrence,rule=rule)
        messages.success(request,f"Lesson billing complete: {len(result.generated)} charge(s) created, {len(result.existing)} already billed, {len(result.skipped)} skipped.")
    except ValidationError as exc: messages.error(request," ".join(exc.messages))
    return redirect(f"{request.path.rsplit('/bill/',1)[0]}/?billing_rule={rule.pk}")


@login_required
def iea_lesson_occurrence_duplicate(request, pk):
    require_iea_lesson_manager(request.user)
    team = organization_for_view_user(request.user)
    source = _occurrence_for_team(team, pk)
    if not source.series.is_iea_series:
        raise PermissionDenied("Only IEA team lessons can use this scheduling workflow.")
    season = source.series.iea_context.season
    initial = {
        "title": source.title,
        "instructor": source.instructor_id,
        "location": source.location,
        "capacity": source.capacity,
        "notes": source.notes,
    }
    if request.GET.get("copy_roster") == "1":
        initial["participants"] = source.iea_participants.values_list("person_id", flat=True)
    form = IEALessonOccurrenceForm(
        request.POST or None, initial=initial, team=team, season=season, series=source.series
    )
    if form.is_valid():
        resource_space = form.cleaned_data.get("resource_space")
        try:
            with transaction.atomic():
                occurrence = form.save()
                if resource_space:
                    assign_lesson_resource(occurrence, resource_space)
        except ValidationError as exc:
            validation_messages = []
            if hasattr(exc, "message_dict"):
                for field_messages in exc.message_dict.values():
                    validation_messages.extend(field_messages)
            else:
                validation_messages.extend(exc.messages)
            form.add_error("resource_space", " ".join(validation_messages))
        else:
            location_suffix = f" in {resource_space.name}" if resource_space else ""
            messages.success(
                request,
                f"{occurrence.title} scheduled with {occurrence.iea_participants.count()} rider(s){location_suffix}.",
            )
            return redirect("lesson_occurrence_detail", pk=occurrence.pk)
    return render(
        request,
        "portal/iea_lesson_occurrence_form.html",
        {"form": form, "season": season, "duplicate_source": source},
    )

@login_required
def lesson_occurrence_prepare(request,pk):
    team=organization_for_view_user(request.user); occurrence=_occurrence_for_team(team,pk); require_lesson_occurrence_manager(request.user,occurrence)
    if request.method=="POST": result=prepare_lesson_occurrence(occurrence); messages.success(request,f"Roster ready: {len(result.attendance_created)} attendance and {len(result.assignments_created)} assignment record(s) added.")
    return redirect("lesson_occurrence_detail",pk=pk)

@login_required
def lesson_attendance_edit(request, pk=None, attendance_pk=None):
    record_pk=pk if pk is not None else attendance_pk; team=organization_for_view_user(request.user); record=get_object_or_404(LessonAttendanceRecord.objects.select_related("occurrence__series__program","person"),pk=record_pk,occurrence__series__program__team=team); require_lesson_occurrence_manager(request.user,record.occurrence); form=LessonAttendanceRecordForm(request.POST or None,instance=record)
    if form.is_valid(): form.save(); messages.success(request,f"Attendance updated for {record.person}."); return redirect("lesson_occurrence_detail",pk=record.occurrence_id)
    return render(request,"portal/form.html",{"form":form,"title":f"Attendance · {record.person}","eyebrow":record.occurrence.title})

@login_required
def lesson_assignment_edit(request,pk):
    team=organization_for_view_user(request.user); assignment=get_object_or_404(LessonAssignment.objects.select_related("occurrence__series__program","person","horse"),pk=pk,role=LessonAssignment.Role.PARTICIPANT,occurrence__series__program__team=team); require_lesson_occurrence_manager(request.user,assignment.occurrence); form=LessonParticipantAssignmentForm(request.POST or None,instance=assignment,occurrence=assignment.occurrence)
    if form.is_valid(): form.save(); messages.success(request,f"Horse assignment updated for {assignment.person}."); return redirect("lesson_occurrence_detail",pk=assignment.occurrence_id)
    return render(request,"portal/form.html",{"form":form,"title":f"Horse assignment · {assignment.person}","eyebrow":assignment.occurrence.title})

@login_required
def lesson_occurrence_complete(request,pk):
    team=organization_for_view_user(request.user); occurrence=_occurrence_for_team(team,pk); require_lesson_occurrence_manager(request.user,occurrence)
    if request.method=="POST":
        try:
            complete_lesson_occurrence(occurrence)
            messages.success(request,"Lesson marked complete.")
        except ValidationError as exc:
            messages.error(request," ".join(exc.messages))
    return redirect("lesson_occurrence_detail",pk=pk)

@login_required
def lesson_occurrence_cancel(request,pk):
    team=organization_for_view_user(request.user); occurrence=_occurrence_for_team(team,pk); require_lesson_occurrence_manager(request.user,occurrence); form=LessonCancelForm(request.POST or None,initial={"notes":occurrence.notes})
    if request.method=="POST" and form.is_valid():
        try: cancel_lesson_occurrence(occurrence,notes=form.cleaned_data["notes"]); messages.success(request,"Lesson cancelled."); return redirect("lesson_occurrence_detail",pk=pk)
        except ValidationError as exc: form.add_error(None,exc)
    return render(request,"portal/form.html",{"form":form,"title":f"Cancel {occurrence.title}","eyebrow":"LESSON OCCURRENCE"})

@login_required
def lesson_occurrence_reschedule(request,pk):
    team=organization_for_view_user(request.user); occurrence=_occurrence_for_team(team,pk); require_lesson_occurrence_manager(request.user,occurrence); initial={"starts_at":timezone.localtime(occurrence.starts_at).strftime("%Y-%m-%dT%H:%M"),"ends_at":timezone.localtime(occurrence.ends_at).strftime("%Y-%m-%dT%H:%M") if occurrence.ends_at else "","notes":occurrence.notes}; form=LessonRescheduleForm(request.POST or None,initial=initial)
    if request.method=="POST" and form.is_valid():
        try: reschedule_lesson_occurrence(occurrence,starts_at=form.cleaned_data["starts_at"],ends_at=form.cleaned_data["ends_at"],notes=form.cleaned_data["notes"]); messages.success(request,"Lesson rescheduled. Its original recurrence slot remains protected."); return redirect("lesson_occurrence_detail",pk=pk)
        except ValidationError as exc: form.add_error(None,exc)
    return render(request,"portal/form.html",{"form":form,"title":f"Reschedule {occurrence.title}","eyebrow":"LESSON OCCURRENCE"})


@login_required
def lesson_occurrence_resource_assign(request, pk):
    team = organization_for_view_user(request.user)
    occurrence = _occurrence_for_team(team, pk)
    require_lesson_occurrence_manager(request.user, occurrence)
    current = current_lesson_resource_reservation(occurrence)
    form = LessonResourceAssignmentForm(request.POST or None, team=team)
    if request.method == "POST" and form.is_valid():
        try:
            reservation = assign_lesson_resource(occurrence, form.cleaned_data["space"])
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"{occurrence.title} assigned to {reservation.space.name}.")
            return redirect("lesson_occurrence_detail", pk=pk)
    return render(request, "portal/form.html", {
        "form": form,
        "title": f"{'Move' if current else 'Assign'} resource — {occurrence.title}",
        "eyebrow": "LESSON RESOURCE",
    })


@login_required
def lesson_occurrence_resource_release(request, pk):
    team = organization_for_view_user(request.user)
    occurrence = _occurrence_for_team(team, pk)
    require_lesson_occurrence_manager(request.user, occurrence)
    current = current_lesson_resource_reservation(occurrence)
    if not current:
        return redirect("lesson_occurrence_detail", pk=pk)
    form = LessonResourceReleaseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        release_lesson_resource(occurrence, location=form.cleaned_data["location"])
        messages.success(request, "Managed resource released. The lesson remains scheduled.")
        return redirect("lesson_occurrence_detail", pk=pk)
    return render(request, "portal/form.html", {
        "form": form,
        "title": f"Release resource — {occurrence.title}",
        "eyebrow": current.space.name,
    })

