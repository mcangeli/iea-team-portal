from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    AuditEvent,
    CommitteeAssignment,
    FamilyCharge,
    FamilyCredit,
    FinancialAccount,
    FinancialCategory,
    FinancialTransaction,
    FundraisingCampaign,
    FundraisingContribution,
    FundraisingPolicy,
    GuardianContact,
    Rider,
    RiderGuardian,
    Season,
    SeasonMembership,
    Show,
    ShowTransactionAllocation,
    Team,
    UserProfile,
)
from portal.views import _can_finance


class FundraisingAndFamilyPrivacyTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
        self.season = Season.objects.create(
            team=self.team, name="2026-27",
            start_date=date(2026, 8, 1), end_date=date(2027, 7, 31),
            is_active=True,
        )
        self.treasurer = User.objects.create_user(username="treasurer", password="testpass")
        self.treasurer.profile.team = self.team
        self.treasurer.profile.role = UserProfile.Role.PARENT
        self.treasurer.profile.save(update_fields=["team", "role"])
        CommitteeAssignment.objects.create(
            team=self.team, season=self.season, user=self.treasurer,
            role=CommitteeAssignment.Role.TREASURER, active=True,
        )

        self.rider_user = User.objects.create_user(username="rider", password="testpass")
        self.rider_user.profile.team = self.team
        self.rider_user.profile.role = UserProfile.Role.RIDER
        self.rider_user.profile.save(update_fields=["team", "role"])

        self.parent_user = User.objects.create_user(username="parent", password="testpass")
        self.parent_user.profile.team = self.team
        self.parent_user.profile.role = UserProfile.Role.PARENT
        self.parent_user.profile.save(update_fields=["team", "role"])

        self.rider = Rider.objects.create(
            team=self.team, user=self.rider_user,
            first_name="Youth", last_name="Rider", grade=8,
        )
        self.membership = SeasonMembership.objects.create(
            rider=self.rider, season=self.season,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )
        guardian = GuardianContact.objects.create(
            team=self.team, user=self.parent_user,
            first_name="Pat", last_name="Parent",
        )
        RiderGuardian.objects.create(
            rider=self.rider, guardian=guardian, relationship="Parent", primary_contact=True
        )

        self.other_rider = Rider.objects.create(
            team=self.team, first_name="Other", last_name="Rider", grade=9,
        )
        self.other_membership = SeasonMembership.objects.create(
            rider=self.other_rider, season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )

        self.account = FinancialAccount.objects.create(team=self.team, name="Checking")
        self.income_category = FinancialCategory.objects.create(
            team=self.team, name="Fundraising Income", kind=FinancialCategory.Kind.INCOME
        )
        self.expense_category = FinancialCategory.objects.create(
            team=self.team, name="Administrative", kind=FinancialCategory.Kind.EXPENSE
        )
        self.charge = FamilyCharge.objects.create(
            membership=self.membership, description="Membership dues",
            amount=Decimal("300.00"), charge_date=date(2026, 9, 1),
        )

    def test_rider_cannot_view_own_family_finance(self):
        self.client.force_login(self.rider_user)
        response = self.client.get(reverse("family_account", args=[self.membership.pk]))
        self.assertEqual(response.status_code, 403)

    def test_linked_parent_can_view_family_finance(self):
        self.client.force_login(self.parent_user)
        response = self.client.get(reverse("family_account", args=[self.membership.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Membership dues")

    def test_parent_cannot_view_unlinked_rider_family_finance(self):
        self.client.force_login(self.parent_user)
        response = self.client.get(reverse("family_account", args=[self.other_membership.pk]))
        self.assertEqual(response.status_code, 403)

    def test_rider_cannot_gain_finance_access_from_committee_assignment(self):
        CommitteeAssignment.objects.create(
            team=self.team, season=self.season, user=self.rider_user,
            role=CommitteeAssignment.Role.TREASURER, active=True,
        )
        self.assertFalse(_can_finance(self.rider_user, self.season))
        self.client.force_login(self.rider_user)
        self.assertEqual(self.client.get(reverse("finance_dashboard")).status_code, 403)

    def test_rider_cannot_access_reimbursements(self):
        self.client.force_login(self.rider_user)
        self.assertEqual(self.client.get(reverse("reimbursement_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("reimbursement_create")).status_code, 403)

    def test_fundraising_contribution_posts_cash_once_and_family_credit_separately(self):
        FundraisingPolicy.objects.create(
            season=self.season,
            model=FundraisingPolicy.Model.HYBRID,
            default_family_credit_percent=Decimal("60.00"),
        )
        campaign = FundraisingCampaign.objects.create(
            team=self.team, season=self.season, name="Fall Fundraiser",
            goal_amount=Decimal("1000.00"), status=FundraisingCampaign.Status.ACTIVE,
            created_by=self.treasurer,
        )
        self.client.force_login(self.treasurer)
        response = self.client.post(
            reverse("fundraising_contribution_add", args=[campaign.pk]),
            {
                "received_date": "2026-09-10",
                "donor_name": "Community Sponsor",
                "amount": "250.00",
                "beneficiary_membership": self.membership.pk,
                "family_credit_amount": "150.00",
                "family_charge": self.charge.pk,
                "account": self.account.pk,
                "category": self.income_category.pk,
                "method": "Check",
                "reference": "CHK-100",
                "notes": "Fall fundraiser contribution",
            },
        )
        self.assertEqual(response.status_code, 302)

        contribution = FundraisingContribution.objects.get(campaign=campaign)
        self.assertIsNotNone(contribution.financial_transaction_id)
        self.assertIsNotNone(contribution.family_credit_id)
        self.assertEqual(contribution.financial_transaction.amount, Decimal("250.00"))
        self.assertEqual(contribution.financial_transaction.kind, FinancialTransaction.Kind.INCOME)
        self.assertEqual(contribution.family_credit.amount, Decimal("150.00"))
        self.assertEqual(contribution.family_credit.credit_type, FamilyCredit.CreditType.FUNDRAISING)
        self.assertEqual(contribution.team_retained_amount, Decimal("100.00"))

        self.charge.refresh_from_db()
        self.assertEqual(self.charge.balance, Decimal("150.00"))
        self.assertEqual(
            FinancialTransaction.objects.filter(
                team=self.team, season=self.season,
                status=FinancialTransaction.Status.POSTED,
                description="Fundraiser · Fall Fundraiser",
            ).count(),
            1,
        )

    def test_voiding_fundraiser_restores_family_balance_without_deleting_history(self):
        campaign = FundraisingCampaign.objects.create(
            team=self.team, season=self.season, name="Fall Fundraiser",
            status=FundraisingCampaign.Status.ACTIVE, created_by=self.treasurer,
        )
        contribution = FundraisingContribution.objects.create(
            campaign=campaign, received_date=date(2026, 9, 10),
            donor_name="Sponsor", amount=Decimal("200.00"),
            beneficiary_membership=self.membership,
            family_credit_amount=Decimal("100.00"), family_charge=self.charge,
            account=self.account, category=self.income_category,
            created_by=self.treasurer,
        )

        tx = FinancialTransaction.objects.create(
            team=self.team, season=self.season, transaction_date=date(2026, 9, 10),
            kind=FinancialTransaction.Kind.INCOME, account=self.account,
            category=self.income_category, amount=Decimal("200.00"),
            payee="Sponsor", description="Fundraiser · Fall Fundraiser",
        )
        credit = FamilyCredit.objects.create(
            charge=self.charge, credit_type=FamilyCredit.CreditType.FUNDRAISING,
            amount=Decimal("100.00"), source=campaign.name,
            status=FamilyCredit.Status.APPLIED, created_by=self.treasurer,
        )
        contribution.financial_transaction = tx
        contribution.family_credit = credit
        contribution.save(update_fields=["financial_transaction", "family_credit"])

        self.assertEqual(self.charge.balance, Decimal("200.00"))
        self.client.force_login(self.treasurer)
        response = self.client.post(
            reverse("fundraising_contribution_void", args=[contribution.pk]),
            {"reason": "Duplicate deposit"},
        )
        self.assertEqual(response.status_code, 302)

        contribution.refresh_from_db()
        tx.refresh_from_db()
        credit.refresh_from_db()
        self.charge.refresh_from_db()
        self.assertEqual(contribution.status, FundraisingContribution.Status.VOID)
        self.assertEqual(tx.status, FinancialTransaction.Status.VOID)
        self.assertEqual(credit.status, FamilyCredit.Status.CANCELLED)
        self.assertEqual(self.charge.balance, Decimal("300.00"))
        self.assertTrue(FundraisingContribution.objects.filter(pk=contribution.pk).exists())

    def test_transaction_cannot_be_reduced_below_show_allocations(self):
        show = Show.objects.create(
            team=self.team, season=self.season, name="Hosted Show",
            show_date=date(2026, 10, 10),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        tx = FinancialTransaction.objects.create(
            team=self.team, season=self.season, transaction_date=date(2026, 9, 10),
            kind=FinancialTransaction.Kind.EXPENSE, account=self.account,
            category=self.expense_category, amount=Decimal("500.00"),
            description="Shared expense",
        )
        ShowTransactionAllocation.objects.create(
            transaction=tx, show=show,
            scope=FinancialTransaction.ShowFinanceScope.HOSTING,
            amount=Decimal("400.00"),
        )
        tx.amount = Decimal("350.00")
        with self.assertRaises(ValidationError):
            tx.full_clean()

    def test_coach_general_audit_log_does_not_expose_finance_events(self):
        coach = User.objects.create_user(username="coach", password="testpass")
        coach.profile.team = self.team
        coach.profile.role = UserProfile.Role.COACH
        coach.profile.save(update_fields=["team", "role"])

        AuditEvent.objects.create(
            team=self.team, season=self.season, actor=self.treasurer,
            action=AuditEvent.Action.CREATED, entity_type="FinancialTransaction",
            entity_id=123, entity_label="Private finance item",
            summary="Created private finance item",
        )
        AuditEvent.objects.create(
            team=self.team, season=self.season, actor=coach,
            action=AuditEvent.Action.UPDATED, entity_type="ShowResult",
            entity_id=456, entity_label="Competition result",
            summary="Updated competition result",
        )

        self.client.force_login(coach)
        response = self.client.get(reverse("audit_log"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Updated competition result")
        self.assertNotContains(response, "Created private finance item")
