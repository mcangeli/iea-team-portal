"""ArenaLine physical facility and resource foundation."""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Facility(models.Model):
    team = models.ForeignKey("portal.Team", on_delete=models.CASCADE, related_name="facilities")
    name = models.CharField(max_length=180)
    address = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(fields=["team", "name"], name="unique_facility_name_per_team"),
        ]

    def __str__(self):
        return self.name


class FacilitySpace(models.Model):
    class SpaceType(models.TextChoices):
        BARN = "barn", "Barn / Building"
        ARENA = "arena", "Arena / Ring"
        STALL = "stall", "Stall"
        PASTURE = "pasture", "Pasture / Paddock"
        FEED_ROOM = "feed_room", "Feed Room"
        TACK_ROOM = "tack_room", "Tack Room"
        STORAGE = "storage", "Storage"
        WASH_AREA = "wash_area", "Wash / Grooming Area"
        OTHER = "other", "Other"

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="spaces")
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children"
    )
    name = models.CharField(max_length=180)
    space_type = models.CharField(max_length=24, choices=SpaceType.choices, default=SpaceType.OTHER)
    reservable = models.BooleanField(default=False)
    housing_capable = models.BooleanField(default=False)
    turnout_capable = models.BooleanField(default=False)
    inventory_storage_capable = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["facility__name", "name", "id"]
        constraints = [
            models.UniqueConstraint(fields=["facility", "parent", "name"], name="unique_facility_space_parent_name"),
        ]

    @property
    def team_id(self):
        return self.facility.team_id

    def clean(self):
        super().clean()
        if not self.parent_id:
            return
        if self.pk and self.parent_id == self.pk:
            raise ValidationError({"parent": "A facility space cannot be its own parent."})
        if self.parent.facility_id != self.facility_id:
            raise ValidationError({"parent": "Parent space must belong to the same facility."})
        ancestor = self.parent
        visited = set()
        while ancestor:
            if ancestor.pk in visited or (self.pk and ancestor.pk == self.pk):
                raise ValidationError({"parent": "Facility space hierarchy cannot contain a cycle."})
            visited.add(ancestor.pk)
            ancestor = ancestor.parent

    def __str__(self):
        return f"{self.facility} — {self.name}"


class _HorseSpaceAssignment(models.Model):
    horse = models.ForeignKey("portal.Horse", on_delete=models.CASCADE)
    space = models.ForeignKey(FacilitySpace, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    capability_field = None
    assignment_label = "assignment"

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be before start date."})
        if self.horse_id and self.space_id:
            if self.horse.team_id != self.space.facility.team_id:
                raise ValidationError({"space": "Horse and facility space must belong to the same organization."})
            if self.capability_field and not getattr(self.space, self.capability_field):
                raise ValidationError({"space": f"Selected space cannot be used for this {self.assignment_label}."})

    def _validate_overlap(self, queryset, message):
        if not self.horse_id or not self.start_date:
            return
        overlapping = queryset.filter(horse_id=self.horse_id).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=self.start_date)
        )
        if self.end_date:
            overlapping = overlapping.filter(start_date__lte=self.end_date)
        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)
        if overlapping.exists():
            raise ValidationError({"start_date": message})


class HorseStallAssignment(_HorseSpaceAssignment):
    horse = models.ForeignKey("portal.Horse", on_delete=models.CASCADE, related_name="stall_assignments")
    space = models.ForeignKey(FacilitySpace, on_delete=models.PROTECT, related_name="stall_assignments")

    capability_field = "housing_capable"
    assignment_label = "stall housing"

    class Meta:
        ordering = ["-start_date", "-id"]

    def clean(self):
        super().clean()
        self._validate_overlap(
            HorseStallAssignment.objects.all(),
            "Horse already has an overlapping stall assignment.",
        )

    def __str__(self):
        return f"{self.horse} — {self.space}"


class HorsePastureAssignment(_HorseSpaceAssignment):
    class TurnoutType(models.TextChoices):
        PRIMARY = "primary", "Primary"
        TEMPORARY = "temporary", "Temporary"
        OTHER = "other", "Other"

    horse = models.ForeignKey("portal.Horse", on_delete=models.CASCADE, related_name="pasture_assignments")
    space = models.ForeignKey(FacilitySpace, on_delete=models.PROTECT, related_name="pasture_assignments")
    turnout_type = models.CharField(max_length=16, choices=TurnoutType.choices, default=TurnoutType.PRIMARY)

    capability_field = "turnout_capable"
    assignment_label = "pasture turnout"

    class Meta:
        ordering = ["-start_date", "-id"]

    def clean(self):
        super().clean()
        if self.turnout_type == self.TurnoutType.PRIMARY:
            self._validate_overlap(
                HorsePastureAssignment.objects.filter(turnout_type=self.TurnoutType.PRIMARY),
                "Horse already has an overlapping primary pasture assignment.",
            )

    def __str__(self):
        return f"{self.horse} — {self.space}"


class ResourceReservation(models.Model):
    space = models.ForeignKey(FacilitySpace, on_delete=models.PROTECT, related_name="reservations")
    title = models.CharField(max_length=180)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    source_type = models.CharField(max_length=80, blank=True)
    source_id = models.PositiveBigIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at", "id"]

    def clean(self):
        super().clean()
        if self.space_id and not self.space.reservable:
            raise ValidationError({"space": "Selected facility space is not reservable."})
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "Reservation end must be after its start."})

    def __str__(self):
        return f"{self.title} — {self.space}"
