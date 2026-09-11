# IEA Team Portal Roadmap

This is a living roadmap for the IEA Team Portal. It should be reviewed and updated as each release family develops so the repository always communicates where the product is headed as well as what has already been built.

The roadmap describes direction rather than a fixed contract. Features may move between point releases as real-world testing identifies better workflows.

## Product direction

The portal is evolving through four broad stages:

- **2.1.x — Show operations:** make the internal team portal excellent at preparing for, running, and preserving the history of a show.
- **2.5.x — Show host operations:** expand the existing host functionality into a complete workspace for a team hosting an event.
- **2.9.x — Foundation and presentation cleanup:** simplify architecture, navigation, layouts, shared UI, deployment, and regression coverage before the next major version.
- **3.x — Public experience:** add an intentionally published external view for spectators, families, other teams, and other non-registered visitors without exposing private portal information.

---

## 2.1.x — Horse, Hoofprint, Course & Show Operations

### 2.1.4 — Course & Show Operations

**Status: released.**

Completed scope includes Course Operations, horse season-eligibility enforcement, Show Horse List revisions, Hoofprint change/completeness checks, Horse of the Day history protection, protected show/course documents, and Show Day/presentation stabilization.

The narrow `ShowPlanningItem.owner_id` compatibility extension remains intentionally in place and is deferred to the planned 2.9.x architectural cleanup.

### 2.1.5 — Post-Show Horse History

**Status: released.**

Completed scope includes:

- Show-level post-show horse history workspace.
- Generate a draft from registry and leased/show-specific horse planning records.
- Preserve horse identity, provider/ownership data, class coverage, and show-specific notes as historical snapshot data.
- Record whether each horse was actually used.
- Record whether each horse counted toward the team's contribution.
- Reconcile leased/show-specific planning placeholders to the actual Horse Registry horse used.
- Finalize and lock the post-show history record.
- Preserve finalizer identity and timestamp.
- Add Horse Legacy statistics to the Team Record Book.
- Add Horse History to Season Review.
- Include Horse of the Day totals with Full Day/Morning/Afternoon distinctions.
- Prefer finalized post-show snapshots for historical horse participation while retaining fallback to older live assignment history.
- Add focused regression coverage for draft generation, reconciliation, finalization, and permissions.

The 2.1.x progression is intentionally:

> **2.1.3:** Are we ready for the show?  
> **2.1.4:** Do we have everything needed to run the show?  
> **2.1.5:** What actually happened, and what should we preserve historically?

---

## 2.5.x — Show Host Operations

### 2.5.0 — Host Show Workspace

**Status: Preview 1 development.**

The Host Show Workspace is intentionally separate from the normal attending-team workflow and is available only to shows marked **Hosting & attending**.

Preview 1 scope:

- Dedicated Host Shows index and per-show Host Show Workspace.
- New show-scoped **Show Manager** assignment, separate from Show Lead.
- Coach/Admin users assign or remove Show Managers.
- Assigned Show Managers can maintain the Host Show operational plan and show-personnel roster for their hosted show.
- Show Leads retain their existing team/show-day responsibilities and can view Host Show Operations without receiving Show Manager administration rights.
- Host readiness summary based on critical leadership, personnel, and operating information.
- Track venue contact, arrival, rider/team check-in, trailer parking, spectator parking, warm-up/schooling, ring operations, volunteer check-in, hospitality, emergency information, prize-list link, schedule link, family-facing notes, and private host-team notes.
- Flexible Show Personnel roster supporting multiple people where appropriate.
- Initial core personnel roles:
  - Show Secretary
  - Judge
  - Steward
  - Gate
  - Show Announcer
  - EMS
  - Other
- Host Show Workspace links into existing Show Planning, Courses, Schedule, and Show Day rather than duplicating those systems.
- Host Operations entry point on hosted Show Detail pages.
- Migration `0045_v250_host_show_operations.py`.
- Focused permission/readiness tests for Coach/Admin, Show Manager, Show Lead, and unrelated team users.

Planned follow-on work in the 2.5.x family:

- Deeper host readiness/checklist workflow and deadlines.
- Host-specific volunteer/staff assignment coordination.
- Prize-list, schedule, course, horse-list, and other document collection/distribution.
- Show-day announcements and host command-center presentation.
- Ring/gate operational tools and staffing handoffs.
- Review of host finance/reporting needs without duplicating the existing Finance system.
- Mobile-first host-show presentation and role dashboards.

---

## 2.9.x — Layout, Architecture & Release Cleanup

Focus: stabilize and simplify the application before v3 rather than introducing another large feature family.

Planned work includes:

- Complete modularization of remaining oversized view modules.
- Normalize feature boundaries and URL modules.
- Move temporary/dynamic model additions into clean model declarations, including `SeasonClass.class_code` and `Season.rides_per_contributed_horse`.
- Remove temporary compatibility extensions and accumulated technical debt, including the v2.1.4 Show Planning `owner_id` compatibility property.
- Consolidate shared templates, page structures, navigation patterns, and reusable UI components.
- Consolidate and simplify CSS while preserving the premium equestrian visual direction.
- Review mobile navigation and role-specific navigation holistically.
- Improve consistency between light and dark modes.
- Fix and simplify `portalctl`, including explicit branch/ref update behavior and the current tag-fetch issue.
- Expand regression and permission testing.
- Normalize release notes, versioning, migrations, and branch/release practices.
- Review database and permission boundaries in preparation for public-facing functionality.

2.9.x should leave the application feeling intentionally designed rather than incrementally accumulated.

---

## 3.x — Public / External Portal

Focus: create a polished external experience for people who do **not** have registered portal accounts.

Potential public experiences include:

- Public show landing pages.
- Show date, venue, host, schedule, classes, and intentionally published general information.
- Published show results.
- Team and rider results where appropriate.
- Public season results or standings where appropriate.
- Mobile-first spectator/show-day presentation.
- Shareable public show URLs and potentially QR codes.
- A public-facing visual identity that complements the authenticated operations portal.

### Public-by-explicit-publication principle

**Nothing becomes public merely because it exists in the internal portal.**

Public visibility must be an explicit action/state. The design should support concepts such as:

- A show must be explicitly marked/published for public viewing.
- Results must be explicitly published before appearing externally.
- Public fields should be deliberately selected and reviewed.
- Sensitive rider, parent, horse, financial, contact, operational, and internal coaching information remains private by default.
- Unpublishing a show or result should remove it from the external experience without destroying the internal historical record.
- Public routes and serializers/views should use an explicit allow-list of public information rather than reusing unrestricted internal objects/templates.

This principle is a foundational requirement for v3, not an optional enhancement.

---

## Longer-term ideas

These are intentionally not assigned to a release yet:

- Convert an uploaded host Show Horse List into a temporary show-specific horse pool that can be matched to classes/riders without polluting the permanent team Horse Registry.
- Public live-show/spectator views if the publishing model proves reliable.
- Additional reporting and historical analytics based on the operational data accumulated throughout the 2.x line.

---

## Maintaining this roadmap

`ROADMAP.md` is a release artifact and should travel with future releases.

When development changes direction:

1. Update this file in the same feature/release branch.
2. Move completed items into the appropriate completed release description rather than simply deleting them.
3. Record newly agreed future direction under the appropriate release family.
4. Keep speculative ideas clearly separated from committed/current work.
5. Preserve the **explicit publication** requirement for all future public-facing features.

The roadmap should answer two questions at any point in development: **What are we building now?** and **Where are we going next?**
