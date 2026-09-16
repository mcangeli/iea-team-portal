from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from portal.horse_models import Horse, HorseIdentifier
from portal.models import Team


class EquineRegistryFoundationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Test Program")
        self.horse = Horse.objects.create(team=self.team, name="Atlas")

    def test_existing_horse_is_canonical_equine_identity(self):
        self.assertEqual(self.horse.display_name, "Atlas")
        self.assertEqual(self.horse.team, self.team)

    def test_horse_identifier_attaches_to_existing_horse(self):
        identifier = HorseIdentifier.objects.create(
            horse=self.horse,
            authority="IEA",
            identifier_type="Horse ID",
            value="IEA-12345",
            is_primary=True,
        )
        self.assertEqual(identifier.horse, self.horse)
        self.assertEqual(self.horse.identifiers.get(), identifier)
        self.assertIn("IEA-12345", str(identifier))

    def test_same_external_identifier_is_not_duplicated_on_one_horse(self):
        HorseIdentifier.objects.create(
            horse=self.horse,
            authority="USEF",
            identifier_type="Registration",
            value="1234567",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                HorseIdentifier.objects.create(
                    horse=self.horse,
                    authority="USEF",
                    identifier_type="Registration",
                    value="1234567",
                )

    def test_same_identifier_value_can_exist_for_different_authorities(self):
        HorseIdentifier.objects.create(horse=self.horse, authority="IEA", value="123")
        HorseIdentifier.objects.create(horse=self.horse, authority="USEF", value="123")
        self.assertEqual(self.horse.identifiers.count(), 2)

    def test_identifier_is_removed_with_horse(self):
        HorseIdentifier.objects.create(horse=self.horse, authority="IEA", value="123")
        horse_id = self.horse.pk
        self.horse.delete()
        self.assertFalse(HorseIdentifier.objects.filter(horse_id=horse_id).exists())
