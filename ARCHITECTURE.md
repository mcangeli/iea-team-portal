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
| `horses.py` | Horse registry, identifiers/relationships, Coggins, season/show assignments, Horse of the Day |
| `equine_care.py` | Care entry/editing and completed-care history |
| `equine_documents.py` | Protected generic horse-document management/downloads |
| `equine_compliance.py` | Organization compliance-requirement management |
| `hoofprint.py` | IEA Hoofprint workflow and finalized snapshots |

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
- horse care/compliance documents;
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

## v3.2 identity and organization direction

v3.2 introduces a compatibility-first People foundation for broader barn operations.

The target model separates four concepts that older portal structures sometimes conflated:

1. **Person identity** — the human being.
2. **Relationships / participation** — parent/guardian/dependent links, rider participation, boarding, leasing, staff/trainer relationships, and other domain relationships.
3. **Authorization** — what the signed-in account is allowed to view or change.
4. **Public identity** — the explicitly published subset of profile information suitable for anonymous/public presentation.

The intended direction is:

```text
User account (optional login)
        ↓
Person
 ├── person-to-person relationships
 ├── organization role assignments
 ├── group/program memberships
 ├── committee memberships/positions
 ├── rider/barn participation
 └── public profile publication (optional)
```

A single Person may hold multiple simultaneous roles (for example adult rider + parent + boarder + committee member + assistant trainer). Role labels must not automatically become permissions.

### Groups / Programs

ArenaLine supports generic organization groups/programs as scopes for functions such as IEA, Lesson Program, Boarding, Staff, Shows, or future disciplines/programs. The persisted model remains flexible enough to support parent/subgroup relationships while the normal UI avoids unnecessary hierarchy.

### Committees

Committees are generic organization structures rather than IEA-only responsibilities. A committee may be organization-wide or optionally scoped to a Group/Program. Committee membership/position is distinct from login authorization.

Assignment-specific responsibilities such as a Show Lead for one event remain event/domain assignments rather than being forced into a committee model.

### Public person/rider profiles

Public rider/person cards follow the v3.1 publication model. The internal Person/Profile object is never serialized directly to anonymous users. Each public field is allow-listed and deliberately published, with especially conservative handling for minors. Exact date of birth and private contact information remain private by default.

## v3.3 equine care and compliance boundary

v3.3 keeps `Horse` as the durable generic equine identity and layers operational records around it rather than expanding the Horse row into a mutable snapshot of current care state.

The core shape is:

```text
Horse
 ├── HorseIdentifier
 ├── HorsePersonRelationship → Person
 ├── HorseCareRecord
 │    ├── care type
 │    ├── provider → Person
 │    ├── performed date
 │    └── next due date
 ├── HorseDocument
 ├── HorseCogginsRecord
 ├── HorseSeasonProfile
 ├── HorseShowAssignment
 └── HorseShowAward / historical activity
```

The design principle is **Horse describes the horse; records describe what happened**. Completed care and historical show records are preserved instead of overwritten by current status.

### Care scheduling

`HorseCareRecord` is generic operational recordkeeping, not diagnosis. The latest record for each care category drives schedule status when it has a next-due date; older records remain immutable history for operational review. Coggins remains a specialized record and is not duplicated as a generic care type.

### Documents and compliance

`HorseDocument` stores generic supporting records with optional effective/expiration dates and optional linkage to a care record. `HorseComplianceRequirement` configures which Coggins/document categories an organization actually requires.

Compliance is evaluated in two contexts:

- registry/profile context defaults to the current date;
- show/Hoofprint context evaluates through `Show.show_date`.

A record that expires before the evaluation date is blocking. Expiration on the evaluation date is valid. Expiring-soon status warns without blocking when the record remains valid through the evaluation date.

Coggins remains the specialized source of truth where a Coggins requirement is configured.

### Horse-document privacy

Generic horse documents and Coggins attachments are not linked directly through their storage URLs in authenticated UI. Manager-only, organization-scoped Django download views enforce authorization and return `private, no-store` responses. Deployment must likewise avoid exposing sensitive media paths through a bypassing public media alias.

Detailed care, document, and configurable compliance information is manager-only. Narrower historical Coggins visibility on established IEA show surfaces remains a compatibility decision and does not grant access to the underlying private documents.

### IEA bridge

Generic equine compliance feeds the existing IEA Show Readiness and Hoofprint workflows without moving IEA-specific terminology or Hoofprint rules into the generic Horse models. Missing/expired/not-valid-through-show configured requirements block show readiness and Hoofprint finalization; ordinary Hoofprint completeness warnings remain advisory.

## Presentation boundary

Shared presentation belongs in static stylesheets and common components rather than template-local style blocks.

`docs/PRODUCT_AND_UI_GUIDE.md` is the standing presentation/product guide for all new or materially redesigned pages. New work must continue the established ArenaLine premium equestrian visual language and reuse shared theme variables/components wherever practical.

Presentation review is part of feature completion:

- desktop, tablet, and mobile behavior are intentional;
- authenticated light/dark modes remain coherent;
- touch targets and form controls are usable on barn/ringside devices;
- empty/no-data/error states are designed, not accidental;
- UI visibility never substitutes for server-side authorization.

v3.1 adds layered presentation files for Show Day and the public spectator experience. These layers are intentionally presentation-only so responsive/mobile polish can evolve without changing workflow or permission logic.

## Compatibility rule

Compatibility layers are deliberate and should be removed only when their callers are known and covered by tests. Examples include:

- `portal.views` re-exporting domain views;
- nullable catalog links on historical `SeasonClass`/`ShowClass` rows;
- organization helpers wrapping the persisted `Team` tenant model;
- legacy scoring heuristics used only when no catalog metadata is available;
- the legacy single `PublicShowPublication.current_class` pointer retained while multi-ring public state is derived from class lifecycle records;
- v3.2 Person/relationship abstractions coexisting with Rider, Guardian/Parent, UserProfile, SeasonMembership, committee, finance, and competition structures until migration is proven safe;
- v3.3 equine-care/document/compliance records coexisting with existing Horse, Coggins, season eligibility, show assignment, Hoofprint, award, and historical structures.

A cleanup should reduce duplicate behavior without rewriting historical records or breaking old URLs.

## Development rules

- Keep generic platform behavior separate from IEA-specific rules.
- Preserve explicit public publication boundaries.
- Follow `docs/PRODUCT_AND_UI_GUIDE.md` for every new/materially redesigned page.
- Prefer domain services/helpers over adding more behavior to monolithic modules.
- Preserve historical data and stable URLs during refactors.
- Separate organizational roles/relationships from authorization decisions.
- Keep horse identity separate from historical care/activity records.
- Protect sensitive horse documents at both application and deployment boundaries.
- Do not combine rulebook/scoring changes with unrelated UI rewrites.
- Add or expand regression tests before removing compatibility behavior.
- Update README, roadmap, changelog, architecture, and release docs as the product changes.
- Run migrations and validation on staging before production promotion.
