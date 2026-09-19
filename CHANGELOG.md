# ArenaLine Changelog

This is the canonical concise release history for ArenaLine. Detailed implementation and validation notes for substantial releases live under `docs/releases/`.

Older detailed release notes that predate this changelog remain available in `RELEASE_NOTES.md` and are preserved as historical documentation.

## v3.6.1 — IEA Lesson Occurrence Hotfix

Released September 2026.

v3.6.1 fixes converted and newly created IEA lesson operations so occurrence-based attendance editing remains in the v3.4 Lesson Program workflow instead of resolving to the legacy lesson attendance editor.

Highlights:

- gives the v3.4 occurrence attendance editor a distinct URL name, eliminating its collision with the legacy IEA lesson attendance route;
- updates occurrence detail actions to use the occurrence-specific attendance editor while preserving the legacy route for compatibility;
- adds regression coverage proving the legacy and occurrence attendance routes remain distinct;
- validates the production legacy IEA lesson conversion workflow: 3 legacy lessons converted into 5 occurrence partitions with 28 attendance records and 28 participant/horse assignments, with zero conversion issues;
- confirms conversion idempotency: a repeat applied conversion created no duplicate programs, series, occurrences, attendance records, or assignments;
- legacy lesson records remain unchanged for compatibility, and new IEA lessons are created directly through the current Lesson Program architecture.

Migrations: no new Django schema migration is introduced by v3.6.1. Existing production legacy IEA lesson data must be converted once, where applicable, with `python manage.py convert_legacy_iea_lessons --apply` after reviewing the command's dry-run report.

Validation: production legacy conversion and idempotency checks completed successfully; occurrence attendance/horse editing and creation of a new IEA lesson were manually verified on the production workflow.

## v3.6.0 — Dashboard Refresh & Account Security

Released September 2026.

v3.6.0 gives ArenaLine a clearer operational home while separating the general barn/program experience from the IEA team workspace, and adds self-service email verification plus optional multi-factor authentication.

Highlights:

- rebuilt the root Dashboard as a permission-aware general barn/program cockpit for schedules, action items, operational snapshots, quick actions, horses, lessons, and authorized finance information;
- established **My Team** as the distinct IEA team hub, with Coach, Team Parent, Points Secretary, Treasurer, Show Lead, and Show Manager workspaces kept inside the team experience;
- parent-first My Team behavior preserves the family view while allowing parents with operational assignments to switch into their authorized team workspaces;
- IEA announcements and competition-specific information stay out of the general Barn Dashboard;
- independently configurable Barn Dashboard and IEA Team hero imagery, with Futures/Upper squad branding retained and safe fallback behavior;
- account email changes now require the current password and verification of the new address before replacing the active login email;
- existing accounts are migrated as verified, while pending email state and replay/stale-token protections preserve account integrity;
- optional TOTP MFA can be enrolled from My Account using authenticator-app QR/manual setup, with one-time recovery codes and password-protected disablement;
- MFA-enabled login requires the second factor after password authentication and supports single-use recovery codes;
- local Postfix is the default mail-delivery target, avoiding embedded third-party SMTP credentials in ArenaLine configuration.

Migrations: v3.6 adds Team Branding barn-hero fields plus account email-verification and MFA profile state. The applied migration filenames include `0067_userprofile_email_verification.py`, `0068_userprofile_mfa.py`, and `0069_teambranding_barn_hero.py`; deployment validation must rely on Django's migration graph rather than filename ordering.

Validation: focused v3.6 dashboard/security regression coverage and manual dashboard/MFA presentation testing completed on staging. Clean system/migration checks and the complete portal suite remain the final release-promotion gate.

Detailed notes: `docs/releases/v3.6.0.md`.

## v3.5.0 — Barn Finance & Business Operations

Released September 2026.

v3.5.0 establishes ArenaLine's generic operational-finance architecture while preserving existing IEA finance workflows and strict domain authorization.

Highlights:

- domain-separated General Barn and IEA finance authorization;
- customer/family receivable accounts with charges, credits, payments, allocations, balances, billing relationships, and correction/unallocation workflows;
- configurable CSV/XLSX bank imports with staged rows, candidate matching, explicit reconciliation confirmation, ignore decisions, and explicit review completion;
- QuickBooks-friendly configurable CSV/XLSX accounting exports that do not mutate the ArenaLine ledger;
- business reporting for posted income, expenses, net activity, monthly cash-flow trends, account/category summaries, receivable balances, aging detail, season/date/as-of filtering, and CSV export;
- point-in-time receivable semantics that exclude future charges from as-of reporting;
- primary navigation integration with General/IEA capability boundaries and compatibility access to legacy IEA finance surfaces;
- release hardening around cross-account/domain authorization, receivable corrections, allocation lifecycle, and finance presentation.

Migrations: v3.5 finance migrations begin at `0090` and include the finance foundation, reconciliation/import, and accounting-export persistence through `0099_v350_accounting_export_profiles.py`.

Validation to date: **154/154 focused v3.5 regression tests passing** on staging. Final system/migration checks and the complete portal regression suite are release-promotion gates.

Detailed notes: `docs/releases/v3.5.0.md`.

## v3.4.0 — Lesson Program

Released September 2026.

v3.4.0 introduces ArenaLine's generic Lesson Program architecture for recurring barn instruction and IEA Team Lessons while preserving legacy lesson history and compatibility.

Highlights:

- generic Lesson Program → Lesson Series → Lesson Occurrence hierarchy with canonical Person/Horse attendance and assignments;
- recurring schedule generation, one-off lessons, immutable recurrence identity, safe future refresh, cancellation and rescheduling;
- Barn enrollment/capacity and IEA season/team roster preparation kept as separate domain concepts;
- Barn instructor eligibility restricted to active Trainer / Assistant Trainer roles and IEA Team Lessons to Coaches;
- durable occurrence snapshots so later series edits do not rewrite history;
- lesson-day attendance, horse assignment, bulk operations, completion safeguards, and role-aware management;
- single-rider move/make-up workflow with capacity/history validation, audit provenance, and rider self-service limited to the rider's own participation;
- legacy IEA lesson conversion with deterministic, idempotent provenance while original records remain unchanged;
- unified operational calendar projection for Barn/IEA lessons alongside shows, horse care, organization events, and other supported operational sources;
- separated Barn Lesson Programs, Team Lessons, and My Lessons navigation with responsive ArenaLine presentation;
- Finance navigation compatibility retained ahead of the dedicated v3.5 Barn Finance & Business Operations release.

Migrations: `0079_v340_lesson_program_foundation.py` through `0089_v340_lesson_model_state_closeout.py`.

Validation: clean Django system checks, `makemigrations --check --dry-run` reporting **No changes detected**, and **949/949 portal tests passing** on the final v3.4.0 staging baseline.

Detailed notes: `docs/releases/v3.4.0.md`.

## v3.3.0 — Equine Care & Horse Management

Released September 2026.

v3.3.0 expands ArenaLine's Horse Registry into an operational equine-care, document, compliance, and delegated horse-management system while preserving established IEA Horse, Show, Hoofprint, Horse of the Day, and historical workflows.

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
- explicit **Manage Horses** capability for organization-wide horse management without requiring Coach/Admin access;
- current Boarder / Responsible Party relationships can manage only their related horse records, with effective-date-aware access;
- horse relationship/season/show authority remains separately restricted so delegated horse managers cannot broaden their own access;
- privacy-safe manager/non-manager presentation and preserved historical Horse of the Day behavior.

Migrations: `0072_v330_horse_identifiers.py` through `0078_v330_organization_capabilities.py`.

Validation: clean Django system/migration checks, **128/128 horse/show/Hoofprint regression tests passing**, **56/56 affected horse/People authorization regressions passing**, and **747/747 portal tests passing** on the final v3.3.0 staging baseline.

Detailed notes: `docs/releases/v3.3.0.md`.

## v3.2.3 — People & Operations Polish

Released September 2026.

v3.2.3 closes the 3.2.x People, Relationships & Barn Operations release family. The family was developed through the v3.2.0 Unified People & Organization Foundation, v3.2.1 Barn Participation & Horse Relationships, v3.2.2 ArenaLine Station, and v3.2.3 People & Operations Polish milestones.

Highlights:

- canonical organization-scoped `Person` identity with optional login access and compatibility bridges for existing Rider/Guardian/User structures;
- multiple simultaneous, effective-date-aware barn roles and parent/guardian relationships;
- generic organization Groups/Programs and generalized Committees/Committee Memberships;
- People↔Horse ownership, boarding, lease, trainer, responsible-party, and caretaker relationships;
- Person-first login/family management workflows;
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
- historical compatibility for unlinked legacy classes;
- architecture/presentation cleanup ahead of public work.

Validation: **425 portal tests passing** before production promotion.

Detailed notes: `docs/releases/v3.0.0.md`.

## Earlier releases

The 2.x release history, including Horse/Hoofprint, Show Host Operations, finance, communications, and the ArenaLine platform transition, is retained in `RELEASE_NOTES.md` and related documents under `docs/`.

## Changelog rule

Every stable production release must add or update its entry here before promotion to `main`. The changelog should remain concise and user-facing; detailed engineering notes belong in the version-specific release document.