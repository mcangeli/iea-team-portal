from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from ..equine_compliance_forms import HorseComplianceRequirementForm
from ..model_modules.equine_compliance_requirements import HorseComplianceRequirement
from ..models import AuditEvent
from ..platform import organization_for_view_user
from .common import _audit_event, _can_manage


def _require_manage(user):
    if not _can_manage(user):
        raise PermissionDenied


@login_required
def requirement_list(request):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    requirements = HorseComplianceRequirement.objects.filter(team=team)
    return render(request, "portal/horse_compliance_requirements.html", {"requirements": requirements})


@login_required
def requirement_add(request):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    form = HorseComplianceRequirementForm(request.POST or None, team=team)
    if form.is_valid():
        requirement = form.save(commit=False)
        requirement.team = team
        requirement.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=requirement, summary=f"Created horse compliance requirement: {requirement.name}")
        messages.success(request, "Horse compliance requirement added.")
        return redirect("horse_compliance_requirements")
    return render(request, "portal/horse_compliance_requirement_form.html", {"form": form, "title": "Add compliance requirement"})


@login_required
def requirement_edit(request, pk):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    requirement = get_object_or_404(HorseComplianceRequirement, pk=pk, team=team)
    form = HorseComplianceRequirementForm(request.POST or None, instance=requirement, team=team)
    if form.is_valid():
        requirement = form.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=requirement, summary=f"Updated horse compliance requirement: {requirement.name}")
        messages.success(request, "Horse compliance requirement updated.")
        return redirect("horse_compliance_requirements")
    return render(request, "portal/horse_compliance_requirement_form.html", {"form": form, "requirement": requirement, "title": f"Edit {requirement.name}"})
