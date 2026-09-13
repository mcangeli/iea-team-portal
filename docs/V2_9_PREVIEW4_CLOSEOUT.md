# ArenaLine v2.9.0 Preview 4 — Closeout

## Status

Preview 4 is complete and staging-validated.

The final staging pass confirmed:

- all focused Preview 4 presentation and navigation tests are green;
- the full `portal` test suite is green;
- desktop and mobile navigation visually match the current ArenaLine module structure;
- light and dark presentation checks are good;
- Finance is a peer platform module rather than a child of Operations;
- shared Back/Cancel behavior works on generic and destructive forms.

## Final navigation contract

The authenticated ArenaLine shell now reflects the v2.9 module registry:

- Core — Dashboard, My Team
- People & Families — Riders, Parents & guardians where authorized
- Horses — Horse Registry
- IEA Competition — Shows, Standings, Season History, Record Book
- Operations — Calendar, Action Items, Lessons, Volunteer, Committees
- Finance — Finance Dashboard, Family Receivables, Dues Setup, Accounts & Categories, Season Budget, Reports, Fundraising, Reimbursements, when the user has Finance authority
- Communications — Notifications
- Manage — Users, Season Setup, Branding, Audit Log, and Django Admin for staff

Module availability and user authorization remain separate concepts. `portal_enabled_modules` controls which modules are available; role/committee permission helpers control whether a user can enter privileged workflows.

## Preview 4 deliverables

Preview 4 established shared ArenaLine presentation layers for:

1. global presentation contract;
2. dashboard family;
3. People / Families;
4. Horses;
5. IEA Competition;
6. Operations / Communications;
7. Finance;
8. Administration and forms;
9. final navigation, responsive, accessibility-focus, and light/dark polish.

No schema migration or business-rule rewrite was part of Preview 4.

## Deferred to ArenaLine 3.0 kickoff

The following deliberate deferrals remain recorded in `docs/V3_0_KICKOFF_REVIEW.md`:

- IEA Rulebook / Class Catalog foundation for Hunt Seat, Dressage, and Western;
- rulebook-season versioning and catalog-derived season classes;
- review of moving suitable class-specific scoring metadata such as team-point eligibility into reference data;
- removal/consolidation of remaining legacy inline presentation, beginning with the Calendar template;
- larger architecture housekeeping that should precede major 3.x feature work.

## Next phase

Preview 5 is the security and data-access audit. The audit should treat organization scoping, role authority, family/rider privacy, Finance access, delegated committee roles, show-specific delegation, exports/downloads, and mutating endpoints as security boundaries rather than presentation concerns.
