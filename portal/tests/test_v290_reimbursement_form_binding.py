"""Focused regression coverage for the v2.9 reimbursement form normalization."""

from django.contrib.auth.models import User
from django.test import TestCase

from portal.forms import ReimbursementRequestForm
from portal.models import Team


class ReimbursementRequestFormBindingTests(TestCase):
    def test_constructor_binds_team_to_model_instance_before_validation(self):
        team = Team.objects.create(name="ArenaLine Test Team")
        user = User.objects.create_user(username="finance-form-test")

        form = ReimbursementRequestForm(team=team, user=user)

        self.assertEqual(form.instance.team, team)
