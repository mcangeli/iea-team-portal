# ArenaLine Roadmap

ArenaLine is a private, self-hosted equestrian operations platform with discipline-specific competition modules. The IEA Team Portal has evolved into ArenaLine while preserving the IEA workflows already built for riders, families, horses, shows, operations, finance, communications, history, and hosted-show management.

This is a living roadmap. It describes current product direction rather than a fixed contract, and should be updated whenever development priorities materially change.

## Product direction

The current progression is:

- **2.1.x — Horse, Hoofprint, Course & Show Operations:** establish strong show preparation, horse management, course operations, and historical preservation.
- **2.5.x — Show Host Operations:** expand hosted-show functionality into a complete operational workspace.
- **2.9.x — ArenaLine foundation:** complete the product transition, platform/module boundaries, shared UI, security audit, deployment hardening, and release cleanup.
- **3.0.x — Competition foundation & architecture cleanup:** begin the next major line with official IEA class/rulebook reference data, remaining architectural housekeeping, and legacy presentation cleanup.
- **Later 3.x — External/public experiences and broader platform growth:** add explicitly published public experiences only after the 3.0 competition foundation is stable, while continuing to prepare ArenaLine for additional equestrian disciplines and organization types.

---

## 2.1.x — Horse, Hoofprint, Course & Show Operations

**Status: released.**

The 2.1 line established the Horse & Hoofprint system and expanded show operations through course management and post-show history.

Major outcomes include:

- Horse registry and season eligibility.
- Show Horse Lists and Hoofprint workflows.
- Course Operations and protected show/course documents.
- Horse of the Day history protection.
- Post-show horse-history snapshots and immutable finalization.
- Horse Legacy statistics in Record Book and Season Review.
- Historical preservation of horse usage and contribution.

The 2.1 progression remains:

> **2.1.3:** Are we ready for the show?  
> **2.1.4:** Do we have everything needed to run the show?  
> **2.1.5:** What actually happened, and what should we preserve historically?

---

## 2.5.x — Show Host Operations

### 2.5.0 — Host Show Operations

**Status: released.**

v2.5.0 turned a show marked **Hosting & attending** into a dedicated host-operations workspace while reusing ArenaLine's existing Show Planning, Courses, Schedule, Show Day, Horse/Hoofprint, Volunteer, and Finance systems.

Major outcomes include:

- Host Shows index, Host Show Workspace, and Show Manager Dashboard.
- Show-scoped Show Manager assignments separate from Show Lead.
- Host personnel roster and operational host plan.
- Readiness tracking and Show-Day Command Center.
- Host duty assignments, shifts, handoff, and completion tracking.
- Selective Host Family Information publication.
- Hosting budget visibility without broadening Finance permissions.
- Hosted-show lifecycle, completion, reopening, and history.
- Role, permission, lifecycle, and family-publication regression coverage.

Data migrations introduced by v2.5.0:

- `0045_v250_host_show_operations.py`
- `0046_v250_host_show_duties.py`
- `0047_v250_host_family_publication.py`

---

## 2.9.x — ArenaLine Foundation

### 2.9.0 — ArenaLine Platform Transition

**Status: released.**

v2.9.0 completed the transition from a single-purpose IEA Team Portal presentation into the ArenaLine product/platform foundation while preserving the existing IEA competition domain.

### Product and platform identity

- Product identity moved to **ArenaLine**.
- ArenaLine platform modules are now explicitly separated from the IEA competition module.
- Generic organization/platform terminology is used where appropriate while real IEA concepts remain IEA-specific.
- `Team` remains the persisted tenant model for compatibility, with organization service boundaries layered above it.
- Module availability is separated from authorization.

Current module boundaries:

- `core`
- `people`
- `horses`
- `competition_iea`
- `operations`
- `finance`
- `communications`

### Presentation and navigation

- Shared ArenaLine visual identity and component styling.
- Consolidated dashboard family.
- Unified People & Families, Horse Registry, Competition, Operations, Communications, Finance, and Administration presentation.
- Role- and permission-aware navigation.
- Light/dark presentation cleanup.
- Premium equestrian visual direction retained across the application.

### Security and data boundaries

- Organization/tenant boundary regression coverage.
- Cross-organization access checks.
- Rider/family privacy checks.
- Finance access and export restrictions.
- Delegated committee/role boundaries.
- Show/operations visibility controls.
- File and private-export access audit.

### Deployment and release operations

- Release identity now derives from a single root `VERSION` source.
- Production/staging isolation is documented and regression-tested.
- `portalctl` validates backups and performs deployment health checks.
- Post-start checks cover PostgreSQL, Django, migrations, static assets, media storage, and gateway configuration.
- Backup/restore and rollback procedures are documented.
- A staging restore drill is part of release qualification.
- v2.9.0 passed the final 359-test portal regression gate before production promotion.

### Deferred intentionally to 3.0

The following were explicitly not forced into v2.9 because they are better handled at the beginning of a major development line:

- Official IEA Rulebook/Class Catalog reference data.
- Remaining legacy template-local styling cleanup.
- Further modularization of oversized view modules where materially useful.

---

# 3.0.x — Competition Foundation & Housekeeping

The first 3.0 work should strengthen the IEA competition model and finish deferred structural cleanup **before** beginning major new public-facing or cross-discipline feature work.

The detailed kickoff review is maintained in `docs/V3_0_KICKOFF_REVIEW.md`.

## 3.0.0 — IEA Rulebook & Class Catalog Foundation

**Priority: first substantive 3.0 feature.**

ArenaLine should stop requiring organization administrators to manually define official IEA competition classes that are already governed by the IEA rulebook.

Create versioned reference/source data for official IEA competition classes for:

- Hunt Seat
- Dressage
- Western

The catalog should be versioned by IEA rulebook / competition season so historical seasons retain the definitions that were valid at that time.

Likely catalog fields include:

- discipline;
- class code / number;
- official class name;
- division / level;
- team-level or eligibility grouping;
- individual/team applicability;
- team-scoring inclusion;
- active status;
- rulebook season/version;
- display/sort order.

### Intended data flow

The planned relationship is:

`IEAClassCatalog -> SeasonClass -> Rider season assignments -> ShowClass -> Entries/results -> Qualification`

Expected administrator workflow:

1. Create or activate an IEA season.
2. Select the disciplines the organization participates in.
3. Load the applicable official IEA class catalog for that rulebook season.
4. Confirm which classes the organization participates in.
5. Generate organization-specific `SeasonClass` records.
6. Build show classes by selecting valid season classes rather than typing official classes free-form.

`SeasonClass` remains organization-specific. The official catalog is reference data owned by `competition_iea`, not ArenaLine core.

### Rule data

Where supported by the applicable official rulebook, competition rules currently embedded in application logic should be reviewed for movement into versioned competition reference data. This includes items such as team-scoring eligibility and exclusions like H8/H14.

No rule should be invented or inferred. Official source material must be verified before catalog content or historical rule behavior is migrated.

---

## 3.0.x — Legacy Presentation Cleanup

The second early 3.0 workstream is removal of presentation debt intentionally left untouched during the v2.9 stabilization release.

Initial work:

1. Inventory remaining template-local `<style>` blocks.
2. Identify rules made obsolete by the ArenaLine v2.9 shared presentation layers.
3. Move reusable rules into shared CSS modules.
4. Remove duplicate/legacy rules only after responsive and light/dark visual regression checks.
5. Preserve behavior while changing presentation structure.

The first known candidate is:

- `templates/portal/calendar_v2.html`

Calendar Month/Agenda behavior, filtering, and mobile switching must remain stable during cleanup.

---

## 3.0.x — Architecture Housekeeping

Before large new 3.x feature families, revisit deferred architecture cleanup where it provides a meaningful ownership or maintenance benefit.

Priorities include:

- Continue modularizing oversized view modules where useful.
- Keep generic platform behavior separate from discipline-specific competition behavior.
- Preserve the organization service boundary introduced in v2.9.
- Avoid unnecessary destructive schema renames merely to make internal naming more generic.
- Review temporary compatibility layers and remove them only when regression coverage proves the replacement path.

This work is housekeeping, not a license for a broad rewrite.

---

# Later 3.x — Public / External Experience

Public/external functionality remains part of ArenaLine's longer 3.x direction, but it is **not the first 3.0 milestone**.

Potential experiences include:

- public show landing pages;
- intentionally published show information;
- published results;
- appropriate team/rider results;
- mobile spectator views;
- shareable show URLs;
- public live-show views where the publication model proves reliable.

## Public-by-explicit-publication principle

**Nothing becomes public merely because it exists inside ArenaLine.**

Public visibility must always be explicit. Public fields must be allow-listed, and private rider, parent, horse, finance, contact, and operational information remains private by default. Unpublishing should remove the external view without destroying internal history.

The security and organization boundaries validated in v2.9 are prerequisites for this work.

---

# Longer-term ArenaLine Platform Direction

ArenaLine's platform architecture should allow future competition disciplines and broader equestrian-program workflows without forcing IEA-specific concepts into generic core modules.

Longer-term ideas not yet assigned to a specific release include:

- Additional competition modules with their own rule/class catalogs.
- Broader barn/program management features outside competition operations.
- Temporary show-specific horse pools built from uploaded host horse lists without polluting the permanent Horse Registry.
- Richer historical analytics and reporting across seasons, riders, horses, shows, and operations.
- Additional controlled external/public experiences.

These remain directional ideas until assigned to a release plan.

---

## Roadmap guardrails

- IEA-specific rules and terminology remain in `competition_iea`; generic ArenaLine core should not absorb them.
- Official competition reference data must come from verified official sources.
- Historical seasons must preserve the rule/class definitions applicable to those seasons.
- Platform cleanup should not trigger destructive migrations solely for naming aesthetics.
- Security, privacy, tenant boundaries, and explicit-publication behavior remain release gates.
- Completed behavior should remain covered by regression tests before structural cleanup removes compatibility paths.

---

## Maintaining this roadmap

`ROADMAP.md` is the canonical product roadmap and should travel with releases.

When development direction changes:

- update this file in the active feature/release branch;
- preserve concise summaries of completed release families;
- keep detailed implementation notes in dedicated documents under `docs/`;
- distinguish committed near-term work from longer-term ideas;
- keep `docs/V3_0_KICKOFF_REVIEW.md` aligned with the active 3.0 work until those items are completed.
