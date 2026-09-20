from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.people import Person
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableAccountPerson, ReceivableCredit, ReceivableCreditRule
from portal.model_modules.station import WorkShiftEntry
from portal.models import AuditEvent, Team, UserProfile


class V323StationShiftReviewTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")
        self.admin = User.objects.create_user(username="shift-admin", password="pass12345")
        profile = self.admin.profile
        profile.team = self.team
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["team", "role"])
        self.person = Person.objects.create(team=self.team, first_name="Jamie", last_name="Worker")

    def _shift(self, *, team=None, person=None, closed=True):
        team = team or self.team
        person = person or self.person
        clock_in = timezone.now() - timedelta(hours=2)
        return WorkShiftEntry.objects.create(
            team=team,
            person=person,
            role=WorkShiftEntry.Role.WORKING_STUDENT,
            clock_in=clock_in,
            clock_out=clock_in + timedelta(minutes=90) if closed else None,
        )

    def test_manager_can_approve_closed_shift_and_audit_is_created(self):
        shift = self._shift()
        self.client.force_login(self.admin)
        response = self.client.post(reverse("station_shift_approve", args=[shift.pk]))
        self.assertRedirects(response, reverse("station_shift_review"))
        shift.refresh_from_db()
        self.assertEqual(shift.approved_by, self.admin)
        self.assertIsNotNone(shift.approved_at)
        self.assertTrue(
            AuditEvent.objects.filter(
                team=self.team,
                actor=self.admin,
                action="station_shift_approved",
                entity_type="WorkShiftEntry",
                entity_id=shift.pk,
            ).exists()
        )

    def test_open_shift_cannot_be_approved(self):
        shift = self._shift(closed=False)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("station_shift_approve", args=[shift.pk]))
        self.assertRedirects(response, reverse("station_shift_review"))
        shift.refresh_from_db()
        self.assertIsNone(shift.approved_by)
        self.assertIsNone(shift.approved_at)
        self.assertFalse(AuditEvent.objects.filter(action="station_shift_approved", entity_id=shift.pk).exists())

    def test_shift_approval_is_cross_organization_isolated(self):
        other_person = Person.objects.create(team=self.other_team, first_name="Other", last_name="Worker")
        shift = self._shift(team=self.other_team, person=other_person)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("station_shift_approve", args=[shift.pk]))
        self.assertEqual(response.status_code, 404)
        shift.refresh_from_db()
        self.assertIsNone(shift.approved_at)

    def test_non_manager_cannot_open_shift_review(self):
        rider = User.objects.create_user(username="shift-rider", password="pass12345")
        profile = rider.profile
        profile.team = self.team
        profile.role = UserProfile.Role.RIDER
        profile.save(update_fields=["team", "role"])
        self.client.force_login(rider)
        response = self.client.get(reverse("station_shift_review"))
        self.assertIn(response.status_code, (403, 404))

    def test_export_contains_only_callers_organization_and_is_audited(self):
        own_shift = self._shift()
        other_person = Person.objects.create(team=self.other_team, first_name="Other", last_name="Worker")
        self._shift(team=self.other_team, person=other_person)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("station_shift_export"))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn(own_shift.person.display_name, body)
        self.assertNotIn(other_person.display_name, body)
        self.assertTrue(
            AuditEvent.objects.filter(
                team=self.team,
                actor=self.admin,
                action="station_shift_exported",
                entity_type="WorkShiftEntry",
            ).exists()
        )

    def test_approved_only_review_renders_attention_empty_state_server_side(self):
        shift = self._shift()
        shift.approved_by = self.admin
        shift.approved_at = timezone.now()
        shift.save(update_fields=["approved_by", "approved_at", "updated_at"])
        self.client.force_login(self.admin)
        response = self.client.get(reverse("station_shift_review"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nothing needs attention right now.")
        self.assertNotContains(response, "data-station-filtered-table")

    def test_unapproved_only_review_renders_approved_history_empty_state_server_side(self):
        self._shift()
        self.client.force_login(self.admin)
        response = self.client.get(reverse("station_shift_review"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No approved work history yet.")
        self.assertNotContains(response, "data-station-filtered-table")


    def _work_credit_setup(self):
        account=ReceivableAccount.objects.create(team=self.team,name="Jamie Board",finance_domain=FinanceDomain.GENERAL)
        ReceivableAccountPerson.objects.create(account=account,person=self.person,role=ReceivableAccountPerson.Role.PARTICIPANT)
        rule=ReceivableCreditRule.objects.create(team=self.team,finance_domain=FinanceDomain.GENERAL,name="Working Student Credit",source_type="barn_work",calculation=ReceivableCreditRule.Calculation.QUANTITY,rate=Decimal("15.00"),credit_type="work")
        return account,rule

    def test_approved_shift_review_previews_work_credit(self):
        account,rule=self._work_credit_setup();shift=self._shift()
        shift.approved_by=self.admin;shift.approved_at=timezone.now();shift.save(update_fields=["approved_by","approved_at","updated_at"])
        self.client.force_login(self.admin)
        response=self.client.get(reverse("station_shift_review"))
        self.assertEqual(response.status_code,200);self.assertContains(response,"$ 22.50");self.assertContains(response,"Post credit");self.assertContains(response,account.name)

    def test_manager_can_post_approved_shift_credit(self):
        account,rule=self._work_credit_setup();shift=self._shift()
        shift.approved_by=self.admin;shift.approved_at=timezone.now();shift.save(update_fields=["approved_by","approved_at","updated_at"])
        self.client.force_login(self.admin)
        response=self.client.post(reverse("station_shift_post_credit",args=[shift.pk]))
        self.assertRedirects(response,reverse("station_shift_review"))
        credit=ReceivableCredit.objects.get(account=account)
        self.assertEqual(credit.amount,Decimal("22.50"));self.assertEqual(credit.credit_rule,rule)

    def test_shift_credit_post_retry_does_not_duplicate(self):
        account,rule=self._work_credit_setup();shift=self._shift()
        shift.approved_by=self.admin;shift.approved_at=timezone.now();shift.save(update_fields=["approved_by","approved_at","updated_at"])
        self.client.force_login(self.admin);url=reverse("station_shift_post_credit",args=[shift.pk])
        self.client.post(url);self.client.post(url)
        self.assertEqual(ReceivableCredit.objects.filter(account=account).count(),1)


    def test_employee_shift_is_not_offered_receivable_credit(self):
        self._work_credit_setup();shift=self._shift()
        shift.role=WorkShiftEntry.Role.BARN_STAFF;shift.approved_by=self.admin;shift.approved_at=timezone.now()
        shift.save(update_fields=["role","approved_by","approved_at","updated_at"])
        self.client.force_login(self.admin)
        response=self.client.get(reverse("station_shift_review"))
        self.assertContains(response,"Employee hours · no receivable credit")
        self.assertNotContains(response,reverse("station_shift_post_credit",args=[shift.pk]))

    def test_employee_shift_cannot_post_receivable_credit(self):
        account,rule=self._work_credit_setup();shift=self._shift()
        shift.role=WorkShiftEntry.Role.BARN_STAFF;shift.approved_by=self.admin;shift.approved_at=timezone.now()
        shift.save(update_fields=["role","approved_by","approved_at","updated_at"])
        self.client.force_login(self.admin)
        response=self.client.post(reverse("station_shift_post_credit",args=[shift.pk]))
        self.assertRedirects(response,reverse("station_shift_review"))
        self.assertFalse(ReceivableCredit.objects.filter(account=account).exists())


    def _coach(self,username,finance=False):
        user=User.objects.create_user(username=username,password="pass12345")
        profile=user.profile;profile.team=self.team;profile.role=UserProfile.Role.COACH;profile.save(update_fields=["team","role"])
        person=Person.objects.create(team=self.team,user=user,first_name=username,last_name="Coach")
        if finance:
            OrganizationCapabilityAssignment.objects.create(team=self.team,person=person,capability=OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE)
        return user

    def test_station_manager_without_finance_can_approve_but_not_post_credit(self):
        account,rule=self._work_credit_setup();shift=self._shift()
        coach=self._coach("station-only")
        self.client.force_login(coach)
        response=self.client.post(reverse("station_shift_approve",args=[shift.pk]))
        self.assertRedirects(response,reverse("station_shift_review"))
        shift.refresh_from_db();self.assertIsNotNone(shift.approved_at)
        review=self.client.get(reverse("station_shift_review"))
        self.assertContains(review,"$ 22.50");self.assertNotContains(review,"Post credit")
        response=self.client.post(reverse("station_shift_post_credit",args=[shift.pk]))
        self.assertRedirects(response,reverse("station_shift_review"))
        self.assertFalse(ReceivableCredit.objects.filter(account=account).exists())

    def test_station_manager_with_finance_can_post_credit(self):
        account,rule=self._work_credit_setup();shift=self._shift()
        coach=self._coach("station-finance",finance=True)
        shift.approved_by=coach;shift.approved_at=timezone.now();shift.save(update_fields=["approved_by","approved_at","updated_at"])
        self.client.force_login(coach)
        review=self.client.get(reverse("station_shift_review"))
        self.assertContains(review,"Post credit")
        response=self.client.post(reverse("station_shift_post_credit",args=[shift.pk]))
        self.assertRedirects(response,reverse("station_shift_review"))
        credit=ReceivableCredit.objects.get(account=account)
        self.assertEqual(credit.amount,Decimal("22.50"));self.assertEqual(credit.credit_rule,rule)

    def test_finance_authority_without_station_management_cannot_use_station_credit_action(self):
        account,rule=self._work_credit_setup();shift=self._shift()
        user=User.objects.create_user(username="finance-only",password="pass12345")
        profile=user.profile;profile.team=self.team;profile.role=UserProfile.Role.PARENT;profile.save(update_fields=["team","role"])
        person=Person.objects.create(team=self.team,user=user,first_name="Finance",last_name="Only")
        OrganizationCapabilityAssignment.objects.create(team=self.team,person=person,capability=OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE)
        shift.approved_by=self.admin;shift.approved_at=timezone.now();shift.save(update_fields=["approved_by","approved_at","updated_at"])
        self.client.force_login(user)
        review=self.client.get(reverse("station_shift_review"))
        self.assertEqual(review.status_code,403)
        response=self.client.post(reverse("station_shift_post_credit",args=[shift.pk]))
        self.assertEqual(response.status_code,403)
        self.assertFalse(ReceivableCredit.objects.filter(account=account).exists())
