from django.db import models

from portal.models import ShowClass


class ShowClassLiveState(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        PAUSED = "paused", "Paused"
        COMPLETE = "complete", "Complete"

    show_class = models.OneToOneField(
        ShowClass,
        on_delete=models.CASCADE,
        related_name="live_state",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    results_published = models.BooleanField(
        default=False,
        help_text="Publishes finalized placings for this class when public show results are enabled.",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="show_class_live_states_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["show_class__sort_order", "show_class__class_number", "show_class_id"]

    def __str__(self):
        return f"{self.show_class} — {self.get_status_display()}"
