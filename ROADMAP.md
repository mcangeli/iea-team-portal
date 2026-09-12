# IEA Team Portal Roadmap

This is a living roadmap for the IEA Team Portal. It should be reviewed and updated as each release family develops so the repository always communicates where the product is headed as well as what has already been built.

The roadmap describes direction rather than a fixed contract. Features may move between point releases as real-world testing identifies better workflows.

## Product direction

The portal is evolving through four broad stages:

- **2.1.x — Show operations:** make the internal team portal excellent at preparing for, running, and preserving the history of a show.
- **2.5.x — Show host operations:** expand host functionality into a complete workspace for a team hosting an event.
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

Completed scope includes post-show horse-history snapshots, registry/leased-horse reconciliation, historical horse usage/contribution records, immutable finalization, Horse Legacy statistics in the Team Record Book, and Season Review horse history.

The 2.1.x progression is intentionally:

> **2.1.3:** Are we ready for the show?  
> **2.1.4:** Do we have everything needed to run the show?  
> **2.1.5:** What actually happened, and what should we preserve historically?

---

## 2.5.x — Show Host Operations

### 2.5.0 — Host Show Operations

**Status: release stabilization. Feature scope complete and live-tested.**

v2.5.0 turns a show marked **Hosting & attending** into a dedicated host-operations workspace while reusing the portal's existing Show Planning, Courses, Schedule, Show Day, Horse/Hoofprint, Volunteer, and Finance systems rather than duplicating them.

Completed scope:

- Dedicated Host Shows index, Host Show Workspace, and Show Manager Dashboard.
- New show-scoped **Show Manager** assignment, separate from Show Lead.
- Coach/Admin assignment and removal of Show Managers; multiple managers are supported.
- Show Managers manage assigned active hosted shows without receiving unrelated team-management or Finance authority.
- Show Leads can review Host Workspace and Command Center information for their assigned show without inheriting Show Manager administration rights.
- Host personnel roster for Show Secretary, Judge, Steward, Gate, Show Announcer, EMS, and other operational contacts.
- Host plan for venue contact, arrival/check-in, trailer and spectator parking, warm-up/schooling, ring operations, volunteer check-in, hospitality, emergency information, show resources, family notes, and private host-team notes.
- Readiness percentage and missing-item presentation.
- Existing Finance hosting budget surfaced in Host Workspace and Show Manager Dashboard without duplicating budget/ledger models or granting transaction-level Finance access.
- **Show-Day Command Center** with readiness checkpoints/deadlines, duty assignments, shifts, check-in, on-duty, handoff, and completion states.
- Host duty assignments are operational staffing only and never create, satisfy, reduce, or alter normal `VolunteerLog` / season volunteer-hour requirements.
- Explicit **Host Family Information** publication controls. Host information remains private until selected sections are deliberately published.
- Family publication can selectively expose arrival/check-in, parking, warm-up, ring operations, hospitality, emergency information, prize-list/schedule links, and family notes.
- Internal host notes, personnel records, readiness checkpoints, duties/handoffs, Command Center data, and budget information are never included on the family page.
- Existing Show Day update audience filtering is reused for family-visible show-day updates.
- Publication can be turned off without deleting the underlying host plan.
- Show Manager dashboard is integrated into the shared role-dashboard selector.
- Mobile, light/dark, empty-state, and partial-configuration presentation polish across host workflows.
- Production 403/404/500 pages now honor the saved/system light/dark theme.
- Explicit host-show lifecycle: status, not calendar date, controls whether a show is operational or historical.
- **Complete** and **Cancelled** hosted shows move to Hosted Show History; Show Manager operational editing becomes read-only while historical review remains available.
- Coach/Admin retain correction authority on archived host shows.
- Host Workspace provides Coach/Admin **Mark Show Complete** and **Reopen Show** controls with confirmation before completion.
- Already-published family information remains available after completion until explicitly unpublished.
- Permission, lifecycle, presentation, family-publication, and role-matrix regression coverage.

Data migrations introduced by v2.5.0:

- `0045_v250_host_show_operations.py`
- `0046_v250_host_show_duties.py`
- `0047_v250_host_family_publication.py`

Release stabilization now focuses only on final documentation, migration verification, complete regression testing, and production-release review. No additional v2.5.0 feature scope should be added without reopening release planning.

---

## 2.9.x — Layout, Architecture & Release Cleanup

Focus: stabilize and simplify the application before v3 rather than introducing another large feature family.

Planned work includes:

- Complete modularization of remaining oversized view modules.
- Normalize feature boundaries and URL modules.
- Move temporary/dynamic model additions into clean model declarations, including `SeasonClass.class_code` and `Season.rides_per_contributed_horse`.
- Remove temporary compatibility extensions and accumulated technical debt, including the v2.1.4 Show Planning `owner_id` compatibility property.
- Integrate Show Manager workspace discovery directly into the dashboard architecture and remove the temporary `dashboard_workspace_extensions.py` compatibility patch.
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

Potential public experiences include public show landing pages, intentionally published show information, published results, appropriate team/rider results, mobile spectator views, and shareable show URLs.

### Public-by-explicit-publication principle

**Nothing becomes public merely because it exists in the internal portal.**

Public visibility must be an explicit action/state. A show or result must be deliberately published, public fields must be allow-listed, sensitive rider/parent/horse/financial/contact/operational information remains private by default, and unpublishing removes the external view without destroying internal history.

This principle is a foundational requirement for v3, not an optional enhancement.

---

## Longer-term ideas

These are intentionally not assigned to a release yet:

- Convert an uploaded host Show Horse List into a temporary show-specific horse pool that can be matched to classes/riders without polluting the permanent team Horse Registry.
- Public live-show/spectator views if the publishing model proves reliable.
- Additional reporting and historical analytics based on the operational data accumulated throughout the 2.x line.

---

## Maintaining this roadmap

`ROADMAP.md` is a release artifact and should travel with future releases. Update it in the same feature/release branch whenever development changes direction, preserve completed release descriptions, keep speculative ideas separate from committed work, and preserve the explicit-publication requirement for future public features.
