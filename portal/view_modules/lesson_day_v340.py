from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from ..model_modules.horses import Horse
from ..model_modules.lessons import LessonAssignment, LessonAttendanceRecord, LessonOccurrence
from ..platform import organization_for_view_user
from ..services.lesson_day_operations import LessonDayRowUpdate, update_lesson_day
from .common import _require_manage


@login_required
def lesson_day_workspace(request, pk):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    occurrence = get_object_or_404(
        LessonOccurrence.objects.select_related("series__program", "series__iea_context__season", "instructor"),
        pk=pk,
        series__program__team=team,
    )
    editable = occurrence.status not in {LessonOccurrence.Status.COMPLETED, LessonOccurrence.Status.CANCELLED}

    attendance = list(occurrence.attendance_records.select_related("person").order_by("person__last_name", "person__first_name", "person_id"))
    assignments = {
        row.person_id: row
        for row in occurrence.assignments.filter(role=LessonAssignment.Role.PARTICIPANT).select_related("person", "horse")
    }
    rows = [{"attendance": record, "assignment": assignments.get(record.person_id)} for record in attendance]
    horses = Horse.objects.filter(team=team, active=True).order_by("name")

    if request.method == "POST":
        if not editable:
            messages.error(request, "Completed or cancelled lessons cannot be edited.")
            return redirect("lesson_day_workspace", pk=pk)
        try:
            updates = []
            for row in rows:
                person_id = row["attendance"].person_id
                horse_value = request.POST.get(f"horse_{person_id}", "").strip()
                updates.append(LessonDayRowUpdate(
                    person_id=person_id,
                    attendance_status=request.POST.get(f"attendance_{person_id}", ""),
                    horse_id=int(horse_value) if horse_value else None,
                    attendance_notes=request.POST.get(f"attendance_notes_{person_id}", "").strip(),
                    assignment_notes=request.POST.get(f"assignment_notes_{person_id}", "").strip(),
                ))
            result = update_lesson_day(occurrence, updates)
            if result.unassigned_horses:
                messages.warning(request, f"Lesson day saved. {result.unassigned_horses} participant(s) still need a horse assignment.")
            else:
                messages.success(request, "Lesson day saved. Attendance and horse assignments are complete.")
            return redirect("lesson_day_workspace", pk=pk)
        except (ValidationError, ValueError) as exc:
            messages.error(request, "; ".join(exc.messages) if isinstance(exc, ValidationError) else "Invalid horse selection.")

    return render(request, "portal/lesson_day_workspace.html", {
        "occurrence": occurrence,
        "rows": rows,
        "horses": horses,
        "attendance_choices": LessonAttendanceRecord.Status.choices,
        "editable": editable,
        "unassigned_count": sum(1 for row in rows if row["assignment"] and not row["assignment"].horse_id),
    })
