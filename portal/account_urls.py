from django.urls import path
from . import account_views

urlpatterns = [
    path("account/", account_views.my_account, name="my_account"),
    path("account/edit/", account_views.my_account_edit, name="my_account_edit"),
    path("account/password/", account_views.my_password_change, name="my_password_change"),
    path("account/email/", account_views.email_change, name="email_change"),
    path("account/email/resend/", account_views.email_verification_resend, name="email_verification_resend"),
    path("account/email/verify/<str:token>/", account_views.email_verify, name="email_verify"),
    path("account/notifications/", account_views.my_notification_preferences, name="my_notification_preferences"),
]
