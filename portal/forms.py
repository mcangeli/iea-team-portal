"""Public form namespace for ArenaLine.

The v2.9 cleanup starts decomposing the legacy monolithic forms module by keeping
its existing forms available while allowing domain forms to be normalized without
startup-time monkey patches.
"""

from django import forms
from django.db import transaction

from .forms_legacy import *  # noqa: F401,F403
from .forms_legacy import ReimbursementRequestForm as _LegacyReimbursementRequestForm
from .forms_legacy import SeasonClassForm as _LegacySeasonClassForm
from .forms_legacy import ShowClassForm as _LegacyShowClassForm
from .forms_legacy import ShowEntryForm as _LegacyShowEntryForm
from .forms_legacy import UserOnboardingForm as _LegacyUserOnboardingForm
from .forms_legacy import UserAccountEditForm as _LegacyUserAccountEditForm
from .model_modules.competition_iea import IEAClassCatalogEntry
from .model_modules.people import IEAParticipant
from .people_accounts import sync_user_person_after_account_edit, sync_user_person_identity


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


class _CatalogEntryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return (
            f"{obj.class_code} · {obj.official_name} · "
            f"{obj.get_team_level_display()} · {obj.get_discipline_display()}"
        )


class SeasonClassForm(_LegacySeasonClassForm):
    """SeasonClass editor with a first-class official IEA catalog path."""

    official_catalog_entry = _CatalogEntryChoiceField(
        queryset=IEAClassCatalogEntry.objects.none(),
        required=False,
        label="Official IEA class",
        help_text="Choose an official class to create or link this season class from the configured IEA rulebook.",
    )
    sync_from_catalog = forms.BooleanField(
        required=False,
        label="Sync details from official catalog",
        help_text="Refresh the class name, code, team level, discipline, and ordering from the selected official definition.",
    )

    def __init__(self, *args, season=None, **kwargs):
        super().__init__(*args, season=season, **kwargs)
        self.season = season or (self.instance.season if self.instance and self.instance.pk else None)
        self.catalog_configuration = None
        self.fields["name"].required = False
        self.fields["team_level"].required = False
        self.fields["discipline"].required = False

        if not self.season:
            self.fields["official_catalog_entry"].queryset = IEAClassCatalogEntry.objects.none()
            return

        self.catalog_configuration = getattr(self.season, "iea_catalog_configuration", None)
        if not self.catalog_configuration:
            self.fields["official_catalog_entry"].queryset = IEAClassCatalogEntry.objects.none()
            self.fields["official_catalog_entry"].help_text = (
                "Configure the season's IEA Class Catalog first to select an official class here."
            )
            return

        linked_elsewhere = self.season.season_classes.exclude(
            pk=getattr(self.instance, "pk", None)
        ).exclude(catalog_entry__isnull=True).values_list("catalog_entry_id", flat=True)

        self.fields["official_catalog_entry"].queryset = IEAClassCatalogEntry.objects.filter(
            rulebook_season=self.catalog_configuration.rulebook_season,
            discipline__in=self.catalog_configuration.disciplines,
            active=True,
            season_assignable=True,
        ).exclude(pk__in=linked_elsewhere).order_by("discipline", "team_level", "sort_order", "class_code")

        if getattr(self.instance, "catalog_entry_id", None):
            self.initial.setdefault("official_catalog_entry", self.instance.catalog_entry_id)

        if not getattr(self.instance, "pk", None):
            self.fields["sync_from_catalog"].widget = forms.HiddenInput()
            self.initial["sync_from_catalog"] = True

    def clean(self):
        cleaned = super(_LegacySeasonClassForm, self).clean()
        entry = cleaned.get("official_catalog_entry")
        current_entry_id = getattr(self.instance, "catalog_entry_id", None)
        sync_requested = bool(cleaned.get("sync_from_catalog"))

        if entry:
            config = self.catalog_configuration
            if not config:
                self.add_error("official_catalog_entry", "Configure the season's IEA Class Catalog first.")
                return cleaned
            if entry.rulebook_season != config.rulebook_season or entry.discipline not in config.disciplines:
                self.add_error("official_catalog_entry", "Choose a class from this season's configured IEA catalog.")
                return cleaned
            if not self.instance.pk or current_entry_id != entry.pk or sync_requested:
                cleaned["name"] = entry.official_name
                cleaned["team_level"] = entry.team_level
                cleaned["discipline"] = entry.discipline
                cleaned["sort_order"] = entry.sort_order
                cleaned.setdefault("active", True)
        else:
            if current_entry_id:
                entry = self.instance.catalog_entry
            if not (cleaned.get("name") or "").strip():
                self.add_error("name", "Enter a class name or choose an official IEA class.")
            if not cleaned.get("team_level"):
                self.add_error("team_level", "Choose the team level for this class.")
            if not cleaned.get("discipline"):
                self.add_error("discipline", "Choose the discipline for this class.")

        name = (cleaned.get("name") or "").strip()
        team_level = cleaned.get("team_level")
        discipline = cleaned.get("discipline")
        if self.season and name and team_level and discipline:
            qs = self.season.season_classes.filter(
                name__iexact=name,
                team_level=team_level,
                discipline=discipline,
            ).exclude(pk=getattr(self.instance, "pk", None))
            if qs.exists():
                self.add_error(
                    "name",
                    "This season already has a class with this name for the selected discipline and team level.",
                )
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        selected = self.cleaned_data.get("official_catalog_entry")
        existing = getattr(obj, "catalog_entry", None) if getattr(obj, "catalog_entry_id", None) else None
        entry = selected or existing
        if entry:
            obj.catalog_entry = entry
            if (
                not obj.pk
                or getattr(self.instance, "catalog_entry_id", None) != entry.pk
                or self.cleaned_data.get("sync_from_catalog")
            ):
                obj.name = entry.official_name
                obj.team_level = entry.team_level
                obj.discipline = entry.discipline
                obj.sort_order = entry.sort_order
                obj.class_code = entry.class_code
        if commit:
            obj.save()
            self.save_m2m()
        return obj


class _CatalogAwareSeasonClassChoiceField(forms.ModelChoiceField):
    """Make official versus exception classes obvious in Show Setup."""

    def label_from_instance(self, obj):
        code = f"{obj.class_code} · " if obj.class_code else ""
        if obj.catalog_entry_id:
            return f"Official IEA · {code}{obj.name}"
        return f"Manual / special case · {code}{obj.name}"


class ShowClassForm(_LegacyShowClassForm):
    """Catalog-aware ShowClass form for ArenaLine v3.

    Normal IEA classes reference SeasonClass. Official show-only offerings such
    as warm-ups and VOC reference the catalog directly and never become rider
    season assignments.
    """

    official_show_only_class = _CatalogEntryChoiceField(
        queryset=IEAClassCatalogEntry.objects.none(),
        required=False,
        label="Official show-only IEA class",
        help_text=(
            "Optional rulebook-defined offering for this show only. These classes are not "
            "added to rider season assignments and do not earn season points."
        ),
    )
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
        self.catalog_configuration = None
        self.fields["season_class"].required = False
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

            used_show_only = show.classes.exclude(
                pk=getattr(self.instance, "pk", None)
            ).exclude(catalog_entry__isnull=True).values_list("catalog_entry_id", flat=True)
            self.fields["official_show_only_class"].queryset = IEAClassCatalogEntry.objects.filter(
                rulebook_season=config.rulebook_season,
                discipline__in=config.disciplines,
                active=True,
                season_assignable=False,
            ).exclude(pk__in=used_show_only).order_by(
                "discipline", "team_level", "sort_order", "class_code"
            )
        else:
            self.fields["official_show_only_class"].queryset = IEAClassCatalogEntry.objects.none()
            self.fields["official_show_only_class"].help_text = (
                "Configure the season's IEA Class Catalog first to use official show-only offerings."
            )

        field = _CatalogAwareSeasonClassChoiceField(
            queryset=available.select_related("catalog_entry").order_by(
                "discipline", "team_level", "sort_order", "name"
            ),
            required=False,
            label="Season class",
            help_text=(
                "Official IEA season classes are the normal choice. Manual/special-case "
                "classes require the exception checkbox below."
            ) if config else self.fields["season_class"].help_text,
        )
        if getattr(self.instance, "season_class_id", None):
            field.initial = self.instance.season_class_id
        self.fields["season_class"] = field
        if getattr(self.instance, "catalog_entry_id", None) and not getattr(self.instance, "season_class_id", None):
            self.initial.setdefault("official_show_only_class", self.instance.catalog_entry_id)

    def clean(self):
        cleaned = super().clean()
        season_class = cleaned.get("season_class")
        show_only = cleaned.get("official_show_only_class")
        if not self.show:
            return cleaned

        if season_class and show_only:
            self.add_error("official_show_only_class", "Choose either a season class or a show-only class, not both.")
            return cleaned
        if not season_class and not show_only:
            self.add_error("season_class", "Choose a season class or an official show-only IEA class.")
            return cleaned

        config = self.catalog_configuration
        if show_only:
            if not config:
                self.add_error("official_show_only_class", "Configure the season's IEA Class Catalog first.")
                return cleaned
            if (
                show_only.rulebook_season != config.rulebook_season
                or show_only.discipline not in config.disciplines
                or show_only.season_assignable
            ):
                self.add_error("official_show_only_class", "Choose a show-only class from this season's configured IEA catalog.")
            if (show_only.class_code or "").upper() == "VOC" and self.show.competition_level != "regular":
                self.add_error("official_show_only_class", "VOC may only be offered at a regular-season show.")
            return cleaned

        if season_class.season_id != self.show.season_id or not season_class.active:
            self.add_error("season_class", "Choose an active class from this show's season.")
            return cleaned
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

    def save(self, commit=True):
        obj = super().save(commit=False)
        show_only = self.cleaned_data.get("official_show_only_class")
        if show_only:
            obj.season_class = None
            obj.catalog_entry = show_only
            obj.name = show_only.official_name
            obj.discipline = show_only.discipline
            obj.class_number = show_only.class_code
            obj.sort_order = show_only.sort_order
        else:
            obj.catalog_entry = None
        if commit:
            obj.save()
            self.save_m2m()
        return obj


class ShowEntryForm(_LegacyShowEntryForm):
    """Catalog-aware rider entry form, including same-show VOC eligibility."""

    def __init__(self, *args, show=None, team=None, **kwargs):
        super().__init__(*args, show=show, team=team, **kwargs)
        if not show:
            return

        selected_class_id = self.data.get("show_class") if self.is_bound else getattr(self.instance, "show_class_id", None)
        if not selected_class_id:
            return
        try:
            selected = show.classes.select_related("catalog_entry", "season_class").get(pk=selected_class_id)
        except (ShowClass.DoesNotExist, ValueError, TypeError):
            return

        catalog = getattr(selected, "catalog_entry", None)
        if not catalog or (catalog.class_code or "").upper() != "VOC":
            return

        from portal.iea_voc import voc_candidate_ids

        candidate_ids = voc_candidate_ids(show)
        legacy_rider_ids = [
            value for kind, value in candidate_ids if kind == "rider"
        ]
        person_ids = [
            value for kind, value in candidate_ids if kind == "person"
        ]
        participant_rider_ids = IEAParticipant.objects.filter(
            person_id__in=person_ids,
            legacy_rider__isnull=False,
        ).values_list("legacy_rider_id", flat=True)
        self.fields["rider"].queryset = Rider.objects.filter(
            pk__in=set(legacy_rider_ids) | set(participant_rider_ids),
            team=team,
            active=True,
        )
        self.fields["rider"].help_text = (
            "VOC candidates come from completed same-show H1/H2 results. "
            "ArenaLine keeps unresolved cutoff ties visible because judge-card scores are not stored."
        )


class UserOnboardingForm(_LegacyUserOnboardingForm):
    """Compatibility onboarding form that makes Person the login identity."""

    @transaction.atomic
    def save(self):
        user = super().save()
        sync_user_person_identity(
            user,
            self.team,
            rider=self.cleaned_data.get("rider"),
            guardian=self.cleaned_data.get("guardian"),
        )
        return user


class UserAccountEditForm(_LegacyUserAccountEditForm):
    """Compatibility account editor that keeps canonical Person synchronized."""

    @transaction.atomic
    def save(self):
        user = super().save()
        sync_user_person_after_account_edit(
            user,
            self.team,
            rider=self.cleaned_data.get("rider"),
            guardian=self.cleaned_data.get("guardian"),
        )
        return user
