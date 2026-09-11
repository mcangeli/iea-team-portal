from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.forms import FundraisingContributionForm
from portal.models import (
    FamilyCharge,
    FinancialAccount,
    FinancialCategory,
    FundraisingCampaign,
    FundraisingContribution,
    FundraisingPolicy,
    GuardianContact,
    Rider,
    RiderGuardian,
    Season,
    SeasonMembership,
    Team,
    UserProfile,
)


class FundraisingPolicyTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )
        self.parent = User.objects.create_user(username="parent", password="testpass")
        self.parent.profile.team = self.team
        self.parent.profile.role = UserProfile.Role.PARENT
        self.parent.profile.save(update_fields=["team", "role"])

        self.rider_user = User.objects.create_user(username="rider", password="testpass")
        self.rider_user.profile.team = self.team
        self.rider_user.profile.role = UserProfile.Role.RIDER
        self.rider_user.profile.save(update_fields=["team", "role"])

        self.rider = Rider.objects.create(
            team=self.team, user=self.rider_user,
            first_name="Youth", last_name="Rider", grade=8,
        )
        self.membership = SeasonMembership.objects.create(
            rider=self.rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )
        guardian = GuardianContact.objects.create(
            team=self.team, user=self.parent,
            first_name="Pat", last_name="Parent",
        )
        RiderGuardian.objects.create(
            rider=self.rider, guardian=guardian, relationship="Parent", primary_contact=True
        )

        self.account = FinancialAccount.objects.create(team=self.team, name="Checking")
        self.category = FinancialCategory.objects.create(
            team=self.team, name="Fundraising", kind=FinancialCategory.Kind.INCOME
        )
        self.charge = FamilyCharge.objects.create(
            membership=self.membership,
            charge_type=FamilyCharge.ChargeType.MEMBERSHIP_DUES,
            description="Membership dues",
            amount=Decimal("500.00"),
            charge_date=date(2026, 9, 1),
        )
        self.campaign = FundraisingCampaign.objects.create(
            team=self.team, season=self.season, name="Fall Fundraiser",
            status=FundraisingCampaign.Status.ACTIVE,
        )

    def test_hybrid_policy_calculates_default_family_credit(self):
        policy = FundraisingPolicy.objects.create(
            season=self.season,
            model=FundraisingPolicy.Model.HYBRID,
            default_family_credit_percent=Decimal("60.00"),
            participation_optional=True,
        )
        self.assertEqual(policy.default_credit_for(Decimal("250.00")), Decimal("150.00"))

    def test_team_wide_policy_rejects_nonzero_family_credit(self):
        policy = FundraisingPolicy(
            season=self.season,
            model=FundraisingPolicy.Model.TEAM_WIDE,
            default_family_credit_percent=Decimal("10.00"),
        )
        with self.assertRaises(Exception):
            policy.full_clean()

    def test_policy_can_limit_eligible_charge_types(self):
        policy = FundraisingPolicy.objects.create(
            season=self.season,
            model=FundraisingPolicy.Model.HYBRID,
            default_family_credit_percent=Decimal("50.00"),
            allowed_charge_types=[FamilyCharge.ChargeType.MEMBERSHIP_DUES],
        )
        self.assertTrue(policy.charge_type_allowed(self.charge))
        show_charge = FamilyCharge(
            membership=self.membership,
            charge_type=FamilyCharge.ChargeType.SHOW_FEE,
            description="Show fee",
            amount=Decimal("100.00"),
        )
        self.assertFalse(policy.charge_type_allowed(show_charge))

    def test_blank_credit_uses_hybrid_policy_default_when_family_is_selected(self):
        policy = FundraisingPolicy.objects.create(
            season=self.season,
            model=FundraisingPolicy.Model.HYBRID,
            default_family_credit_percent=Decimal("60.00"),
            allowed_charge_types=[FamilyCharge.ChargeType.MEMBERSHIP_DUES],
        )
        form = FundraisingContributionForm(
            data={
                "received_date": "2026-09-10",
                "donor_name": "Community Supporter",
                "amount": "250.00",
                "beneficiary_membership": self.membership.pk,
                "family_credit_amount": "",
                "family_charge": self.charge.pk,
                "account": self.account.pk,
                "category": self.category.pk,
                "method": "Check",
                "reference": "",
                "notes": "",
            },
            campaign=self.campaign,
            policy=policy,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["family_credit_amount"], Decimal("150.00"))

    def test_parent_family_fundraising_view_hides_donor_identity(self):
        policy = FundraisingPolicy.objects.create(
            season=self.season,
            model=FundraisingPolicy.Model.HYBRID,
            default_family_credit_percent=Decimal("50.00"),
            family_message="Half of attributed fundraising reduces eligible family charges.",
        )
        FundraisingContribution.objects.create(
            campaign=self.campaign,
            received_date=date(2026, 9, 10),
            donor_name="Private Donor Name",
            amount=Decimal("200.00"),
            beneficiary_membership=self.membership,
            family_credit_amount=Decimal("100.00"),
            family_charge=self.charge,
            account=self.account,
            category=self.category,
        )

        self.client.force_login(self.parent)
        response = self.client.get(reverse("family_fundraising", args=[self.membership.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fall Fundraiser")
        self.assertContains(response, "$200.00")
        self.assertContains(response, "$100.00")
        self.assertContains(response, policy.family_message)
        self.assertNotContains(response, "Private Donor Name")

    def test_rider_cannot_access_family_fundraising_view(self):
        FundraisingPolicy.objects.create(
            season=self.season,
            model=FundraisingPolicy.Model.TEAM_WIDE,
            default_family_credit_percent=Decimal("0"),
        )
        self.client.force_login(self.rider_user)
        response = self.client.get(reverse("family_fundraising", args=[self.membership.pk]))
        self.assertEqual(response.status_code, 403)
