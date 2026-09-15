from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.model_modules.barn_participation import HorsePersonRelationship
from portal.model_modules.horses import Horse
from portal.model_modules.people import Person
from portal.models import Team


class V320BarnParticipationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")
        self.person = Person.objects.create(team=self.team, first_name="Jane", last_name="Smith")
        self.horse = Horse.objects.create(team=self.team, name="Jasper")

    def test_person_can_have_multiple_horse_relationship_types(self):
        owner = HorsePersonRelationship.objects.create(
            team=self.team,
            horse=self.horse,
            person=self.person,
            relationship_type=HorsePersonRelationship.RelationshipType.OWNER,
        )
        trainer = HorsePersonRelationship.objects.create(
            team=self.team,
            horse=self.horse,
            person=self.person,
            relationship_type=HorsePersonRelationship.RelationshipType.TRAINER,
        )
        self.assertEqual(owner.person, self.person)
        self.assertEqual(trainer.horse, self.horse)
        self.assertEqual(self.person.horse_relationships.count(), 2)

    def test_lease_share_is_supported(self):
        relationship = HorsePersonRelationship(
            team=self.team,
            horse=self.horse,
            person=self.person,
            relationship_type=HorsePersonRelationship.RelationshipType.HALF_LEASE,
            share_percent=50,
        )
        relationship.full_clean()
        relationship.save()
        self.assertEqual(relationship.share_percent, 50)

    def test_share_must_be_between_one_and_one_hundred(self):
        relationship = HorsePersonRelationship(
            team=self.team,
            horse=self.horse,
            person=self.person,
            relationship_type=HorsePersonRelationship.RelationshipType.PARTIAL_LEASE,
            share_percent=0,
        )
        with self.assertRaises(ValidationError):
            relationship.full_clean()

    def test_cross_organization_person_is_rejected(self):
        outsider = Person.objects.create(team=self.other_team, first_name="Other", last_name="Person")
        relationship = HorsePersonRelationship(
            team=self.team,
            horse=self.horse,
            person=outsider,
            relationship_type=HorsePersonRelationship.RelationshipType.BOARDER,
        )
        with self.assertRaises(ValidationError):
            relationship.full_clean()

    def test_cross_organization_horse_is_rejected(self):
        outsider_horse = Horse.objects.create(team=self.other_team, name="Outside Horse")
        relationship = HorsePersonRelationship(
            team=self.team,
            horse=outsider_horse,
            person=self.person,
            relationship_type=HorsePersonRelationship.RelationshipType.TRAINER,
        )
        with self.assertRaises(ValidationError):
            relationship.full_clean()

    def test_end_date_cannot_precede_start_date(self):
        relationship = HorsePersonRelationship(
            team=self.team,
            horse=self.horse,
            person=self.person,
            relationship_type=HorsePersonRelationship.RelationshipType.CARETAKER,
            start_date="2026-09-14",
            end_date="2026-09-13",
        )
        with self.assertRaises(ValidationError):
            relationship.full_clean()
