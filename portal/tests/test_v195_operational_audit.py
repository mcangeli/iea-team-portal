from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    AuditEvent,
    CommitteeAssignment,
    FamilyCharge,
    FamilyPayment,
    FinancialAccount,
    FinancialCategory,
    FinancialTransaction,
    ReimbursementRequest,
    Rider,
    Season,
    SeasonMembership,
    Team,
    UserProfile,
)
from portal.views import _audit_event


class OperationalAuditTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )
        self.treasurer = User.objects.create_user(
            username="treasurer", password="testpass", first_name="Terry", last_name="Treasurer"
        )
        self.treasurer.profile.team = self.team
        self.treasurer.profile.role = UserProfile.Role.PARENT
        self.treasurer.profile.save(update_fields=["team", "role"])
        CommitteeAssignment.objects.create(
            team=self.team, season=self.season, user=self.treasurer,
            role=CommitteeAssignment.Role.TREASURER, active=True,
        )
        self.submitter = User.objects.create_user(
            username="parent", password="testpass", first_name="Pat", last_name="Parent"
        )
        self.submitter.profile.team = self.team
        self.submitter.profile.role = UserProfile.Role.PARENT
        self.submitter.profile.save(update_fields=["team", "role"])
        self.account = FinancialAccount.objects.create(team=self.team, name="Checking")
        self.expense_category = FinancialCategory.objects.create(
            team=self.team, name="Administrative", kind=FinancialCategory.Kind.EXPENSE
        )
        self.income_category = FinancialCategory.objects.create(
            team=self.team, name="Family payments", kind=FinancialCategory.Kind.INCOME
        )

    def test_audit_event_helper_creates_immutable_history_row(self):
        tx = FinancialTransaction.objects.create(
            team=self.team, season=self.season, transaction_date=date(2026, 9, 10),
            kind=FinancialTransaction.Kind.EXPENSE, account=self.account,
            category=self.expense_category, amount=Decimal("50.00"),
            description="Insurance",
        )
        event = _audit_event(
            team=self.team, actor=self.treasurer, action=AuditEvent.Action.CREATED,
            obj=tx, summary="Created insurance transaction",
            details={"amount": tx.amount},
        )
        self.assertEqual(event.entity_type, "FinancialTransaction")
        self.assertEqual(event.entity_id, tx.pk)
        self.assertEqual(event.details["amount"], "50.00")

    def test_financial_transaction_create_writes_audit_event(self):
        self.client.force_login(self.treasurer)
        response = self.client.post(reverse("finance_transaction_create"), {
            "season": self.season.pk,
            "transaction_date": "2026-09-10",
            "kind": FinancialTransaction.Kind.EXPENSE,
            "account": self.account.pk,
            "category": self.expense_category.pk,
            "amount": "125.00",
            "payee": "Insurance Company",
            "description": "Show insurance",
            "reference": "",
            "notes": "",
        })
        self.assertEqual(response.status_code, 302)
        tx = FinancialTransaction.objects.get(description="Show insurance")
        self.assertTrue(AuditEvent.objects.filter(
            team=self.team, entity_type="FinancialTransaction",
            entity_id=tx.pk, action=AuditEvent.Action.CREATED,
        ).exists())

    def test_reimbursement_draft_is_private_until_submitted(self):
        self.client.force_login(self.submitter)
        response = self.client.post(reverse("reimbursement_create"), {
            "season": self.season.pk,
            "show": "",
            "show_finance_scope": "",
            "payee_name": "Pat Parent",
            "expense_date": "2026-09-10",
            "category": self.expense_category.pk,
            "amount": "42.50",
            "description": "Office supplies draft",
            "notes": "",
            "action": "draft",
        })
        form_errors = ""
        if response.status_code == 200 and getattr(response, "context", None):
            form = response.context.get("form")
            if form is not None:
                form_errors = form.errors.as_text()
        self.assertEqual(response.status_code, 302, form_errors)
        item = ReimbursementRequest.objects.get(description="Office supplies draft")
        self.assertEqual(item.status, ReimbursementRequest.Status.DRAFT)

        self.client.force_login(self.treasurer)
        response = self.client.get(reverse("reimbursement_list"))
        self.assertNotContains(response, "Office supplies draft")

        self.client.force_login(self.submitter)
        response = self.client.get(reverse("reimbursement_list"))
        self.assertContains(response, "Office supplies draft")
        self.client.post(reverse("reimbursement_submit", args=[item.pk]))
        item.refresh_from_db()
        self.assertEqual(item.status, ReimbursementRequest.Status.SUBMITTED)

        self.client.force_login(self.treasurer)
        response = self.client.get(reverse("reimbursement_list"))
        self.assertContains(response, "Office supplies draft")

    def test_void_family_payment_retains_record_and_voids_ledger_transaction(self):
        rider = Rider.objects.create(
            team=self.team, first_name="Riley", last_name="Rider", grade=8
        )
        membership = SeasonMembership.objects.create(
            rider=rider, season=self.season, team_level=SeasonMembership.TeamLevel.FUTURES
        )
        charge = FamilyCharge.objects.create(
            membership=membership, description="Membership dues",
            amount=Decimal("500.00"), charge_date=date(2026, 9, 1),
        )
        tx = FinancialTransaction.objects.create(
            team=self.team, season=self.season, transaction_date=date(2026, 9, 10),
            kind=FinancialTransaction.Kind.INCOME, account=self.account,
            category=self.income_category, amount=Decimal("100.00"),
            description="Family payment",
        )
        payment = FamilyPayment.objects.create(
            membership=membership, charge=charge, amount=Decimal("100.00"),
            received_date=date(2026, 9, 10), account=self.account,
            category=self.income_category, financial_transaction=tx,
            created_by=self.treasurer,
        )
        self.assertEqual(charge.payment_total, Decimal("100.00"))

        self.client.force_login(self.treasurer)
        response = self.client.post(
            reverse("family_payment_delete", args=[payment.pk]),
            {"reason": "Duplicate payment"},
        )
        self.assertEqual(response.status_code, 302)

        payment.refresh_from_db()
        tx.refresh_from_db()
        charge.refresh_from_db()
        self.assertEqual(payment.status, FamilyPayment.Status.VOID)
        self.assertEqual(tx.status, FinancialTransaction.Status.VOID)
        self.assertEqual(charge.payment_total, Decimal("0"))
        self.assertTrue(AuditEvent.objects.filter(
            entity_type="FamilyPayment", entity_id=payment.pk,
            action=AuditEvent.Action.VOIDED,
        ).exists())
