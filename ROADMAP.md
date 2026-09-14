# ArenaLine Roadmap

ArenaLine is a private, self-hosted equestrian operations platform with discipline-specific competition modules. The IEA Team Portal has evolved into ArenaLine while preserving the IEA workflows already built for riders, families, horses, shows, operations, finance, communications, history, hosted-show management, and now deliberately published public/spectator experiences.

This roadmap is a living product-direction document. Completed releases are summarized here; implementation detail belongs in release/supporting documents under `docs/`.

## Current progression

- **2.1.x — Horse, Hoofprint, Course & Show Operations:** released.
- **2.5.x — Show Host Operations:** released.
- **2.9.x — ArenaLine Platform Foundation:** released.
- **3.0.0 — IEA Class Catalog & Competition Foundation:** released.
- **3.1.0 — Public / Live Spectator Experience:** released.
- **Next 3.x — Broader ArenaLine growth:** additional competition modules, broader program-management capabilities, richer public/history experiences, and future live-show enhancements.

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

### Official catalog

The initial 2026–2027 catalog includes Hunt Seat, Western, and Dressage youth classes:

- H1–H14
- W1–W14
- D1–D14

Catalog metadata includes:

- rulebook season;
- discipline;
- official class code/name;
- team level;
- ability/class family;
- individual/team scoring eligibility;
- season assignability;
- active/display order;
- verified source rule and revision date.

### Season workflow

Administrator/Coach flow:

1. Create/activate the season.
2. Configure the IEA rulebook season and participating disciplines.
3. Create/link the official season classes from the catalog.
4. Preserve manual/historical classes as deliberate exceptions.
5. Assign season classes to riders.

`SeasonClass` remains organization-specific.

### Show workflow

Normal classes flow through:

```text
IEAClassCatalogEntry
        ↓
SeasonClass
        ↓
ShowClass
        ↓
Entries/results
```

Official show-only classes may link directly from the catalog.

v3.0.0 adds official show-only warm-ups:

- H7x/H8x and H13x/H14x
- W7x/W8x and W13x/W14x
- D7x/D8x and D13x/D14x

These remain outside season assignments and never award individual/team points.

### Hunt Seat VOC

Hunt Seat Varsity Open Championship is modeled as an official show-only class.

Eligibility is derived from same-show H1/H2 participation/results. ArenaLine ranks candidates using combined H1/H2 points and H1 placing and does not invent judge-card tie-break data it does not store.

VOC remains regular-season-only and non-scoring.

### Catalog-driven scoring

Scoring policy now resolves from effective catalog metadata rather than Hunt Seat-only hard-coded exclusions.

Standard no-team-points classes:

- H8 / H14
- W8 / W14
- D8 / D14

Catalog metadata also governs show-only warm-ups, VOC, and future official classes.

A historical H8/H14 heuristic remains only as a compatibility fallback for unlinked legacy records.

### Presentation/architecture cleanup

- Removed the legacy Calendar inline-style block.
- Consolidated Calendar presentation into the shared Operations stylesheet.
- Preserved Month/Agenda/filter/mobile behavior.
- Refreshed `ARCHITECTURE.md` for the ArenaLine v3 platform/IEA boundary.
- Added v3 cleanup closeout documentation.

### Validation

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

# Longer-term ArenaLine direction

Longer-term ideas not yet assigned to a specific release include:

- additional competition modules with their own official rule/class catalogs;
- broader barn/program management outside competition operations;
- temporary show-specific horse pools from host-provided lists without polluting the permanent Horse Registry;
- richer cross-season rider/horse/show analytics;
- controlled public historical archives;
- additional organization types beyond IEA programs;
- richer multi-ring spectator boards, announcements, and live-event tooling.

---

# Release/process guardrails

- IEA-specific rules/terminology remain in `competition_iea`.
- Official competition reference data must come from verified official sources.
- Historical seasons preserve the applicable historical rule/class definitions.
- Platform cleanup must not trigger destructive schema changes solely for naming aesthetics.
- Security, privacy, tenant boundaries, and explicit publication remain release gates.
- Completed behavior remains regression-tested before compatibility paths are removed.
- **Before promotion to `main`, follow `RELEASE_CHECKLIST.md` and update `VERSION`, `README.md`, release notes, roadmap, architecture/supporting documentation, and the stable-tag plan together.**

---

## Maintaining this roadmap

`ROADMAP.md` is the canonical product roadmap and should travel with every release.

When direction changes:

- update this file in the active feature/release branch;
- preserve concise summaries of completed release families;
- keep detailed implementation notes under `docs/`;
- distinguish committed near-term work from directional ideas;
- update documentation **before** promotion to `main`, not afterward.
