# ArenaLine Changelog

This is the canonical concise release history for ArenaLine. Detailed implementation and validation notes for substantial releases live under `docs/releases/`.

Older detailed release notes that predate this changelog remain available in `RELEASE_NOTES.md` and are preserved as historical documentation.

## v3.3.0 — Equine Care & Horse Management

Released September 2026.

v3.3.0 expands ArenaLine's Horse Registry into an operational equine-care, document, and compliance system while preserving established IEA Horse, Show, Hoofprint, Horse of the Day, and historical workflows.

Highlights:

- durable horse identifiers and expanded People↔Horse care-provider relationships;
- historical care records for vaccination, farrier, dental, veterinary, medication, wellness, and other care activity;
- next-due scheduling intelligence with overdue, due-soon, and current status;
- full completed-care history organized by year;
- generic horse documents with effective/expiration dates and optional care-record linkage;
- configurable organization compliance requirements for Coggins and horse document types;
- show-date-aware compliance so records must remain valid through the actual show date;
- Show Readiness and Show Horses integration with blocking vs warning compliance states;
- Hoofprint compliance integration that blocks finalization for unresolved required horse records while preserving preview and advisory Hoofprint warnings;
- authenticated, organization-scoped protected downloads for generic horse documents and Coggins attachments;
- privacy-safe manager/non-manager presentation and preserved historical Horse of the Day behavior.

Migrations: `0072_v330_horse_identifiers.py` through `0077_v330_horse_compliance_requirements.py`.

Validation: clean Django system/migration checks, **128/128 horse/show/Hoofprint regression tests passing**, and **732/732 portal tests passing** on the final v3.3.0 staging baseline.

Detailed notes: `docs/releases/v3.3.0.md`.

## v3.2.3 — People & Operations Polish

Released September 2026.

v3.2.3 closes the 3.2.x People, Relationships & Barn Operations release family. The family was developed through the v3.2.0 Unified People & Organization Foundation, v3.2.1 Barn Participation & Horse Relationships, v3.2.2 ArenaLine Station, and v3.2.3 People & Operations Polish milestones.

Highlights:

- canonical organization-scoped `Person` identity with optional login access and compatibility bridges for existing Rider/Guardian/User structures;
- multiple simultaneous, effective-date-aware barn roles and parent/guardian relationships;
- generic organization Groups/Programs and generalized Committees/Committee Memberships;
- People↔Horse ownership, boarding, lease, trainer, responsible-party, and caretaker relationships;
- People directory/profile and Person-first login/family management workflows;
- Barn Operations and People Structure operational views with current-effective relationship handling;
- ArenaLine Station shared-device authentication, Person PINs, work-role clock-in/out, manager review/correction/approval, summaries, export, and audit history;
- privacy-aware My Account and Person work-history access;
- deliberately published public rider profiles/cards using allow-listed profile fields;
- Instagram/YouTube-only public social profile surface while legacy database fields remain compatibility-safe;
- responsive People/Station/public presentation plus keyboard, mobile-navigation, empty-state, and accessibility hardening;
- regression reconciliation around current People-first architecture and terminology.

Migrations: `0066_v320_people_foundation.py` through `0070_v322_person_multi_roles.py` establish the core People/horse/committee/Station/multi-role persistence used by the 3.2.x family.

Validation: clean Django system checks and **643/643 portal tests passing** on the final v3.2.3 staging baseline.

Detailed notes: `docs/releases/v3.2.3.md`.

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
