# ArenaLine Architecture

## Application shape

ArenaLine is a generic equestrian operations platform with discipline-specific competition modules layered on top. The persisted `Team` model remains the current tenant/organization record for compatibility, while platform code should prefer the organization service boundary rather than introducing new direct tenant assumptions.

The current platform modules are:

- `core`
- `people`
- `horses`
- `operations`
- `finance`
- `communications`

IEA-specific competition behavior lives under `competition_iea` and should not leak into generic platform surfaces unless the workflow explicitly requires IEA rules.

## View layer

The Django view layer is organized by functional domain under `portal/view_modules/`.

`portal/views.py` remains a compatibility namespace so existing URL configuration and imports such as `portal.views.show_detail` continue to work while implementations live in smaller domain modules.

### Domain modules

| Module | Responsibility |
| --- | --- |
| `dashboards.py` | Role-aware dashboard entry points |
| `roster.py` | Team roster, riders, parents/guardians, season membership/classes |
| `communications.py` | Calendar, events/RSVPs, announcements, action items, notifications |
| `competitions.py` | Shows, show classes, entries, and result editing |
| `show_day.py` | My Show Day, rider status, schedule, updates, weekly summary |
| `scoring.py` | Standings, qualification, scoring configuration, points-rider operations |
| `show_planning.py` | Show planning, Show Lead assignments, planning items |
| `lessons.py` | Lessons, attendance, availability, volunteer workflows |
| `history.py` | Season archive/review, historical import/corrections, awards, Record Book |
| `administration.py` | Users, committee assignments, general audit log |
| `finance_core.py` | Finance dashboard, ledger, accounts, categories, budgets |
| `family_finance.py` | Dues, family accounts, payments/charges/credits, assistance |
| `fundraising.py` | Fundraising policy, campaigns, contributions, family fundraising |
| `finance_reports.py` | Financial reporting and CSV exports |
| `show_finance.py` | Show budgets, allocations, funding policy, reimbursements |

Most domains also have a matching `*_helpers.py` containing private logic used only by that domain.

`common.py` is limited to helpers shared across multiple domains, including permissions, audit utilities, organization/season visibility, and shared scoring/query calculations.

## IEA competition boundary

IEA rulebook reference data and rule-specific behavior live under the competition boundary rather than on generic platform models whenever practical.

The v3 competition chain is:

```text
Official IEA rulebook
        ↓
IEAClassCatalogEntry
        ↓
SeasonClass (normal rider/season placement classes)
        ↓
ShowClass
        ↓
ShowEntry / ShowResult
        ↓
Scoring / qualification
```

Official show-only offerings such as warm-ups and VOC use a direct catalog relationship:

```text
IEAClassCatalogEntry
        ↓
ShowClass
        ↓
ShowEntry / ShowResult
```

They do not create `SeasonClass` records and therefore do not enter normal rider season assignments.

Catalog metadata is authoritative for scoring eligibility where available:

- `individual_points_enabled`
- `team_points_enabled`
- `season_assignable`

Legacy code/name heuristics may remain only as compatibility fallbacks for historical rows that are not linked to catalog data.

## Public-facing boundary

The v3.1 public layer uses explicit publication records under `portal/model_modules/public_site.py`:

- `PublicSiteProfile` controls whether an organization has an anonymous public site;
- `PublicShowPublication` controls whether a show is public and which categories of show data may be exposed.

Anonymous routes do not reuse authenticated portal views. They consume deliberately allow-listed payload builders in `portal/publication.py`.

### Public allow-list

Depending on explicit publication controls, public payloads may include:

- organization display identity/logo/website;
- show name/date/time;
- venue/address/host/IEA area;
- published class schedule and ring;
- spectator-facing live state;
- explicitly published class results;
- spectator-safe notices/delays.

Public results expose only approved placement information such as class identity, place, and rider display name.

### Private-by-default data

The public layer must not expose:

- rider/guardian contact information;
- private rider notes;
- horse medical/Coggins/internal notes;
- finance data;
- committee/admin records;
- points-rider strategy;
- entry notes/internal strategy;
- private operational documents/files.

### Stable live URL

`/public/<site-slug>/live/` is a stable season-long spectator entry point. It resolves to a currently active published show and otherwise falls back to the public schedule. This lets organizations reuse one QR code/link without weakening the publication boundary.

## Show Day lifecycle and ring model

Show-level lifecycle is persisted on `Show.status` (`planning`, `registration`, `entered`, `in_progress`, `paused`, `complete`, `cancelled`).

Class-level lifecycle is persisted separately in `ShowClassLiveState` so a class can be started, paused, resumed, and completed independently from the show itself.

Structured ring assignment lives in a companion model (`ShowClassRingAssignment`) rather than rewriting the legacy `ShowClass` schema. Multiple rings may run simultaneously, while a given ring may have only one active/paused class at a time.

Show Day row visibility is role-aware:

- full-team operational roles receive the complete show order;
- squad-scoped operational roles receive complete no-entry rows only where explicit Season Class metadata proves the class belongs to their squad;
- ordinary family/rider views can retain read-only class-order visibility without inheriting operational controls or hidden rider data.

## Result publication

Result publication has two layers for compatibility:

- legacy show-level `publish_results` remains the broad compatibility gate;
- live-managed classes use `ShowClassLiveState.results_published` as the class-level publication decision.

Completing a class does not automatically publish results. Publication remains explicit and reversible.

## Presentation boundary

Shared presentation belongs in static stylesheets and common components rather than template-local style blocks.

v3.1 adds layered presentation files for Show Day and the public spectator experience. These layers are intentionally presentation-only so responsive/mobile polish can evolve without changing workflow or permission logic.

At tablet/mobile widths, Show Day converts the wide class board into stacked class cards while preserving the same actions and permissions.

## Compatibility rule

Compatibility layers are deliberate and should be removed only when their callers are known and covered by tests. Examples include:

- `portal.views` re-exporting domain views;
- nullable catalog links on historical `SeasonClass`/`ShowClass` rows;
- organization helpers wrapping the persisted `Team` tenant model;
- legacy scoring heuristics used only when no catalog metadata is available;
- the legacy single `PublicShowPublication.current_class` pointer retained while multi-ring public state is derived from class lifecycle records.

A cleanup should reduce duplicate behavior without rewriting historical records or breaking old URLs.

## Development rules

- Keep generic platform behavior separate from IEA-specific rules.
- Preserve explicit public publication boundaries.
- Prefer domain services/helpers over adding more behavior to monolithic modules.
- Preserve historical data and stable URLs during refactors.
- Do not combine rulebook/scoring changes with unrelated UI rewrites.
- Add or expand regression tests before removing compatibility behavior.
- Run migrations and validation on staging before production promotion.
