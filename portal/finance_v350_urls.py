from django.urls import path

from portal.view_modules import finance_v350


urlpatterns = [
    path("finance/workspace/", finance_v350.finance_workspace, name="finance_workspace"),
    path(
        "finance/workspace/accounts/<int:pk>/",
        finance_v350.finance_receivable_account_detail,
        name="finance_receivable_account_detail",
    ),
    path(
        "finance/workspace/accounts/<int:pk>/statement/",
        finance_v350.finance_receivable_statement,
        name="finance_receivable_statement",
    ),
]
