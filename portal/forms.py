"""Public form namespace for ArenaLine.

The v2.9 cleanup starts decomposing the legacy monolithic forms module by keeping
its existing forms available while allowing domain forms to be normalized without
startup-time monkey patches.
"""

from django import forms

from .forms_legacy import *  # noqa: F401,F403
from .forms_legacy import ReimbursementRequestForm as _LegacyReimbursementRequestForm
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
