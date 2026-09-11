from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Max

from ..hoofprint_forms import HoofprintFinalizeForm
from ..hoofprint_models import HoofprintSnapshot
from ..hoofprint_service import build_hoofprint_payload, render_hoofprint_pdf
from ..models import AuditEvent, Show
from .common import _audit_event, _can_manage, _ensure_season_open, _team


def _pdf_response(show, payload, filename_suffix):
    pdf = render_hoofprint_pdf(payload)
    response = HttpResponse(pdf, content_type="application/pdf")
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in show.name).strip("-") or "show"
    response["Content-Disposition"] = f'inline; filename="{safe_name}-hoofprint-{filename_suffix}.pdf"'
    return response


@login_required
def show_hoofprint(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season", "team"), pk=show_pk, team=team)
    latest = show.hoofprint_snapshots.order_by("-version").first()
    form = HoofprintFinalizeForm(show=show)
    payload = build_hoofprint_payload(show)
    return render(request, "portal/show_hoofprint.html", {
        "show": show,
        "payload": payload,
        "form": form,
        "latest_snapshot": latest,
        "snapshots": show.hoofprint_snapshots.all()[:10],
        "can_manage": _can_manage(request.user),
    })


@login_required
def show_hoofprint_preview_pdf(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season", "team"), pk=show_pk, team=team)
    payload = build_hoofprint_payload(show)
    return _pdf_response(show, payload, "preview")


@login_required
def show_hoofprint_finalize(request, show_pk):
    if not _can_manage(request.user):
        raise PermissionDenied
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season", "team"), pk=show_pk, team=team)
    _ensure_season_open(show.season)
    if request.method != "POST":
        return redirect("show_hoofprint", show_pk=show.pk)
    form = HoofprintFinalizeForm(request.POST, show=show)
    if not form.is_valid():
        payload = build_hoofprint_payload(show, request.POST)
        return render(request, "portal/show_hoofprint.html", {
            "show": show, "payload": payload, "form": form,
            "latest_snapshot": show.hoofprint_snapshots.order_by("-version").first(),
            "snapshots": show.hoofprint_snapshots.all()[:10], "can_manage": True,
        }, status=400)
    payload = build_hoofprint_payload(show, form.cleaned_data)
    max_version = show.hoofprint_snapshots.aggregate(value=Max("version"))["value"] or 0
    snapshot = HoofprintSnapshot.objects.create(
        show=show, version=max_version + 1, payload=payload, finalized_by=request.user
    )
    _audit_event(
        team=team, actor=request.user, action=AuditEvent.Action.GENERATED,
        obj=snapshot, season=show.season,
        summary=f"Finalized Hoofprint v{snapshot.version} for {show.name}",
    )
    messages.success(request, f"Hoofprint v{snapshot.version} finalized. The saved snapshot will not change if horse records are edited later.")
    return redirect("show_hoofprint_pdf", show_pk=show.pk, snapshot_pk=snapshot.pk)


@login_required
def show_hoofprint_pdf(request, show_pk, snapshot_pk):
    team = _team(request.user)
    show = get_object_or_404(Show, pk=show_pk, team=team)
    snapshot = get_object_or_404(HoofprintSnapshot, pk=snapshot_pk, show=show)
    return _pdf_response(show, snapshot.payload, f"v{snapshot.version}")
