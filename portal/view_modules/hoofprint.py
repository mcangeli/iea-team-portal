from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Max

from ..hoofprint_checks import hoofprint_warnings, live_differs_from_snapshot
from ..hoofprint_forms import HoofprintFinalizeForm, ShowHorseListDocumentForm
from ..hoofprint_models import HoofprintSnapshot, ShowHorseListDocument
from ..hoofprint_service import build_hoofprint_payload, render_hoofprint_pdf
from ..models import AuditEvent, Show
from ..show_readiness_views import _can_manage_show_horses
from .common import _audit_event, _ensure_season_open, _team


def _pdf_response(show, payload, filename_suffix):
    pdf = render_hoofprint_pdf(payload)
    response = HttpResponse(pdf, content_type="application/pdf")
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in show.name).strip("-") or "show"
    response["Content-Disposition"] = f'inline; filename="{safe_name}-hoofprint-{filename_suffix}.pdf"'
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


def _hoofprint_context(show, payload, form, can_manage):
    latest = show.hoofprint_snapshots.order_by("-version").first()
    horse_lists = show.horse_list_documents.select_related("uploaded_by").all()[:10]
    return {
        "show": show,
        "payload": payload,
        "form": form,
        "latest_snapshot": latest,
        "snapshots": show.hoofprint_snapshots.all()[:10],
        "horse_lists": horse_lists,
        "latest_horse_list": horse_lists[0] if horse_lists else None,
        "can_manage": can_manage,
        "live_differs": live_differs_from_snapshot(payload, latest),
        "hoofprint_warnings": hoofprint_warnings(payload),
    }


@login_required
def show_hoofprint(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season", "team"), pk=show_pk, team=team)
    payload = build_hoofprint_payload(show)
    return render(request, "portal/show_hoofprint.html", _hoofprint_context(
        show, payload, HoofprintFinalizeForm(show=show), _can_manage_show_horses(request.user, show)
    ))


@login_required
def show_horse_list_upload(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season", "team"), pk=show_pk, team=team)
    if not _can_manage_show_horses(request.user, show):
        raise PermissionDenied
    _ensure_season_open(show.season)
    form = ShowHorseListDocumentForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        max_revision = show.horse_list_documents.aggregate(value=Max("revision"))["value"] or 0
        document = form.save(commit=False)
        document.show = show
        document.revision = max_revision + 1
        document.uploaded_by = request.user
        document.full_clean()
        document.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=document, season=show.season, summary=f"Uploaded show horse list revision {document.revision} for {show.name}")
        messages.success(request, f"Horse list revision {document.revision} uploaded.")
        return redirect("show_hoofprint", show_pk=show.pk)
    return render(request, "portal/show_horse_list_upload.html", {"show": show, "form": form, "title": "Upload show horse list"})


@login_required
def show_horse_list_document(request, show_pk, document_pk):
    team = _team(request.user)
    show = get_object_or_404(Show, pk=show_pk, team=team)
    document = get_object_or_404(ShowHorseListDocument, pk=document_pk, show=show)
    file_obj = document.document.open("rb")
    filename = Path(document.document.name).name
    response = FileResponse(file_obj, as_attachment=False, filename=filename)
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
def show_hoofprint_preview_pdf(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season", "team"), pk=show_pk, team=team)
    return _pdf_response(show, build_hoofprint_payload(show), "preview")


@login_required
def show_hoofprint_finalize(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season", "team"), pk=show_pk, team=team)
    if not _can_manage_show_horses(request.user, show):
        raise PermissionDenied
    _ensure_season_open(show.season)
    if request.method != "POST":
        return redirect("show_hoofprint", show_pk=show.pk)
    form = HoofprintFinalizeForm(request.POST, show=show)
    if not form.is_valid():
        payload = build_hoofprint_payload(show, request.POST)
        return render(request, "portal/show_hoofprint.html", _hoofprint_context(show, payload, form, True), status=400)
    payload = build_hoofprint_payload(show, form.cleaned_data)
    max_version = show.hoofprint_snapshots.aggregate(value=Max("version"))["value"] or 0
    snapshot = HoofprintSnapshot.objects.create(show=show, version=max_version + 1, payload=payload, finalized_by=request.user)
    _audit_event(team=team, actor=request.user, action=AuditEvent.Action.GENERATED, obj=snapshot, season=show.season, summary=f"Finalized Hoofprint v{snapshot.version} for {show.name}")
    messages.success(request, f"Hoofprint v{snapshot.version} finalized. The saved snapshot will not change if horse records are edited later.")
    return redirect("show_hoofprint_pdf", show_pk=show.pk, snapshot_pk=snapshot.pk)


@login_required
def show_hoofprint_pdf(request, show_pk, snapshot_pk):
    team = _team(request.user)
    show = get_object_or_404(Show, pk=show_pk, team=team)
    snapshot = get_object_or_404(HoofprintSnapshot, pk=snapshot_pk, show=show)
    return _pdf_response(show, snapshot.payload, f"v{snapshot.version}")
