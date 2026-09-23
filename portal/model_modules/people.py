from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from portal.models import GuardianContact, Rider, Team


class Person(models.Model):
    """Canonical organization-scoped human identity for ArenaLine.

    A Person may optionally have one Django login account and may participate in
    many roles, relationships, groups, committees, and domain workflows at once.
    Legacy Rider/Guardian records remain compatibility records during v3.2.
    """

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="people")
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="arena_person",
        help_text="Optional Django auth account used to sign in as this person.",
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    preferred_name = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    school = models.CharField(max_length=150, blank=True)
    graduation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="people/", blank=True, null=True)
    website_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    public_profile_enabled = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name", "id"]

    @property
    def display_name(self):
        first = self.preferred_name or self.first_name
        return f"{first} {self.last_name}".strip()

    def clean(self):
        super().clean()
        if self.user_id and hasattr(self.user, "profile"):
            profile_team_id = self.user.profile.team_id
            if profile_team_id and profile_team_id != self.team_id:
                raise ValidationError("Person and login account must belong to the same organization.")

    def __str__(self):
        return self.display_name


class LegacyPersonLink(models.Model):
    """Compatibility bridge from legacy identity records to one Person.

    Rider and GuardianContact remain authoritative compatibility records during
    v3.2 migration. A single Person may point to both when the same human was
    historically represented in both domains.
    """

    person = models.OneToOneField(
        Person,
        on_delete=models.CASCADE,
        related_name="legacy_identity",
    )
    rider = models.OneToOneField(
        Rider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="person_bridge",
    )
    guardian = models.OneToOneField(
        GuardianContact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="person_bridge",
    )

    def clean(self):
        super().clean()
        if self.rider_id and self.rider.team_id != self.person.team_id:
            raise ValidationError("Linked rider must belong to the person's organization.")
        if self.guardian_id and self.guardian.team_id != self.person.team_id:
            raise ValidationError("Linked guardian must belong to the person's organization.")

    def __str__(self):
        return f"Legacy identity — {self.person}"


class PersonRelationship(models.Model):
    class RelationshipType(models.TextChoices):
        PARENT_GUARDIAN = "parent_guardian", "Parent / Guardian"
        SPOUSE_PARTNER = "spouse_partner", "Spouse / Partner"
        EMERGENCY_CONTACT = "emergency_contact", "Emergency Contact"
        OTHER = "other", "Other"

    from_person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="outgoing_relationships"
    )
    to_person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="incoming_relationships"
    )
    relationship_type = models.CharField(max_length=30, choices=RelationshipType.choices)
    label = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional display label such as Mother, Father, Guardian, or Grandparent.",
    )
    primary_contact = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["relationship_type", "from_person__last_name", "from_person__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["from_person", "to_person", "relationship_type"],
                name="unique_person_relationship",
            )
        ]

    def clean(self):
        super().clean()
        if self.from_person_id and self.to_person_id:
            if self.from_person_id == self.to_person_id:
                raise ValidationError("A person cannot have a relationship to themselves.")
            if self.from_person.team_id != self.to_person.team_id:
                raise ValidationError("Related people must belong to the same organization.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("Relationship end date cannot be before the start date.")

    def __str__(self):
        return f"{self.from_person} → {self.get_relationship_type_display()} → {self.to_person}"


class OrganizationRoleAssignment(models.Model):
    class Role(models.TextChoices):
        PARENT_GUARDIAN = "parent_guardian", "Parent / Guardian"
        RIDER = "rider", "Rider"
        BOARDER = "boarder", "Boarder"
        TRAINER = "trainer", "Trainer"
        ASSISTANT_TRAINER = "assistant_trainer", "Assistant Trainer"
        BARN_MANAGER = "barn_manager", "Barn Manager"
        BARN_STAFF = "barn_staff", "Barn Staff"
        WORKING_STUDENT = "working_student", "Working Student"
        BOARD_MEMBER = "board_member", "Board Member"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="person_role_assignments")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="role_assignments")
    role = models.CharField(max_length=30, choices=Role.choices)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["role", "person__last_name", "person__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "person", "role", "start_date"],
                name="unique_person_role_assignment_period",
            ),
            models.UniqueConstraint(
                fields=["team", "person", "role"],
                condition=models.Q(start_date__isnull=True),
                name="unique_person_role_assignment_null_start",
            ),
        ]

    def clean(self):
        super().clean()
        if self.person_id and self.team_id and self.person.team_id != self.team_id:
            raise ValidationError("Role assignment must belong to the person's organization.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("Role end date cannot be before the start date.")

    def __str__(self):
        return f"{self.person} — {self.get_role_display()}"


class OrganizationGroup(models.Model):
    class GroupType(models.TextChoices):
        PROGRAM = "program", "Program"
        TEAM = "team", "Team"
        SHOW = "show", "Show"
        DEPARTMENT = "department", "Department"
        OTHER = "other", "Other"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="organization_groups")
    name = models.CharField(max_length=120)
    group_type = models.CharField(max_length=20, choices=GroupType.choices, default=GroupType.PROGRAM)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subgroups",
    )
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["team", "name"], name="unique_organization_group_name")
        ]

    def clean(self):
        super().clean()
        if self.parent_id:
            if self.parent_id == self.id:
                raise ValidationError("A group cannot be its own parent.")
            if self.parent.team_id != self.team_id:
                raise ValidationError("A parent group must belong to the same organization.")

    def __str__(self):
        return self.name


class OrganizationGroupMembership(models.Model):
    """Durable Person membership in an organizational group or program.

    This records where a Person participates. Domain-specific facts remain in
    their owning models (for example LessonEnrollment or IEA season records).
    Membership does not grant application authorization by itself.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        PENDING = "pending", "Pending"
        ALUMNI = "alumni", "Alumni"

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="organization_group_memberships",
    )
    group = models.ForeignKey(
        OrganizationGroup,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="organization_group_memberships",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    role_label = models.CharField(
        max_length=80,
        blank=True,
        help_text="Optional program-specific label; this does not grant application permissions.",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["group__sort_order", "group__name", "person__last_name", "person__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "person", "start_date"],
                name="unique_group_person_membership_period",
            ),
            models.UniqueConstraint(
                fields=["group", "person"],
                condition=models.Q(start_date__isnull=True),
                name="unique_group_person_membership_null_start",
            ),
        ]

    def clean(self):
        super().clean()
        if self.group_id and self.team_id and self.group.team_id != self.team_id:
            raise ValidationError("Group membership must belong to the group's organization.")
        if self.person_id and self.team_id and self.person.team_id != self.team_id:
            raise ValidationError("Group membership must belong to the person's organization.")
        if self.group_id and self.person_id and self.group.team_id != self.person.team_id:
            raise ValidationError("Group and person must belong to the same organization.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("Group membership end date cannot be before the start date.")

    def __str__(self):
        return f"{self.group} — {self.person}"


class Committee(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="committees")
    group = models.ForeignKey(
        OrganizationGroup,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="committees",
        help_text="Optional program/group scope such as IEA, Shows, or another barn program.",
    )
    name = models.CharField(max_length=120)
    purpose = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["team", "group", "name"], name="unique_scoped_committee_name"),
            models.UniqueConstraint(
                fields=["team", "name"],
                condition=models.Q(group__isnull=True),
                name="unique_barnwide_committee_name",
            ),
        ]

    def clean(self):
        super().clean()
        if self.group_id and self.group.team_id != self.team_id:
            raise ValidationError("Committee group must belong to the same organization.")

    def __str__(self):
        return self.name


class CommitteeMembership(models.Model):
    class Position(models.TextChoices):
        CHAIR = "chair", "Chair"
        CO_CHAIR = "co_chair", "Co-chair"
        SECRETARY = "secretary", "Secretary"
        TREASURER = "treasurer", "Treasurer"
        MEMBER = "member", "Member"
        LIAISON = "liaison", "Liaison"

    committee = models.ForeignKey(Committee, on_delete=models.CASCADE, related_name="memberships")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="committee_memberships")
    legacy_committee_assignment = models.OneToOneField(
        "portal.CommitteeAssignment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="canonical_membership",
        help_text="Compatibility source when this membership mirrors a legacy IEA committee assignment.",
    )
    position = models.CharField(max_length=20, choices=Position.choices, default=Position.MEMBER)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["position", "person__last_name", "person__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["committee", "person", "position", "start_date"],
                name="unique_committee_membership_period",
            ),
            models.UniqueConstraint(
                fields=["committee", "person", "position"],
                condition=models.Q(start_date__isnull=True),
                name="unique_committee_membership_null_start",
            ),
        ]

    def clean(self):
        super().clean()
        if self.committee_id and self.person_id and self.committee.team_id != self.person.team_id:
            raise ValidationError("Committee membership must remain within one organization.")
        if self.legacy_committee_assignment_id:
            legacy = self.legacy_committee_assignment
            if legacy.team_id != self.committee.team_id or legacy.team_id != self.person.team_id:
                raise ValidationError("Legacy committee source must belong to the same organization.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("Committee membership end date cannot be before the start date.")

    def __str__(self):
        return f"{self.committee} — {self.person} ({self.get_position_display()})"
