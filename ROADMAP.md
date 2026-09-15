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
- **3.2.3 — People & Operations Polish:** active development milestone and current focus.
- **3.3.0 — Equine Care & Horse Management:** committed next major release.
- **3.4.0 — Lesson Program:** committed next major release.
- **3.5.0 — Barn Finance & Business Operations:** committed next major release.

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

Platform modules:

- `core`
- `people`
- `horses`
- `operations`
- `finance`
- `communications`

IEA competition remains isolated in `competition_iea`.

---

# 3.0.x — IEA Competition Foundation

## 3.0.0 — IEA Rulebook & Class Catalog Foundation

**Status: released.**

v3.0.0 replaced repeated manual definition of official IEA classes with versioned official rulebook reference data and made catalog metadata authoritative for class/scoring behavior where supported.

Major outcomes:

- official 2026–2027 Hunt Seat, Western, and Dressage class catalog;
- catalog-linked `SeasonClass` and `ShowClass` workflows;
- official show-only warm-ups and Hunt Seat VOC;
- catalog-driven individual/team scoring eligibility;
- historical compatibility for unlinked legacy classes;
- architecture/presentation cleanup needed before public work.

The v3.0.0 staging baseline completed with **425 portal tests passing** before production promotion.

Supporting docs:

- `docs/V3_0_0_IEA_CLASS_CATALOG_FOUNDATION.md`
- `docs/V3_0_CLEANUP_CLOSEOUT.md`
- `docs/releases/v3.0.0.md`

---

# 3.1.0 — Public / Live Spectator Experience

**Status: released.**

v3.1.0 adds ArenaLine's first deliberate anonymous/public experience while preserving a strict private-by-default boundary.

Major outcomes:

- explicit public-site and public-show publication controls;
- separate allow-listed anonymous payload services;
- public organization/program landing pages;
- published upcoming/active/past show lists;
- public show detail pages and schedules;
- live show lifecycle and class lifecycle;
- structured ring assignments and multi-ring live operation;
- class-level public result publication;
- spectator-safe notices and ring delays;
- stable `/public/<program>/live/` links suitable for reusable QR codes;
- polished public spectator presentation;
- responsive Show Day command-center layout for desktop, tablet, and mobile;
- squad-scoped Show Day behavior preserved for Futures/Upper Team Parents while ordinary family views remain read-only.

Release validation completed with **486 portal tests passing** on the final release candidate, plus clean Django system and migration-drift checks.

Supporting doc:

- `docs/releases/v3.1.0.md`

---

# 3.2.x — People, Relationships & Barn Operations

**Status: active release family; v3.2.3 is the current development milestone.**

v3.2 moves ArenaLine from separate rider/parent/user assumptions toward a unified human and organizational model suitable for a full barn program.

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

The Person foundation established the rule that login credentials are access, while Person is the durable human identity used by ArenaLine.

## v3.2.1 — Barn Participation & Horse Relationships

**Status: completed development milestone.**

Major outcomes:

- broader organization participation roles including rider, boarder, trainer/assistant trainer, barn manager/staff, working student, and board member concepts;
- Person participation independent of age or login identity;
- horse ownership/responsible-party relationships;
- boarding and lease relationship foundations, including shared/partial participation patterns;
- date-aware participation and relationship history;
- People/horse relationship architecture designed to feed v3.3 Equine Care without moving care-detail concerns prematurely into v3.2.

## v3.2.2 — ArenaLine Station

**Status: completed development milestone.**

Major outcomes:

- tablet-first shared barn Station experience;
- trusted station/device model and limited station identity/PIN separate from full portal passwords;
- today's lesson-oriented station workflow;
- rider attendance/check-in actions;
- staff and working-student clock-in/clock-out workflow;
- touch-first presentation with restricted administrative exposure;
- audit history for station actions;
- shared-device authentication boundary that does not grant unrestricted portal access.

## v3.2.3 — People & Operations Polish

**Status: active development milestone.**

Current focus is consolidating the 3.2 People architecture across the existing portal and hardening the operational experience before the release family closes.

Completed/current work includes:

- canonical People presentation for rider/family relationships and current IEA participation;
- People-first private rider/family authorization with compatibility fallbacks;
- explicit family-finance authorization boundaries separate from ordinary operational rider visibility;
- People-aware communications recipient discovery;
- canonical Person identity synchronization for login accounts;
- Person-first login-access creation and management surfaces;
- regression coverage for canonical family, authorization, communications, and account identity behavior.

Remaining closeout areas include:

- finish removal/wrapping of remaining legacy identity and communications entry points where canonical People services now exist;
- work-time review/approval and attendance/work-history polish where needed;
- working-student hour tracking review;
- group/program/committee dashboard polish;
- role/permission default review and authorization audit;
- reporting/export review;
- public rider/person-card refinement;
- privacy, mobile/tablet, accessibility, and audit hardening;
- full portal regression testing and release documentation before closing the 3.2.x family.

## Migration strategy

v3.2 remains compatibility-first. Existing `Rider`, Guardian/Parent, `UserProfile`, `SeasonMembership`, committee, competition, finance, and historical records are not destructively rewritten merely to achieve cleaner naming.

Person/relationship/group abstractions are layered alongside existing structures, linked conservatively, with stable URLs and historical references preserved. Legacy identity paths are removed only after callers are known and covered by regression tests.

---

# 3.3.0 — Equine Care & Horse Management

**Status: committed next major release after v3.2.3 closeout.**

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

v3.4 expands ArenaLine's existing lesson functionality into a broader lesson-program operating system using the richer Person and Horse foundations.

Planned areas include:

- lesson enrollment and recurring schedules;
- lesson groups/programs and trainer assignments;
- rider and horse assignment;
- lesson capacity and waitlists;
- cancellations and makeups;
- attendance/check-in integration with ArenaLine Station;
- lesson notes and trainer notes;
- rider progression/history;
- horse workload/use visibility;
- packages/credits or billing hooks needed by v3.5 without duplicating Finance logic.

---

# 3.5.0 — Barn Finance & Business Operations

**Status: committed future release.**

v3.5 reviews and expands the existing Finance domain for general barn management while retaining IEA/team finance functionality.

Potential operational finance areas:

- boarding charges;
- full/half/shared lease charges;
- lesson packages and private/group lesson charges;
- training fees;
- horse-care pass-through expenses;
- show/team/program fees;
- memberships and service/working-student credits;
- staff/work-hour inputs where appropriate;
- family/customer account balances;
- payments, credits, reimbursements, fundraising, and reporting;
- operational invoice/account statements and exports.

ArenaLine should remain focused on operational finance/account management and integrations/exports rather than trying to replace a complete external accounting/general-ledger system without a deliberate future decision.

---

# Longer-term ArenaLine direction

Longer-term ideas not yet assigned to a specific release include:

- additional competition modules with their own official rule/class catalogs;
- richer cross-season rider/horse/show analytics;
- controlled public historical archives;
- additional organization types beyond IEA programs;
- richer multi-ring spectator boards, announcements, and live-event tooling;
- deeper scheduling/resource management across staff, riders, horses, rings, and facilities.

---

# Product, presentation, and documentation guardrails

`docs/PRODUCT_AND_UI_GUIDE.md` is a standing development guide and applies to every release.

Core rules:

- every new/materially redesigned page follows established ArenaLine branding, components, typography, spacing, light/dark behavior, and responsive conventions;
- desktop, tablet, and mobile presentation are considered during implementation, not after feature completion;
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
- `RELEASE_NOTES.md` is the canonical top-level changelog/release history;
- `docs/releases/<version>.md` holds detailed release-specific notes;
- `ARCHITECTURE.md` documents technical/domain boundaries and compatibility strategy;
- documentation changes are made as product decisions/features change, not deferred until after release.

**Before promotion to `main`, follow `RELEASE_CHECKLIST.md` and update `VERSION`, README, changelog/release notes, roadmap, architecture/supporting documentation, and the stable-tag plan together.**

---

## Maintaining this roadmap

When direction changes:

- update this file in the active feature/release branch;
- preserve concise summaries of completed release families;
- keep detailed implementation notes under `docs/`;
- distinguish committed near-term work from directional ideas;
- update documentation **before** promotion to `main`, not afterward.
