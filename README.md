# ArenaLine

**Current version: v3.2.3**

ArenaLine is a private, self-hosted equestrian operations platform with discipline-specific competition modules. The included IEA module supports team administration, riders and families, horses and Hoofprint workflows, shows, scoring, qualification, operations, finance, communications, history, hosted-show management, and an explicitly published public spectator experience.

v3.2.3 completes the 3.2.x People & Operations release family: canonical People identity, multi-role barn participation, horse relationships, ArenaLine Station, work-history review, People Structure, privacy-aware public rider profiles, and the operational/accessibility hardening needed to carry those foundations into broader barn management.

> ArenaLine is independent software. The included IEA competition workflows are not an official IEA website or IEA product.

## Documentation map

- `README.md` — product overview, installation, setup, operation, updating, and troubleshooting.
- `ROADMAP.md` — canonical product roadmap and committed future release direction.
- `CHANGELOG.md` — concise release history/changelog.
- `ARCHITECTURE.md` — technical/domain boundaries and compatibility strategy.
- `docs/PRODUCT_AND_UI_GUIDE.md` — standing ArenaLine branding, UI, privacy, and documentation rules.
- `docs/releases/` — detailed release-specific notes; current stable release: `docs/releases/v3.2.3.md`.
- `RELEASE_CHECKLIST.md` — release-promotion gates.
- `RELEASE_NOTES.md` — retained detailed historical release notes for earlier releases.

The README intentionally remains an overview/instructions document; roadmap decisions and changelog history belong in their dedicated files.

## v3.2.3 highlights

### People-first identity and access

ArenaLine now treats **Person** as the durable human identity and a login account as optional access. Existing Rider, Guardian/Parent, UserProfile, season, finance, competition, and historical structures remain compatibility-safe while workflows move toward the canonical People model.

A Person can hold multiple simultaneous barn roles and relationships without those labels automatically granting permissions. Parent/guardian relationships, login access, private profile visibility, family finance access, and public identity remain separate concerns.

### Barn participation and People Structure

People can participate as riders, boarders, trainers, assistant trainers, barn managers/staff, working students, board members, and parents/guardians. Effective dates preserve current and historical participation.

People Structure provides generic organization groups/programs and committees while keeping IEA-specific responsibilities and terminology intact. Horse relationships support ownership/responsible-party, boarding, lease, trainer, and caretaker participation and form the foundation for v3.3 Equine Care.

### ArenaLine Station and work history

ArenaLine Station provides a shared-device barn workflow with device activation, separate Station PINs, restricted Person identification, and staff/working-student clock-in and clock-out. Managers can review, correct, approve, summarize, and export work history with audit coverage.

Station credentials do not reuse portal passwords and do not grant unrestricted portal access.

### Public rider profiles and privacy

Opted-in rider profiles can be deliberately published through the public ArenaLine site using allow-listed fields only. Public cards support photo, display name, bio, website, Instagram, and YouTube while private contact, birth-date, family, role, finance, and operational information remain private.

### Presentation and accessibility

The 3.2.3 closeout includes responsive People/Station/public-card presentation, keyboard and focus improvements, mobile navigation hardening, intentional empty states, and continued light/dark ArenaLine styling.

### Validation

The final v3.2.3 staging baseline passed Django system checks and the complete `portal.tests` regression suite: **643/643 tests green**.

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
7. Add people through **People**, link/create login access only where needed, and assign current barn roles/relationships.
8. Link riders to their current season, Futures/Upper team, home barn, and classes; link parents/guardians through the rider's family relationships.
9. Configure organization groups/programs and committees where needed.
10. Add Horses and maintain People↔Horse participation relationships.
11. Add Shows, official show classes, availability, entries, and Show Lead assignments.
12. Add Lessons, Calendar events, announcements, volunteer requirements, and Action Items.
13. Configure ArenaLine Station devices/PINs if using shared-device work tracking.
14. If using Finance, configure its accounts/categories/rates before entering family activity.
15. Add prior-season information through the historical-data tools when desired.

## Core workflows

### People, riders, seasons, and families

A **Person** is the canonical human identity. A login account is optional and is managed separately as access. A Person may hold multiple barn roles and relationships simultaneously.

A **Rider** remains the competition-compatible rider record. A **Season Membership** places that rider on a specific season's Futures or Upper roster and stores season-specific classes, home barn, and notes. Do not delete a Person/Rider simply because they graduate or leave the organization; use lifecycle/effective-date controls so history remains intact.

Parent/guardian relationships are represented through People while legacy family structures remain compatibility bridges. One parent/guardian may be linked to multiple riders.

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

ArenaLine includes Horse Registry, Coggins tracking, season class eligibility, show horse assignments, Horse of the Day, Horse Readiness, Show Horse Lists, Course Operations, Hoofprint Builder/finalized snapshots, post-show horse history/Record Book summaries, and People↔Horse participation relationships.

### Station and work history

ArenaLine Station is a tablet/shared-device surface for barn operations. Station devices use their own activation secrets and Person PINs rather than full portal credentials. Staff and working students can clock in/out for their current work roles; managers can review, edit, approve, summarize, and export work history.

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

Use **Competition → Season History** for prior seasons and Season Review. Use **Competition → Record Book** for honors/archive presentation. Preserve historical People/Riders rather than recreating them as current Riders.

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

Or install v3.2.3 explicitly:

```bash
./portalctl update v3.2.3
```

`portalctl update` requires a clean Git tree, fetches stable tags, creates a validated database backup, switches to the selected release, rebuilds, runs deployment/schema preflight, starts the release, and performs health checks.

`./portalctl upgrade` does **not** select a newer Git revision. It rebuilds/migrates the revision already checked out and is appropriate for staging/preview workflows after the desired branch commit has already been selected.

The v3.2.x migration chain adds the People/relationship and ArenaLine Station foundations on top of the v3.1 public-experience schema. See `docs/releases/v3.2.3.md` for the release-specific migration summary.

## Backups and rollback

`portalctl update` and `portalctl upgrade` create validated PostgreSQL backups. `portalctl rollback-code` can return application code to the previous recorded checkout and then runs deployment health checks.

Code rollback does not automatically reverse an incompatible database migration. Restore the matching database backup when schema/data rollback is required. Uploaded media is separate from PostgreSQL and must have its own backup policy.

See `docs/BACKUP_RESTORE_ROLLBACK.md` and `docs/STAGING.md`.

## Architecture

ArenaLine retains `Team` as the persisted tenant model for compatibility while generic platform code resolves organization context through service boundaries.

Generic platform domains include Core, People, Horses, Operations, Finance, and Communications. IEA-specific competition behavior belongs to `competition_iea`.

The public/external layer is a separate publication boundary. Anonymous routes consume explicit allow-listed publication payloads rather than authenticated internal views.

The v3.2 People layer is compatibility-first: Person/relationship/group abstractions coexist with legacy Rider, Guardian/Parent, UserProfile, season, committee, finance, and competition structures until callers can be migrated safely.

See `ARCHITECTURE.md`, `docs/PRODUCT_AND_UI_GUIDE.md`, and `docs/releases/v3.2.3.md`.

## Release process

Before any release is promoted to `main`, use `RELEASE_CHECKLIST.md`.

The release is not promotion-ready until code, tests, presentation, privacy/permissions, `VERSION`, README, changelog, roadmap, architecture/supporting documentation, and release tagging plan are consistent.

## Troubleshooting

For deployment problems, capture the failing command plus:

```bash
./portalctl git-status
./portalctl health
./portalctl ps
docker compose logs --tail=200
```

Do not include `.env` secrets or passwords when sharing logs.
