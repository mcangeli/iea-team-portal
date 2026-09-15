from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.people_forms import PersonRolesForm
from portal.models import Team


class V323PeopleRolesFormTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.person = Person.objects.create(team=self.team, first_name="Casey", last_name="Morgan")

    def test_current_role_is_selected(self):
        OrganizationRoleAssignment.objects.create(team=self.team, person=self.person, role=OrganizationRoleAssignment.Role.BOARDER, active=True)
        form = PersonRolesForm(person=self.person)
        self.assertIn(OrganizationRoleAssignment.Role.BOARDER, form.fields["roles"].initial)

    def test_future_role_is_not_selected(self):
        OrganizationRoleAssignment.objects.create(team=self.team, person=self.person, role=OrganizationRoleAssignment.Role.BOARDER, start_date=timezone.localdate() + timedelta(days=1), active=True)
        form = PersonRolesForm(person=self.person)
        self.assertNotIn(OrganizationRoleAssignment.Role.BOARDER, form.fields["roles"].initial)

    def test_role_ending_today_is_not_selected(self):
        OrganizationRoleAssignment.objects.create(team=self.team, person=self.person, role=OrganizationRoleAssignment.Role.BOARDER, end_date=timezone.localdate(), active=True)
        form = PersonRolesForm(person=self.person)
        self.assertNotIn(OrganizationRoleAssignment.Role.BOARDER, form.fields["roles"].initial)
