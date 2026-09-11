from django.urls import path

from . import course_views

urlpatterns = [
    path("shows/<int:show_pk>/courses/", course_views.show_courses, name="show_courses"),
    path("shows/<int:show_pk>/courses/add/", course_views.show_course_add, name="show_course_add"),
    path("shows/<int:show_pk>/courses/<int:course_pk>/edit/", course_views.show_course_edit, name="show_course_edit"),
    path("shows/<int:show_pk>/courses/<int:course_pk>/media/", course_views.show_course_media, name="show_course_media"),
    path("shows/<int:show_pk>/courses/<int:course_pk>/remove/", course_views.show_course_remove, name="show_course_remove"),
]
