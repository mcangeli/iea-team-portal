from django.urls import path

from .view_modules import lesson_programs_v340 as views

urlpatterns = [
    path("lesson-programs/", views.lesson_program_list, name="lesson_program_list"),
    path("lesson-programs/add/", views.lesson_program_create, name="lesson_program_create"),
    path("lesson-programs/<int:pk>/", views.lesson_program_detail, name="lesson_program_detail"),
    path("lesson-programs/<int:pk>/edit/", views.lesson_program_edit, name="lesson_program_edit"),
    path("lesson-programs/<int:program_pk>/series/add/", views.lesson_series_create, name="lesson_series_create"),
    path("lesson-series/<int:pk>/edit/", views.lesson_series_edit, name="lesson_series_edit"),
]
