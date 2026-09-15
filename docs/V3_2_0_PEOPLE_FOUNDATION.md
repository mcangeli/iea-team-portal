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

## Implemented People directory/profile slice

The first management UI is now built on the canonical Person layer rather than the legacy Rider/Guardian tables.

Implemented behavior:

- `/people/` is the canonical authenticated organization People directory;
- Person cards use the established ArenaLine People branding and responsive card language;
- `/people/<id>/` provides a canonical profile view;
- Admin/Coach users can add and edit Person profiles;
- organization members may browse organization-safe Person identity/role information;
- private contact/account/birth-date information is visible only to Admin/Coach or the Person's own linked Django account;
- Person profile creation/editing may attach an existing Django `auth.User` account;
- account choices are restricted to the current organization and to logins not already attached to another Person, while an existing Person retains its current account as an editable choice;
- tenant scoping is enforced in the service/view layer rather than only in presentation;
- existing Riders and Parents/Guardians remain available as compatibility navigation/workflows while the canonical People experience is introduced;
- `people-v320.css` provides ArenaLine-consistent desktop/tablet/mobile profile and directory presentation.

Focused regression coverage lives in `portal/tests/test_v320_people_directory.py` and includes private-field visibility, management permissions, tenant isolation, and Django account-link safety.

## Implemented roles, relationships, groups & committees slice

The Person experience now exposes the multi-role organization model directly rather than requiring Django admin.

Implemented behavior:

- Admin/Coach users may add and edit multiple concurrent `OrganizationRoleAssignment` records from a Person profile;
- directional relationships are managed from the source Person profile, including Parent/Guardian, Spouse/Partner, Emergency Contact, labels, primary-contact state, and effective dates;
- relationship selectors are organization-scoped and cannot attach a Person from another tenant;
- committee memberships are Person-based and support Chair, Co-chair, Secretary, Treasurer, Member, and Liaison positions;
- `/people/structure/` manages reusable Organization Groups / Programs and generalized Committees;
- committees may be organization-wide or scoped to a Group/Program such as IEA, Shows, Lessons, or another barn function;
- groups support one optional parent for modest subgroup hierarchy without making the UI an unrestricted org-chart editor;
- People structure editing is manager-only;
- legacy `CommitteeAssignment` remains authoritative for existing IEA authorization until those permission callers are explicitly migrated and regression-tested.

Focused regression coverage lives in `portal/tests/test_v320_people_relationships.py` and protects multi-role behavior, directional parent/guardian relationships, tenant isolation, group-scoped committees, Person-based committee memberships, and manager-only structure editing.

## Implemented barn participation bridge

Migration `0067_v320_horse_person_relationship.py` introduces a narrow People↔Horse relationship layer without pulling the broader v3.3 Equine Care scope into v3.2.

`HorsePersonRelationship` currently supports:

- Owner;
- Boarder / Responsible Party;
- Full Lease;
- Half Lease;
- Partial Lease;
- Trainer;
- Caretaker.

Relationships may carry an optional share percentage, start/end dates, active state, and notes. Horse, Person, and relationship tenant ownership must all match.

The Horse profile is the editing surface for these relationships. Admin/Coach users may add or edit a linked person from the Horse profile, while the canonical Person profile mirrors the same relationship and links back to the Horse. The relationship record remains single-source; ArenaLine does not create a duplicate Person-side ownership/lease record.

This preserves a clean handoff into v3.3: veterinary, farrier, medication, feed, health, and broader care records remain future Equine Care work rather than being prematurely mixed into the v3.2 people foundation.

Focused regression coverage lives in `portal/tests/test_v320_barn_participation.py` for model rules and `portal/tests/test_v320_barn_participation_ui.py` for manager permissions, tenant isolation, form behavior, and mirrored Horse/Person profile presentation.

## Implemented Barn Operations roster

`/people/operations/` turns the multi-role model into a practical operational view rather than leaving Trainer, Staff, Working Student, Boarder, and Board Member as profile labels only.

The roster groups active people into:

- Training team — Trainer and Assistant Trainer;
- Barn management & staff — Barn Manager and Barn Staff;
- Working students;
- Boarders;
- Board members.

Where a person also has active `HorsePersonRelationship` records, the roster surfaces the horse, relationship type, and optional share and links back to the Horse profile. This gives barn staff one operational directory while keeping horse relationships single-source.

The roster is readable by authenticated organization members; management actions remain permission-aware and all queries are tenant-scoped. Work-shift clock-in/out and shared-device workflows are intentionally deferred to ArenaLine Station in v3.2.2.

Focused regression coverage lives in `portal/tests/test_v320_barn_operations.py` and protects authenticated access, horse responsibility display, and tenant isolation.

## Implemented legacy committee compatibility bridge

Migration `0068_v320_legacy_committee_bridge.py` gives legacy IEA committee assignments a traceable path into the generalized committee model without changing the authorization source used by existing IEA workflows.

Each mirrored `CommitteeMembership` may carry an optional one-to-one `legacy_committee_assignment` reference. This source link prevents ArenaLine from confusing migrated compatibility rows with committee memberships created directly in the new People Structure experience.

Legacy role mapping is:

- Upper Team Parent → IEA Program / Upper Team Parent Committee / Chair;
- Futures Team Parent → IEA Program / Futures Team Parent Committee / Chair;
- Treasurer → organization-wide Finance Committee / Treasurer;
- Secretary / Points Secretary → IEA Program / IEA Points & Records / Secretary.

The mirrored membership inherits the legacy season start/end dates and active state. A compatibility signal keeps later legacy creates, edits, deactivations, and deletes synchronized to the source-linked canonical membership. Deleting a legacy assignment removes only its mirrored membership; manually created generalized committee memberships are not touched.

Existing IEA permission checks continue to read `CommitteeAssignment` during this transition. `ShowLeadAssignment` remains a separate show-specific operational assignment and is intentionally not converted into a committee membership.

Focused regression coverage lives in `portal/tests/test_v320_committee_compat.py` and protects mapping, season dates, deactivation, source tracing, and manual-membership isolation.

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
