from django.db import models

from portal.models import Show, ShowClass


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


class ShowClassRingAssignment(models.Model):
    show_class = models.OneToOneField(
        ShowClass,
        on_delete=models.CASCADE,
        related_name="ring_assignment",
    )
    ring = models.CharField(
        max_length=80,
        blank=True,
        help_text="Show-day ring name, such as 'Ring 1', 'Ring 2', or 'Main Arena'. Blank uses Main ring.",
    )
    updated_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="show_class_ring_assignments_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["ring", "show_class__sort_order", "show_class_id"]

    @property
    def display_name(self):
        return self.ring.strip() or "Main ring"

    def __str__(self):
        return f"{self.show_class} — {self.display_name}"


class SpectatorShowUpdate(models.Model):
    class Kind(models.TextChoices):
        ANNOUNCEMENT = "announcement", "Announcement"
        DELAY = "delay", "Delay"
        BREAK = "break", "Break"
        SCHEDULE = "schedule", "Schedule update"

    show = models.ForeignKey(
        Show,
        on_delete=models.CASCADE,
        related_name="spectator_updates",
    )
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.ANNOUNCEMENT,
    )
    ring = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=120)
    message = models.CharField(max_length=280, blank=True)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="spectator_show_updates_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    @property
    def ring_display(self):
        return self.ring.strip() or "Main ring"

    def __str__(self):
        scope = f"{self.ring_display} · " if self.ring else ""
        return f"{self.show} — {scope}{self.title}"
