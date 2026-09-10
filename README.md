# IEA Team Portal

**Current version: v1.9.8**

IEA Team Portal is a private, self-hosted team-management application for an interscholastic equestrian program. It brings rider records, season setup, shows and results, standings and qualification tracking, lessons, calendars, volunteer activity, communications, team operations, historical records, and team finance into one portal.

The portal is intended to complement official IEA systems and records, not replace them. It is **not an official IEA website**.

For version-by-version changes, see [`RELEASE_NOTES.md`](RELEASE_NOTES.md).

## What the portal does

### Dashboard and My Team

The dashboard gives users a season-oriented view of upcoming shows and events, announcements, action items, RSVP or availability items needing attention, volunteer progress, and qualification information appropriate to their role.

**My Team** provides a more personal view of linked riders, upcoming events, RSVPs, and assigned or claimable action items.

### Riders, parents, and season enrollment

Rider records are permanent team records while `SeasonMembership` represents a rider's enrollment for a particular season. A season membership can identify the rider's Futures or Upper School team and the classes they ride that season.

The portal also maintains Guardian/Parent contacts and rider-to-guardian relationships. A user's primary portal role is independent of being a parent or guardian, so an Administrator or Coach can also be linked to their own rider without giving up staff permissions.

### Shows, entries, results, and availability

The Shows area supports:

- show schedule and details;
- show classes;
- rider entries;
- regular-season Individual/Team/Both entry types;
- point-rider designation for eligible regular-season team classes;
- rider availability responses;
- show planning and show-lead workflows;
- show-week summaries;
- result entry including place, points, horse, and notes;
- Region, Zone, and National Finals competition levels;
- separate Individual and Team finals tracks, including the same rider competing in both tracks in the same class;
- Futures and Upper School overall team placing at finals.

Regular-season qualification scoring is kept separate from postseason finals results. Region Finals Individual results can identify the top two riders in a class as Zone qualifiers, while a first-place overall team result can identify team advancement to Zones. Later postseason advancement rules can be expanded when needed.

### Standings and qualification

Standings calculate regular-season rider/class points and team points using the season's scoring configuration.

Individual qualification is tracked **by class**, not by a rider's combined points across classes. Team scoring uses designated point riders and excludes classes such as H8/H14 where team points do not apply.

Administrators/Coaches can manage point-rider strategy. Rider and Parent accounts do not see point-rider identity or other protected team strategy.

### Season history and record book

Closed seasons remain available for historical review. The portal includes:

- Season Review;
- Team Record Book;
- rider season history;
- development notes;
- awards;
- printable rider season summaries;
- historical result entry for regular season, Region Finals, Zone Finals, and National Finals.

Historical finals can record separate Individual and Team tracks as well as overall Futures and Upper School team placing.

### Calendar and event RSVP

The calendar combines shows, lessons, and manually created team events. Team events can request rider RSVPs. Synced show and lesson calendar entries are managed through their source records, while manual calendar events can be edited or deleted directly.

### Lessons and attendance

Lesson groups can organize riders by season/team level and coach. Lessons support recurring weekly creation, rider attendance, attendance status, horse name, and notes.

### Volunteer tracking

Families can submit volunteer activity for linked riders. Managers review submissions, and only approved hours count toward season requirements. Futures and Upper School can have separate volunteer-hour requirements.

### Team operations

Operational tools include:

- committees and committee assignments;
- Futures and Upper Team Parent roles;
- Treasurer;
- Secretary / Points Secretary;
- show leads;
- show-planning items;
- team action items;
- claim/complete workflows.

Capabilities are delegated by responsibility rather than making every committee role a full Administrator.

### Communications and notifications

The portal includes in-app announcements, audience targeting, notifications, email preferences, optional SMTP email delivery, show-week communication, and reminder processing.

### Team Finance

The Finance area includes:

- financial accounts such as checking, savings, cash, and payment/clearing accounts;
- configurable income/expense categories;
- transaction ledger;
- optional show and rider relationships on transactions;
- PDF/JPG/JPEG/PNG receipt attachments;
- season budgets and budget-vs-actual reporting;
- account balances calculated from opening balance and ledger activity;
- CSV transaction export;
- Financial Reports hub;
- budget-vs-actual reporting with favorable/unfavorable variance;
- family receivables aging with overdue and due-soon status;
- financial-assistance/reimbursement reporting;
- category activity drill-down;
- CSV exports for budget, receivables, assistance, and category activity;
- Treasurer worklist for overdue balances, reimbursement claims, missing home barns/rates, and dues not yet generated;
- created/updated audit information;
- family receivables;
- season-specific home barns and home-barn membership-dues rates;
- rider/family charges and payments;
- credits and adjustments;
- conditional service-agreement credits;
- external financial-assistance awards and reimbursement claims.

Home barn is stored on the rider's **Season Membership**, not the permanent Rider record. A rider can therefore change barns between seasons while historical dues rules remain accurate.

Membership dues can be configured by Home Barn for each season. Finance users can generate an individual rider's dues charge or generate dues for the entire active season. Existing dues charges are skipped so bulk generation does not create duplicates.

Family accounts distinguish:

- **charges** — money the family is responsible for;
- **credits/adjustments** — team-authorized reductions;
- **service-agreement credits** — reductions earned through an agreed service obligation;
- **external assistance** — portions of charges allocated to a reimbursable grant/award;
- **payments** — actual money received from a family.

External financial assistance is tracked as an award with an approved maximum. Claims can move through Not Submitted, Submitted, Approved, Reimbursed, Denied, or Cancelled states. Submitted/approved/reimbursed claim allocations reduce family responsibility, while a Draft claim does not.

When an outside reimbursement is actually received, marking the claim Reimbursed requires the received date, destination financial account, income category, and amount received. The portal then posts a real income transaction to the v1.9 finance ledger. This keeps the family receivable and the team's actual cash activity separate.

Finance access is intentionally separate from ordinary Coach access. Administrators, active-season Treasurers, and superusers can use the Finance area. Parents and riders can see only the family account for riders they are authorized to view; they cannot see the team ledger or other families' accounts.

## Roles and privacy

The primary portal roles are:

| Role | Typical access |
| --- | --- |
| Administrator | Full team administration and Finance |
| Coach | Team/rider/show operations and competition management |
| Parent/Guardian | Linked riders and family-visible team information |
| Rider | Own private information plus team-visible information |

Additional committee assignments delegate specific capabilities. For example, the Points Secretary can assist with standings-related work and the Treasurer can access Finance without needing to become an Administrator.

Private rider information is limited to staff, the rider, and linked guardians as appropriate. Team roster/profile information can be visible to teammates while protected personal details remain restricted.

## Requirements

The provided deployment is designed for a Linux server with:

- Docker Engine;
- Docker Compose v2 (`docker compose`);
- an existing reverse proxy such as Apache, Nginx, or Caddy for public HTTPS access;
- a DNS hostname pointing to the server.

The application stack includes Django, PostgreSQL, Gunicorn, and the services defined in `docker-compose.yml`.

Docker does **not** need to own host ports 80 or 443. By default the portal gateway is exposed only on loopback at port `8088`, and the host web server proxies the public HTTPS hostname to it.

## Recommended installation layout

Keep the environment file and backups outside individual release directories:

```text
/opt/iea-team-portal/
├── .env
├── backups/
└── iea-team-portal-v1.9.6.1.1/
```

Future versions can sit beside prior releases while continuing to use the same environment configuration and Docker volumes.

## Fresh installation

### 1. Extract the release

Copy the release ZIP to the server and extract it under `/opt/iea-team-portal`.

For example:

```bash
sudo mkdir -p /opt/iea-team-portal
cd /opt/iea-team-portal
sudo unzip iea-team-portal-v1.9.8.zip
cd iea-team-portal-v1.9.8
chmod +x portalctl
```

Adjust ownership/permissions for the account that will operate Docker on your server.

### 2. Create the persistent environment file

Create:

```text
/opt/iea-team-portal/.env
```

A typical production configuration is:

```env
APP_PORT=8088

DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=iea.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://iea.example.com

POSTGRES_DB=iea_team
POSTGRES_USER=iea_team
POSTGRES_PASSWORD=replace-with-a-strong-database-password
POSTGRES_HOST=db
POSTGRES_PORT=5432

TIME_ZONE=America/New_York

SECURE_COOKIES=1
SECURE_HSTS_SECONDS=31536000
PORTAL_REPOSITORY_URL=https://github.com/mcangeli/iea-team-portal
```

Use your real hostname instead of `iea.example.com`.

Optional email settings can also be added:

```env
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-user
EMAIL_HOST_PASSWORD=your-password
EMAIL_USE_TLS=1
EMAIL_USE_SSL=0
DEFAULT_FROM_EMAIL=team@example.com
```

If `EMAIL_HOST` is blank, communications remain available in-app and Django uses its console email backend.

`DEFAULT_TEMP_PASSWORD` may optionally be configured for onboarding workflows, although using individually generated temporary credentials is preferable.

### 3. Start the portal

From the release directory:

```bash
./portalctl upgrade
```

The upgrade/start workflow starts PostgreSQL, creates a database backup when an existing database is present, builds the web image, runs the portal schema preflight, applies Django migrations, and starts the release.

Check status with the commands supported by `portalctl`, or with:

```bash
docker compose ps
```

### 4. Configure the reverse proxy

The default gateway binds only to:

```text
127.0.0.1:8088
```

Configure the existing host Apache/Nginx/Caddy installation to proxy the public HTTPS site to:

```text
http://127.0.0.1:8088
```

The reverse proxy should forward the original host and HTTPS/proxy headers. The portal's production settings expect HTTPS when `SECURE_COOKIES=1`.

### 5. Create the initial administrator

If the deployment does not already contain an administrator account, run Django's superuser command inside the web service using Docker Compose. The exact service name is defined in `docker-compose.yml`; for the standard release it can be run with the web service, for example:

```bash
docker compose exec web python manage.py createsuperuser
```

Sign in with that account and create/configure the team, season, users, riders, and other portal data.

## Upgrading an existing installation

Keep the existing `.env`, database volume, media volume, and backups. Extract the new release beside the old one:

```text
/opt/iea-team-portal/
├── .env
├── backups/
├── iea-team-portal-v1.8.14/
└── iea-team-portal-v1.9.6.1.1/
```

Then:

```bash
cd /opt/iea-team-portal/iea-team-portal-v1.9.6.1
chmod +x portalctl
./portalctl upgrade
```

The Compose project uses the stable project name `iea-team-portal`, so releases continue to use the same persistent PostgreSQL and media volumes.

Do **not** replace the shared `/opt/iea-team-portal/.env` with a release-specific environment file during normal upgrades.

Review `RELEASE_NOTES.md` before upgrading, especially when a release contains database migrations.

## Initial portal setup

After the first login, a practical setup order is:

1. Configure the Team identity and authorized team logo.
2. Create/activate the current Season.
3. Configure Season Classes.
4. Add Riders and their season memberships/classes.
5. Add Parent/Guardian contacts and link them to riders.
6. Create user accounts and assign the appropriate primary roles.
7. Configure scoring/qualification settings.
8. Add Shows and Lessons.
9. Set volunteer requirements if the team uses them.
10. Assign committee roles such as Treasurer or Points Secretary.
11. For Finance, create at least one Financial Account and review the seeded categories before entering transactions and budget lines.

## Using Finance for the first time

After assigning an active-season Treasurer or signing in as an Administrator, open **Team → Finance**.

A sensible starting workflow is:

1. Open **Accounts & Categories** and create the team's checking/savings/cash accounts.
2. Review the starter ledger categories and edit/deactivate them as needed.
3. Open **Dues Setup**, create the team's Home Barn records, and enter the current season's dues rate for each barn.
4. Confirm each rider's Home Barn on the rider's Season Membership page.
5. Generate membership-dues charges individually or use **Generate season dues**.
6. Open **Family Receivables** to review billed amounts and balances.
7. Add other family charges as they arise.
8. Record payments; each payment posts corresponding income to the team ledger.
9. For outside grants or financial assistance, create an Assistance Award and allocate eligible charges through reimbursement claims.
10. For reduced dues earned through agreed services, create a Service Agreement Credit and keep it Pending until the obligation is fulfilled.
11. Enter the Season Budget and use the Finance dashboard for account balances, budget-vs-actual, receivables, and remaining assistance-award capacity.
12. Export the ledger to CSV when an external working copy or report is needed.

The portal is a team-maintained ledger and receivables system, not a bank feed or replacement for professional accounting/tax software.

## Backups and persistent data

The deployment is designed so application releases are replaceable while important data persists outside the release code.

The stable Docker volumes are:

```text
iea-team-portal_postgres_data
iea-team-portal_media_data
```

PostgreSQL contains application records. The media volume contains rider/team images, finance receipts, and other uploaded media.

`portalctl upgrade` creates a timestamped PostgreSQL dump before upgrading an existing installation. Keep `/opt/iea-team-portal/backups/` protected and include it in the server's normal backup strategy.

For a complete disaster-recovery plan, back up both:

- PostgreSQL/database dumps; and
- the persistent media volume.

## Reminder processing

The portal includes reminder processing for supported workflows. It can be invoked with:

```bash
./portalctl reminders
```

If automatic reminders are desired, schedule that command using the server's preferred scheduler (for example cron or a systemd timer) at an appropriate daily interval.

## Security and production notes

- Keep `DJANGO_DEBUG=0` in production.
- Use a strong, unique `DJANGO_SECRET_KEY`.
- Use a strong PostgreSQL password.
- Serve the public portal through HTTPS.
- Keep the Docker application port bound to loopback unless there is a deliberate network architecture requiring otherwise.
- Restrict server/Docker access to trusted administrators.
- Treat uploaded receipts and rider/guardian information as private team data.
- Review user and committee assignments when staff responsibilities change.
- Do not expose the media volume directly as a public file directory; sensitive Finance receipt access in the portal is permission checked.

## Branding

The portal supports an authorized team logo and team identity. Only upload branding artwork that the team is permitted to use.

The portal identifies itself as a private team portal and not an official IEA website.

The footer version number links to the formatted README for the matching Git tag (for example, `v1.9.2.3`). The repository defaults to `https://github.com/mcangeli/iea-team-portal` and can be overridden with `PORTAL_REPOSITORY_URL` for a fork or alternate repository. Publish a Git tag matching each `VERSION` value so the version-specific documentation link resolves correctly.

## Release history

Detailed release history and upgrade notes are maintained in:

```text
RELEASE_NOTES.md
```

The README intentionally describes the **current product, installation, configuration, and usage** rather than duplicating the version changelog.

## Roadmap

Planned areas include additional v1.9.x finance workflows such as family balances, rider fees, fundraising, reimbursements, and richer reports.

Horse & Hoofprint Management remains planned for the v2.x series rather than being folded into the v1.9 finance work.

### Fundraising

Fundraising is managed from **Finance → Fundraising** by authorized Finance users.

A campaign tracks:
- campaign name, dates, status, goal and notes;
- contributions and donors;
- optional rider/family attribution;
- the portion of a contribution applied as a family receivable credit;
- the amount retained for the team.

Accounting rule: each fundraising contribution is posted to the team ledger **once** as income. An optional family fundraising credit is a separate receivable adjustment and does not create a second cash transaction.

Family fundraising credits must be tied to a specific rider-season and family charge. Voiding a fundraising contribution retains history, voids its linked ledger transaction, and cancels its linked family credit.

### Fundraising policy

Each season can define a fundraising policy from **Finance → Fundraising → Edit fundraising policy**.

Available models:
- **Team-wide** — fundraising stays with the team; default family credit is 0%.
- **Family credit** — attributed fundraising defaults to 100% family credit.
- **Hybrid** — set the normal percentage credited to an attributed family, with the remainder retained by the team.

The policy can also define whether participation is optional, which FamilyCharge types fundraising may offset, and a family-facing explanation.

Linked Parent/Guardian accounts can open **Family Account → Fundraising** to see only their family's attributed fundraising totals and campaign activity. Donor identities, bank/account information, and other families' fundraising are not shown. Rider accounts remain blocked from this financial view.

### Family finance privacy

Youth **Rider** logins do not have access to Finance or family-account financial data.

Family-account financial information is visible to:
- the Parent/Guardian login actually linked to that rider;
- Administrator users;
- Treasurer users with Finance permission for that season.

A Rider login cannot see its own family account, reimbursements, Finance audit history, fundraiser administration, or other Finance pages. Finance restrictions are enforced in the views as well as navigation.

### v2.x architecture note

The large `portal/views.py` modularization is intentionally deferred from the v1.9.x stabilization line. It is the first planned architecture task for v2.x before major v2 feature work, with the target structure split into focused modules such as dashboard, riders, shows, standings, communications, and `views/finance/`.


### Historical data and season management

v1.9.8 begins a dedicated historical-data workflow under **Season Archive**.

Each season card shows its rider, show, and result counts. Managers can open **Historical data** to review the season roster and add prior results rider-by-rider. This workflow intentionally permits historical result entry for archived seasons while keeping normal operational edits protected.

Season lifecycle behavior:
- **Archive season** closes the season to normal operational changes and removes it from active-season use.
- **Reopen for corrections** temporarily allows normal corrections but does **not** automatically make that season active.
- Archive and reopen actions are Administrator-only and are recorded in the audit log.

Historical results can also be imported in bulk from **Historical data → Import CSV**. AccessIEA Rider Performance exports are detected automatically. The importer always previews the file before writing records, flags validation problems, and skips matching existing results instead of overwriting them.

For AccessIEA exports, **Create missing historical roster/classes** can bootstrap the selected historical season directly from the export. Existing riders are matched by `#IEA` first and exact name second; the portal proposes missing season memberships, season classes, class assignments, and genuinely missing riders. Proposed setup is shown before commit. Varsity/JV class names map to Upper School and Future/Futures class names map to Futures; ambiguous team-level cases are blocked for manual review rather than guessed.

The portal's own row-oriented CSV template remains supported for manual data preparation. Imports are atomic and can be used against archived seasons without reopening normal operations. After a successful import, Historical Data shows a one-time reconciliation summary of records created, duplicates skipped, and setup changes made.

Before archiving an open season, Administrators now review an **Archive readiness** screen for incomplete shows, entries without results, riders without classes, open family charges, and unresolved reimbursements. These are warnings rather than hard blockers; intentional archive-with-warnings is supported after explicit confirmation.


### Show-day updates and active notifications

v1.9.7 introduces show-scoped public communication as part of the Show Day Operations work. Authorized users can publish updates for **Everyone**, **Futures Team**, or **Upper School Team**. Upper/Futures Team Parent committee chairs are restricted to their own team designation; Coach/Admin and assigned Show Leads can publish broader updates. Youth Rider logins cannot gain publishing rights through an accidental committee assignment.

Publishing with **Notify recipients now** creates an in-portal notification immediately for the relevant entered riders, their linked Parent/Guardian accounts, Coach/Admin, the appropriate Team Parent, assigned Show Leads, and the Points Secretary. Optional email delivery respects the user's separate **Email show-day updates** preference. Revisions can be saved silently or actively re-notified.

Families can open **Show Week → Show updates** to see only updates relevant to their rider/team. Public updates intentionally do not expose Coach-only strategy, points-rider controls, Finance, or private rider information.

### Prize-list and estimated show schedule

v1.9.7 adds a show-specific class schedule designed for prize-list information and show-day changes.

- Each class keeps a **Prize list time** as the published baseline.
- Each class can also have a separate **Current estimate** for show-day adjustments.
- Blank times are supported because prize lists do not always provide precise timing.
- A short public note can identify a ring, break, or other timing context.
- Authorized users can edit the schedule in one table rather than opening each class separately.
- The entire remaining schedule can be shifted by `-30`, `-15`, `-10`, `+10`, `+15`, or `+30` minutes starting with a selected class.
- **Reset estimates to prize list** restores the working estimates without changing the published baseline.

Schedule editing follows show-day delegation:
- Admin/Coach: all classes.
- Assigned Show Lead: all classes.
- Secretary / Points Secretary: all classes.
- Futures Team Parent: Futures and shared classes.
- Upper Team Parent: Upper and shared classes.
- Parent/Rider: read-only.

The schedule is explicitly presented as an estimate; official show announcements remain authoritative.

### Show Day dashboard and rider check-in

The portal provides a combined mobile-friendly Show Day workspace at:

`Show → Open Show Day`

The dashboard brings together:
- rider check-in/status;
- estimated class schedule;
- recent public show-day updates;
- show-day items that need attention;
- direct result-entry links for Coach/Admin and Secretary / Points Secretary.

Rider show-day statuses are:
- Expected;
- Arrived;
- Running Late;
- Scratched;
- Finished / Left.

Status changes record who made the update and when. The optional status note is intended for short operational context such as “parking now” or “at Ring 2.”

Check-in permissions:
- Admin/Coach and assigned Show Leads can update all participating riders.
- Futures Team Parent can update Futures riders.
- Upper Team Parent can update Upper riders.
- Ordinary linked Parent/Guardian can update only their own rider.
- Rider accounts can update only themselves.
- Secretary / Points Secretary can see the operational dashboard and enter results, but does not receive general rider check-in authority solely from the Secretary role.

The Show Day dashboard continues to keep points-rider editing restricted to the existing competition-management permissions. Secretary / Points Secretary receives result-entry links through the existing points-management permission without gaining Coach/Admin access.

### Show-day checklist and volunteer coordination

The existing show-planning workflow includes structured show-day checklist and volunteer coordination.

Planning items now include:
- **Checklist**
- **Volunteer**
- **Supply / Hospitality**

Each item also has a team designation:
- Everyone
- Futures Team
- Upper School Team

Permissions:
- Admin/Coach and assigned Show Leads can manage all planning items.
- Futures Team Parent can create/edit/complete Futures items.
- Upper Team Parent can create/edit/complete Upper items.
- Team Parents may see family-visible Everyone items but cannot edit them unless they otherwise have full show-planning authority.
- Linked families can see and claim family-visible volunteer/supply items applicable to their rider’s squad.
- A user who is assigned to or claims an item can mark that item complete.
- Rider accounts do not gain planning authority through committee assignments.

A **starter show-day plan** can be generated by Coach/Admin or an assigned Show Lead. It is duplicate-safe and adapts to the show’s operating mode:
- Attending shows get a lightweight checklist for paperwork, rider arrival, banner/signage, drinks, and food.
- Hosted + attending shows add setup, officials, parking, ring crew, hospitality, awards, and cleanup operations.

The Show Day Dashboard now surfaces:
- open checklist count;
- open volunteer count;
- planning items that need attention;
- the logged-in user’s assigned or claimed items.

### My Show Day

The portal provides a personal show-day view for riders and linked parents/guardians at:

```text
/shows/<show-id>/my-day/
```

The page intentionally reuses the mobile-friendly Show Day visual language while removing staff-only operational detail. It shows only the logged-in user's directly linked rider(s) and includes:
- rider arrival/check-in status with quick update controls;
- the rider's active classes and current estimated/prize-list time;
- public schedule notes;
- the user's assigned or claimed show-day volunteer/supply jobs;
- a count/link for other family-visible volunteer openings;
- recent show-day updates applicable to that rider/team designation;
- quick links to the full schedule and all show updates.

Privacy behavior:
- unrelated riders and their classes are not shown;
- no points-rider designation is exposed;
- no finance information is exposed;
- no other family's assignments are presented as personal work;
- an account without a linked rider receives a clear empty state.

Show-day status and assignment-completion actions return to My Show Day when started there, keeping the family workflow on one phone-friendly screen.
