# ArenaLine

**Current version: v3.1.0**

ArenaLine is a private, self-hosted equestrian operations platform with discipline-specific competition modules. The included IEA module supports team administration, riders and families, horses and Hoofprint workflows, shows, scoring, qualification, operations, finance, communications, history, hosted-show management, and an explicitly published public spectator experience.

v3.1.0 adds the first ArenaLine public/external layer: opt-in public program pages, published show information, live show/ring status, class-by-class public results, spectator notices, stable live URLs, and a polished mobile-first Show Day workflow.

> ArenaLine is independent software. The included IEA competition workflows are not an official IEA website or IEA product.

For release history, see `docs/releases/v3.1.0.md`. For architecture, see `ARCHITECTURE.md`. For release promotion requirements, see `RELEASE_CHECKLIST.md`.

## v3.1.0 highlights

### Explicit public publication boundary

Nothing becomes public merely because it exists internally. ArenaLine v3.1.0 adds explicit organization and show publication controls with allow-listed public payloads.

Public publication can independently expose selected show data such as:

- show date/time;
- venue/address;
- host and IEA area;
- class schedule;
- finalized published results;
- live show/class status;
- spectator-safe public notices.

Private information remains private by default, including contact data, rider notes, horse medical/Coggins/internal notes, finance, committee/admin information, points-rider strategy, and private files.

### Public program and show pages

Organizations can enable a public program page and deliberately publish individual shows. Public pages support:

- organization branding and public website links;
- upcoming/active/past show grouping;
- public show detail pages;
- published class order and estimated times;
- class-by-class published results;
- traditional equestrian placing colors for 1st–10th;
- stable `/public/<program>/live/` links for reusable QR codes and printed materials.

### Live Show Day and multi-ring operations

Show Day now supports an operational live-show workflow:

- show lifecycle: Ready/Upcoming, In progress, Paused, Complete;
- per-class lifecycle: Not started, In progress, Paused, Complete;
- structured ring assignments;
- multiple rings active simultaneously;
- one active/paused class per ring;
- complete show order even when the organization has no rider in a class;
- mobile/tablet presentation optimized for ringside use.

At tablet/mobile widths the Show Day class board becomes stacked class cards rather than forcing a wide desktop table.

### Public class results

Completed classes can publish results independently. Results remain private until explicitly published.

Public result payloads expose only approved fields such as class identity, place, and rider display name. They do not expose points-rider flags, internal notes, entry strategy, horse medical information, or finance data.

### Spectator notices and delays

Admin, Coach, or the assigned Show Lead can post spectator-safe notices from Show Day, including:

- general announcements;
- break/schedule notices;
- ring-specific notices;
- +15 / +30 / +45 / +60 minute delay updates;
- clearing stale notices.

These notices are separate from internal family/team communications and appear publicly only when the show is published with live status enabled.

## Roles and dashboards

| Role / assignment | Primary use |
| --- | --- |
| Administrator | Full organization administration; can review every operational dashboard |
| Coach | Roster, classes, shows, results, qualification, lessons, availability and organization operations |
| Parent/Guardian | Linked riders, family-visible schedules, actions, volunteer activity and permitted family finance |
| Rider | Own rider/team information; staff strategy and private information remain restricted |
| Futures / Upper Team Parent | Squad-scoped coordination dashboard |
| Show Lead | Assigned-show operations, planning, volunteers and Show Day |
| Secretary / Points Secretary | Standings, missing results and qualification review |
| Treasurer | Finance operations without requiring Administrator access |

Administrators can open all role workspaces. Coaches receive the Coach workspace by role and only receive Team Parent, Show Lead, or Points Secretary dashboards when explicitly assigned that responsibility.

## Recommended first-time setup

1. Install ArenaLine and configure the persistent `.env`.
2. Sign in as Administrator.
3. Open **Manage → Branding** and configure Program/Futures/Upper imagery.
4. Open **Manage → Season Setup** and create/activate the current season.
5. Configure the season's official IEA rulebook/catalog and participating disciplines.
6. Review/create the official season classes needed by the organization.
7. Add Riders and assign season, team level, home barn, and classes.
8. Add/link Parents and Guardians.
9. Open **Manage → Users** and create logins linked to the appropriate Rider or Parent record.
10. Assign committee responsibilities such as Team Parent, Treasurer, and Secretary/Points Secretary.
11. Add Shows, official show classes, availability, entries, and Show Lead assignments.
12. Add Lessons, Calendar events, announcements, volunteer requirements, and Action Items.
13. If using Finance, configure its accounts/categories/rates before entering family activity.
14. Add prior-season information through the historical-data tools when desired.

## Core workflows

### Riders, seasons, and families

A **Rider** is a permanent person record. A **Season Membership** places that rider on a specific season's Futures or Upper roster and stores season-specific classes, home barn, and notes.

Do not delete a rider simply because they graduate or leave the organization. Use lifecycle controls so historical results and relationships remain intact.

Parent/Guardian records are separate from Riders and one parent may be linked to multiple riders. User accounts are linked to the appropriate Rider or Parent/Guardian record.

### Shows and Show Day

Create the Show first, then configure its classes/schedule, rider availability, and entries. Results are recorded against the appropriate rider and class.

A show can include availability, entries, points-rider designation, results, Show Lead assignment, planning/checklists, volunteers, Show Week communication, Show Day status, Prize List/Schedule, Horse & Hoofprint workflows, show finance, and deliberate public publication where enabled.

**Points-rider designation is staff strategy and is intentionally hidden from Rider and Parent accounts.**

Show Day is designed for phone/tablet use at the ring. Full-team operators can use the complete class order, squad Team Parents remain Futures/Upper scoped, and ordinary family/rider views remain read-only for operational controls.

### Points and qualification

Rider points are tracked **per class**. Qualification/postseason behavior remains part of the IEA competition module and should be changed only from verified official rule sources.

Team scoring eligibility is catalog-driven. H8/H14, W8/W14, and D8/D14 do not count toward team points.

Use **Competition → Standings** for individual progress and team scoring. Postseason records support Regionals, Zones, and Nationals, including individual and team results.

### Horses and Hoofprint

ArenaLine includes Horse Registry, Coggins tracking, season class eligibility, show horse assignments, Horse of the Day, Horse Readiness, Show Horse Lists, Course Operations, Hoofprint Builder/finalized snapshots, and post-show horse history/Record Book summaries.

### Calendar, communication, lessons, and volunteers

Calendar supports Month and Agenda views, event-type filtering, RSVP-enabled events, and Futures/Upper filtering where the source record carries a squad.

Announcements are for organization communication. Action Items are for work needing an owner, response, or completion state. Notifications surface relevant ArenaLine activity.

Lessons support groups, scheduled lessons, and rider attendance. Volunteer requirements/logs support service tracking and approval. Committee assignments delegate operational responsibility without granting full Administrator access.

### Finance

Finance is intentionally restricted:

- **Administrator/Treasurer:** internal organization finance.
- **Linked Parent/Guardian:** permitted family-account information.
- **Rider:** no Finance access.
- **Coach alone:** does not automatically grant Finance access.

Finance includes family charges/credits/payments, dues and service credits, assistance, budgets, reimbursements, show funding/allocation, fundraising, and reporting.

### History and Record Book

Use **Competition → Season History** for prior seasons and Season Review. Use **Competition → Record Book** for honors/archive presentation. Preserve historical Riders rather than recreating them as current Riders.

## Production installation

### Requirements

- Linux server
- Docker Engine and Docker Compose v2
- Git
- DNS hostname and an existing reverse proxy/web server for public HTTPS access

Supported layout:

```text
/opt/iea-team-portal/
├── app/          # Git checkout
├── .env          # persistent production configuration
├── backups/
└── logs/
```

The `.env` lives outside the Git checkout so updates do not replace production secrets/configuration.

### Install from Git

ArenaLine server Git operations use SSH:

```bash
sudo git clone git@github.com:mcangeli/iea-team-portal.git /opt/iea-team-portal/app
cd /opt/iea-team-portal/app
sudo ./install.sh
```

Populate `/opt/iea-team-portal/.env`. Start from `.env.example` and replace every placeholder secret/password.

Typical production settings include:

```env
COMPOSE_PROJECT_NAME=iea-team-portal
POSTGRES_VOLUME_NAME=iea-team-portal_postgres_data
MEDIA_VOLUME_NAME=iea-team-portal_media_data
PORTAL_ENVIRONMENT=production
APP_PORT=8088
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=iea.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://iea.example.com
POSTGRES_DB=iea_team
POSTGRES_USER=iea_team
POSTGRES_PASSWORD=replace-with-a-strong-password
POSTGRES_HOST=db
POSTGRES_PORT=5432
TIME_ZONE=America/New_York
SECURE_COOKIES=1
SECURE_HSTS_SECONDS=31536000
PORTAL_UPDATE_CHANNEL=stable
```

Before first public use:

```bash
./portalctl preflight
./portalctl up -d --build
./portalctl health
```

## Updating production

Stable production installations follow stable Git release tags.

```bash
cd /opt/iea-team-portal/app
./portalctl git-status
./portalctl update
```

Or install v3.1.0 explicitly:

```bash
./portalctl update v3.1.0
```

`portalctl update` requires a clean Git tree, fetches stable tags, creates a validated database backup, switches to the selected release, rebuilds, runs deployment/schema preflight, starts the release, and performs health checks.

`./portalctl upgrade` does **not** select a newer Git revision. It rebuilds/migrates the revision already checked out and is appropriate for staging/preview workflows after the desired branch commit has already been selected.

For v3.1.0 the portal migration chain extends through:

```text
0065_v310_spectator_show_updates
```

## Backups and rollback

`portalctl update` and `portalctl upgrade` create validated PostgreSQL backups. `portalctl rollback-code` can return application code to the previous recorded checkout and then runs deployment health checks.

Code rollback does not automatically reverse an incompatible database migration. Restore the matching database backup when schema/data rollback is required. Uploaded media is separate from PostgreSQL and must have its own backup policy.

See `docs/BACKUP_RESTORE_ROLLBACK.md` and `docs/STAGING.md`.

## Architecture

ArenaLine retains `Team` as the persisted tenant model for compatibility while generic platform code resolves organization context through service boundaries.

Generic platform domains include Core, People, Horses, Operations, Finance, and Communications. IEA-specific competition behavior belongs to `competition_iea`.

The public/external layer is a separate publication boundary. Anonymous routes consume explicit allow-listed publication payloads rather than authenticated internal views.

See `ARCHITECTURE.md` and `docs/releases/v3.1.0.md`.

## Release process

Before any release is promoted to `main`, use `RELEASE_CHECKLIST.md`.

The release is not promotion-ready until code, tests, `VERSION`, README, release notes, roadmap, architecture/supporting documentation, and release tagging plan are consistent.

## Troubleshooting

For deployment problems, capture the failing command plus:

```bash
./portalctl git-status
./portalctl health
./portalctl ps
docker compose logs --tail=200
```

Do not include `.env` secrets or passwords when sharing logs.
