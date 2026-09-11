# IEA Team Portal

**Current version: v2.0.0 Release Candidate 1**

IEA Team Portal is a private, self-hosted operations system for an Interscholastic Equestrian Association team. It brings riders and families, seasons, classes, shows, points and qualification, lessons, calendars, communications, volunteers, show-day operations, history, and team finance into one portal.

> Private team software. This project is not an official IEA website or IEA product.

For version-by-version changes, see `RELEASE_NOTES.md`. For the v2 code organization, see `ARCHITECTURE.md`.

## Roles and dashboards

The portal uses primary roles plus operational assignments.

| Role / assignment | Primary use |
| --- | --- |
| Administrator | Full team administration; can open every operational dashboard |
| Coach | Roster, classes, shows, results, qualification, lessons, availability and team operations |
| Parent/Guardian | Linked riders, family-visible schedules, actions, volunteer activity and permitted family finance |
| Rider | Own rider/team information; staff strategy and private information remain restricted |
| Futures / Upper Team Parent | Squad-scoped coordination dashboard |
| Show Lead | Assigned-show operations, planning, volunteers and Show Day |
| Secretary / Points Secretary | Standings, missing results and qualification review |
| Treasurer | Finance operations without requiring Administrator access |

Administrators intentionally see buttons for all role workspaces. Users with multiple responsibilities can switch between the workspaces available to them.

## Recommended first-time setup

Use this order so records are created after the information they depend on:

1. Install the portal and configure the persistent `.env`.
2. Sign in as Administrator.
3. Open **Manage → Branding** and configure the team presentation.
4. Open **Manage → Season setup** and create/activate the current season.
5. Create the season's Futures and Upper classes.
6. Add Riders and assign season, team level, home barn and classes.
7. Add/link Parents and Guardians.
8. Open **Manage → Users** and create logins linked to the appropriate Rider or Parent record.
9. Assign committee responsibilities such as Team Parent, Treasurer and Secretary/Points Secretary.
10. Add Shows, show classes, availability, entries and Show Lead assignments.
11. Add Lessons, Calendar events, announcements, volunteer requirements and Action Items.
12. If using Finance, configure its accounts/categories/rates before entering family activity.
13. Add prior-season information through the historical-data tools when desired.

## Using the portal

### Dashboard

The main Dashboard is the season overview. Operational dashboards emphasize the information needed for that responsibility:

- **Coach:** roster health, qualification, availability, volunteer approvals, action items, lessons and shows.
- **Team Parent:** squad coordination, availability, volunteers and planning.
- **Show Lead:** **Open Show Day**, **Planning & Volunteers**, and **Prize List / Schedule** for the assigned show.
- **Secretary / Points:** missing results, standings, qualification and result review.

### Riders, seasons and families

A **Rider** is a permanent person record. A **Season Membership** places that rider on a particular season's Futures or Upper roster and stores season-specific classes, home barn and notes.

Do not delete a rider simply because they graduate or leave the team. Use the rider lifecycle controls so historical results and relationships remain intact.

Parent/Guardian records are separate from Riders and one parent may be linked to multiple riders. User accounts are then linked to the appropriate Rider or Parent/Guardian record.

### Shows and Show Day

Create the Show first, then configure its classes/schedule, rider availability and entries. Results are recorded against the appropriate rider and class.

A show can include availability, entries, points-rider designation, results, Show Lead assignment, planning/checklists, volunteers, Show Week communication, Show Day status, Prize List/Schedule and show finance where enabled.

**Points-rider designation is staff strategy and is intentionally hidden from Rider and Parent accounts.**

Show Day is designed for phone use at the ring. Coaches and authorized Show Leads should use it for rider status/check-in, schedule context, open operational items and public show updates instead of moving among multiple administrative screens.

### Points and qualification

Rider points are tracked **per class**, not as one combined rider total. The standard individual qualification threshold represented by the portal is **18 points in a class**.

Team points use the coach-designated points rider for each eligible class/show. Walk/Trot classes **H8 and H14 do not count toward team points**.

Use **Competition → Standings** for individual progress and team scoring. Postseason records support Regionals, Zones and Nationals, including individual and team results.

### Calendar, communication and lessons

Calendar supports Month and Agenda views, event-type filtering, RSVP-enabled events, and Futures/Upper filtering where the source record carries a squad.

Announcements are for team communication. Action Items are for work needing an owner, response or completion state. Notifications surface relevant portal activity.

Lessons support groups, scheduled lessons and rider attendance. Users see only information permitted by their role/linked riders.

### Volunteers and committees

Volunteer requirements/logs support service tracking and approval. Committee assignments delegate responsibilities without granting full Administrator access. Show Lead responsibility is assigned per show.

### Finance

Finance is intentionally restricted:

- **Administrator/Treasurer:** internal team finance.
- **Linked Parent/Guardian:** permitted family-account information.
- **Rider:** no Finance access.
- **Coach alone:** does not automatically grant Finance access.

Finance includes family charges/credits/payments, dues and service credits, assistance, budgets, reimbursements, show funding/allocation, fundraising and reporting. Configure the season's finance structure before relying on its reports.

### History and Record Book

Use **Competition → Season history** for prior seasons and Season Review. Use **Competition → Record book** for the team's honors/archive presentation. Preserve historical Riders rather than recreating them as current Riders.

## Privacy

The portal deliberately separates team-visible, operational and private information.

- Administrators and Coaches have broad management access.
- Parents can access linked Riders.
- Riders can access their own private information.
- Teammates may see permitted profile information without private personal data.
- Points-rider designation is staff-only.
- Finance follows the restrictions above.
- Former riders remain in history while normal roster views focus on active riders.

Use the least-privileged role that matches a person's actual responsibility.

## Branding and appearance

Under **Manage → Branding**, upload a wide team/show photograph used by the Dashboard and sign-in presentation and choose whether the crop favors the top, center or bottom. The existing team logo appears alongside the photographic treatment.

A landscape photo around 16:9 or slightly wider works best. Responsive cropping and readability overlays are automatic. Light/dark appearance can be switched from the top navigation.

## Production installation

### Requirements

- Linux server
- Docker Engine and Docker Compose v2
- Git
- DNS hostname and an existing reverse proxy/web server for public HTTPS access

The supported Git deployment layout is:

```text
/opt/iea-team-portal/
├── app/          # Git checkout
├── .env          # persistent production configuration
├── backups/
└── logs/
```

The `.env` is outside the Git checkout so application updates do not replace production secrets/configuration.

### Install from Git

```bash
sudo git clone https://github.com/mcangeli/iea-team-portal.git /opt/iea-team-portal/app
cd /opt/iea-team-portal/app
sudo ./install.sh
```

Populate `/opt/iea-team-portal/.env`. A typical production configuration is:

```env
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

The gateway normally binds to `127.0.0.1:8088`. Point the host reverse proxy at that address and terminate HTTPS at the host proxy.

## Updating

Check the current checkout:

```bash
cd /opt/iea-team-portal/app
./portalctl git-status
```

Update the stable channel:

```bash
./portalctl update
```

Install a specific tested ref:

```bash
./portalctl update v2.0.0-rc1
```

The updater requires a clean Git tree, creates a pre-update PostgreSQL backup, fetches the selected ref, performs preflight/schema checks, applies required migrations, rebuilds and restarts the application.

Verify after updating:

```bash
./portalctl ps
./portalctl git-status
```

## Backups and rollback

`portalctl update` creates a database backup before changing the application. `portalctl rollback-code` can return application code to the previous recorded checkout.

Code rollback does **not** automatically reverse an incompatible database migration. If a release changes schema and the database must also be rolled back, restore the matching pre-update database backup.

Keep the persistent `.env`, PostgreSQL data, uploaded media and `/opt/iea-team-portal/backups/` in the server's normal backup plan.

Useful commands:

```bash
./portalctl git-status
./portalctl update
./portalctl update <ref>
./portalctl rollback-code
./portalctl ps
```

## v2 architecture

The former monolithic `portal/views.py` is now a compatibility/re-export layer. Active implementations live in domain modules under `portal/view_modules/`. Specialized v2 URL/model modules isolate lifecycle, Calendar and branding additions. See `ARCHITECTURE.md`.

## Release Candidate 1

RC1 freezes the v2 feature and visual scope. It contains the modular view architecture, Git deployment/update workflow, role dashboards, rider lifecycle/archive, redesigned Calendar, photographic branding, and the completed Preview 7–9 visual system.

No new database migration is introduced by RC1. `0031_v200_team_branding.py` remains the latest migration.

## Troubleshooting

For deployment problems, capture the failing command plus:

```bash
./portalctl git-status
./portalctl ps
docker compose logs --tail=200
```

Do not include `.env` secrets or passwords when sharing logs.
