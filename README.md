# ArenaLine

**Current version: v3.0.0**

ArenaLine is a private, self-hosted equestrian operations platform with discipline-specific competition modules. The included IEA module supports team administration, riders and families, horses and Hoofprint workflows, shows, scoring, qualification, operations, finance, communications, history, and hosted-show management.

v3.0.0 establishes the official IEA class-catalog foundation and moves scoring eligibility away from hard-coded class exceptions toward versioned rulebook metadata.

> ArenaLine is independent software. The included IEA competition workflows are not an official IEA website or IEA product.

For release history, see `RELEASE_NOTES.md` and `docs/releases/v3.0.0.md`. For architecture, see `ARCHITECTURE.md`. For release promotion requirements, see `RELEASE_CHECKLIST.md`.

## v3.0.0 highlights

### Official IEA class catalog

ArenaLine now includes versioned official class reference data for the 2026–2027 IEA rulebook season across:

- Hunt Seat
- Western
- Dressage

The catalog records official class code/name, discipline, team level, class family, scoring eligibility, season assignability, source rule, revision date, and display order.

### Season Setup

An Administrator/Coach can configure the IEA rulebook season and participating disciplines from **Manage → Season Setup**.

Official classes can then be created or linked from the catalog instead of being retyped manually. Existing historical/manual classes remain supported and can be reconciled deliberately without guessing from display names.

### Show Setup

Normal competition classes flow through the season catalog:

`IEA catalog → SeasonClass → ShowClass → Entries/results`

Official show-only classes are represented directly at the show level. v3.0.0 includes:

- Hunt Seat H7x/H8x and H13x/H14x warm-ups
- Western W7x/W8x and W13x/W14x warm-ups
- Dressage D7x/D8x and D13x/D14x warm-ups
- Hunt Seat Varsity Open Championship (VOC)

Warm-ups require the appropriate same-show prerequisite entry and never award individual or team points.

VOC eligibility is derived from same-show H1/H2 participation/results. ArenaLine ranks eligible riders by combined points and H1 placing and does not invent unresolved judge-card tie-break information that is not stored by the portal.

### Catalog-driven scoring policy

ArenaLine now uses catalog metadata to determine effective scoring eligibility rather than relying on Hunt Seat-only special cases.

The standard no-team-points classes are:

- H8 / H14
- W8 / W14
- D8 / D14

Classes with `team_points_enabled=False` cannot be designated as points-rider/team entries. Classes with `individual_points_enabled=False` cannot retain result points. Historical unlinked H8/H14 behavior remains available only as a compatibility fallback.

### Presentation and architecture cleanup

- Removed the legacy inline Calendar style block and moved Calendar presentation into the shared Operations layer.
- Preserved Month/Agenda, filtering, responsive behavior, light/dark presentation, and mobile switching.
- Refreshed ArenaLine architecture documentation and clarified the IEA competition-module boundary.
- Established the rule that future public/external pages must use explicit publication controls and allow-listed public data.

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

A show can include availability, entries, points-rider designation, results, Show Lead assignment, planning/checklists, volunteers, Show Week communication, Show Day status, Prize List/Schedule, Horse & Hoofprint workflows, and show finance where enabled.

**Points-rider designation is staff strategy and is intentionally hidden from Rider and Parent accounts.**

Show Day is designed for phone use at the ring.

### Points and qualification

Rider points are tracked **per class**. Qualification/postseason behavior remains part of the IEA competition module and should be changed only from verified official rule sources.

Team scoring eligibility is catalog-driven in v3.0.0. H8/H14, W8/W14, and D8/D14 do not count toward team points.

Use **Competition → Standings** for individual progress and team scoring. Postseason records support Regionals, Zones, and Nationals, including individual and team results.

### Horses and Hoofprint

ArenaLine includes:

- Horse Registry
- Coggins tracking
- season class eligibility
- show horse assignments
- Horse of the Day
- Horse Readiness
- Show Horse Lists
- Course Operations
- Hoofprint Builder/finalized snapshots
- post-show horse history and Record Book summaries

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

```bash
sudo git clone https://github.com/mcangeli/iea-team-portal.git /opt/iea-team-portal/app
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

The application gateway normally listens only on `127.0.0.1:8088`. Put the existing HTTPS reverse proxy in front of that local port.

## Updating production

Stable production installations follow stable Git release tags.

Check status first:

```bash
cd /opt/iea-team-portal/app
./portalctl git-status
```

Install the latest stable release with:

```bash
./portalctl update
```

Or install a specific release explicitly:

```bash
./portalctl update v3.0.0
```

`portalctl update`:

- requires a clean Git tree;
- fetches tags/repository updates;
- resolves the stable/preview channel;
- creates and validates a pre-update PostgreSQL backup;
- switches the application checkout to the selected release;
- rebuilds the application;
- runs deployment/schema preflight;
- starts the new release;
- runs post-start health checks.

### `update` vs `upgrade`

Use `./portalctl update` to move production to a newer Git release/tag.

`./portalctl upgrade` **does not choose or fetch a newer release**. It backs up, rebuilds, migrates, and restarts the revision already checked out. This is useful after intentionally selecting code by another supported workflow, but it is not the normal stable-release update command.

Verify after updating:

```bash
./portalctl git-status
./portalctl health
./portalctl exec web python manage.py showmigrations portal
```

For v3.0.0 the migration chain extends through:

```text
0056_v300_reconcile_catalog_non_team_entries
```

## Backups and rollback

`portalctl update` and `portalctl upgrade` create validated PostgreSQL backups. `portalctl rollback-code` can return application code to the previous recorded checkout and then runs deployment health checks.

Code rollback does **not** automatically reverse an incompatible database migration. Restore the matching database backup when schema/data rollback is required. Uploaded media is separate from PostgreSQL and must have its own backup policy.

See `docs/BACKUP_RESTORE_ROLLBACK.md` and `docs/STAGING.md`.

## Architecture

ArenaLine retains `Team` as the persisted tenant model for compatibility while generic platform code resolves organization context through service boundaries.

Generic platform domains include:

- Core
- People
- Horses
- Operations
- Finance
- Communications

IEA-specific competition behavior belongs to `competition_iea`.

The v3 class architecture is:

```text
IEA rulebook source
        ↓
IEAClassCatalogEntry
        ↓
SeasonClass / direct show-only class
        ↓
ShowClass
        ↓
Entries and results
        ↓
Catalog-driven scoring / qualification workflows
```

`portal/views.py` remains a compatibility/re-export namespace while implementations live under `portal/view_modules/`.

Future public-facing functionality must use a separate explicit-publication boundary. Nothing becomes public merely because it exists in ArenaLine.

See `ARCHITECTURE.md` and `docs/V3_0_CLEANUP_CLOSEOUT.md`.

## Release process

Before any release is promoted to `main`, use `RELEASE_CHECKLIST.md`.

The release is not promotion-ready until code, tests, `VERSION`, `README.md`, release notes, roadmap, architecture/supporting documentation, and release tagging plan are consistent.

## Troubleshooting

For deployment problems, capture the failing command plus:

```bash
./portalctl git-status
./portalctl health
./portalctl ps
docker compose logs --tail=200
```

Do not include `.env` secrets or passwords when sharing logs.
