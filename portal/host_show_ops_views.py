from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .host_show_forms import HostShowDutyAssignmentForm, HostShowReadinessCheckpointForm
from .host_show_models import HostShowDutyAssignment, HostShowOperations, HostShowReadinessCheckpoint
from .host_show_views import _can_manage_host_show, _host_show, _is_show_manager
from .view_modules.common import _can_manage, _is_show_lead


def _operations_for(request, show_pk, *, create=False):
    show = _host_show(request, show_pk)
    if create:
        operations, _ = HostShowOperations.objects.get_or_create(
            show=show,
            defaults={"created_by": request.user, "updated_by": request.user},
        )
    else:
        operations = get_object_or_404(HostShowOperations, show=show)
    return show, operations


@login_required
def host_command_center(request, show_pk):
    show = _host_show(request, show_pk)
    can_manage = _can_manage(request.user)
    is_manager = _is_show_manager(request.user, show)
    is_lead = _is_show_lead(request.user, show)
    if not (can_manage or is_manager or is_lead):
        raise PermissionDenied

    operations = HostShowOperations.objects.filter(show=show).first()
    if not operations and (can_manage or is_manager):
        operations = HostShowOperations.objects.create(
            show=show,
            created_by=request.user,
            updated_by=request.user,
        )
    if not operations:
        return render(request, "portal/host_show_command_center.html", {
            "show": show,
            "operations": None,
            "duties": HostShowDutyAssignment.objects.none(),
            "checkpoints": HostShowReadinessCheckpoint.objects.none(),
            "open_checkpoint_count": 0,
            "overdue_checkpoint_count": 0,
            "active_duty_count": 0,
            "handoff_count": 0,
            "can_manage_host_show": False,
            "is_show_lead": is_lead,
        })

    now = timezone.now()
    duties = operations.duty_assignments.select_related("assigned_user", "relieved_by").all()
    checkpoints = operations.readiness_checkpoints.select_related("owner").all()
    open_checkpoints = [checkpoint for checkpoint in checkpoints if not checkpoint.is_done]
    overdue_checkpoints = [
        checkpoint for checkpoint in open_checkpoints
        if checkpoint.due_at and checkpoint.due_at < now
    ]
    active_duties = duties.filter(
        status__in=[
            HostShowDutyAssignment.Status.CHECKED_IN,
            HostShowDutyAssignment.Status.ACTIVE,
        ]
    )
    handoff_duties = duties.filter(status=HostShowDutyAssignment.Status.HANDED_OFF)

    return render(request, "portal/host_show_command_center.html", {
        "show": show,
        "operations": operations,
        "duties": duties,
        "checkpoints": checkpoints,
        "open_checkpoint_count": len(open_checkpoints),
        "overdue_checkpoint_count": len(overdue_checkpoints),
        "active_duty_count": active_duties.count(),
        "handoff_count": handoff_duties.count(),
        "can_manage_host_show": can_manage or is_manager,
        "is_show_lead": is_lead,
    })


@login_required
def host_checkpoint_add(request, show_pk):
    show, operations = _operations_for(request, show_pk, create=True)
    if not _can_manage_host_show(request.user, show):
        raise PermissionDenied
    form = HostShowReadinessCheckpointForm(request.POST or None, team=show.team)
    if request.method == "POST" and form.is_valid():
        checkpoint = form.save(commit=False)
        checkpoint.operations = operations
        if checkpoint.status == HostShowReadinessCheckpoint.Status.COMPLETE:
            checkpoint.completed_at = timezone.now()
        checkpoint.save()
        messages.success(request, "Host readiness checkpoint added.")
        return redirect("host_command_center", show_pk=show.pk)
    return render(request, "portal/host_show_assignment_form.html", {
        "show": show,
        "form": form,
        "title": "Add Readiness Checkpoint",
        "eyebrow": "HOST SHOW READINESS",
    })


@login_required
def host_checkpoint_edit(request, show_pk, checkpoint_pk):
    show, operations = _operations_for(request, show_pk)
    if not _can_manage_host_show(request.user, show):
        raise PermissionDenied
    checkpoint = get_object_or_404(HostShowReadinessCheckpoint, pk=checkpoint_pk, operations=operations)
    form = HostShowReadinessCheckpointForm(request.POST or None, instance=checkpoint, team=show.team)
    if request.method == "POST" and form.is_valid():
        checkpoint = form.save(commit=False)
        if checkpoint.status == HostShowReadinessCheckpoint.Status.COMPLETE and not checkpoint.completed_at:
            checkpoint.completed_at = timezone.now()
        elif checkpoint.status != HostShowReadinessCheckpoint.Status.COMPLETE:
            checkpoint.completed_at = None
        checkpoint.save()
        messages.success(request, "Readiness checkpoint updated.")
        return redirect("host_command_center", show_pk=show.pk)
    return render(request, "portal/host_show_assignment_form.html", {
        "show": show,
        "form": form,
        "title": "Edit Readiness Checkpoint",
        "eyebrow": "HOST SHOW READINESS",
    })


@login_required
@require_POST
def host_checkpoint_complete(request, show_pk, checkpoint_pk):
    show, operations = _operations_for(request, show_pk)
    if not _can_manage_host_show(request.user, show):
        raise PermissionDenied
    checkpoint = get_object_or_404(HostShowReadinessCheckpoint, pk=checkpoint_pk, operations=operations)
    checkpoint.status = HostShowReadinessCheckpoint.Status.COMPLETE
    checkpoint.completed_at = timezone.now()
    checkpoint.save(update_fields=["status", "completed_at"])
    messages.success(request, "Readiness checkpoint completed.")
    return redirect("host_command_center", show_pk=show.pk)


@login_required
def host_duty_add(request, show_pk):
    show, operations = _operations_for(request, show_pk, create=True)
    if not _can_manage_host_show(request.user, show):
        raise PermissionDenied
    form = HostShowDutyAssignmentForm(request.POST or None, team=show.team)
    form.instance.operations = operations
    if request.method == "POST" and form.is_valid():
        duty = form.save(commit=False)
        duty.operations = operations
        duty.save()
        messages.success(request, "Show-day duty assigned. This does not affect season volunteer hours.")
        return redirect("host_command_center", show_pk=show.pk)
    return render(request, "portal/host_show_assignment_form.html", {
        "show": show,
        "form": form,
        "title": "Assign Show-Day Duty",
        "eyebrow": "HOST SHOW STAFFING",
        "notice": "Operational staffing only — this assignment does not count toward season volunteer-hour requirements.",
    })


@login_required
def host_duty_edit(request, show_pk, duty_pk):
    show, operations = _operations_for(request, show_pk)
    if not _can_manage_host_show(request.user, show):
        raise PermissionDenied
    duty = get_object_or_404(HostShowDutyAssignment, pk=duty_pk, operations=operations)
    form = HostShowDutyAssignmentForm(request.POST or None, instance=duty, team=show.team)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Show-day duty updated. Volunteer-hour records are unchanged.")
        return redirect("host_command_center", show_pk=show.pk)
    return render(request, "portal/host_show_assignment_form.html", {
        "show": show,
        "form": form,
        "title": "Edit Show-Day Duty",
        "eyebrow": "HOST SHOW STAFFING",
        "notice": "Operational staffing only — this assignment does not count toward season volunteer-hour requirements.",
    })


@login_required
@require_POST
def host_duty_status(request, show_pk, duty_pk):
    show, operations = _operations_for(request, show_pk)
    if not _can_manage_host_show(request.user, show):
        raise PermissionDenied
    duty = get_object_or_404(HostShowDutyAssignment, pk=duty_pk, operations=operations)
    status = request.POST.get("status", "")
    allowed = {value for value, _ in HostShowDutyAssignment.Status.choices}
    if status not in allowed:
        messages.error(request, "Choose a valid duty status.")
        return redirect("host_command_center", show_pk=show.pk)
    duty.status = status
    if status == HostShowDutyAssignment.Status.HANDED_OFF:
        duty.handoff_notes = request.POST.get("handoff_notes", duty.handoff_notes).strip()
        duty.relieved_by = request.user
    duty.save()
    messages.success(request, f"{duty.title} marked {duty.get_status_display()}.")
    return redirect("host_command_center", show_pk=show.pk)