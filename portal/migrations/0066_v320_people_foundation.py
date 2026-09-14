from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_people(apps, schema_editor):
    Person = apps.get_model("portal", "Person")
    LegacyPersonLink = apps.get_model("portal", "LegacyPersonLink")
    OrganizationRoleAssignment = apps.get_model("portal", "OrganizationRoleAssignment")
    PersonRelationship = apps.get_model("portal", "PersonRelationship")
    Rider = apps.get_model("portal", "Rider")
    GuardianContact = apps.get_model("portal", "GuardianContact")
    RiderGuardian = apps.get_model("portal", "RiderGuardian")
    UserProfile = apps.get_model("portal", "UserProfile")

    person_by_user = {}

    def user_defaults(user, fallback_first="", fallback_last="", fallback_email=""):
        if not user:
            return {
                "first_name": fallback_first,
                "last_name": fallback_last,
                "email": fallback_email,
            }
        return {
            "first_name": user.first_name or fallback_first,
            "last_name": user.last_name or fallback_last,
            "email": user.email or fallback_email,
        }

    def person_for_user(team_id, user_id, **defaults):
        if not user_id:
            return None
        cached = person_by_user.get(user_id)
        if cached:
            return cached
        existing = Person.objects.filter(user_id=user_id).first()
        if existing:
            person_by_user[user_id] = existing
            return existing
        person = Person.objects.create(team_id=team_id, user_id=user_id, **defaults)
        person_by_user[user_id] = person
        return person

    # Build canonical people from riders first. A Rider with a Django account owns
    # that Person identity. Riders without accounts remain separate people.
    for rider in Rider.objects.select_related("user").all().iterator():
        defaults = user_defaults(
            rider.user,
            fallback_first=rider.first_name,
            fallback_last=rider.last_name,
            fallback_email=rider.email,
        )
        person = person_for_user(rider.team_id, rider.user_id, **defaults)
        if person is None:
            person = Person.objects.create(
                team_id=rider.team_id,
                first_name=rider.first_name,
                last_name=rider.last_name,
                preferred_name=rider.preferred_name,
                email=rider.email,
                school=rider.school,
                bio=rider.bio,
                photo=rider.photo,
                active=rider.active,
            )
        else:
            changed = []
            for field, value in (
                ("preferred_name", rider.preferred_name),
                ("school", rider.school),
                ("bio", rider.bio),
            ):
                if value and not getattr(person, field):
                    setattr(person, field, value)
                    changed.append(field)
            if rider.photo and not person.photo:
                person.photo = rider.photo
                changed.append("photo")
            if changed:
                person.save(update_fields=changed)

        link, _ = LegacyPersonLink.objects.get_or_create(person=person)
        if not link.rider_id:
            link.rider_id = rider.id
            link.save(update_fields=["rider"])

        OrganizationRoleAssignment.objects.get_or_create(
            team_id=rider.team_id,
            person=person,
            role="rider",
            start_date=None,
            defaults={"active": rider.active},
        )

    # Guardians sharing the same Django account as a rider intentionally converge
    # onto the same Person, enabling adult-rider + parent use cases.
    for guardian in GuardianContact.objects.select_related("user").all().iterator():
        defaults = user_defaults(
            guardian.user,
            fallback_first=guardian.first_name,
            fallback_last=guardian.last_name,
            fallback_email=guardian.email,
        )
        person = person_for_user(guardian.team_id, guardian.user_id, **defaults)
        if person is None:
            person = Person.objects.create(
                team_id=guardian.team_id,
                first_name=guardian.first_name,
                last_name=guardian.last_name,
                email=guardian.email,
                phone=guardian.phone,
            )
        elif guardian.phone and not person.phone:
            person.phone = guardian.phone
            person.save(update_fields=["phone"])

        link, _ = LegacyPersonLink.objects.get_or_create(person=person)
        if not link.guardian_id:
            link.guardian_id = guardian.id
            link.save(update_fields=["guardian"])

    # Users that exist only as Django/UserProfile accounts still receive a Person.
    for profile in UserProfile.objects.select_related("user").all().iterator():
        if not profile.team_id or profile.user_id in person_by_user:
            continue
        defaults = user_defaults(profile.user)
        person = person_for_user(profile.team_id, profile.user_id, **defaults)
        if person and profile.phone and not person.phone:
            person.phone = profile.phone
            person.save(update_fields=["phone"])

    # Convert explicit guardian relationships without name-based guessing.
    rider_links = {
        link.rider_id: link.person_id
        for link in LegacyPersonLink.objects.exclude(rider_id=None)
    }
    guardian_links = {
        link.guardian_id: link.person_id
        for link in LegacyPersonLink.objects.exclude(guardian_id=None)
    }
    for relation in RiderGuardian.objects.all().iterator():
        guardian_person_id = guardian_links.get(relation.guardian_id)
        rider_person_id = rider_links.get(relation.rider_id)
        if not guardian_person_id or not rider_person_id or guardian_person_id == rider_person_id:
            continue
        PersonRelationship.objects.get_or_create(
            from_person_id=guardian_person_id,
            to_person_id=rider_person_id,
            relationship_type="parent_guardian",
            defaults={
                "label": relation.relationship,
                "primary_contact": relation.primary_contact,
                "active": True,
            },
        )


def reverse_backfill(apps, schema_editor):
    # New v3.2 records are additive. Reversing the schema drops them without
    # altering legacy Rider/Guardian/UserProfile data.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0065_v310_spectator_show_updates"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Person",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("first_name", models.CharField(max_length=80)),
                ("last_name", models.CharField(max_length=80)),
                ("preferred_name", models.CharField(blank=True, max_length=80)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("birth_date", models.DateField(blank=True, null=True)),
                ("school", models.CharField(blank=True, max_length=150)),
                ("graduation_year", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("bio", models.TextField(blank=True)),
                ("photo", models.ImageField(blank=True, null=True, upload_to="people/")),
                ("website_url", models.URLField(blank=True)),
                ("instagram_url", models.URLField(blank=True)),
                ("facebook_url", models.URLField(blank=True)),
                ("tiktok_url", models.URLField(blank=True)),
                ("youtube_url", models.URLField(blank=True)),
                ("public_profile_enabled", models.BooleanField(default=False)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="people", to="portal.team")),
                ("user", models.OneToOneField(blank=True, help_text="Optional Django auth account used to sign in as this person.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="arena_person", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["last_name", "first_name", "id"]},
        ),
        migrations.CreateModel(
            name="OrganizationGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("group_type", models.CharField(choices=[("program", "Program"), ("team", "Team"), ("show", "Show"), ("department", "Department"), ("other", "Other")], default="program", max_length=20)),
                ("description", models.TextField(blank=True)),
                ("active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="subgroups", to="portal.organizationgroup")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="organization_groups", to="portal.team")),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="Committee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("purpose", models.TextField(blank=True)),
                ("active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("group", models.ForeignKey(blank=True, help_text="Optional program/group scope such as IEA, Shows, or another barn program.", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="committees", to="portal.organizationgroup")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="committees", to="portal.team")),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="LegacyPersonLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("guardian", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="person_bridge", to="portal.guardiancontact")),
                ("person", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="legacy_identity", to="portal.person")),
                ("rider", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="person_bridge", to="portal.rider")),
            ],
        ),
        migrations.CreateModel(
            name="OrganizationRoleAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("rider", "Rider"), ("boarder", "Boarder"), ("trainer", "Trainer"), ("assistant_trainer", "Assistant Trainer"), ("barn_manager", "Barn Manager"), ("barn_staff", "Barn Staff"), ("working_student", "Working Student"), ("board_member", "Board Member")], max_length=30)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="role_assignments", to="portal.person")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="person_role_assignments", to="portal.team")),
            ],
            options={"ordering": ["role", "person__last_name", "person__first_name"]},
        ),
        migrations.CreateModel(
            name="PersonRelationship",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("relationship_type", models.CharField(choices=[("parent_guardian", "Parent / Guardian"), ("spouse_partner", "Spouse / Partner"), ("emergency_contact", "Emergency Contact"), ("other", "Other")], max_length=30)),
                ("label", models.CharField(blank=True, help_text="Optional display label such as Mother, Father, Guardian, or Grandparent.", max_length=50)),
                ("primary_contact", models.BooleanField(default=False)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("from_person", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outgoing_relationships", to="portal.person")),
                ("to_person", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="incoming_relationships", to="portal.person")),
            ],
            options={"ordering": ["relationship_type", "from_person__last_name", "from_person__first_name"]},
        ),
        migrations.CreateModel(
            name="CommitteeMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.CharField(choices=[("chair", "Chair"), ("co_chair", "Co-chair"), ("secretary", "Secretary"), ("treasurer", "Treasurer"), ("member", "Member"), ("liaison", "Liaison")], default="member", max_length=20)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("committee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="portal.committee")),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="committee_memberships", to="portal.person")),
            ],
            options={"ordering": ["position", "person__last_name", "person__first_name"]},
        ),
        migrations.AddConstraint(
            model_name="organizationgroup",
            constraint=models.UniqueConstraint(fields=("team", "name"), name="unique_organization_group_name"),
        ),
        migrations.AddConstraint(
            model_name="committee",
            constraint=models.UniqueConstraint(fields=("team", "group", "name"), name="unique_scoped_committee_name"),
        ),
        migrations.AddConstraint(
            model_name="organizationroleassignment",
            constraint=models.UniqueConstraint(fields=("team", "person", "role", "start_date"), name="unique_person_role_assignment_period"),
        ),
        migrations.AddConstraint(
            model_name="personrelationship",
            constraint=models.UniqueConstraint(fields=("from_person", "to_person", "relationship_type"), name="unique_person_relationship"),
        ),
        migrations.AddConstraint(
            model_name="committeemembership",
            constraint=models.UniqueConstraint(fields=("committee", "person", "position", "start_date"), name="unique_committee_membership_period"),
        ),
        migrations.RunPython(backfill_people, reverse_backfill),
    ]
