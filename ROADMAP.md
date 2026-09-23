# ArenaLine Roadmap

ArenaLine is a private, self-hosted equestrian operations platform with discipline-specific competition modules. The IEA Team Portal has evolved into ArenaLine while preserving the IEA workflows already built for riders, families, horses, shows, operations, finance, communications, history, hosted-show management, and deliberately published public/spectator experiences.

This roadmap is the canonical product-direction document. Completed releases are summarized here; implementation detail belongs in release/supporting documents under `docs/`.

## Current progression

- **2.1.x — Horse, Hoofprint, Course & Show Operations:** released.
- **2.5.x — Show Host Operations:** released.
- **2.9.x — ArenaLine Platform Foundation:** released.
- **3.0.0 — IEA Class Catalog & Competition Foundation:** released.
- **3.1.0 — Public / Live Spectator Experience:** released.
- **3.2.x — People, Relationships & Barn Operations:** released with v3.2.3.
- **3.3.0 — Equine Care & Horse Management:** released.
- **3.4.0 — Lesson Program:** released.
- **3.5.0 — Barn Finance & Business Operations:** released.
- **3.6.0 — Dashboard Refresh & Account Security:** released.
- **3.7.0 — Barn Finance Completion:** released.
- **3.8.0 — Barn, Facility & Resource Operations:** released.
- **3.9.x — Operations, Communications & Boarding Completion:** tentative.
- **3.10.x — Analytics & History:** tentative.
- **3.11.x — 3.x Platform Stabilization & Completion:** tentative.

---

# 3.8.0 — Barn, Facility & Resource Operations

**Status: released.**

v3.8.0 establishes the canonical physical-operations foundation for ArenaLine while preserving domain ownership: Facilities own physical-place identity, Horses own horse records, Lessons own lesson facts, Inventory owns stock facts, Calendar remains a projection, and Finance remains authoritative for financial transactions.

Major outcomes:

- organization-scoped Facilities with nested Facility Spaces;
- capability-driven arenas/resources, stalls, pastures/paddocks, storage, and other physical spaces;
- independent effective-dated stall housing and pasture/turnout assignments with preserved history;
- reservable Facility Spaces and lesson-resource scheduling/collision controls;
- additive canonical location links while retaining established free-text location/venue compatibility;
- inventory categories/items, stock by storage location, receive/use/adjust/transfer movements, low-stock visibility, and transaction history;
- integrated Facilities and Inventory navigation/presentation with hierarchical resource navigation;
- migrations 0111–0114 and regression coverage across facility, housing, turnout, scheduling, and inventory boundaries.

Final validation: **102/102 focused v3.8 tests** and **1452/1452 complete ArenaLine tests passing**, with clean migration-state and Django system checks.

Detailed release notes: `docs/releases/v3.8.0.md`.

---

# 3.6.0 — Dashboard Refresh & Account Security

**Status: released.**

v3.6.0 separates ArenaLine's general barn/program home from its IEA team experience and adds account-level email verification and optional MFA.

Major outcomes:

- permission-aware general Barn Dashboard for everyday operational awareness;
- My Team as the dedicated IEA team hub, with authorized role workspaces beneath it;
- parent-first team navigation and strict separation of IEA announcements/competition context from the general dashboard;
- independently configurable Barn, Team, Futures, and Upper hero presentation;
- verified self-service email changes with current-password confirmation and signed verification links;
- optional TOTP MFA with authenticator QR/manual enrollment and single-use recovery codes;
- local Postfix as ArenaLine's default mail-delivery target.

The previously planned non-dashboard v3.6 scope remains deferred intact to v3.7.x.

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

**Status: released with v3.2.3.**

v3.2 moved ArenaLine from separate rider/parent/user assumptions toward a unified human and organizational model suitable for a full barn program.

## Core identity principle

**An account is a login; a Person is the human. A Person may have zero, one, or many simultaneous roles, relationships, group memberships, and committee responsibilities.**

Roles, relationships, permissions, and public identity remain separate concepts.

Major outcomes across v3.2.0–v3.2.3:

- canonical `Person` identity with optional login account and compatibility bridges for Rider/Guardian/User structures;
- multiple simultaneous effective-date-aware organization roles and family relationships;
- organization Groups/Programs and generalized Committees;
- People↔Horse ownership, boarding, lease, trainer, responsible-party, and caretaker relationships;
- Person-first login/family/account workflows and privacy-aware public profile publication;
- ArenaLine Station shared-device authentication, Person PINs, work clock-in/out, manager review/approval, summaries, export, and audit history;
- People & Operations presentation, accessibility, privacy, and regression hardening.

Final validation: clean Django system checks and **643/643 portal tests passing** on staging.

Detailed release notes: `docs/releases/v3.2.3.md`.

---

# 3.3.0 — Equine Care & Horse Management

**Status: released.**

v3.3 expands the competition/Hoofprint-oriented Horse Registry into broader equine-care, document, compliance, delegated-management, and show-readiness functionality while preserving existing competition and historical workflows.

Major outcomes:

- durable horse identifiers and expanded veterinarian/farrier/dentist/emergency People↔Horse relationships;
- historical care records with provider, performed date, next-due date, notes, and year-organized completed-care history;
- scheduling intelligence for overdue, due-soon, and current care;
- generic horse documents with effective/expiration dates and optional care-record linkage;
- configurable organization compliance requirements for Coggins and selected document types;
- show-date-aware compliance and Hoofprint/Show Readiness enforcement;
- protected organization-scoped horse document/Coggins downloads;
- explicit Manage Horses capability and scoped Boarder / Responsible Party management;
- privacy-safe presentation with preserved Horse of the Day, Hoofprint, show-assignment, and historical compatibility.

Final validation: clean Django system/migration checks and **747/747 portal tests passing** on staging.

Detailed release notes: `docs/releases/v3.3.0.md`.

---

# 3.4.0 — Lesson Program

**Status: release-complete.**

v3.4 introduces a generic lesson-program architecture for both Barn instruction and IEA Team Lessons without baking IEA behavior into the generic lesson core.

Major outcomes:

- `LessonProgram → LessonSeries → LessonOccurrence` hierarchy with enrollment, attendance, and Person/Horse assignments;
- recurring scheduling, one-off lessons, immutable recurrence identity, safe future refresh, cancellation and rescheduling;
- Barn enrollment/capacity and IEA season/team roster specialization;
- Trainer / Assistant Trainer instructor boundary for Barn lessons and Coach boundary for IEA Team Lessons;
- durable occurrence snapshots and idempotent roster/instructor preparation;
- lesson-day attendance, horse assignment, bulk operations, and completion safeguards;
- single-rider move/make-up workflow with capacity/history validation, audit provenance, and rider self-service;
- deterministic/idempotent legacy IEA conversion with durable provenance while legacy records remain unchanged;
- unified operational calendar projection with domain-owned navigation;
- role-aware Barn Lesson Programs, Team Lessons, and My Lessons presentation;
- compatibility and migration-state hardening through migration 0089.

Final validation: clean Django system checks, **No changes detected** from the migration-state gate, and **949/949 portal tests passing** on staging.

Detailed release notes: `docs/releases/v3.4.0.md`.

---

# 3.5.x — Barn Finance & Business Operations

**Status: released with v3.5.0.**

ArenaLine Finance should handle operational accounting/account management for an equestrian organization without trying to become a complete external accounting/general-ledger package.

Committed scope includes:

- customer/family accounts, charges, credits, payments, allocations, balances, statements and invoices;
- lesson billing for private/group lessons, packages, cancellations and make-ups using v3.4 operational facts rather than duplicating lesson logic;
- recurring boarding charges and horse lease-related account activity;
- training fees and horse-care pass-through expenses tied to canonical Horse/Equine Care records;
- show, team, membership and program-specific fees while keeping IEA specialization outside the generic finance core;
- working-student/service credits, reimbursements and operational adjustments;
- business reporting, revenue/activity views, balances, statements and exports;
- fundraising as part of the broader operational-finance picture where it fits existing ArenaLine workflows.

The preferred generic financial architecture is:

```text
Account
  → Charge / Credit
  → Payment
  → Allocation
  → Balance / Statement
```

Boarding, lessons, horse care, shows and IEA workflows should produce financial activity through explicit boundaries rather than owning parallel ledgers.

Implemented v3.5 outcomes include domain-separated finance authorization, generic receivables and correction workflows, bank import/reconciliation, accounting export profiles, and business reporting. The release keeps ArenaLine's operational ledger authoritative and leaves full external general-ledger/accounting ownership outside ArenaLine.

---

# 3.6.x — Dashboard Rework

**Status: released with v3.6.0.**

v3.6 is reserved for a dedicated dashboard and information-architecture rework after People, Horses, Lessons, Calendar and Finance have mature operational data.

The release should rethink dashboards around role-aware actionable information rather than simply adding more cards. Planned design areas include useful metrics, upcoming work/events, attention queues, cross-domain operational signals, stronger hierarchy, responsive presentation, and the premium ArenaLine visual system. Dashboard authorization must continue to follow underlying domain permissions rather than exposing data merely because it is useful as a metric.

---

# 3.7.0 — Barn Finance Completion

**Status: released.**

v3.7.0 completed ArenaLine's generic Barn Finance architecture with Accounts Payable, completed Receivables, generic budgeting, unified operational reporting, transaction traceability, historical as-of reporting, and compatibility bridges for established IEA finance workflows while preserving General Barn / IEA domain separation.

Detailed release notes: `docs/releases/v3.7.0.md`.

---

# Tentative remainder of the 3.x series

The following sequence is intentionally tentative. It records the agreed product direction while allowing the detailed architecture of each release to be locked only after an inventory of the released baseline.

## 3.8.x — Barn, Facility & Resource Operations

**Status: tentatively committed; architecture inventory next.**

Purpose: establish ArenaLine's missing physical barn-operations layer without duplicating the ownership of Lessons, Horses, Shows, People, Calendar, Station, or Finance.

Tentative sequence:

- **3.8.0 — Facility & Resource Foundation:** generic facilities/locations and typed operational resources, including barns/buildings, arenas/rings, stalls, pastures/paddocks, storage/feed/tack areas, and reusable assignment/reservation boundaries.
- **3.8.1 — Stall & Horse Housing:** effective-date-aware horse/stall assignments, occupancy, availability, status, and housing history.
- **3.8.2 — Pasture & Turnout Management:** pasture/paddock assignments, horse groups, capacity, rotation/rest periods, inspections, fencing/water/maintenance notes, and turnout history.
- **3.8.3 — Arena & Resource Scheduling:** arena/ring reservations and cross-domain conflict detection for people, horses, facilities, lessons, shows, schooling, maintenance, and other operational activity.
- **3.8.4 — Inventory & Supplies:** inventory catalog, categories, units of measure, storage locations, stock movements, consumption, transfers, waste/adjustments, reorder thresholds, and low-stock attention states for supplies such as feed, hay, bedding, fly spray, supplements, and barn consumables.
- **3.8.5 — Purchasing & Deliveries:** suppliers, orders/deliveries, receiving and delivery history, inventory receipts, and an explicit integration boundary to v3.7 Accounts Payable rather than a parallel accounting ledger.
- **3.8.6 — Barn Operations Integration & Polish:** Dashboard/Calendar/Station integration, mobile barn workflows, attention queues, reporting, authorization/privacy review, compatibility, and regression hardening.

Architectural principles:

- physical resources are canonical records rather than free-text fields where durable identity/history matters;
- assignments and reservations preserve history rather than storing only current state;
- operational domains continue to own their facts, while scheduling consumes them through explicit boundaries;
- inventory uses durable transactions/movements rather than mutable quantity-only records;
- Inventory/Purchasing may create or link Finance activity, but Finance remains authoritative for AP/financial transactions;
- selected fast barn actions may be exposed through ArenaLine Station without making Station the domain owner.

Before migrations are written, inventory existing Calendar, Lessons, Horses, Shows, People/Station, Finance, location/facility, and storage concepts and lock the canonical v3.8 model/regression boundaries.

## 3.9.x — Operations, Communications & Boarding Completion

**Status: tentative.**

Bring ArenaLine's cross-domain operational layer up to the maturity of People, Horses, Lessons, Finance, and Facilities. Candidate scope includes richer task/work assignment, recurring operational work, staff/team coordination, notification preferences/delivery, resource-aware calendars and attention queues, and a cohesive boarding/program-management lifecycle connecting Horse, Person, services, recurring operations, facilities, and Finance.

Detailed scope will be locked only after the v3.8 physical-operations architecture is released.

## 3.10.x — Analytics & History

**Status: tentative.**

Build generic cross-season/cross-year operational reporting on ArenaLine's durable records: participation, lessons, horse utilization, facility/resource utilization, work/service, inventory, finance, and organization trends. Strengthen historical exports and controlled historical publication where appropriate. IEA competition analytics remain a specialization of the generic analytics/reporting foundation.

## 3.11.x — 3.x Platform Stabilization & Completion

**Status: tentative final 3.x release family.**

Close the 3.x architecture deliberately: compatibility-path review and safe retirement, permission/privacy audit, mobile/accessibility and presentation sweep, query/performance review, documentation normalization, backup/restore/rollback validation, deployment hardening, and a full platform-boundary audit. The goal is a mature generic ArenaLine platform baseline before expansion into major new competition modules or organization types.

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