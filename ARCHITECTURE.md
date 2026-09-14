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

## Compatibility rule

Compatibility layers are deliberate and should be removed only when their callers are known and covered by tests. Examples include:

- `portal.views` re-exporting domain views;
- nullable catalog links on historical `SeasonClass` and `ShowClass` rows;
- organization helpers wrapping the persisted `Team` tenant model;
- legacy scoring heuristics used only when no catalog metadata is available.

A cleanup should reduce duplicate behavior without rewriting historical records or breaking old URLs.

## Presentation boundary

Shared presentation belongs in static stylesheets and common components rather than template-local `<style>` blocks. ArenaLine surfaces should use the established theme variables and typography so light/dark mode and organization branding remain consistent.

The calendar is the first v3 cleanup target following this rule; month, agenda, filter, and mobile behavior remain intact while presentation moves into the Operations stylesheet.

## Public-facing boundary

Nothing becomes public merely because it exists inside ArenaLine.

Future public pages must use an explicit publication/allow-list model. Public routes should expose only fields intentionally approved for spectators or external audiences and must not reuse authenticated internal views as a shortcut.

Public-facing work should be built as a separate presentation and access boundary on top of stable competition data, not by weakening internal permissions.

## Development rules

- Keep generic platform behavior separate from IEA-specific rules.
- Prefer domain services/helpers over adding more behavior to monolithic modules.
- Preserve historical data and stable URLs during refactors.
- Do not combine rulebook/scoring changes with unrelated UI rewrites.
- Add or expand regression tests before removing compatibility behavior.
- Run v3 migrations and validation on staging before production promotion.
