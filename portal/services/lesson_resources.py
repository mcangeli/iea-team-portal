"""Physical resource scheduling for lesson occurrences.

LessonOccurrence owns the lesson. ResourceReservation owns occupancy of managed
facility resources. Moving/releasing a lesson resource preserves reservation
history rather than rewriting it.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from portal.model_modules.facilities import FacilitySpace, ResourceReservation
from portal.model_modules.lessons import LessonOccurrence


LESSON_OCCURRENCE_SOURCE = "lesson_occurrence"


def current_lesson_resource_reservation(occurrence):
    return (
        ResourceReservation.objects.filter(
            source_type=LESSON_OCCURRENCE_SOURCE,
            source_id=occurrence.pk,
            cancelled_at__isnull=True,
        )
        .select_related("space__facility")
        .order_by("-created_at", "-id")
        .first()
    )


def _validate_space(occurrence, space):
    if not space.reservable or not space.active:
        raise ValidationError({"space": "Choose an active reservable facility resource."})
    if space.facility.team_id != occurrence.series.program.team_id:
        raise ValidationError({"space": "Lesson and resource must belong to the same organization."})
    if not occurrence.ends_at:
        raise ValidationError("Lesson requires an end time before reserving a resource.")


@transaction.atomic
def assign_lesson_resource(occurrence, space):
    """Assign or move a lesson to a managed resource.

    The replacement reservation is validated before the old reservation is
    released, so a failed move leaves the existing reservation intact.
    """
    if occurrence.status in {LessonOccurrence.Status.COMPLETED, LessonOccurrence.Status.CANCELLED}:
        raise ValidationError("Completed or cancelled lessons cannot change resources.")
    _validate_space(occurrence, space)
    current = current_lesson_resource_reservation(occurrence)
    if current and current.space_id == space.pk:
        return current

    reservation = ResourceReservation(
        space=space,
        title=occurrence.title,
        starts_at=occurrence.starts_at,
        ends_at=occurrence.ends_at,
        source_type=LESSON_OCCURRENCE_SOURCE,
        source_id=occurrence.pk,
        notes=f"Lesson occurrence #{occurrence.pk}",
    )
    reservation.full_clean()
    reservation.save()

    if current:
        current.cancelled_at = timezone.now()
        current.save(update_fields=["cancelled_at", "updated_at"])

    occurrence.location = space.name
    occurrence.save(update_fields=["location", "updated_at"])
    return reservation


@transaction.atomic
def release_lesson_resource(occurrence, *, location=""):
    current = current_lesson_resource_reservation(occurrence)
    if current:
        current.cancelled_at = timezone.now()
        current.save(update_fields=["cancelled_at", "updated_at"])
    occurrence.location = location
    occurrence.save(update_fields=["location", "updated_at"])
    return current


@transaction.atomic
def sync_lesson_resource_times(occurrence):
    current = current_lesson_resource_reservation(occurrence)
    if not current:
        return None
    current.title = occurrence.title
    current.starts_at = occurrence.starts_at
    current.ends_at = occurrence.ends_at
    current.full_clean()
    current.save(update_fields=["title", "starts_at", "ends_at", "updated_at"])
    return current
