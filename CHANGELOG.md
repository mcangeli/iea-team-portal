# ArenaLine Changelog

This is the canonical concise release history for ArenaLine. Detailed implementation and validation notes for substantial releases live under `docs/releases/`.

Older detailed release notes that predate this changelog remain available in `RELEASE_NOTES.md` and are preserved as historical documentation.

## v3.2.0 — People, Relationships & Barn Operations

**Unreleased — active development.**

Foundation work started with:

- a canonical organization-scoped `Person` identity;
- optional one-to-one linkage from `Person` to the Django `auth.User` login account;
- compatibility bridging from existing Rider and GuardianContact records without deleting or rewriting legacy identities;
- support for one Person to represent both a Rider and Parent/Guardian when those legacy records belong to the same human;
- date-aware multi-role assignments for Rider, Boarder, Trainer, Assistant Trainer, Barn Manager, Barn Staff, Working Student, and Board Member;
- directional Person relationships such as Parent/Guardian;
- generic Organization Groups / Programs;
- barn-wide or group-scoped Committees and Committee Memberships;
- expanded Person profile fields for birth date, school, graduation year, bio, photo, website, and social links;
- a new ArenaLine-branded People directory and canonical Person profile UI;
- Admin/Coach Person create/edit workflows with tenant-safe linkage to available Django login accounts;
- direct Person-profile management of multiple roles, relationships, and committee memberships;
- a manager-only People Structure workspace for organization groups/programs and generalized committees;
- a first barn-participation bridge linking canonical People to Horses as Owner, Boarder/Responsible Party, Full Lease, Half Lease, Partial Lease, Trainer, or Caretaker, with optional share and effective dates;
- manager workflows on Horse profiles to add/edit those People↔Horse relationships, with mirrored horse participation shown on Person profiles;
- a Barn Operations roster organizing active Trainers, Assistant Trainers, Barn Managers, Barn Staff, Working Students, Boarders, and Board Members into operational groups, with active horse responsibilities shown alongside each person;
- privacy-aware profile rendering so private contact/account/birth-date data is limited to managers or the linked person;
- responsive `people-v320.css` presentation and regression coverage for tenant, permission, account-link, relationship, committee, horse-person, cross-profile, and barn-operations safety;
- privacy-safe public-profile enablement as a future publication surface, with public fields still requiring explicit allow-listed publication behavior.

Migrations begin with `0066_v320_people_foundation.py`; `0067_v320_horse_person_relationship.py` adds the narrow People↔Horse participation bridge ahead of the broader v3.3 Equine Care release. Existing Rider, GuardianContact, UserProfile, CommitteeAssignment, and horse registry behavior remain compatibility structures while callers are migrated and regression-tested.

## v3.1.0 — Public / Live Spectator Experience

Released September 2026.

Highlights:

- explicit public organization/show publication controls and allow-listed anonymous payloads;
- public program/show pages, schedules, live status, and class-level results;
- stable reusable public live URL;
- show/class lifecycle controls and structured multi-ring operation;
- spectator-safe announcements and ring delays;
- responsive authenticated Show Day and polished public spectator presentation;
- privacy-safe family/squad visibility behavior.

Migrations: `0057` through `0065`.

Validation: clean Django system/migration checks and **486 portal tests passing**.

Detailed notes: `docs/releases/v3.1.0.md`.

## v3.0.0 — IEA Class Catalog & Competition Foundation

Released 2026.

Highlights:

- versioned official IEA Hunt Seat, Western, and Dressage class catalog;
- catalog-linked season/show classes;
- show-only warm-ups and Hunt Seat VOC;
- catalog-driven scoring eligibility;
- architecture/presentation cleanup ahead of public work.

Validation: **425 portal tests passing** before production promotion.

Detailed notes: `docs/releases/v3.0.0.md`.

## Earlier releases

The 2.x release history, including Horse/Hoofprint, Show Host Operations, finance, communications, and the ArenaLine platform transition, is retained in `RELEASE_NOTES.md` and related documents under `docs/`.

## Changelog rule

Every stable production release must add or update its entry here before promotion to `main`. The changelog should remain concise and user-facing; detailed engineering notes belong in the version-specific release document.
