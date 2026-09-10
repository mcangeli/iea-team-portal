# Release Notes

Version-by-version changes for IEA Team Portal. For installation, configuration, and day-to-day usage, see `README.md`.

## v1.9.5 — Operational & Audit Polish

### Audit history
- Added an immutable-style `AuditEvent` activity log for important portal changes.
- Added **Manage → Audit log** for Admin/Coach users.
- Added a Treasurer-scoped **Finance audit log** that is limited to finance-related record types and seasons where the user has Finance access.
- Audit events are recorded for:
  - financial transaction create/edit/void/reversal;
  - show allocation add/edit/remove;
  - show budget item create/edit;
  - reimbursement draft/submit/review/payment state changes;
  - family charges, credits, payments, service agreements, and assistance workflows;
  - financial account/category and season-budget changes;
  - user account changes;
  - committee assignments;
  - show results.
- Ledger and reimbursement rows include direct History links where appropriate.

### Finance ledger usability
- Added ledger filters for:
  - search text;
  - posted / void / all history;
  - income / expense;
  - season;
  - account;
  - category;
  - show;
  - date range.
- Pagination preserves active filters.
- CSV export now preserves the active ledger filters and includes status/void audit fields.

### Reimbursement workflow
- Reimbursements now support a true **Draft → Submit → Review → Paid** workflow.
- Drafts remain private to the submitter until submitted.
- Submitters can edit drafts and either save again or submit for review.
- Treasurer review cannot access Draft records.
- Paid remains a terminal state under the existing transition rules.

### Financial safety
- Family Payments are no longer permanently deleted.
- Voiding a Family Payment:
  - retains the FamilyPayment row;
  - removes it from family balance calculations;
  - voids the linked ledger transaction instead of deleting it;
  - records who voided it, when, and why.
- Voided Family Payments cannot be edited.
- Financial-assistance reimbursement corrections now void previously-created ledger transactions rather than deleting them.

### Show Finance polish
- Added printable Show Finance summaries.
- Added Hosting vs Participation planned/actual summary cards.
- Added a warning when show allocations are included in show totals but are not assigned to a specific budget item.
- Existing itemized Show Budget and multi-show allocation behavior remains unchanged.

### Architecture
- The large `portal/views.py` refactor is intentionally **not** part of v1.9.5.
- Modularizing `views.py` is now the first planned architecture task for the v2.x line before major v2 feature work.

### Migration
- `0023_v195_operational_audit.py`
- Creates `AuditEvent`.
- Adds audit-safe void fields/status to `FamilyPayment`.

## v1.9.4.2.3 — Budget Item Label Fix

### Fixed
- Show allocation add/edit forms now display meaningful budget item labels instead of `ShowBudgetLine object (N)`.
- Budget items are shown as `Description · Category · $Planned Amount`, making similar hosted-show expenses much easier to identify during allocation.

### Database
- No migration is required.

## v1.9.4.2.2 — Itemized Hosted-Show Budgets

### Fixed
- Show budgets are no longer limited to one line per Scope + Type + Category.
- A hosted show can now contain multiple Administrative expense lines such as Insurance, Judge fee, Officials, Food, Permits, or Supplies.
- Removed the database uniqueness constraint that incorrectly treated those valid budget items as duplicates.

### Added
- Show Budget lines now include a required **Description / Budget item** field.
- Show allocations can optionally target a specific budget item.
- Plan vs Actual now calculates actuals against the selected budget item rather than repeating the category total on every same-category line.
- Multiple allocations from the same transaction to the same show/scope are supported when a payment covers more than one budget item.
- Existing budget lines receive their category name as an initial description during migration.
- Existing allocations remain valid and may be assigned to a budget item later.

### Migration
- `0022_v19422_itemized_show_budget.py`
- Removes the old show-budget uniqueness constraint.
- Removes the old one-allocation-per-transaction/show/scope constraint.
- Adds `ShowBudgetLine.description`.
- Adds optional `ShowTransactionAllocation.budget_line`.

## v1.9.4.2.1 — Show Budget Validation Fix

### Fixed
- Adding or editing a Show Budget line no longer runs an uncaught second model `full_clean()` after form validation.
- The Show is attached to the `ShowBudgetLineForm` instance before model validation.
- Duplicate Show Budget lines now return a normal form error instead of a 500 error.
- Category income/expense compatibility is validated in the form with a readable message.
- Hosting budget scope validation now stays inside the form rather than surfacing as a server error.

### Database
- No new migration is required.

## v1.9.4.2 — Multi-Show Financial Allocation

### Added
- One ledger payment or receipt can now be allocated across multiple shows.
- New `ShowTransactionAllocation` records distribute a transaction amount without creating duplicate ledger transactions.
- Each allocation records:
  - show;
  - Hosting operations vs Our team participation;
  - allocated amount;
  - optional notes.
- Allocation totals may be less than the source transaction, leaving a clearly displayed unallocated balance.
- Allocation totals can never exceed the source transaction amount.
- Hosting allocations are allowed only for shows marked **Hosting & attending**.
- Allocation management page shows Transaction Total, Allocated, and Unallocated amounts.
- Ledger rows now include **Allocate** / **Show allocations** actions.
- Show Finance now calculates income, expense, Budget vs Actual, and hosted-show P&L from allocation records.
- Hosted shows display Hosting income, Hosting expenses, Hosting surplus/loss, and Our Team Participation cost separately.
- Show-linked paid reimbursements automatically create a full allocation using the reimbursement's selected financial scope.
- Regression coverage for multi-show splitting and over-allocation prevention.

### Backward compatibility
- Existing v1.9.4.1 transactions that already have a show and Hosting/Participation scope are automatically migrated into a full-value allocation.
- Older show-linked transactions without a scope are not guessed. Show Finance flags them for explicit Treasurer allocation.

### Migration
- `0021_v1942_multi_show_allocations.py`
- Creates `ShowTransactionAllocation`.
- Adds show finance scope to reimbursement requests.
- Includes a data migration for existing classified single-show transactions.

### Accounting principle
The bank/ledger transaction remains the authoritative cash movement. Show allocations are management-reporting distributions only, so splitting a shared insurance, facility, transportation, or supply payment never duplicates the underlying expense.

## v1.9.4.1 — Project Hardening

### Fixed
- Reimbursement receipt downloads no longer fail because `Path` is now imported.
- Treasurer reimbursement visibility is season-aware; a Treasurer only receives finance access for seasons where that assignment is active.
- Hosted-show Budget vs Actual now matches real ledger activity by **Hosting operations** vs **Our team participation** scope.
- Existing show-linked transactions without a scope are preserved and surfaced as **Unclassified** for Treasurer review rather than guessed.
- Season Show Package funding now behaves like dues-covered funding for bulk per-show family charges.
- Direct web-server access to all `/media/finance/*` files is blocked; Finance receipts must use authenticated Django download views.
- Account balances and Finance reports exclude voided ledger entries.

### Added
- Show finance scope on ledger transactions.
- Non-destructive ledger transaction lifecycle: Posted / Void.
- Void audit fields: who, when, and why.
- Optional opposite-direction reversal entry when voiding.
- Ledger audit views for Posted, Voided, or All History.
- Voided transactions cannot be edited.
- Pagination for the Finance ledger and reimbursement inbox (50 rows/page).
- Formal reimbursement state transitions; Paid requests cannot be silently reopened.
- Targeted automated tests for season-specific Treasurer permissions, funding-policy routing, show-scope validation, and retained void history.

### Migration
- `0020_v1941_finance_hardening.py`
- Adds transaction scope, status, void audit metadata, and reversal linkage.

### Security
- Caddy now returns 404 for `/media/finance/*`, including legacy and new Finance receipts. Permission-checked Django receipt endpoints remain the supported access path.

## v1.9.4 — Show Finance & Funding Policies

### Added
- Distinguishes shows the team **attends** from shows it **hosts & attends**.
- Configurable season show-fee policies for Regular Season, Region Finals, Zone Finals, National Finals, and other/special events.
- Funding choices: Included in membership dues, Bill families per show, Season show package, or Manual/mixed.
- Optional default rider show fee and plain-language dues/package coverage notes.
- Show Finance workspace with ledger income, expenses, net result, family charges, outstanding family responsibility, show budget, and reimbursements.
- Show budget lines distinguish **Our team participation** from **Hosting operations**.
- Hosted-show finance guidance keeps hosting economics distinct from the team's own participation costs.
- Optional family show-charge generation from actual show participants, with duplicate protection.
- Shows covered by membership dues do not suggest family show charges and actively block bulk generation unless the funding policy is changed.
- Reimbursement workflow available to team users without granting ledger access: submit expense → Treasurer review → approved/rejected → paid.
- Marking a reimbursement Paid creates the corresponding expense transaction in the team ledger.
- Treasurer reimbursement inbox; non-finance users see only their own requests.
- Permission-checked private reimbursement receipt downloads.
- New transaction receipts are stored under the private finance receipt path.
- Show Detail displays Attending / Hosting & attending financial role and links authorized finance users to Show Finance.

### Migration
- Adds show funding-policy fields to Season.
- Adds Show financial role.
- Adds ShowBudgetLine and ReimbursementRequest.
- Updates the upload path for new FinancialTransaction receipts.
- Migration: `0019_v194_show_finance.py`.

### Design principle
Show cost and funding source are deliberately separate. A team's dues can cover show fees without generating family receivables, while another team can bill per show or use a mixed policy.

## v1.9.3 — Financial Reporting

### Added
- Financial Reports landing page with season selection.
- Budget vs Actual report with planned income/expense, actuals, percentage used/achieved, favorable/unfavorable variance, and net comparison.
- Family Receivables report with billed, credits, external assistance, payments, outstanding balance, overdue amount, due-soon amount, and status filters.
- Financial Assistance & Reimbursements report with award ceiling, allocated, submitted, approved, reimbursed, remaining eligibility, draft claims, and outstanding claims.
- Category Activity report with category/type filters and transaction drill-down.
- CSV exports for Budget vs Actual, Family Receivables, Assistance/Reimbursements, and Category Activity.
- Season switching on all Financial Report pages.
- Treasurer “Needs attention” worklist on the Finance dashboard for:
  - overdue family balances;
  - reimbursement claims not submitted;
  - submitted/approved reimbursements still outstanding;
  - riders missing a Home Barn;
  - rider barns missing a season dues rate;
  - memberships whose dues charge has not been generated.
- Print-friendly report styling.

### Notes
- No database migration is required.
- v1.9.3 uses the Finance, family receivable, dues, and assistance data introduced in v1.9.0-v1.9.2.x.

## v1.9.2.3 — Version-linked Documentation

### Improved
- The version number in the site footer is now a documentation link.
- Each release links to the GitHub repository at its matching version tag, where GitHub renders that release's README.
- The default repository is `mcangeli/iea-team-portal`.
- Added optional `PORTAL_REPOSITORY_URL` configuration so forks/installations can point the footer to another repository.
- If the application is running a development build without a release version, the link falls back to the repository root.

### Deployment note
- Publish a Git tag matching the `VERSION` value (for this release, `v1.9.2.3`) so the version-specific README link resolves.
- No database migration is required.

## v1.9.2.2 — UX Polish

### Improved
- Active navigation highlighting for Dashboard, My Team, Riders, Shows, Calendar, Competition, Team, Finance, and Manage areas.
- Parent menu headings remain visibly active while the user is on one of their child pages.
- Mobile tables use horizontal scrolling with a clear swipe cue and touch-friendly spacing.
- Long operational pages use sticky mobile action controls so common actions remain reachable without scrolling back to the top.
- Generic POST forms now warn before navigating away after unsaved changes.
- High-traffic empty states were clarified with more useful next-step guidance.
- Existing v1.9.2 contextual Back navigation and v1.9.2.1 mobile-menu behavior are preserved.

### Notes
- No database migration is required.
- This release is UX-only and keeps the v1.9.3 Finance/reporting roadmap intact.

## v1.9.2.1 — Navigation & Mobile Menu Polish

### Improved
- Opening one expanding navigation menu now closes any other open menu.
- Clicking outside the navigation closes open expanding menus.
- Escape closes the active expanding menu and returns focus to its menu heading.
- Added a compact mobile Menu button for authenticated users.
- On phones, the primary navigation is collapsed by default instead of occupying the top of every page.
- Mobile navigation is presented in a single-column, touch-friendly layout with larger tap targets.
- Competition, Team, and Manage expand inline on mobile.
- Choosing a navigation link closes the mobile menu automatically.
- Theme and Sign Out remain available inside the mobile navigation.
- The Menu icon changes to a close icon while the mobile navigation is open.

### Notes
- No database migration is required.
- This is a navigation/UX patch and preserves the planned v1.9.3 Finance/reporting release number.

## v1.9.2 — Contextual Navigation

### Added
- Consistent contextual back navigation on subordinate pages.
- Rider Profile → Back to Riders.
- Rider History → Back to Rider Profile.
- Family Account → Back to Family Receivables for Finance users, or Back to My Team for family users.
- Show Detail → Back to Shows.
- Show Planning / Availability / Show Week → Back to Show.
- Lesson Detail → Back to Lessons.
- Season Review → Back to Season History.
- Awards → Back to Season Review.
- Finance Receivables / Ledger / Accounts / Budget / Dues Setup → Back to Finance.
- Generic create/edit/delete forms receive a compact Back action using browser history, with Dashboard fallback when opened directly.

### Notes
- No database migration is required.
- This release is navigation/UX only.

## v1.9.1 — Membership Dues & Family Receivables

### Added
- Home Barn records for the team.
- `SeasonMembership.home_barn`, preserving a rider's barn historically by season.
- Home Barn selection during rider season enrollment and on the Season Membership page.
- Season-specific membership-dues rates by Home Barn.
- Individual dues-charge generation and active-season bulk dues generation.
- Family receivables dashboard with billed, credits/assistance, paid, and outstanding totals.
- Private rider/family account ledger.
- Family charges with due dates, charge type, show association, and notes.
- Family credits/adjustments.
- Conditional Service Agreement Credits with Pending, Applied, and Cancelled states and optional required hosted shows.
- External Financial Assistance Awards with configurable approved maximum, provider/program, eligibility notes, and status.
- Assistance Claims with Not Submitted, Submitted, Approved, Reimbursed, Denied, and Cancelled states.
- Tracking for requested, approved, reimbursed, and family-relief amounts on assistance claims.
- Automatic posting of received external reimbursements to the v1.9.0 team ledger only when a claim is marked Reimbursed.
- Family payments that automatically create corresponding team-ledger income transactions.
- Treasurer correction workflows for family credits and payments; editing or deleting a payment updates/removes its linked team-ledger transaction.
- Finance dashboard snapshots for outstanding family receivables and remaining active external-assistance eligibility.
- Family-account link in My Team for authorized parents/riders and Finance users.
- Django admin coverage for all new v1.9.1 finance models.

### Privacy and permissions
- Team Finance remains available to Administrators, active-season Treasurers, and superusers.
- Coach status alone does not grant Finance access.
- Parents/Riders can view only the family account for their authorized rider(s).
- Ordinary Coaches do not gain family-account access solely from their rider-management permissions.

### Accounting behavior
- Home-barn dues establish the rider's normal membership charge.
- Team credits and service agreements reduce family responsibility without pretending cash was received.
- External assistance awards are treated as reimbursable programs with an approved ceiling, not as immediate team income.
- Draft assistance claims do not reduce the family balance.
- Submitted, Approved, and Reimbursed claim allocations reduce family responsibility.
- Reimbursed claims require an account, income category, received date, and amount actually received; that cash receipt is posted to the team ledger.
- Family payments are separate from credits and post actual cash income to the team ledger.

### Migration
`0018_v191_family_finance.py`

## v1.9.0 — Team Finance Foundation

## Added
- Team financial accounts with calculated ledger balances.
- Income/expense/category transaction ledger.
- Optional show and rider transaction relationships.
- Receipt/document uploads with finance permission checks in the portal workflow.
- Season budgets with explicit Income/Expense direction.
- Budget-vs-actual dashboard.
- CSV ledger export.
- Created-by / updated-by audit fields and timestamps.
- Treasurer finance capability independent of primary portal role.
- Starter finance categories for existing teams.
- Premium light/dark Finance presentation consistent with the equestrian-club visual direction.

## Access
Administrators, active-season Treasurers, and superusers can access Finance. Coach status by itself does not grant financial access.

## Migration
`0017_v190_finance_foundation.py`

# IEA Team Portal v1.8.14 — Regional Advancement Tracking

## Added
Region Finals Individual entries placing 1st or 2nd are automatically identified as Zone qualifiers.

Futures and Upper School overall team placing can now be recorded on finals shows. A first-place overall team result at Region Finals is identified as advancing to Zone Finals.

Historical finals entry supports the same overall team placing fields.

## Corrected
Regular-season points qualification remains separate from post-season placement advancement.

The dashboard qualified-count calculation introduced in v1.8.13 has been corrected.

Zone-to-National advancement is not automatically inferred because National allotments vary by zone and season.

## Migration
`0016_v1814_regional_advancement.py`

# IEA Team Portal v1.8.13 — Equestrian Club Visual Refinement

## Refined
The portal now uses a more distinctive premium barn-club / equestrian-program visual language.

Dashboard gains a clubhouse-style hero and season-at-a-glance strip. Rider roster cards use larger editorial photography and season information. Record Book receives an honors-board treatment with Region, Zone, and National finalist counts.

Operational forms and show-day workflows remain deliberately straightforward.

Both light and dark themes receive the new treatment.

## Migration
No new migration.

# IEA Team Portal v1.8.12 — Dark Theme Surface Polish

## Fixed
Rider cards and several secondary card types now use proper dark-theme surfaces instead of retaining bright light-theme backgrounds.

Avatar placeholders, class chips, progress panels, and related card details have also been adjusted for better contrast in dark mode.

## Migration
No new migration.

# IEA Team Portal v1.8.11 — Welcome Dashboard & Dark Theme

## Added
The dashboard now displays `Welcome, <first name>` for the signed-in user, with username as a fallback.

A Light/Dark theme control has been added to the authenticated navigation. The selected theme persists in the user's browser.

## Refined
The light theme received a broader visual polish: layered neutral backgrounds, quieter card shadows, cleaner tables, improved spacing, and a more restrained equestrian-club/editorial look.

## Migration
No new migration.

# IEA Team Portal v1.8.10 — Historical Finals Results

## Added
Historical Results now asks for the competition level: Regular Season, Region Finals, Zone Finals, or National Finals.

Region, Zone, and National historical shows all use the same finals structure. Each class result can be marked Individual or Team, allowing one rider to have two separate results in the same class/show when appropriate.

The Track field appears dynamically for finals and stays hidden for Regular Season historical entries.

## Migration
No new migration. This release uses the post-season fields introduced by `0015_v189_postseason_competition_tracks.py`.

# IEA Team Portal v1.8.9 — Post-Season Competition Tracks

## Added
Region Finals, Zone Finals and National Finals are now distinct competition levels.

Finals entries have separate Individual and Team tracks. The same rider can therefore ride both tracks in the same class and receive separate results.

## Scoring safeguards
Post-season results are stored and reported independently from regular-season qualification totals. Finals points do not inflate a rider's regular-season class qualification points or regular-season team qualification total.

H8/H14 Walk/Trot remains individual-only for team scoring purposes and cannot be added as a Team-track finals entry.

## Reporting
Season Review, Rider History, printable Rider summaries, Show Detail and Show List now identify finals competition levels/tracks.

## Migration
`0015_v189_postseason_competition_tracks.py`

# IEA Team Portal v1.8.8 — Record Book & Season Review Layout

## Refined
Record Book and Season Review now visually follow the same presentation system as Standings.

Season Review now leads with team qualification cards, followed by individual class qualification progress and the rider season snapshot.

Record Book now uses the standard competition table layout for Rider/Class/Season records, with improved ranking and award cards.

This release is presentation-only and does not change scoring logic or the database schema.

## Migration
No new migration.

# IEA Team Portal v1.8.7 — Historical Season Page 500 Fix

## Fixed
Season Review and Team Record Book could return HTTP 500 because some queries still used the retired reverse relation name `season_memberships`. The current `SeasonMembership.rider` relation uses `related_name="memberships"`.

All stale references were replaced with `memberships`, including related filters used by announcements and show-entry rider selection.

Rider History also now handles an unexpectedly empty summary defensively.

## Migration
No new migration.

# IEA Team Portal v1.8.6 — Class-Specific Rider Points & H8/H14 Team Scoring

## Fixed — Rider points
Season points for an individual rider are qualification totals **per class**, not one total across all classes. The qualification calculation was already class-specific, but several history/reporting screens still displayed an all-class aggregate. Those displays have been corrected.

Rider History and printable summaries now show class point totals. Season Review shows class point totals per rider. The Record Book now ranks Rider/Class/Season records.

## Fixed — Team points
H8 and H14 Walk/Trot classes do not count toward team points. v1.8.6 excludes those classes from all team-scoring rows/totals and prevents a point-rider designation from being applied to them.

## Migration
No new migration.

# IEA Team Portal v1.8.5 — Historical Rider Results

## Added
A dedicated **Add Historical Results** workflow is now available from Rider Development History.

Administrators and Coaches can select a prior season, enter a historical show once, and record multiple class results for the rider. Archived seasons are intentionally supported.

Historical entries are stored in the portal's normal result structure so individual points, wins, qualification progress, season summaries, and record-book calculations continue to use one consistent source of truth. Historical imports are individual-only and do not designate a points rider, preventing them from changing team points-rider totals.

Rider Development History now displays individual result lines and marks imported shows as **Historical entry**.

## Migration
`0014_v185_historical_results.py`

## Included fixes
v1.8.5 includes the v1.8.3 user-creation double-submit protection and the v1.8.4 media upload/storage fix.

# IEA Team Portal v1.8.4 — Media Upload Storage Hotfix

## Fixed
Rider photo uploads could return a 500 error because `settings.STORAGES` defined only the `staticfiles` backend. In Django 5.2, uploaded model files use the `default` storage alias; without it, the first attempt to save an uploaded image can fail while ordinary non-file edits continue to work.

v1.8.4 adds the filesystem `default` storage backend while preserving WhiteNoise for static files. The existing Docker media volume at `/app/media` continues to provide persistent storage.

## Migration
No new database migration is required.

# IEA Team Portal v1.8.3 — User Creation Double-Submit Hotfix

## Fixed
Creating a Rider/Guardian login could successfully create the account but still display a database conflict error. This was consistent with two near-simultaneous onboarding submissions: the first request completed successfully while the second collided with the newly-created username/link.

v1.8.3 prevents duplicate submits in the browser and also reconciles raced requests on the server. If the same username is already linked to the intended Rider/Guardian, the request is treated as a successful create rather than an error.

## Migration
No new migration is required. v1.8.3 includes all prior migrations through `0013_v182_user_sequence_repair.py`.

# IEA Team Portal v1.8.2 — User Onboarding Sequence Repair

## Fixed
New Rider/Parent login creation could still fail with a generic database constraint message. v1.8.2 repairs PostgreSQL sequences for `auth_user` and `portal_userprofile`, which can become out of sync after historical restores or schema repair work.

The onboarding view now also maps common database constraints to specific messages and includes the unexpected constraint name when one is encountered.

## Migration
`0013_v182_user_sequence_repair.py`

# IEA Team Portal v1.8.1 — Startup Hotfix

## Fixed
v1.8.0 could fail during Docker image build while running `collectstatic` with:

`NameError: name 'CalendarEvent' is not defined`

The new EventRSVP and ActionItem models were declared before CalendarEvent in `models.py` and used direct class references. v1.8.1 changes those relationships to Django string-based forward references.

## Upgrade
No additional migration was added. v1.8.1 still includes `0012_v180_team_hub.py`, which will apply normally if the v1.8.0 build failed before migrations ran.

# IEA Team Portal v1.8.0 — Team Hub

## Major features

### My Team
A new family/team hub combines current rider enrollment, upcoming events, event RSVP requests, and action items. Parents with multiple linked riders see their family in one place.

### General calendar RSVP
Calendar events may now request rider/family responses using Going, Maybe, or Not going, with an optional deadline.

### Reusable action items
Managers can create team tasks and sign-ups associated with a rider, event, show, or season. Items may be directly assigned or opened for families to claim.

### Dashboard coordination
The dashboard now surfaces My Week and a manager Needs Attention area for RSVP gaps, overdue/unclaimed tasks, volunteer approvals, and show availability.

### Reminder expansion
The daily reminder command now includes general event RSVP reminders and due assigned action items.

## Fixed
Creating a login from a Rider has been hardened so account/profile/linking conflicts are handled transactionally and displayed as form errors rather than a 500 page.

## Migration
`0012_v180_team_hub.py`

## Roadmap
- Finance & Fundraising remains targeted for v1.9.0 or later.
- Horse & Hoofprint Management has been added to the v2.x.x roadmap.

# IEA Team Portal v1.7.3 — Rider Season Enrollment

## Added
The Add Rider workflow can now create the rider's first SeasonMembership at the same time as the permanent Rider record.

### Rider creation
- Optional season selector.
- Active season preselected when available.
- Futures / Upper School team selection.
- Season class selection.
- Season-specific notes.
- Dynamic class filtering by season and team level.

### Data model
This does not change the underlying model: a Rider is still created once, while SeasonMembership records represent that rider's participation each year.

## Database
No migration is required for v1.7.3.

# IEA Team Portal v1.7.2 — Validation & Calendar Editing

## Fixed
- Duplicate create attempts no longer produce raw 500 errors in the hardened workflows.
- Context-aware validation catches duplicates whose uniqueness includes season/show context that is assigned after normal form validation.

## Added
- Edit action for manually-created calendar events.
- Synced show calendar entries link to Edit Show.
- Synced lesson calendar entries link to Edit Lesson.
- Friendly fallback message for database constraint collisions in key create workflows.

## Database
No migration is required for v1.7.2.

# IEA Team Portal v1.7.1 — Existing Guardian Linking

## Fixed
The rider page previously allowed creating a new parent/guardian but did not expose the existing many-to-many family relationship workflow.

## Added
- **Create new parent** and **Link existing parent** are now separate actions on Rider profiles.
- The existing-parent workflow lists GuardianContact records on the same team that are not already linked to that rider.
- Relationship label and primary-contact status can be set when linking.
- Existing guardian user accounts are preserved and linked to the additional rider.
- A guardian can be unlinked from one rider without deleting the guardian contact or user account.

## Database
No migration is required for v1.7.1.

# IEA Team Portal v1.7.0 — Season History & Reporting

## Added
- Season archive and Season Review workspace.
- Administrator close/reopen season workflow.
- Rider Development History across seasons.
- Staff-only or family-visible rider development notes.
- Awards & Recognition.
- Printable end-of-season rider summaries.
- Team record book with historical season point totals, wins, and published awards.
- Delegated Points Secretary access for results, detailed standings, qualification review, and standings export.

## Privacy
Competition-reporting delegation does not expose rider contact details or unrelated private operational information. Rider history remains limited to staff and the rider/linked family.

## Database
Adds `0011_v170_season_history_reporting`:
- `Season.is_closed`
- `Season.closed_at`
- `RiderDevelopmentNote`
- `RiderAward`

## Upgrade
`./portalctl upgrade` creates the normal pre-upgrade database backup before applying the release.
