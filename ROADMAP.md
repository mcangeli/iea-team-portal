# ArenaLine Roadmap

ArenaLine is a private, self-hosted equestrian operations platform with discipline-specific competition modules. The IEA Team Portal has evolved into ArenaLine while preserving the IEA workflows already built for riders, families, horses, shows, operations, finance, communications, history, hosted-show management, and now deliberately published public/spectator experiences.

This roadmap is a living product-direction document. Completed releases are summarized here; implementation detail belongs in release/supporting documents under `docs/`.

## Current progression

- **2.1.x — Horse, Hoofprint, Course & Show Operations:** released.
- **2.5.x — Show Host Operations:** released.
- **2.9.x — ArenaLine Platform Foundation:** released.
- **3.0.0 — IEA Class Catalog & Competition Foundation:** released.
- **3.1.0 — Public / Live Spectator Experience:** release candidate / promotion-ready pending final staging gate.
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

Major outcomes:

- versioned official H1–H14, W1–W14, and D1–D14 catalog data;
- season-level rulebook/discipline configuration;
- linked official `SeasonClass` records while preserving historical/manual exceptions;
- show-only warm-up classes and Hunt Seat VOC support;
- catalog-driven individual/team scoring eligibility;
- compatibility fallback for historical unlinked rows;
- architecture and presentation cleanup before external/public work.

The v3.0.0 staging baseline completed with **425 portal tests passing** before production promotion.

Supporting docs:

- `docs/V3_0_0_IEA_CLASS_CATALOG_FOUNDATION.md`
- `docs/V3_0_CLEANUP_CLOSEOUT.md`
- `docs/releases/v3.0.0.md`

---

# 3.1.0 — Public / Live Spectator Experience

**Status: release candidate.**

v3.1.0 establishes ArenaLine's first anonymous/public experience while preserving a strict explicit-publication boundary.

## Publication foundation

Delivered:

- `PublicSiteProfile` for organization-level public identity;
- `PublicShowPublication` for explicit show publication and field-category controls;
- separate anonymous/public routes and payload services;
- allow-listed public fields;
- reversible publication without deleting internal history;
- tenant isolation and regression coverage.

Private by default remains:

- rider/guardian contact information;
- private rider notes;
- horse medical/Coggins/internal notes;
- Finance data;
- committee/admin records;
- points-rider strategy;
- internal entry/show notes and private files.

## Public identity and shows

Delivered:

- public organization/program landing page;
- selected logo/website publication;
- published show landing pages;
- published show date/location/basic information;
- active/upcoming/past grouping;
- published class order, ring, and current estimated time;
- mobile spectator presentation.

## Live Show Day

Delivered:

- show-level lifecycle controls for Ready/Upcoming, In progress, Paused, Complete;
- per-class lifecycle for Not started, In progress, Paused, Complete;
- full show order independent of team entries;
- structured ring assignments;
- simultaneous active classes across different rings;
- one active/paused class per ring;
- responsive Show Day command-center presentation for desktop/tablet/mobile.

## Public results

Delivered:

- explicit class-level publish/unpublish after completion;
- public result payload restricted to approved placing information;
- 1st–10th ordinal presentation;
- traditional equestrian ribbon colors;
- no public points-rider/internal strategy leakage.

## Spectator updates

Delivered:

- separate public-safe spectator notice stream;
- whole-show and ring-specific announcements;
- break/schedule notices;
- +15 / +30 / +45 / +60 ring-delay controls;
- clear/dismiss workflow;
- publication only when live status is explicitly enabled.

## Stable live link

Delivered:

- `/public/<program>/live/` stable season-long link;
- redirect to the active published show when one exists;
- safe fallback to public schedule when nothing is live;
- suitable for reusable QR codes/printed materials.

## Presentation polish

Delivered:

- ArenaLine public spectator styling using navy/hunter/gold/cream visual language;
- live-ring cards and clearer current/paused states;
- polished result cards/badges;
- ring shown separately beneath schedule time;
- tablet/mobile Show Day conversion from wide table to stacked class cards;
- retained dark-mode support on authenticated Show Day.

## v3.1 migrations

- `0057_v310_public_site_foundation.py`
- `0058_v310_public_show_schedule.py`
- `0059_v310_public_show_results.py`
- `0060_v310_public_live_status.py`
- `0061_v310_show_live_lifecycle.py`
- `0062_v310_show_class_live_state.py`
- `0063_v310_class_result_publication.py`
- `0064_v310_show_class_ring_assignment.py`
- `0065_v310_spectator_show_updates.py`

Supporting release document:

- `docs/releases/v3.1.0.md`

---

# Next 3.x direction

Near-term candidates after v3.1.0 release include:

- richer public historical archives;
- multi-ring enhancements beyond the current single active class per ring model;
- optional “advance to next class” operational shortcuts;
- additional live/show-day reporting and analytics;
- broader program-management capabilities outside IEA competition;
- additional competition modules with their own official rule/class catalogs;
- temporary show-specific horse pools from host-provided lists without polluting the permanent Horse Registry;
- richer cross-season rider/horse/show analytics;
- additional organization types beyond IEA programs.

These are directional items, not commitments to a specific release number until the next release line is opened.

---

# Release/process guardrails

- IEA-specific rules/terminology remain in `competition_iea`.
- Official competition reference data must come from verified official sources.
- Historical seasons preserve the applicable historical rule/class definitions.
- Platform cleanup must not trigger destructive schema changes solely for naming aesthetics.
- Security, privacy, tenant boundaries, and explicit publication remain release gates.
- Completed behavior remains regression-tested before compatibility paths are removed.
- Before promotion to `main`, follow `RELEASE_CHECKLIST.md` and update `VERSION`, README, release notes/version-specific release doc, roadmap, architecture/supporting documentation, and the stable-tag plan together.

## Maintaining this roadmap

`ROADMAP.md` is the canonical product roadmap and should travel with every release.

When direction changes:

- update this file in the active feature/release branch;
- preserve concise summaries of completed release families;
- keep detailed implementation notes under `docs/`;
- distinguish committed near-term work from directional ideas;
- update documentation before promotion to `main`, not afterward.
