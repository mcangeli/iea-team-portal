from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Rider


class RiderLifecycle(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        GRADUATED = "graduated", "Graduated"
        LEFT_TEAM = "left_team", "Left Team"
        INACTIVE = "inactive", "Inactive"

    rider = models.OneToOneField(
        Rider,
        on_delete=models.CASCADE,
        related_name="lifecycle",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    graduation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    ended_on = models.DateField(
        null=True,
        blank=True,
        help_text="Optional date the rider graduated, left the team, or otherwise became inactive.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rider__last_name", "rider__first_name"]

    @property
    def is_current(self):
        return self.status == self.Status.ACTIVE

    def __str__(self):
        return f"{self.rider} — {self.get_status_display()}"


@receiver(post_save, sender=Rider)
def ensure_rider_lifecycle(sender, instance, created, **kwargs):
    """Keep the legacy Rider.active flag and lifecycle status compatible.

    Existing code already treats Rider.active as the current-roster gate. New
    lifecycle UI writes both values, while legacy profile edits that toggle
    Rider.active are reflected back into the lifecycle record.
    """
    lifecycle, lifecycle_created = RiderLifecycle.objects.get_or_create(
        rider=instance,
        defaults={
            "status": (
                RiderLifecycle.Status.ACTIVE
                if instance.active
                else RiderLifecycle.Status.INACTIVE
            )
        },
    )
    if lifecycle_created:
        return

    should_be_active = lifecycle.status == RiderLifecycle.Status.ACTIVE
    if instance.active != should_be_active:
        lifecycle.status = (
            RiderLifecycle.Status.ACTIVE
            if instance.active
            else RiderLifecycle.Status.INACTIVE
        )
        lifecycle.graduation_year = None if instance.active else lifecycle.graduation_year
        lifecycle.ended_on = None if instance.active else lifecycle.ended_on
        lifecycle.save(update_fields=[
            "status", "graduation_year", "ended_on", "updated_at"
        ])
