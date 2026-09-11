from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .horse_models import HorseShowAssignment
from .post_show_horse_models import ShowHorseHistory, ShowHorseHistoryRecord
from .show_readiness_models import ShowLeasedHorse


def _class_snapshot(show_classes):
    return [
        {
            "id": show_class.pk,
            "class_number": show_class.class_number,
            "name": show_class.display_name,
        }
        for show_class in show_classes.order_by("sort_order", "class_number", "name")
    ]


@transaction.atomic
def build_post_show_horse_history(show, actor=None):
    history, _ = ShowHorseHistory.objects.select_for_update().get_or_create(
        show=show,
        defaults={"generated_by": actor},
    )
    if history.is_final:
        raise ValidationError("Final post-show horse history cannot be rebuilt.")

    history.generated_by = actor or history.generated_by
    history.save(update_fields=["generated_by", "updated_at"])
    history.records.all().delete()

    assignments = (
        HorseShowAssignment.objects.filter(show=show)
        .select_related("horse")
        .prefetch_related("show_classes", "show_classes__season_class")
    )
    for assignment in assignments:
        horse = assignment.horse
        ShowHorseHistoryRecord.objects.create(
            history=history,
            source_type=ShowHorseHistoryRecord.SourceType.REGISTRY,
            source_assignment=assignment,
            horse=horse,
            barn_name=horse.name,
            show_name=horse.show_name,
            provider=horse.owner_name or horse.home_barn,
            ownership_type=horse.ownership_type,
            actually_used=assignment.available,
            counted_as_contribution=assignment.available,
            class_snapshot=_class_snapshot(assignment.show_classes.all()),
            notes=assignment.notes,
        )

    leased_horses = ShowLeasedHorse.objects.filter(show=show).prefetch_related(
        "show_classes", "show_classes__season_class"
    )
    for leased in leased_horses:
        ShowHorseHistoryRecord.objects.create(
            history=history,
            source_type=ShowHorseHistoryRecord.SourceType.LEASED,
            source_leased_horse=leased,
            barn_name=leased.barn_name,
            show_name=leased.show_name,
            provider=leased.provider,
            ownership_type="leased",
            actually_used=leased.available,
            counted_as_contribution=leased.available,
            class_snapshot=_class_snapshot(leased.show_classes.all()),
            notes=leased.notes,
        )

    return history


@transaction.atomic
def finalize_post_show_horse_history(history, actor=None):
    history = ShowHorseHistory.objects.select_for_update().get(pk=history.pk)
    if history.is_final:
        return history
    if not history.records.exists():
        raise ValidationError("Add or generate at least one horse record before finalizing post-show history.")
    history.status = ShowHorseHistory.Status.FINAL
    history.finalized_by = actor
    history.finalized_at = timezone.now()
    history.save(update_fields=["status", "finalized_by", "finalized_at", "updated_at"])
    return history
