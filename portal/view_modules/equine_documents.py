from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from ..equine_access import require_horse_management
from ..equine_document_forms import HorseDocumentForm
from ..horse_models import Horse
from ..model_modules.equine_documents import HorseDocument
from ..models import AuditEvent
from ..platform import organization_for_view_user
from .common import _audit_event


def _horse_for_user(user, pk):
    team = organization_for_view_user(user)
    return get_object_or_404(Horse, pk=pk, team=team)


def _managed_horse(user, pk):
    horse = _horse_for_user(user, pk)
    require_horse_management(user, horse)
    return horse


@login_required
def horse_document_add(request, horse_pk):
    horse = _managed_horse(request.user, horse_pk)
    form = HorseDocumentForm(request.POST or None, request.FILES or None, horse=horse)
    if form.is_valid():
        document = form.save(commit=False)
        document.horse = horse
        document.save()
        _audit_event(
            team=horse.team,
            actor=request.user,
            action=AuditEvent.Action.CREATED,
            obj=document,
            summary=f"Added horse document for {horse.display_name}: {document.title}",
        )
        messages.success(request, f"Document added for {horse.display_name}.")
        return redirect("horse_detail", pk=horse.pk)
    return render(request, "portal/horse_document_form.html", {
        "form": form,
        "horse": horse,
        "title": f"Add document — {horse.display_name}",
    })


@login_required
def horse_document_edit(request, horse_pk, pk):
    horse = _managed_horse(request.user, horse_pk)
    document = get_object_or_404(HorseDocument, pk=pk, horse=horse)
    form = HorseDocumentForm(request.POST or None, request.FILES or None, instance=document, horse=horse)
    if form.is_valid():
        document = form.save()
        _audit_event(
            team=horse.team,
            actor=request.user,
            action=AuditEvent.Action.UPDATED,
            obj=document,
            summary=f"Updated horse document for {horse.display_name}: {document.title}",
        )
        messages.success(request, "Horse document updated.")
        return redirect("horse_detail", pk=horse.pk)
    return render(request, "portal/horse_document_form.html", {
        "form": form,
        "horse": horse,
        "document": document,
        "title": f"Edit document — {horse.display_name}",
    })


@login_required
def horse_document_download(request, horse_pk, pk):
    """Serve sensitive horse records only through horse-scoped authorized access."""
    horse = _managed_horse(request.user, horse_pk)
    document = get_object_or_404(HorseDocument, pk=pk, horse=horse)
    file_obj = document.file.open("rb")
    filename = Path(document.file.name).name
    response = FileResponse(file_obj, as_attachment=False, filename=filename)
    response["Cache-Control"] = "private, no-store"
    response["Pragma"] = "no-cache"
    return response
