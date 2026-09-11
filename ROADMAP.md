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

**Status: release stabilization / live validation.** No additional major feature scope should be added unless live testing reveals a release-blocking workflow gap.

Completed scope includes:

- Course Operations workspace for Coach/Admin users.
- Course status integrated into dashboards, Show Detail, and Show Day.
- Assigned Show Leads can maintain course media without receiving private coaching access.
- Protected, authenticated course-document delivery rather than raw media URLs.
- Phone-friendly course image/PDF upload with file-type and size validation.
- Horse season-eligibility enforcement with explicit Coach/Admin override and recorded reason.
- Show Horse List documents stored per show as versioned revisions.
- Phone-first Show Horse List upload for photos of printed lists, while retaining PDF/file support.
- Authenticated access to uploaded horse-list documents rather than exposing raw media URLs.
- Separate internal operational notes and **Coach Notes for Riders & Parents**.
- Family-visible horse-list information available through Hoofprint and My Show Day.
- Live-vs-finalized Hoofprint change detection.
- Hoofprint completeness/readiness warnings.
- Horse of the Day history protection when show-horse assignments change.
- Branded 403, 404, and 500 error experiences.
- Focused v2.1.4 permission, privacy, file-upload, Show Day, Hoofprint, and historical-data regression tests.
- Dedicated `RELEASE_CHECKLIST_v2.1.4.md` for final live validation.

Remaining release work is validation/polish only:

- Complete Administrator/Coach/Show Lead/Rider/Parent live-role validation.
- Verify mobile, light-mode, dark-mode, and ringside presentation.
- Confirm migrations `0040` through `0042` on the live upgrade path.
- Resolve only defects found during release validation.
- Promote 2.1.4 after the release checklist passes.

The narrow `ShowPlanningItem.owner_id` compatibility extension remains intentionally in 2.1.4 because the current behavior is live-tested and regression-covered. Its removal belongs in the planned 2.9.x architectural cleanup, where the oversized legacy Show Day module can be refactored safely rather than changed late in this release.

### 2.1.5 — Post-Show Horse History

Focus: preserve what actually happened after the show.

Planned direction:

- Final horse contribution/history records.
- Reconcile leased-horse planning placeholders with the actual horses used.
- Preserve show-specific horse participation and operational history.
- Make historical horse information useful when planning later shows.
- Review how contributed horses, Horse of the Day, Hoofprints, and show assignments become a coherent historical record.

The 2.1.x progression is intentionally:

> **2.1.3:** Are we ready for the show?  
> **2.1.4:** Do we have everything needed to run the show?  
> **2.1.5:** What actually happened, and what should we preserve historically?

---

## 2.5.x — Show Host Operations

Focus: build significantly more around the portal's existing show-host functionality.

The goal is a **Host Show Workspace** that distinguishes between attending somebody else's show and operating a show our team is hosting.

Areas to explore include:

- Host contacts, responsibilities, and key show personnel.
- Venue, ring, warm-up, schooling, parking, arrival, check-in, and hospitality information.
- Prize lists, schedules, course documents, and host-provided horse lists.
- Host preparation and readiness checklists.
- Show-day instructions and announcements.
- Document collection and distribution.
- Course and ring operations.
- Volunteer and staffing coordination where appropriate.
- Clear host-specific dashboards and navigation rather than overloading the attending-team workflow.

Exact 2.5.x point releases will be designed after the 2.1.x show-operations work is stable and the existing host workflow has been reviewed in detail.

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
