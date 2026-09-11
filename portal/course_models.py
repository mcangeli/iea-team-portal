from django.conf import settings
from django.db import models

from .models import Show, ShowClass


class ShowCourse(models.Model):
    """Coach-facing course information for a show.

    A course may apply to the whole show/ring or to selected ShowClass records.
    Coach notes remain private operational information; rider-facing publication can
    be added separately without exposing those notes.
    """

    class CourseType(models.TextChoices):
        OVER_FENCES = "over_fences", "Over fences"
        FLAT = "flat", "Flat / rail"
        WARMUP = "warmup", "Warm-up"
        OTHER = "other", "Other"

    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=160)
    course_type = models.CharField(max_length=20, choices=CourseType.choices, default=CourseType.OVER_FENCES)
    ring = models.CharField(max_length=100, blank=True)
    show_classes = models.ManyToManyField(ShowClass, blank=True, related_name="courses")
    course_walk_at = models.DateTimeField(null=True, blank=True)
    course_designer = models.CharField(max_length=120, blank=True)
    fence_count = models.PositiveSmallIntegerField(null=True, blank=True)
    combinations = models.CharField(max_length=160, blank=True)
    related_distances = models.CharField(max_length=255, blank=True)
    handy_options = models.CharField(max_length=255, blank=True)
    posted_notes = models.TextField(blank=True, help_text="General course details suitable for the show operations workspace.")
    coach_notes = models.TextField(blank=True, help_text="Private Coach/Admin notes. Not shown to riders or parents.")
    course_file = models.FileField(upload_to="course_files/", blank=True)
    external_link = models.URLField(blank=True)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_show_courses")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_show_courses")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["ring", "course_walk_at", "title", "id"]

    def __str__(self):
        return f"{self.show.name} — {self.title}"
