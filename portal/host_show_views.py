from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .host_show_forms import HostShowOperationsForm
from .host_show_models import HostShowOperations
from .models import Show
from .view_modules.common import _can_manage, _is_show_lead, _team


def _host_show(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show, pk=show_pk, team=team)
    if show.financial_role != Show.FinancialRole.HOSTING_ATTENDING:
        raise PermissionDenied("This show is not marked as a hosted show.")
    return show


@login_required
def host_show_workspace(request, show_pk):
    show = _host_show(request, show_pk)
    operations = HostShowOperations.objects.filter(show=show).first()
    can_manage = _can_manage(request.user)
    is_show_lead = _is_show_lead(request.user, show)
    if not (can_manage or is_show_lead):
        raise PermissionDenied

    readiness_items = operations.readiness_items if operations else []
    return render(
        request,
        "portal/host_show_workspace.html",
        {
            "show": show,
            "operations": operations,
            "readiness_items": readiness_items,
            "can_manage": can_manage,
            "is_show_lead": is_show_lead,
        },
    )


@login_required
def host_show_edit(request, show_pk):
    show = _host_show(request, show_pk)
    if not _can_manage(request.user):
        raise PermissionDenied

    operations, created = HostShowOperations.objects.get_or_create(
        show=show,
        defaults={"created_by": request.user, "updated_by": request.user},
    )
    form = HostShowOperationsForm(request.POST or None, instance=operations)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if created and not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()
        messages.success(request, "Host Show Operations updated.")
        return redirect("host_show_workspace", show_pk=show.pk)

    return render(
        request,
        "portal/host_show_form.html",
        {"show": show, "form": form, "operations": operations},
    )
