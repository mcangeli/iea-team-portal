# IEA Team Portal v1.7.3

Private team operations portal for an IEA team.

## v1.7.0 — Season History & Reporting

This release turns the operational data accumulated by the portal into a long-term team history.

### Season archive and review
- Browse current and historical seasons.
- Season Review combines rider participation, points, wins, lesson attendance, volunteer hours, qualification progress, and team qualification totals.
- Administrators can close a season into the archive and reopen it when corrections are required.
- Closed seasons are removed from active-season workflows and key operational edits are blocked until reopened.

### Rider development history
- Private multi-season history for the rider, linked family, Coaches, and Administrators.
- Season-by-season points, shows, wins, lesson attendance, volunteer hours, awards, and coach development notes.
- Development notes can remain staff-only or be explicitly shared with the rider/family.

### Awards and recognition
- Record configurable rider awards for a season.
- Awards support descriptions, presentation dates, draft/unpublished status, and historical display.
- Published awards feed the team record book.

### Printable rider summaries
- Print-friendly end-of-season rider summary.
- Includes performance, qualification, volunteer/lesson participation, published awards, and family-visible coach comments.
- Clearly labeled as a team-maintained record, not an official IEA record.

### Team record book
- Historical top rider season point totals and wins from portal data.
- Published awards archive.
- Explicitly presented as team records rather than official IEA records.

### Points Secretary
The Secretary / Points Secretary committee assignment now has meaningful delegated competition access:
- detailed standings review,
- standings CSV export,
- result entry/correction,
- qualification override/review.
The role does not receive general Coach/Admin access, contact-directory access, lesson administration, user management, or scoring-rule administration.

### Privacy
v1.6 privacy rules remain intact. Rider development history and printable summaries are private to Coaches/Admins and the rider/linked family. A Points Secretary can work with competition records but does not gain unrelated rider personal information.

## Upgrade

```bash
cd /opt/iea-team-portal/iea-team-portal-v1.7.0
chmod +x portalctl
./portalctl upgrade
```

Then verify:

```bash
./portalctl exec web python manage.py showmigrations portal
./portalctl exec web python manage.py check
```

Expected latest portal migration:

```text
[X] 0011_v170_season_history_reporting
```


## v1.7.1 — Existing Guardian Linking

- Rider pages now provide separate actions to create a new parent/guardian or link an existing GuardianContact.
- One GuardianContact can be linked to multiple riders without duplicate contact records or logins.
- Linking an existing guardian preserves the existing account relationship and syncs the legacy rider guardian user link when applicable.
- Managers can unlink a guardian from one rider without deleting the GuardianContact or its login.
- No database migration is required.


## v1.7.2 — Validation & Calendar Editing

- Duplicate records now fail gracefully instead of surfacing raw database 500 errors in common create workflows.
- Season Classes, Lesson Groups, Committee assignments, Show Leads, and Rider Awards have contextual duplicate validation before save.
- A database integrity fallback catches remaining create-time constraint collisions and returns a friendly message.
- Existing manually-created calendar events can now be edited.
- Calendar entries synced from Shows or Lessons provide direct links to edit their source record so synchronization remains authoritative.
- No database migration is required.


## v1.7.3 — Rider Season Enrollment

- Rider creation now optionally enrolls the new rider into a season in the same workflow.
- The active season is preselected when available.
- Managers can choose Futures/Upper team level, season classes, and season-specific notes while creating the rider.
- Class choices dynamically follow the selected season and team level.
- The Rider remains a permanent person record; future years continue to use separate SeasonMembership records instead of recreating the rider.
- Existing Rider edit remains focused on permanent rider information; yearly assignments continue to use the Season Assignment workflow.
- No database migration is required.


## v1.8.0 — Team Hub, Coordination & Action Items

### Team Hub / My Team
- New **My Team** page brings together the riders a user is responsible for, current-season enrollment, upcoming team events, RSVP requests, and open action items.
- Parents linked to multiple riders see those riders together in one family-centric view.
- Administrators and Coaches can use the same view across the team.

### General event RSVP
- Calendar events can optionally request an RSVP.
- Families/riders can answer **Going**, **Maybe**, or **Not going** per rider.
- RSVP deadlines can be configured.
- Calendar entries surface RSVP status and link back to My Team.
- Shows keep their existing Show Availability workflow for compatibility.

### Reusable Action Items
- New ActionItem model for team tasks, supplies, paperwork, volunteer needs, and other assignments.
- Items can be linked to a Calendar Event, Show, Rider, Season, assignee, or left team-wide.
- Team-wide items can be made claimable by families.
- Assigned/claimed users and managers can mark items complete.
- Family-visible controls protect operational-only tasks.

### Dashboard / Coach attention
- Dashboard now includes My Week attention items.
- Pending general-event RSVPs appear alongside assigned/claimed tasks.
- Managers get a consolidated Needs Attention area for overdue tasks, unclaimed tasks, pending volunteer approvals, and missing show availability.

### Reminders
- `./portalctl reminders` now also checks upcoming event RSVPs and assigned rider/user Action Items due in the next seven days.
- Existing daily notification de-duplication remains in place.

### Rider login creation fix
- Creating a login from a Rider is now wrapped in a database transaction.
- UserProfile creation is hardened with `get_or_create`.
- Rider/guardian OneToOne link conflicts are rechecked under a row lock.
- Link/constraint failures return a friendly form error instead of a raw 500.

### Database
v1.8.0 adds migration:
`0012_v180_team_hub.py`

### Roadmap
- **v1.9.0+** — Finance & Fundraising.
- **v2.x.x** — Horse & Hoofprint Management, with the exact feature set to be designed closer to that release.


## v1.8.1 — Startup Hotfix

- Fixes the v1.8.0 Docker build failure caused by `EventRSVP` and `ActionItem` referencing `CalendarEvent` before that model class is defined.
- Uses Django string-based forward model references so app loading and `collectstatic` can complete normally.
- Includes all v1.8.0 Team Hub features and the Rider login creation 500 fix.
- No new migration beyond the existing v1.8.0 `0012_v180_team_hub.py`; systems that failed while building v1.8.0 can upgrade directly to v1.8.1.


## v1.8.2 — User Onboarding Sequence Repair

- Repairs PostgreSQL ID sequences used by `auth_user` and `portal_userprofile`.
- This addresses onboarding failures where a new login collides with an existing primary key even though the username/rider link is valid.
- Improves login-creation error messages by identifying the actual database constraint when possible.
- Keeps the v1.8.1 startup hotfix and all v1.8.0 Team Hub features.
- Adds migration `0013_v182_user_sequence_repair.py`.


## v1.8.3 — User Creation Double-Submit Hotfix

- Prevents the User Onboarding form from being submitted twice by disabling the Save button after the first submit and showing `Creating user…`.
- Adds server-side reconciliation for duplicate/raced onboarding requests.
- If one request successfully creates and links the user while a second request collides on the same username, the second request now recognizes that the intended Rider/Guardian is already linked to that exact account and treats the operation as successful.
- Keeps the v1.8.2 sequence repair and all v1.8.x Team Hub functionality.
- No new database migration is required.


## v1.8.4 — Media Upload Storage Hotfix

- Fixes Rider photo uploads returning HTTP 500.
- Restores Django's required `default` storage backend using `django.core.files.storage.FileSystemStorage`.
- Retains WhiteNoise's compressed manifest backend for static files.
- Fix also applies to other uploaded media such as authorized team logos.
- Existing Docker `media_data` volume remains unchanged and continues to persist `/app/media`.
- No database migration is required.


## v1.8.5 — Historical Rider Results

Managers can now add prior-season results directly from **Rider → Development History** without rebuilding the normal show-entry workflow.

### Historical result entry
- Choose any season in which the Rider has a SeasonMembership, including an archived/closed season.
- Enter the historical show name, date, venue, and optional source note.
- Enter up to 12 class results from the same show in one batch.
- Each row supports season class, placing, points, horse name, and notes.
- If explicit points are supplied, they are preserved as manual historical points.
- If points are omitted but a placing is supplied, the season's configured scoring table calculates the points.
- Historical entries are always individual entries and never become points-rider/team scoring entries.

### Reporting
Historical results use the existing Show/ShowClass/ShowEntry/ShowResult data model, so they automatically contribute to:
- Rider season points and wins.
- Individual qualification calculations.
- Season review.
- Rider Development History.
- Team Record Book individual records.

Rider Development History now also lists the underlying class results and labels shows created by this workflow as **Historical entry**.

### Database
Adds migration `0014_v185_historical_results.py`, which adds `Show.is_historical_import`.

All v1.8.3 user-creation protections and v1.8.4 media-storage fixes are included.


## v1.8.6 — Class-Specific Rider Points & H8/H14 Team Scoring

### Rider qualification points
Rider season points are now presented and reported on a **class-by-class basis**. Points from different classes are never combined into a single qualification total.

Updated areas:
- Rider Development History
- Season Review rider snapshot
- Printable Rider season summary
- Team Record Book

The Record Book now ranks **Rider + Class + Season** point totals rather than combining all of a rider's classes.

The existing qualification engine already calculated qualification by SeasonClass; v1.8.6 aligns the surrounding summaries and reports with that same rule.

### Team scoring
Hunt Seat **H8** and **H14** Walk/Trot classes are excluded from team point totals.
- Existing entries accidentally marked as points riders in H8/H14 are ignored by team-scoring calculations.
- The point-rider action now refuses to designate an H8/H14 entry as a team points rider.

Class detection supports `ShowClass.class_number` values `H8`/`H14` and labels beginning with `H8` or `H14`.

### Database
No new migration is required for v1.8.6. It includes all migrations through `0014_v185_historical_results.py`.


## v1.8.7 — Historical Season Page 500 Fix

Fixes 500 errors on historical/season pages caused by stale Django reverse-relation lookups using `season_memberships` instead of the current `Rider.memberships` relation.

Corrected affected lookups in:
- Season Review
- Team Record Book
- Announcement audience filtering
- Show entry rider filtering

Also adds defensive Rider History handling so an empty summary never indexes into an empty result set.

Pages with little or no historical data now render their normal empty states instead of failing.
No new database migration is required.


## v1.8.8 — Record Book & Season Review UI Refinement

Presentation-only refinement to bring Record Book and historical Season Review pages in line with the Standings experience.

### Season Review
- Uses the same page-intro, section-heading, stat-card, status-pill, progress-bar, and entry-table patterns as Standings.
- Team qualification is presented first as summary cards.
- Individual qualification uses the same rider/class progress table as Standings.
- Season snapshot follows with compact class-specific point totals and participation details.
- Empty seasons render clean table/empty states.

### Record Book
- Uses the same editorial page-intro and competition section hierarchy.
- Historical Rider/Class/Season records are displayed in the standard entry table.
- Ranking, points, and award presentation are cleaner and easier to scan.
- Awards use card styling consistent with other portal summary surfaces.

No data model or migration changes.


## v1.8.9 — Post-Season Individual & Team Competition Tracks

Adds first-class support for Region Finals, Zone Finals and National Finals.

### Competition level
Shows can now be marked as:
- Regular season
- Region Finals
- Zone Finals
- National Finals

Existing shows migrate as Regular season.

### Finals entries
At a finals show, rider entries use one of two explicit tracks:
- Individual
- Team

A rider may have both an Individual and Team entry in the same show/class. Each entry has its own ShowResult, allowing separate horse, placing, points and notes.

Regular-season entries retain the existing Individual / Team / Individual + Team and point-rider workflow.

### Scoring separation
Regular-season qualification totals now explicitly include only:
- Regular-season shows
- Regular-season entries

Region/Zone/National results do not add back into the rider's regular-season class qualification points.

Regular-season team qualification totals likewise exclude finals shows.

At a finals show, Team-track points are summarized separately by Futures and Upper School team. H8 and H14 are excluded from team scoring and cannot be entered on the Team finals track.

### Reporting
- Show Detail identifies the finals level and displays Individual/Team track labels.
- Season Review includes a separate Post-Season Finals Results table.
- Rider History labels finals level and track.
- Printable Rider Season Summary includes post-season results separately.

### Migration
Adds `0015_v189_postseason_competition_tracks.py`.


## v1.8.10 — Historical Finals Results

Historical result entry now uses the same competition structure as live competition records.

### Historical show type
When adding historical results, managers choose:
- Regular Season
- Region Finals
- Zone Finals
- National Finals

### Finals tracks
For Region, Zone, and National historical results, each result row includes:
- Individual
- Team

The same rider can therefore have both an Individual and Team historical result in the same class/show, with separate placing, points, horse, and notes.

Regular Season historical entries continue to use the regular track and contribute to regular-season class qualification totals. Region/Zone/National historical results stay on their finals tracks and remain separate from regular-season qualification totals.

Zone Finals and National Finals use exactly the same entry/result structure as Region Finals; only the competition-level label differs.

No new migration is required beyond v1.8.9 migration `0015_v189_postseason_competition_tracks.py`.


## v1.8.11 — Welcome Dashboard & Theme Refinement

### Dashboard welcome
The dashboard hero now greets the signed-in user by first name, falling back to username when no first name is available.

### Visual refinement
The light theme has been polished with:
- softer layered page backgrounds
- more refined card and table surfaces
- improved spacing and hierarchy
- cleaner hero treatment
- more consistent shadows and navigation presentation

The goal is a more polished equestrian-club/editorial feel without making the portal visually heavy.

### Dark theme
Authenticated users now have a Theme control in the top navigation.
- Switches between Light and Dark.
- The choice is stored in the browser with localStorage and persists across visits on that browser.
- Dark styling covers navigation, cards, forms, tables, show pages, status pills, menus, and supporting surfaces.
- No account/profile migration is required.

No database migration.


## v1.8.12 — Dark Theme Surface Polish
Dark-mode coverage now explicitly includes rider cards and other secondary card surfaces, with darker avatar placeholders, chips, progress panels, and improved hover contrast. No database migration.


## v1.8.13 — Equestrian Club Visual Refinement

A broader visual pass moves the portal toward a premium barn-club / equestrian-program identity while retaining straightforward operational workflows.

### Clubhouse dashboard
- Larger editorial team hero.
- Personalized welcome retained.
- Floating season-at-a-glance strip for next show, active roster, qualified rider/class combinations, and items needing the signed-in user's attention.
- Reduced generic-dashboard feel through stronger typography and editorial spacing.

### Rider roster
- Rider cards now use a program-book treatment.
- Rider photos receive wider editorial crops.
- Cards surface team level, grade, and current season classes when available.
- Photo-less riders use a restrained monogram treatment.
- Light and dark versions are both supported.

### Record Book
- Stronger honors-board presentation.
- Region, Zone, and National finalist counts appear as historical headline statistics.
- Refined typography and award accents make the page feel more like a team honors archive than a database report.

### Design language
- Warm brass/tan is used sparingly as a secondary accent.
- IEA blue-green remains the primary portal identity.
- Serif display typography is reserved for names, honors, and major headings; operational controls remain clean sans-serif.
- Dark mode remains deep charcoal/blue-green rather than pure black.

No database migration.


## v1.8.14 — Regional Advancement Tracking

Post-season presentation now distinguishes regular-season qualification from finals advancement.

### Region Finals → Zone Finals
- Individual-track Region Finals results automatically show `Zone qualifier` when the rider places 1st or 2nd in the class.
- Other completed individual results show that the rider did not advance.
- Team advancement is based on overall team placing rather than the sum of this portal's rider points.
- Shows now store separate overall team placing for Futures and Upper School.
- A 1st-place overall team finish at Region Finals is shown as `Advances to Zone Finals`.

### Historical finals
Historical show entry now also accepts Futures and Upper School overall team placing for finals, allowing older Region Finals team advancement to be represented correctly.

### National advancement
Zone-to-National advancement is intentionally not hard-coded in this release because IEA National allotments can vary by zone and season.

### Dashboard fix
Corrected the v1.8.13 dashboard qualifier count to use the existing regular-season qualification rows correctly.

Migration: `0016_v1814_regional_advancement.py`.


## v1.9.0 — Team Finance Foundation

v1.9.0 introduces the first finance layer for the team portal.

### Permissions
Finance is intentionally separate from general Coach permissions.
- Administrator: finance access
- Active-season Treasurer committee assignment: finance access
- Superuser: finance access
- Coach alone: no finance access
- Parent/Rider: no team-ledger access

### Financial accounts
Create team accounts such as checking, savings, cash, or payment/clearing accounts. Each account stores an opening balance and the portal calculates its current ledger balance from income and expenses. Accounts can be deactivated without removing historical transactions.

### Categories
Finance categories classify transactions as Income, Expense, or Income/Expense. v1.9.0 seeds a practical starter category set for existing teams during migration:
Membership dues, Fundraising, Show fees, Coaching, Facility / barn, Horse rental, Apparel, Travel, Awards / banquet, Administrative, and Miscellaneous.

### Transaction ledger
Transactions record:
- season
- date
- income/expense
- account
- category
- amount
- payee
- description
- optional show
- optional rider
- optional receipt
- payment/check/reference value
- notes
- created/updated user and timestamps

Amounts are stored as positive values; transaction direction is represented explicitly as Income or Expense.

Receipt uploads are limited in the form to PDF/JPG/JPEG/PNG and 10 MB. Receipt links in the Finance UI use a permission-checked download route. Replacing, clearing, or deleting a receipt cleans up the prior stored file.

### Season budgets
Budgets are entered by Category + Income/Expense direction so dual-purpose categories remain unambiguous. The Finance dashboard compares actual ledger activity against each budget line.

### Dashboard and reporting
The Finance dashboard shows:
- active-season income
- active-season expenses
- active-season net
- total budget entered
- calculated financial-account balances
- budget vs actual
- recent transactions

The full transaction ledger can be exported as CSV.

### Scope intentionally deferred
Family balances, individual fee invoices, payments due, fundraising campaigns, reimbursements, and richer reports remain future v1.9.x work.

### Migration
`0017_v190_finance_foundation.py`
