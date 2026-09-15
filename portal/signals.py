from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from . import season_class_code  # noqa: F401
from .committee_compat import remove_legacy_committee_membership, sync_legacy_committee_assignment
from .models import CommitteeAssignment, UserProfile


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=CommitteeAssignment)
def mirror_legacy_committee_assignment(sender, instance, **kwargs):
    sync_legacy_committee_assignment(instance)


@receiver(pre_delete, sender=CommitteeAssignment)
def remove_mirrored_legacy_committee_membership(sender, instance, **kwargs):
    remove_legacy_committee_membership(instance)
