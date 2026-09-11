from django import forms


class HoofprintFinalizeForm(forms.Form):
    coach_name = forms.CharField(max_length=160, required=False, label="Coach name")
    coach_phone = forms.CharField(max_length=40, required=False, label="Coach phone")
    horses_contributed = forms.IntegerField(min_value=0, required=False, label="Horses contributed")
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}), label="Submission notes")

    def __init__(self, *args, show=None, **kwargs):
        super().__init__(*args, **kwargs)
        if show and not self.is_bound:
            self.fields["horses_contributed"].initial = show.horse_assignments.filter(available=True).count()
