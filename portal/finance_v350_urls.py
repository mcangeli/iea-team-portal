from django.urls import path
from portal.view_modules import finance_v350

urlpatterns = [
    path("finance/workspace/", finance_v350.finance_workspace, name="finance_workspace"),
    path("finance/workspace/accounts/add/", finance_v350.finance_receivable_account_add, name="finance_receivable_account_add"),
    path("finance/workspace/accounts/<int:pk>/", finance_v350.finance_receivable_account_detail, name="finance_receivable_account_detail"),
    path("finance/workspace/accounts/<int:pk>/statement/", finance_v350.finance_receivable_statement, name="finance_receivable_statement"),
    path("finance/workspace/accounts/<int:pk>/charges/add/", finance_v350.finance_charge_add, name="finance_charge_add"),
    path("finance/workspace/accounts/<int:pk>/payments/add/", finance_v350.finance_payment_add, name="finance_payment_add"),
    path("finance/workspace/accounts/<int:pk>/credits/add/", finance_v350.finance_credit_add, name="finance_credit_add"),
    path("finance/workspace/accounts/<int:pk>/payments/<int:payment_id>/allocate/", finance_v350.finance_payment_allocate, name="finance_payment_allocate"),
    path("finance/workspace/accounts/<int:pk>/credits/<int:credit_id>/allocate/", finance_v350.finance_credit_allocate, name="finance_credit_allocate"),
]
