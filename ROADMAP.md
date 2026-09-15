# ArenaLine Roadmap

ArenaLine is a private, self-hosted equestrian operations platform with discipline-specific competition modules. The IEA Team Portal has evolved into ArenaLine while preserving the IEA workflows already built for riders, families, horses, shows, operations, finance, communications, history, hosted-show management, and deliberately published public/spectator experiences.

This roadmap is the canonical product-direction document. Completed releases are summarized here; implementation detail belongs in release/supporting documents under `docs/`.

## Current progression

- **2.1.x — Horse, Hoofprint, Course & Show Operations:** released.
- **2.5.x — Show Host Operations:** released.
- **2.9.x — ArenaLine Platform Foundation:** released.
- **3.0.0 — IEA Class Catalog & Competition Foundation:** released.
- **3.1.0 — Public / Live Spectator Experience:** released.
- **3.2.0 — Unified People & Organization Foundation:** completed development milestone.
- **3.2.1 — Barn Participation & Horse Relationships:** completed development milestone.
- **3.2.2 — ArenaLine Station:** completed development milestone.
- **3.2.3 — People & Operations Polish:** release-complete; closes the 3.2.x family.
- **3.3.0 — Equine Care & Horse Management:** current next major release.
- **3.4.0 — Lesson Program:** committed future release.
- **3.5.0 — Barn Finance & Business Operations:** committed future release.

---

# Released foundations

## 2.1.x — Horse, Hoofprint, Course & Show Operations

**Status: released.**

Major outcomes:

- Horse Registry and season eligibility.
- Show horse assignments and Horse Readiness.
- Hoofprint Builder/finalized snapshots.
- Show Horse Lists and Course Operations.
- Horse of the Day and protected horse history.
- Post-show horse-history snapshots.
- Horse Legacy statistics in Record Book and Season Review.

## 2.5.x — Show Host Operations

**Status: released.**

Major outcomes:

- Host Shows index and Host Show Workspace.
- Show Manager assignments separate from Show Lead.
- Host personnel, readiness, Show-Day Command Center, duties/shifts/handoff/completion.
- Selective family-visible host information.
- Hosting budget visibility without broadening Finance permissions.
- Hosted-show completion/reopening/history.

## 2.9.x — ArenaLine Platform Foundation

**Status: released.**

Major outcomes:

- ArenaLine product identity and shared presentation system.
- Explicit platform/module boundaries.
- Organization service boundary layered over persisted `Team` tenant records.
- Role/module-aware navigation.
- Security/privacy/tenant-boundary regression coverage.
- Finance/export/file/Hoofprint access review.
- Release identity from the root `VERSION` file.
- Production/staging isolation.
- `portalctl` backup, preflight, health, rollback, and stable/preview update-channel workflows.

Platform modules: `core`, `people`, `horses`, `operations`, `finance`, and `communications`. IEA competition remains isolated in `competition_iea`.

---

# 3.0.0 — IEA Competition Foundation

**Status: released.**

v3.0.0 replaced repeated manual definition of official IEA classes with versioned official rulebook reference data and made catalog metadata authoritative for class/scoring behavior where supported.

Major outcomes:

- official 2026–2027 Hunt Seat, Western, and Dressage class catalog;
- catalog-linked `SeasonClass` and `ShowClass` workflows;
- official show-only warm-ups and Hunt Seat VOC;
- catalog-driven individual/team scoring eligibility;
- historical compatibility for unlinked legacy classes;
- architecture/presentation cleanup needed before public work.

Validation: **425 portal tests passing** before production promotion.

Supporting docs: `docs/V3_0_0_IEA_CLASS_CATALOG_FOUNDATION.md`, `docs/V3_0_CLEANUP_CLOSEOUT.md`, and `docs/releases/v3.0.0.md`.

---

# 3.1.0 — Public / Live Spectator Experience

**Status: released.**

v3.1.0 added ArenaLine's first deliberate anonymous/public experience while preserving a strict private-by-default boundary.

Major outcomes:

- explicit public-site and public-show publication controls;
- separate allow-listed anonymous payload services;
- public organization/program landing pages;
- published upcoming/active/past show lists;
- public show detail pages and schedules;
- live show/class lifecycle and structured multi-ring operation;
- class-level public result publication;
- spectator-safe notices and ring delays;
- stable reusable public live links/QR destinations;
- polished responsive Show Day and spectator presentation;
- squad-scoped Futures/Upper Team Parent behavior preserved.

Validation: **486 portal tests passing** plus clean Django system/migration checks.

Supporting doc: `docs/releases/v3.1.0.md`.

---

# 3.2.x — People, Relationships & Barn Operations

**Status: release-complete with v3.2.3.**

v3.2 moved ArenaLine from separate rider/parent/user assumptions toward a unified human and organizational model suitable for a full barn program.

## Core identity principle

**An account is a login; a Person is the human. A Person may have zero, one, or many simultaneous roles, relationships, group memberships, and committee responsibilities.**

Roles, relationships, permissions, and public identity remain separate concepts.

## v3.2.0 — Unified People & Organization Foundation

**Status: completed development milestone.**

Major outcomes:

- canonical `Person` identity layer with optional login account;
- compatibility relationships from existing Rider, Guardian/Parent, User/Profile, and committee data;
- multiple concurrent organization role assignments;
- explicit parent/guardian/dependent person-to-person relationships;
- expanded Person profiles with preferred/display identity and private profile information;
- privacy/visibility boundaries for private Person information;
- organization Groups/Programs as reusable scopes;
- generalized Committees and Committee Memberships;
- permissions kept independent from organizational labels and roles;
- compatibility-first migration strategy preserving Rider, Guardian, UserProfile, SeasonMembership, finance, competition, and historical references.

## v3.2.1 — Barn Participation & Horse Relationships

**Status: completed development milestone.**

Major outcomes:

- broader organization participation roles including rider, boarder, trainer/assistant trainer, barn manager/staff, working student, and board member concepts;
- Person participation independent of age or login identity;
- horse ownership/responsible-party relationships;
- boarding and lease relationship foundations, including shared/partial participation patterns;
- date-aware participation and relationship history;
- People/horse relationship architecture designed to feed v3.3 Equine Care.

## v3.2.2 — ArenaLine Station

**Status: completed development milestone.**

Major outcomes:

- tablet-first shared barn Station experience;
- trusted station/device model and limited Station identity/PIN separate from full portal passwords;
- staff and working-student clock-in/clock-out;
- manager review/correction/approval, summaries, export, and audit history;
- touch-first presentation with restricted administrative exposure;
- shared-device authentication boundary that does not grant unrestricted portal access.

## v3.2.3 — People & Operations Polish

**Status: release-complete.**

Closeout outcomes:

- canonical People presentation for rider/family relationships and current IEA participation;
- People-first private rider/family authorization with compatibility fallbacks;
- explicit family-finance authorization boundaries separate from ordinary operational rider visibility;
- People-aware communications and canonical account identity synchronization;
- Person-first login-access creation/management and My Account surfaces;
- current-effective role, family, committee, Barn Operations, and People↔Horse relationship handling;
- work-time review/approval, work-history visibility, Working Student tracking, and Station review queues;
- group/program/committee presentation polish;
- public rider/person cards using explicit allow-listed publication fields;
- privacy, mobile/tablet, keyboard, accessibility, and audit hardening;
- full-suite regression reconciliation against the current People-first architecture and terminology.

Final validation: clean Django system checks and **643/643 portal tests passing** on staging.

Detailed release notes: `docs/releases/v3.2.3.md`.

## Migration strategy

v3.2 remains compatibility-first. Existing `Rider`, Guardian/Parent, `UserProfile`, `SeasonMembership`, committee, competition, finance, and historical records are not destructively rewritten merely to achieve cleaner naming. Person/relationship/group abstractions are layered alongside existing structures, linked conservatively, with stable URLs and historical references preserved.

---

# 3.3.0 — Equine Care & Horse Management

**Status: committed next major release and next development focus.**

v3.3 expands the current competition/Hoofprint-oriented Horse Registry into broader equine-care and barn-management functionality while preserving show/competition workflows.

Planned areas include:

- ownership, boarding, leasing, responsible-party, trainer, and care-team relationships built on v3.2 People;
- veterinarian, farrier, dentist, and other care-provider information;
- vaccinations, medications, treatments, Coggins, health records, and documents;
- feed, supplements, turnout, blanketing, shoeing, and routine care preferences;
- appointments and care reminders;
- emergency information and care notes;
- workload/use restrictions and availability;
- horse-care calendar/history;
- integration with existing Horse Readiness, Hoofprint, Show Horses, Horse of the Day, and horse-history features.

---

# 3.4.0 — Lesson Program

**Status: committed future release.**

Planned areas include lesson enrollment/recurring schedules, groups/programs and trainer assignments, rider/horse assignment, capacity/waitlists, cancellations/makeups, Station attendance integration, lesson/trainer notes, progression/history, workload visibility, and billing hooks needed by v3.5 without duplicating Finance logic.

---

# 3.5.0 — Barn Finance & Business Operations

**Status: committed future release.**

Potential operational finance areas include boarding/lease/lesson/training charges, horse-care pass-through expenses, show/team/program fees, memberships and working-student credits, staff/work-hour inputs, family/customer balances, payments/credits/reimbursements/fundraising, statements, reporting, and exports.

ArenaLine should remain focused on operational finance/account management and integrations/exports rather than trying to replace a complete external accounting/general-ledger system without a deliberate future decision.

---

# Longer-term ArenaLine direction

Longer-term ideas not yet assigned to a specific release include additional competition modules, richer cross-season analytics, controlled public historical archives, additional organization types, richer spectator/event tooling, and deeper scheduling/resource management across staff, riders, horses, rings, and facilities.

---

# Product, presentation, and documentation guardrails

`docs/PRODUCT_AND_UI_GUIDE.md` is a standing development guide and applies to every release.

Core rules:

- every new/materially redesigned page follows established ArenaLine branding, components, typography, spacing, light/dark behavior, and responsive conventions;
- desktop, tablet, and mobile presentation are considered during implementation;
- authorization/privacy is enforced server-side, not merely hidden in presentation;
- IEA-specific rules/terminology remain in `competition_iea`;
- official competition reference data comes from verified official sources;
- historical seasons preserve applicable historical rule/class definitions;
- platform cleanup does not trigger destructive schema changes solely for naming aesthetics;
- security, privacy, tenant boundaries, and explicit publication remain release gates;
- completed behavior remains regression-tested before compatibility paths are removed.

Documentation responsibilities:

- `README.md` is the practical overview/install/use/update document;
- `ROADMAP.md` is the canonical roadmap;
- `CHANGELOG.md` is the concise current release history;
- `RELEASE_NOTES.md` retains detailed historical release notes from earlier release families;
- `docs/releases/<version>.md` holds detailed current release-specific notes;
- `ARCHITECTURE.md` documents technical/domain boundaries and compatibility strategy.

**Before promotion to `main`, follow `RELEASE_CHECKLIST.md` and update `VERSION`, README, changelog/release notes, roadmap, architecture/supporting documentation, and the stable-tag plan together.**
