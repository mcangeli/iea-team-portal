from django.core.exceptions import ValidationError
from django.db import models

from .horse_models import Horse
from .models import Season, Show, ShowClass


class ShowLeasedHorse(models.Model):
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="leased_horses")
    barn_name = models.CharField(max_length=120)
    show_name = models.CharField(max_length=120, blank=True)
    provider = models.CharField(max_length=160, blank=True, help_text="Barn, owner, or organization providing the leased horse.")
    breed = models.CharField(max_length=120, blank=True)
    sex = models.CharField(max_length=12, choices=Horse.Sex.choices, blank=True)
    size_type = models.CharField(max_length=80, blank=True)
    height_hands = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    show_classes = models.ManyToManyField(ShowClass, blank=True, related_name="leased_horses")
    available = models.BooleanField(default=True)
    crop_preference = models.CharField(max_length=12, choices=Horse.Preference.choices, default=Horse.Preference.OPTIONAL)
    spur_preference = models.CharField(max_length=12, choices=Horse.Preference.choices, default=Horse.Preference.OPTIONAL)
    lead_change = models.CharField(max_length=12, choices=Horse.LeadChange.choices, default=Horse.LeadChange.EITHER)
    riding_description = models.TextField(blank=True)
    restriction_notes = models.CharField(max_length=255, blank=True)
    coggins_status = models.CharField(max_length=40, blank=True, help_text="Optional show-day Coggins status or expiration note.")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["barn_name", "id"]
        constraints = [
            models.UniqueConstraint(fields=["show", "barn_name"], name="unique_leased_horse_name_per_show")
        ]

    @property
    def display_name(self):
        return self.barn_name or self.show_name

    def clean(self):
        super().clean()
        if self.show_id:
            for show_class in self.show_classes.all() if self.pk else []:
                if show_class.show_id != self.show_id:
                    raise ValidationError("Leased horse classes must belong to the same show.")

    def __str__(self):
        return f"{self.show.name} — {self.display_name} (leased)"
