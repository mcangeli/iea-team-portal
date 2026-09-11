from pathlib import Path

from django import forms

from .course_models import ShowCourse
from .models import ShowClass


_ALLOWED_COURSE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"}
_MAX_COURSE_FILE_SIZE = 20 * 1024 * 1024


def _validate_course_file(course_file):
    if not course_file:
        return course_file
    suffix = Path(course_file.name).suffix.lower()
    if suffix not in _ALLOWED_COURSE_SUFFIXES:
        raise forms.ValidationError("Upload a course photo (JPG, PNG, WEBP, HEIC) or PDF.")
    if course_file.size > _MAX_COURSE_FILE_SIZE:
        raise forms.ValidationError("The course file must be 20 MB or smaller.")
    return course_file


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
            "course_file": forms.ClearableFileInput(attrs={"accept": "image/*,application/pdf", "capture": "environment"}),
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

    def clean_course_file(self):
        return _validate_course_file(self.cleaned_data.get("course_file"))


class ShowCourseMediaForm(forms.ModelForm):
    class Meta:
        model = ShowCourse
        fields = ["course_file", "external_link"]
        labels = {
            "course_file": "Course image or PDF",
            "external_link": "External course link",
        }
        help_texts = {
            "course_file": "Take a course photo from your phone, upload a PDF/image, or replace the current course media.",
            "external_link": "Optional link to a hosted course image or document.",
        }
        widgets = {
            "course_file": forms.ClearableFileInput(attrs={"accept": "image/*,application/pdf", "capture": "environment"}),
        }

    def clean_course_file(self):
        return _validate_course_file(self.cleaned_data.get("course_file"))
