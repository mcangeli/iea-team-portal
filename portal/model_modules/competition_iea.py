"""IEA-specific reference models for ArenaLine competition workflows."""

from django.db import models


class IEAClassCatalogEntry(models.Model):
    """Immutable-by-version reference definition for an official IEA class.

    Organization-specific participation remains on ``SeasonClass``.  This
    model stores the official rulebook definition so later IEA rulebook
    seasons can coexist with historical definitions instead of mutating them.
    """

    class Discipline(models.TextChoices):
        HUNT_SEAT = "hunt_seat", "Hunt Seat"
        WESTERN = "western", "Western"
        DRESSAGE = "dressage", "Dressage"

    class TeamLevel(models.TextChoices):
        FUTURES = "futures", "Futures Team"
        UPPER = "upper", "Upper School Team"
        BOTH = "both", "Both teams"

    rulebook_season = models.CharField(
        max_length=20,
        help_text="Canonical IEA rulebook season, for example 2026-2027.",
    )
    discipline = models.CharField(max_length=30, choices=Discipline.choices)
    class_code = models.CharField(max_length=30)
    official_name = models.CharField(max_length=200)
    team_level = models.CharField(max_length=20, choices=TeamLevel.choices)
    ability_level = models.CharField(max_length=40, blank=True)
    class_family = models.CharField(max_length=60, blank=True)
    individual_points_enabled = models.BooleanField(default=True)
    team_points_enabled = models.BooleanField(default=True)
    season_assignable = models.BooleanField(
        default=True,
        help_text="Whether this class is a normal rider/season placement class.",
    )
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    source_rule = models.CharField(max_length=80, blank=True)
    source_revision_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["rulebook_season", "discipline", "sort_order", "class_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["rulebook_season", "discipline", "class_code"],
                name="unique_iea_catalog_class_version",
            )
        ]
        indexes = [
            models.Index(
                fields=["rulebook_season", "discipline", "active"],
                name="iea_catalog_version_idx",
            )
        ]

    def __str__(self):
        return f"{self.rulebook_season} · {self.class_code} · {self.official_name}"
