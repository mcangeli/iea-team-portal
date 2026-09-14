from django.urls import path

from portal.view_modules.station import (
    station_action,
    station_activate,
    station_deactivate,
    station_device_add,
    station_device_edit,
    station_device_rotate_secret,
    station_home,
    station_identify,
    station_manage,
    station_person_pin,
    station_shift_approve,
    station_shift_edit,
    station_shift_export,
    station_shift_review,
)

urlpatterns = [
    path("station/activate/", station_activate, name="station_activate"),
    path("station/deactivate/", station_deactivate, name="station_deactivate"),
    path("station/", station_home, name="station_home"),
    path("station/person/<int:person_pk>/", station_identify, name="station_identify"),
    path("station/action/", station_action, name="station_action"),
    path("people/station/", station_manage, name="station_manage"),
    path("people/station/shifts/", station_shift_review, name="station_shift_review"),
    path("people/station/shifts/export/", station_shift_export, name="station_shift_export"),
    path("people/station/shifts/<int:shift_pk>/edit/", station_shift_edit, name="station_shift_edit"),
    path("people/station/shifts/<int:shift_pk>/approve/", station_shift_approve, name="station_shift_approve"),
    path("people/station/devices/add/", station_device_add, name="station_device_add"),
    path("people/station/devices/<int:device_pk>/edit/", station_device_edit, name="station_device_edit"),
    path("people/station/devices/<int:device_pk>/rotate-secret/", station_device_rotate_secret, name="station_device_rotate_secret"),
    path("people/station/people/<int:person_pk>/pin/", station_person_pin, name="station_person_pin"),
]
