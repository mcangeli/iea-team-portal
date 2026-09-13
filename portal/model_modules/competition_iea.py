"""IEA-specific reference models for ArenaLine competition workflows."""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver


class IEAClassCatalogEntry(models.Model):
    """Immutable-by-version reference definition for an official IEA class.

    Organization-specific participation remains on ``SeasonClass``. This
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


class IEASeasonCatalogConfiguration(models.Model):
    """IEA catalog selection for one ArenaLine season.

    Keeping this as an IEA companion record avoids adding competition-specific
    fields to the generic ArenaLine ``Season`` model.
    """

    season = models.OneToOneField(
        "portal.Season",
        on_delete=models.CASCADE,
        related_name="iea_catalog_configuration",
    )
    rulebook_season = models.CharField(max_length=20)
    disciplines = models.JSONField(default=list, blank=True)
    configured_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["season_id"]

    def clean(self):
        super().clean()
        supported = {value for value, _label in IEAClassCatalogEntry.Discipline.choices}
        selected = set(self.disciplines or [])
        unsupported = selected - supported
        if unsupported:
            raise ValidationError({
                "disciplines": f"Unsupported IEA discipline(s): {', '.join(sorted(unsupported))}."
            })

    def __str__(self):
        disciplines = ", ".join(self.disciplines or []) or "No disciplines"
        return f"{self.season} · {self.rulebook_season} · {disciplines}"


from portal.models import (  # noqa: E402
    SeasonClass,
    SeasonMembership,
    ShowClass,
    ShowEntry,
    ShowResult,
)

_catalog_entry_field = models.ForeignKey(
    IEAClassCatalogEntry,
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    related_name="season_classes",
    help_text="Optional official IEA class definition for this season-specific class.",
)
_catalog_entry_field.contribute_to_class(SeasonClass, "catalog_entry")

_show_catalog_entry_field = models.ForeignKey(
    IEAClassCatalogEntry,
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    related_name="direct_show_classes",
    help_text="Official show-only IEA class definition when no SeasonClass should be created.",
)
_show_catalog_entry_field.contribute_to_class(ShowClass, "catalog_entry")


def _catalog_aware_show_class_team_level(instance):
    if instance.season_class_id:
        return instance.season_class.team_level
    if getattr(instance, "catalog_entry_id", None):
        return instance.catalog_entry.team_level
    return "both"


ShowClass.team_level = property(_catalog_aware_show_class_team_level)


WARMUP_PREREQUISITE_CODES = {
    "H7X/H8X": {"H7", "H8"},
    "H13X/H14X": {"H13", "H14"},
    "W7X/W8X": {"W7", "W8"},
    "W13X/W14X": {"W13", "W14"},
    "D7X/D8X": {"D7", "D8"},
    "D13X/D14X": {"D13", "D14"},
}


_original_show_entry_clean = ShowEntry.clean


def _catalog_aware_show_entry_clean(instance):
    _original_show_entry_clean(instance)
    if not instance.show_class_id or not instance.rider_id:
        return
    show_class = instance.show_class
    if show_class.season_class_id or not getattr(show_class, "catalog_entry_id", None):
        return

    catalog = show_class.catalog_entry
    if catalog.season_assignable:
        return

    show = show_class.show
    if show.competition_level != "regular":
        raise ValidationError("Official IEA show-only classes are regular-season offerings.")

    membership = SeasonMembership.objects.filter(
        rider=instance.rider,
        season=show.season,
    ).first()
    if not membership:
        raise ValidationError("This rider is not on the roster for this show's season.")
    if catalog.team_level != IEAClassCatalogEntry.TeamLevel.BOTH and membership.team_level != catalog.team_level:
        raise ValidationError("This show-only class belongs to a different team level than the rider's season roster.")

    code = (catalog.class_code or "").upper()
    if code == "VOC":
        from portal.iea_voc import voc_candidate_ids

        if instance.rider_id not in voc_candidate_ids(show):
            raise ValidationError(
                "This rider is not currently eligible for VOC from completed same-show H1/H2 results."
            )
        instance.is_point_rider = False
        instance.entry_type = ShowEntry.EntryType.INDIVIDUAL
        return

    prerequisite_codes = WARMUP_PREREQUISITE_CODES.get(code)
    if prerequisite_codes:
        eligible = ShowEntry.objects.filter(
            rider=instance.rider,
            show_class__show=show,
            show_class__class_number__in=prerequisite_codes,
        ).exclude(status=ShowEntry.Status.SCRATCHED)
        if instance.pk:
            eligible = eligible.exclude(pk=instance.pk)
        if not eligible.exists():
            codes = " or ".join(sorted(prerequisite_codes))
            raise ValidationError(
                f"This rider must already be entered in {codes} at this show before entering this warm-up."
            )

    instance.is_point_rider = False
    instance.entry_type = ShowEntry.EntryType.INDIVIDUAL


ShowEntry.clean = _catalog_aware_show_entry_clean


@receiver(pre_save, sender=ShowClass)
def snapshot_direct_iea_show_class(sender, instance, **kwargs):
    """Snapshot a direct show-only catalog entry onto legacy ShowClass fields."""
    if instance.season_class_id or not getattr(instance, "catalog_entry_id", None):
        return
    entry = instance.catalog_entry
    instance.name = entry.official_name
    instance.discipline = entry.discipline
    instance.class_number = entry.class_code
    if not instance.sort_order:
        instance.sort_order = entry.sort_order


@receiver(pre_save, sender=ShowResult)
def suppress_points_for_non_scoring_catalog_class(sender, instance, **kwargs):
    """Official show-only warm-ups and VOC never earn ArenaLine points."""
    if not instance.entry_id:
        return
    show_class = instance.entry.show_class
    entry = getattr(show_class, "catalog_entry", None)
    if entry and not entry.individual_points_enabled and not entry.team_points_enabled:
        instance.points = None
        instance.manual_points = False
