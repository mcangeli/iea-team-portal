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

`portal/views.py` remains a compatibility namespace so existing URL configuration and imports continue to work while implementations live in smaller domain modules.

Important v3.1 domains include:

| Module | Responsibility |
| --- | --- |
| `dashboards.py` | Role-aware dashboard entry points |
| `roster.py` | Team roster, riders, parents/guardians, season membership/classes |
| `competitions.py` | Shows, show classes, entries, and result editing |
| `show_day.py` | Authenticated Show Day operations and family/team show-day views |
| `show_day_live.py` | Show-level live lifecycle control |
| `show_class_live.py` | Per-class lifecycle, ring assignment, result publication |
| `spectator_updates.py` | Public-safe show-day announcements and ring delays |
| `public_site.py` | Anonymous public program/show views and stable live resolver |
| `scoring.py` | Standings, qualification, scoring configuration, points-rider operations |
| `show_planning.py` | Show planning, Show Lead assignments, planning items |
| `history.py` | Season archive/review, historical import/corrections, awards, Record Book |
| `finance_*` | Restricted finance domains and reporting |

Most domains also have matching helper modules containing private logic used only by that domain.

## IEA competition boundary

IEA rulebook reference data and rule-specific behavior live under the competition boundary rather than on generic platform models whenever practical.

The v3 competition chain is:

```text
Official IEA rulebook
        ↓
IEAClassCatalogEntry
        ↓
SeasonClass
        ↓
ShowClass
        ↓
ShowEntry / ShowResult
        ↓
Scoring / qualification
```

Official show-only offerings such as warm-ups and VOC may link directly from catalog data to `ShowClass` without creating `SeasonClass` rows.

Catalog metadata is authoritative for scoring eligibility where available. Legacy code/name heuristics remain only as compatibility fallbacks for historical rows that are not linked to catalog data.

## Live Show Day model

v3.1 adds explicit show-day state without rewriting the legacy `ShowClass` model.

Companion models under `portal/model_modules/show_day_state.py` provide:

- `ShowClassLiveState` — Not started / In progress / Paused / Complete plus result publication state;
- `ShowClassRingAssignment` — structured ring assignment while preserving old schedule-note data;
- `SpectatorShowUpdate` — public-safe announcements, breaks, schedule notices, and ring delays.

The design intentionally supports multiple simultaneous active classes as long as they are in different rings. A ring may have only one active/paused class at a time.

Show-level lifecycle remains on `Show.status`. Completing a class does not complete the show. Pausing a class does not pause the entire show.

## Public publication boundary

Nothing becomes public merely because it exists inside ArenaLine.

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
