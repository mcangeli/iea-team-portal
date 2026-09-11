from django import forms

from .course_models import ShowCourse
from .models import ShowClass


class ShowCourseForm(forms.ModelForm):
    class Meta:
        model = ShowCourse
        fields = [
            "title", "course_type", "ring", "show_classes", "course_walk_at",
            "course_designer", "fence_count", "combinations", "related_distances",
            "handy_options", "posted_notes", "coach_notes", "course_file",
            "external_link", "active",
        ]
        labels = {
            "show_classes": "Applies to classes",
            "course_walk_at": "Course walk",
            "posted_notes": "Course / operational notes",
            "coach_notes": "Private Coach/Admin notes",
            "course_file": "Course image or PDF",
            "external_link": "External course link",
        }
        widgets = {
            "show_classes": forms.CheckboxSelectMultiple(),
            "course_walk_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "posted_notes": forms.Textarea(attrs={"rows": 4}),
            "coach_notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, show=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.show = show
        if show:
            self.fields["show_classes"].queryset = ShowClass.objects.filter(show=show).select_related("season_class").order_by("sort_order", "class_number", "name")

    def clean_show_classes(self):
        classes = self.cleaned_data["show_classes"]
        if self.show and any(show_class.show_id != self.show.id for show_class in classes):
            raise forms.ValidationError("Every selected class must belong to this show.")
        return classes


class ShowCourseMediaForm(forms.ModelForm):
    class Meta:
        model = ShowCourse
        fields = ["course_file", "external_link"]
        labels = {
            "course_file": "Course image or PDF",
            "external_link": "External course link",
        }
        help_texts = {
            "course_file": "Upload or replace the posted course image/PDF for this course.",
            "external_link": "Optional link to a hosted course image or document.",
        }
