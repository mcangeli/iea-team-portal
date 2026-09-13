# ArenaLine v2.9 Module Boundaries

Preview 2C establishes stable product-domain boundaries without changing the current database tenancy model. `Team` remains the tenant boundary in v2.9; the application presentation and future extension points begin using broader ArenaLine concepts.

## Platform domains

These domains are intended to work across IEA programs, lesson barns, show barns, and future ArenaLine organizations:

- `core` — organization context, dashboards, configuration, permissions, shared application services
- `people` — riders, parents/guardians, households, users, staff, relationships
- `horses` — horse registry, season profiles, documents, health/care expansion points
- `operations` — calendar, tasks, lessons, volunteers, committees, day-to-day coordination
- `finance` — organizational finance, billing, payments, reimbursements, reporting
- `communications` — notifications and future announcements/messaging/publication workflows

## Competition specialization

`competition_iea` is intentionally separate from the platform domains. It owns IEA-specific concepts such as:

- Futures / Upper competition structure
- IEA class identifiers and eligibility
- points riders and IEA team-point behavior
- IEA qualification rules
- Hoofprint workflows
- IEA-specific season standings and historical competition records

Generic competition concepts such as shows, venues, entries, classes, results, schedules, horses, and documents should gradually move toward a shared ArenaLine competition engine. Future disciplines and governing bodies can then attach their own rule modules without changing the platform core.

## v2.9 rules

1. Do not rename the `Team` model or database tables in v2.9.
2. Do not add new platform code that assumes every ArenaLine organization is an IEA team.
3. Prefer `organization` in generic administrative/product language; keep `team` where the concept is genuinely team-specific.
4. Keep IEA terminology inside IEA competition workflows and content.
5. Use stable module IDs in UI and context so a later organization-level module configuration can enable or disable capabilities without another navigation redesign.
6. Current v2.9 behavior keeps all existing modules enabled by default. Module configuration is a later feature, not part of this preview.

## Current module IDs

- `core`
- `people`
- `horses`
- `competition_iea`
- `operations`
- `finance`
- `communications`

These IDs are application contracts for future module enablement and should not be casually renamed.
