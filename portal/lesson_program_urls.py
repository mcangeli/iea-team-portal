from django.urls import path

from .view_modules import lesson_day_v340
from .view_modules import lesson_programs_v340 as views

urlpatterns = [
    path("lesson-programs/", views.lesson_program_list, name="lesson_program_list"),
    path("lesson-programs/add/", views.lesson_program_create, name="lesson_program_create"),
    path("lesson-programs/<int:pk>/", views.lesson_program_detail, name="lesson_program_detail"),
    path("lesson-programs/<int:pk>/edit/", views.lesson_program_edit, name="lesson_program_edit"),
    path("lesson-programs/<int:program_pk>/series/add/", views.lesson_series_create, name="lesson_series_create"),
    path("iea/lessons/", views.iea_lesson_list, name="iea_lesson_list"),
    path("iea/lessons/add/", views.iea_lesson_series_create, name="iea_lesson_series_create"),
    path("lesson-series/<int:pk>/", views.lesson_series_detail, name="lesson_series_detail"),
    path("lesson-series/<int:pk>/edit/", views.lesson_series_edit, name="lesson_series_edit"),
    path("lesson-series/<int:pk>/generate/", views.lesson_series_generate, name="lesson_series_generate"),
    path("lesson-series/<int:series_pk>/enrollments/add/", views.lesson_enrollment_create, name="lesson_enrollment_create"),
    path("lesson-enrollments/<int:pk>/edit/", views.lesson_enrollment_edit, name="lesson_enrollment_edit"),
    path("lesson-occurrences/<int:pk>/", views.lesson_occurrence_detail, name="lesson_occurrence_detail"),
    path("lesson-occurrences/<int:pk>/day/", lesson_day_v340.lesson_day_workspace, name="lesson_day_workspace"),
    path("lesson-occurrences/<int:pk>/prepare/", views.lesson_occurrence_prepare, name="lesson_occurrence_prepare"),
    path("lesson-occurrences/<int:pk>/complete/", views.lesson_occurrence_complete, name="lesson_occurrence_complete"),
    path("lesson-occurrences/<int:pk>/cancel/", views.lesson_occurrence_cancel, name="lesson_occurrence_cancel"),
    path("lesson-occurrences/<int:pk>/reschedule/", views.lesson_occurrence_reschedule, name="lesson_occurrence_reschedule"),
    path("lesson-attendance/<int:pk>/edit/", views.lesson_attendance_edit, name="lesson_attendance_edit"),
    path("lesson-assignments/<int:pk>/edit/", views.lesson_assignment_edit, name="lesson_assignment_edit"),
]
