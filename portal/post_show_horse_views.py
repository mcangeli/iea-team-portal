from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Show
from .post_show_horse_forms import ShowHorseHistoryForm, ShowHorseHistoryRecordForm
from .post_show_horse_models import ShowHorseHistory, ShowHorseHistoryRecord
from .post_show_horse_service import build_post_show_horse_history, finalize_post_show_horse_history
from .view_modules.common import _can_manage, _team


def _history_for_team(team, show_pk):
    show = get_object_or_404(Show.objects.select_related("season", "team"), pk=show_pk, team=team)
    history = ShowHorseHistory.objects.filter(show=show).first()
    return show, history


@login_required
def post_show_horse_history(request, show_pk):
    if not _can_manage(request.user):
        raise PermissionDenied
    team = _team(request.user)
    show, history = _history_for_team(team, show_pk)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "generate":
            try:
                history = build_post_show_horse_history(show, request.user)
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
            else:
                messages.success(request, "Draft post-show horse history generated from the current show horse plan.")
            return redirect("post_show_horse_history", show_pk=show.pk)

        if not history:
            messages.error(request, "Generate a draft before editing or finalizing post-show horse history.")
            return redirect("post_show_horse_history", show_pk=show.pk)

        if action == "save_notes":
            if history.is_final:
                messages.error(request, "Final post-show horse history is locked.")
            else:
                form = ShowHorseHistoryForm(request.POST, instance=history)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Post-show horse history notes saved.")
                else:
                    for error in form.non_field_errors():
                        messages.error(request, error)
            return redirect("post_show_horse_history", show_pk=show.pk)

        if action == "finalize":
            try:
                finalize_post_show_horse_history(history, request.user)
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
            else:
                messages.success(request, "Post-show horse history finalized and locked.")
            return redirect("post_show_horse_history", show_pk=show.pk)

    history_form = ShowHorseHistoryForm(instance=history) if history else None
    records = (
        history.records.select_related("horse", "source_assignment__horse", "source_leased_horse")
        if history else []
    )
    return render(request, "portal/post_show_horse_history.html", {
        "show": show,
        "history": history,
        "history_form": history_form,
        "records": records,
    })


@login_required
def post_show_horse_record_edit(request, show_pk, record_pk):
    if not _can_manage(request.user):
        raise PermissionDenied
    team = _team(request.user)
    show, history = _history_for_team(team, show_pk)
    if not history:
        raise PermissionDenied
    record = get_object_or_404(ShowHorseHistoryRecord, pk=record_pk, history=history)
    if history.is_final:
        messages.error(request, "Final post-show horse history is locked.")
        return redirect("post_show_horse_history", show_pk=show.pk)

    form = ShowHorseHistoryRecordForm(request.POST or None, instance=record, history=history)
    if form.is_valid():
        form.save()
        messages.success(request, f"Updated final horse record for {record.display_name}.")
        return redirect("post_show_horse_history", show_pk=show.pk)

    return render(request, "portal/post_show_horse_record_form.html", {
        "show": show,
        "history": history,
        "record": record,
        "form": form,
    })


@login_required
@require_POST
def post_show_horse_record_add(request, show_pk):
    if not _can_manage(request.user):
        raise PermissionDenied
    team = _team(request.user)
    show, history = _history_for_team(team, show_pk)
    if not history or history.is_final:
        messages.error(request, "Generate an editable draft before adding a horse record.")
        return redirect("post_show_horse_history", show_pk=show.pk)

    horse_id = request.POST.get("horse")
    from .horse_models import Horse
    horse = get_object_or_404(Horse, pk=horse_id, team=team)
    if history.records.filter(horse=horse, actually_used=True).exists():
        messages.info(request, f"{horse.display_name} is already represented in this draft.")
        return redirect("post_show_horse_history", show_pk=show.pk)

    ShowHorseHistoryRecord.objects.create(
        history=history,
        source_type=ShowHorseHistoryRecord.SourceType.OTHER,
        horse=horse,
        barn_name=horse.name,
        show_name=horse.show_name,
        provider=horse.owner_name or horse.home_barn,
        ownership_type=horse.ownership_type,
        actually_used=True,
        counted_as_contribution=False,
        class_snapshot=[],
        notes="Added during post-show reconciliation.",
    )
    messages.success(request, f"Added {horse.display_name} to the post-show history draft.")
    return redirect("post_show_horse_history", show_pk=show.pk)
