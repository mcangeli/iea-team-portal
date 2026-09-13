"""Public form namespace for ArenaLine.

The v2.9 cleanup starts decomposing the legacy monolithic forms module by keeping
its existing forms available while allowing domain forms to be normalized without
startup-time monkey patches.
"""

from django import forms

from .forms_legacy import *  # noqa: F401,F403
from .forms_legacy import ReimbursementRequestForm as _LegacyReimbursementRequestForm
from .forms_legacy import ShowClassForm as _LegacyShowClassForm
from .model_modules.competition_iea import IEAClassCatalogEntry


class ReimbursementRequestForm(_LegacyReimbursementRequestForm):
    """Team-bound reimbursement form with explicit model-validation context."""

    def __init__(self, *args, team=None, user=None, **kwargs):
        super().__init__(*args, team=team, user=user, **kwargs)
        if team is not None:
            self.instance.team = team


class IEASeasonCatalogConfigurationForm(forms.Form):
    """Configure the official IEA catalog backing one ArenaLine season."""

    rulebook_season = forms.ChoiceField(label="IEA rulebook season")
    disciplines = forms.MultipleChoiceField(
        label="Disciplines",
        choices=IEAClassCatalogEntry.Discipline.choices,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, initial_config=None, **kwargs):
        super().__init__(*args, **kwargs)
        seasons = list(
            IEAClassCatalogEntry.objects.filter(active=True, season_assignable=True)
            .order_by("-rulebook_season")
            .values_list("rulebook_season", flat=True)
            .distinct()
        )
        self.fields["rulebook_season"].choices = [(value, value) for value in seasons]
        if initial_config is not None:
            self.initial.setdefault("rulebook_season", initial_config.rulebook_season)
            self.initial.setdefault("disciplines", initial_config.disciplines)


class _CatalogAwareSeasonClassChoiceField(forms.ModelChoiceField):
    """Make official versus exception classes obvious in Show Setup."""

    def label_from_instance(self, obj):
        code = f"{obj.class_code} · " if obj.class_code else ""
        if obj.catalog_entry_id:
            return f"Official IEA · {code}{obj.name}"
        return f"Manual / special case · {code}{obj.name}"


class ShowClassForm(_LegacyShowClassForm):
    """Catalog-aware ShowClass form for ArenaLine v3.

    Catalog-backed classes are the normal IEA path. Existing manual/special
    SeasonClass rows remain usable only with an explicit exception acknowledgement.
    """

    use_manual_special_class = forms.BooleanField(
        required=False,
        label="Use a manual / special-case season class",
        help_text=(
            "Required only when selecting a season class that is not backed by the "
            "configured official IEA catalog. Use this for historical or deliberate exceptions."
        ),
    )

    def __init__(self, *args, show=None, **kwargs):
        super().__init__(*args, show=show, **kwargs)
        self.show = show
        if not show:
            return

        used = show.classes.exclude(pk=getattr(self.instance, "pk", None)).values_list(
            "season_class_id", flat=True
        )
        available = show.season.season_classes.filter(active=True).exclude(pk__in=used)

        config = getattr(show.season, "iea_catalog_configuration", None)
        self.catalog_configuration = config
        if config:
            available = available.filter(
                discipline__in=config.disciplines,
            ) | show.season.season_classes.filter(
                active=True,
                catalog_entry__isnull=True,
            ).exclude(pk__in=used)
            available = available.distinct()

        field = _CatalogAwareSeasonClassChoiceField(
            queryset=available.select_related("catalog_entry").order_by(
                "discipline", "team_level", "sort_order", "name"
            ),
            label="Season class",
            help_text=(
                "Official IEA catalog classes are the normal choice. Manual/special-case "
                "classes require the exception checkbox below."
            ) if config else self.fields["season_class"].help_text,
        )
        if getattr(self.instance, "season_class_id", None):
            field.initial = self.instance.season_class_id
        self.fields["season_class"] = field

    def clean(self):
        cleaned = super().clean()
        season_class = cleaned.get("season_class")
        if not season_class or not self.show:
            return cleaned

        if season_class.season_id != self.show.season_id or not season_class.active:
            self.add_error("season_class", "Choose an active class from this show's season.")
            return cleaned

        config = getattr(self, "catalog_configuration", None)
        if not config:
            return cleaned

        entry = getattr(season_class, "catalog_entry", None)
        if entry:
            if entry.rulebook_season != config.rulebook_season:
                self.add_error(
                    "season_class",
                    "Choose a class from this season's configured IEA rulebook version.",
                )
            elif entry.discipline not in config.disciplines:
                self.add_error(
                    "season_class",
                    "Choose a class from one of this season's configured IEA disciplines.",
                )
        elif not cleaned.get("use_manual_special_class"):
            self.add_error(
                "use_manual_special_class",
                "Confirm the manual/special-case exception to use this non-catalog class.",
            )

        return cleaned
