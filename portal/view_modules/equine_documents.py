from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from ..equine_document_forms import HorseDocumentForm
from ..horse_models import Horse
from ..model_modules.equine_documents import HorseDocument
from ..models import AuditEvent
from ..platform import organization_for_view_user
from .common import _audit_event, _can_manage


def _horse_for_user(user, pk):
    team = organization_for_view_user(user)
    return get_object_or_404(Horse, pk=pk, team=team)


def _require_horse_manage(user):
    if not _can_manage(user):
        raise PermissionDenied


@login_required
def horse_document_add(request, horse_pk):
    _require_horse_manage(request.user)
    horse = _horse_for_user(request.user, horse_pk)
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
    _require_horse_manage(request.user)
    horse = _horse_for_user(request.user, horse_pk)
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
