# ArenaLine Roadmap

ArenaLine is a private, self-hosted equestrian operations platform with discipline-specific competition modules. The IEA Team Portal has evolved into ArenaLine while preserving the IEA workflows already built for riders, families, horses, shows, operations, finance, communications, history, hosted-show management, and deliberately published public/spectator experiences.

This roadmap is the canonical product-direction document. Completed releases are summarized here; implementation detail belongs in release/supporting documents under `docs/`.

## Current progression

- **2.1.x — Horse, Hoofprint, Course & Show Operations:** released.
- **2.5.x — Show Host Operations:** released.
- **2.9.x — ArenaLine Platform Foundation:** released.
- **3.0.0 — IEA Class Catalog & Competition Foundation:** released.
- **3.1.0 — Public / Live Spectator Experience:** released.
- **3.2.x — People, Relationships & Barn Operations:** active next release family.
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

**Status: active next release family.**

v3.2 moves ArenaLine from separate rider/parent/user assumptions toward a unified human and organizational model suitable for a full barn program.

## Core identity principle

**An account is a login; a Person is the human. A Person may have zero, one, or many simultaneous roles, relationships, group memberships, and committee responsibilities.**

Roles, relationships, permissions, and public identity must remain separate concepts.

Examples ArenaLine must support cleanly:

- a youth rider linked to one or more parents/guardians;
- an adult rider who is also a parent/guardian of one or more youth riders;
- a boarder who may or may not ride or take lessons;
- a full, half, shared, or partial leaser;
- a trainer or assistant trainer;
- a barn manager;
- barn staff or working student;
- a board member who may have no riding/boarding relationship;
- one person holding several of these roles at the same time.

## v3.2.0 — Unified People & Organization Foundation

Planned foundation:

- canonical `Person` identity layer with optional login account;
- compatibility relationships from existing Rider, Guardian/Parent, User/Profile, and committee data;
- multiple concurrent organization role assignments;
- explicit parent/guardian/dependent person-to-person relationships;
- person profile expansion including preferred/display name, date of birth, derived age, school, graduation/class year where relevant, profile photo, bio, riding/program interests, and social/profile links;
- privacy/visibility controls for profile fields;
- dedicated public-profile publication payloads rather than direct exposure of internal Person data;
- conservative youth/minor publication defaults;
- organization Groups/Programs as reusable scopes for IEA, lessons, boarding, shows, staff, and future program types;
- generalized Committees and Committee Memberships;
- committees optionally scoped to an organization Group/Program (for example IEA, SHOW, Lesson Program, or another barn subgroup);
- committee positions such as Chair, Co-chair, Secretary, Treasurer, Member, or Liaison;
- preserve assignment-specific concepts such as Show Lead where the responsibility belongs to a specific event rather than a committee identity;
- permissions remain independent from organizational labels/roles.

Examples of committee structure:

```text
Organization
├── General committees
│   ├── Governance
│   ├── Finance
│   ├── Communications
│   └── Events
├── IEA Program
│   ├── Futures Parent Committee
│   ├── Upper Parent Committee
│   └── Competition / Points support
└── Show Program
    ├── Show Committee
    ├── Hospitality
    └── Volunteers
```

Public rider/person cards are a target outcome of this foundation. They may eventually showcase selected photo, display name, biography, riding discipline/program, school or graduation year when explicitly approved, accomplishments/results, and approved social links. Exact birthdate and other sensitive personal information remain private by default.

## v3.2.1 — Barn Participation & Horse Relationships

Planned work:

- Boarder participation;
- Rider participation independent of age;
- Trainer / Assistant Trainer roles;
- Barn Manager;
- Barn Staff;
- Working Student;
- Board Member;
- horse ownership/responsible-party relationships;
- boarding relationships;
- full/half/shared/partial lease relationships;
- date-aware participation/relationship history.

Horse-care detail remains primarily a v3.3 responsibility; v3.2 establishes the people/horse relationship foundation it needs.

## v3.2.2 — ArenaLine Station

Create a simple tablet-first station mode for shared barn devices.

Initial station workflows:

- trusted station/device registration;
- limited station identity/PIN separate from full account passwords;
- today's lesson list;
- rider lesson check-in/check-out/attendance actions;
- staff and working-student clock-in/clock-out;
- touch-first layout with minimal administrative navigation;
- audit history for station actions.

Station authentication must not turn a shared tablet into unrestricted portal access.

## v3.2.3 — People & Operations Polish

Likely closeout work:

- work-time review/approval;
- attendance/work history;
- working-student hour tracking;
- group/program/committee dashboards;
- role/permission default review;
- reporting/export;
- public rider-card refinement;
- privacy, mobile/tablet, accessibility, and audit hardening.

## Migration strategy

v3.2 must be compatibility-first. Existing `Rider`, Guardian/Parent, `UserProfile`, `SeasonMembership`, committee, competition, finance, and historical records must not be destructively rewritten merely to achieve cleaner naming.

Introduce the Person/relationship/group abstractions alongside existing structures, migrate/link conservatively, preserve stable URLs and historical references, and remove legacy identity paths only after callers are known and covered by regression tests.

---

# 3.3.0 — Equine Care & Horse Management

**Status: committed future release.**

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
