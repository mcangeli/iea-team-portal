from django.core.exceptions import PermissionDenied

from portal.model_modules.people import OrganizationRoleAssignment
from portal.models import UserProfile


def _profile_role(user):
    return getattr(getattr(user, "profile", None), "role", None)


def is_lesson_admin(user):
    return bool(user.is_superuser or _profile_role(user) == UserProfile.Role.ADMIN)


def is_iea_lesson_manager(user):
    """IEA team lessons are operated by Coaches (and administrators)."""
    return bool(is_lesson_admin(user) or _profile_role(user) == UserProfile.Role.COACH)


def is_barn_lesson_manager(user):
    """General barn lessons are operated by Trainers/Assistant Trainers (and administrators)."""
    if is_lesson_admin(user):
        return True
    person = getattr(user, "arena_person", None)
    if not person or not person.active:
        return False
    return person.role_assignments.filter(
        active=True,
        role__in=[
            OrganizationRoleAssignment.Role.TRAINER,
            OrganizationRoleAssignment.Role.ASSISTANT_TRAINER,
        ],
    ).exists()


def can_manage_lesson_occurrence(user, occurrence):
    return is_iea_lesson_manager(user) if occurrence.series.is_iea_series else is_barn_lesson_manager(user)


def can_manage_lesson_series(user, series):
    return is_iea_lesson_manager(user) if series.is_iea_series else is_barn_lesson_manager(user)


def require_lesson_occurrence_manager(user, occurrence):
    if not can_manage_lesson_occurrence(user, occurrence):
        label = "Coach" if occurrence.series.is_iea_series else "Trainer or Assistant Trainer"
        raise PermissionDenied(f"{label} lesson-management access is required.")


def require_barn_lesson_manager(user):
    if not is_barn_lesson_manager(user):
        raise PermissionDenied("Trainer or Assistant Trainer lesson-management access is required.")


def require_iea_lesson_manager(user):
    if not is_iea_lesson_manager(user):
        raise PermissionDenied("Coach lesson-management access is required.")
