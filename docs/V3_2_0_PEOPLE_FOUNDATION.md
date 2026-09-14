# ArenaLine v3.2.0 — People, Relationships & Barn Operations Foundation

## Goal

v3.2.0 establishes a canonical human/organization model that can represent real barn operations without forcing one person into a single mutually exclusive account type.

The central rule is:

> A Django login account authenticates a Person; roles, relationships, memberships, permissions, and public identity are separate concerns.

## Canonical identity

`Person` becomes the long-term organization-scoped human identity.

A Person may optionally link one-to-one to Django `auth.User` through `Person.user`.

This means:

- not every Person requires a login;
- one Django account represents one Person;
- a Person may hold many organizational roles at the same time;
- a Person may participate in many relationships, groups, and committees;
- a Person may be both a Rider and a Parent/Guardian;
- authentication continues to use Django's built-in auth system rather than introducing a parallel credential store.

`UserProfile` remains a compatibility authorization/profile record during the v3.2 migration. It is not the new canonical person identity.

## Legacy compatibility

Existing models remain in place during the migration:

- `Rider`
- `GuardianContact`
- `RiderGuardian`
- `UserProfile`
- `CommitteeAssignment`

`LegacyPersonLink` bridges a Person to zero or one legacy Rider and zero or one legacy GuardianContact.

A single bridge may point to both records. This is intentional and supports an adult rider who is also the parent/guardian of another rider.

### Backfill safety

Automatic migration may merge legacy identities only when the same existing Django `User` account proves they represent the same person.

ArenaLine must not merge Rider and GuardianContact records merely because names or email addresses look similar. Ambiguous duplicates require deliberate review/merge tooling later in v3.2.

## Person profile

The initial canonical profile supports:

- legal/given name;
- preferred name;
- email and phone;
- birth date;
- school;
- graduation year;
- bio;
- photo;
- website;
- Instagram, Facebook, TikTok, and YouTube links;
- active/inactive lifecycle;
- public-profile enablement.

Age is derived from birth date when needed and should not be stored independently.

Public profile enablement does not itself expose the internal Person record. A later v3.2 publication slice must create an explicit allow-listed public payload, following the same private-by-default rules introduced in v3.1.

## Roles

`OrganizationRoleAssignment` records what a person does in the barn/program and permits simultaneous roles.

Initial roles:

- Rider
- Boarder
- Trainer
- Assistant Trainer
- Barn Manager
- Barn Staff
- Working Student
- Board Member

These role labels do not automatically grant application permissions. Authorization remains explicit and separately testable.

## Person relationships

`PersonRelationship` records directional human relationships.

Initial relationship types include:

- Parent / Guardian
- Spouse / Partner
- Emergency Contact
- Other

Parent/Guardian is stored guardian → dependent. The inverse can be derived for display rather than storing duplicate inverse rows.

## Groups and programs

`OrganizationGroup` supplies a generic scoping layer for barn programs and operational groups.

Initial group types:

- Program
- Team
- Show
- Department
- Other

Groups may optionally have one parent group. The normal UI should remain simple even though the data model permits a modest hierarchy.

Examples:

- IEA Program
- Lesson Program
- Boarding
- Staff
- Shows

## Committees

`Committee` is organization-wide by default and may optionally be scoped to an `OrganizationGroup`.

Examples:

- Finance Committee — organization-wide
- Governance Committee — organization-wide
- Events Committee — organization-wide
- IEA Events Committee — scoped to IEA Program
- Show Hospitality Committee — scoped to a Show group

`CommitteeMembership` records a Person's position and effective period.

Initial positions:

- Chair
- Co-chair
- Secretary
- Treasurer
- Member
- Liaison

Existing `CommitteeAssignment` behavior remains active until its authorization callers are deliberately ported to the new committee model.

## Migration 0066

`0066_v320_people_foundation.py` is additive.

It creates the new people/group/committee tables and then performs conservative backfill:

1. Existing Riders create or attach to Person records.
2. Rider-backed people receive the Rider organization role.
3. Existing GuardianContact records create or attach to Person records.
4. If Rider and GuardianContact share the same Django User, they converge on one Person.
5. UserProfile accounts not represented by Rider/Guardian records still receive a Person when they have an organization.
6. Existing RiderGuardian links become Person parent/guardian relationships when both sides can be resolved safely.
7. Legacy records are retained unchanged.

The migration does not infer identity from names.

## Planned v3.2 slices

### v3.2.0 foundation

- canonical Person identity;
- Django auth linkage;
- legacy bridge/backfill;
- roles and relationships;
- groups/programs;
- generalized committees;
- expanded profile data;
- compatibility services and tests;
- People management UI following the ArenaLine product/UI guide.

### v3.2.1 barn participation

- richer boarder/lease participation;
- horse-person operational relationships in preparation for v3.3;
- trainer/staff/board-member workflows;
- migration of appropriate legacy committee experiences onto generalized groups/committees.

### v3.2.2 ArenaLine Station

- registered barn tablet/station mode;
- limited station identity/PIN workflow;
- lesson check-in/out;
- work-shift clock-in/out;
- no reuse of full ArenaLine passwords on a shared station.

### v3.2.3 polish and reporting

- time-entry review/approval;
- attendance/work history;
- working-student hour tracking;
- group/committee dashboards;
- reporting/export;
- permission, privacy, and presentation hardening.

## Presentation requirement

Every v3.2 People page must follow `docs/PRODUCT_AND_UI_GUIDE.md` and the established ArenaLine visual system. Desktop, tablet, mobile, light/dark behavior, empty states, and server-side authorization are part of completion criteria rather than follow-up polish.

## Documentation requirement

As v3.2 evolves, keep the following current in the feature branch:

- `README.md` for overview/setup/usage/update instructions;
- `ROADMAP.md` for product direction;
- `CHANGELOG.md` for concise release history;
- `ARCHITECTURE.md` for boundaries/data flow/compatibility;
- this document and the eventual `docs/releases/v3.2.0.md` for implementation/release detail.
