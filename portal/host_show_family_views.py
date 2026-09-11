from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .host_show_forms import HostShowFamilyPublicationForm
from .host_show_models import HostShowFamilyPublication, HostShowOperations
from .host_show_views import _can_manage_host_show, _host_show
from .view_modules.common import _team
from .view_modules.show_day_helpers import _visible_show_day_updates


@login_required
def host_family_information(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(_hosted_show_queryset(team), pk=show_pk)
    operations = HostShowOperations.objects.filter(show=show).first()
    publication = None
    if operations:
        publication = HostShowFamilyPublication.objects.filter(operations=operations).first()

    can_manage = _can_manage_host_show(request.user, show)
    if not publication or not publication.published:
        if not can_manage:
            raise PermissionDenied("Family host-show information has not been published.")

    recent_updates = list(_visible_show_day_updates(request.user, show)[:5]) if publication and publication.published else []
    return render(request, "portal/host_show_family_information.html", {
        "show": show,
        "operations": operations,
        "publication": publication,
        "can_manage_host_show": can_manage,
        "recent_updates": recent_updates,
    })


def _hosted_show_queryset(team):
    from .models import Show
    return Show.objects.filter(team=team, financial_role=Show.FinancialRole.HOSTING_ATTENDING).select_related("season")


@login_required
def host_family_publication_edit(request, show_pk):
    show = _host_show(request, show_pk)
    if not _can_manage_host_show(request.user, show):
        raise PermissionDenied
    operations, _ = HostShowOperations.objects.get_or_create(
        show=show,
        defaults={"created_by": request.user, "updated_by": request.user},
    )
    publication, _ = HostShowFamilyPublication.objects.get_or_create(operations=operations)
    form = HostShowFamilyPublicationForm(request.POST or None, instance=publication)
    if request.method == "POST" and form.is_valid():
        publication = form.save(commit=False)
        publication.updated_by = request.user
        publication.save()
        if publication.published:
            messages.success(request, f"Family information published with {publication.selected_count} section(s) selected.")
        else:
            messages.success(request, "Family information is unpublished. The host plan remains intact.")
        return redirect("host_family_information", show_pk=show.pk)
    return render(request, "portal/host_show_family_publication_form.html", {
        "show": show,
        "operations": operations,
        "publication": publication,
        "form": form,
    })
