# ArenaLine Product, Branding & Documentation Guide

This document is a standing product-development guardrail for ArenaLine. It applies to every feature branch and release.

## Product direction

ArenaLine is a private, self-hosted equestrian operations platform with discipline-specific competition modules. New work should strengthen the generic barn/program platform while preserving first-class IEA competition workflows.

## Presentation and branding

Every new or materially redesigned ArenaLine page must follow the established ArenaLine visual language rather than introducing an isolated page style.

Core direction:

- premium equestrian presentation;
- deep navy, hunter green, warm gold, cream/warm neutral surfaces;
- elegant serif display typography paired with a clean sans-serif UI typeface;
- restrained decorative/script accents only where they improve hierarchy;
- refined horse/equestrian line-art and arena-line motifs;
- deliberate spacing, strong section hierarchy, and polished card/table states;
- light and dark modes where the authenticated application supports them;
- tablet/mobile behavior designed intentionally rather than treated as an afterthought;
- accessible contrast, touch targets, focus states, and readable form controls.

### Reuse before invention

New pages should reuse established ArenaLine components, theme variables, typography, buttons, forms, cards, tables, status treatments, page intros, empty states, navigation patterns, and responsive conventions whenever practical.

Shared presentation belongs in static stylesheets/common components. Avoid page-local style blocks unless there is a narrowly justified compatibility need.

### Role and privacy awareness

Presentation must reflect authorization rather than merely hiding controls cosmetically. A user may have multiple organizational roles, relationships, and memberships, but visible data and available actions must still come from explicit permissions and scope checks.

### Public-facing pages

Public experiences follow the v3.1 publication boundary:

- nothing becomes public merely because it exists internally;
- fields are explicitly allow-listed;
- publication is deliberate and reversible;
- youth/minor information requires especially conservative defaults;
- public rider/person cards must use a dedicated public payload rather than exposing the internal Person/Profile model directly.

## Documentation contract

Documentation is part of the feature, not a post-release cleanup task.

### `README.md`

The README is the practical entry point. It should contain:

- what ArenaLine is;
- current stable version;
- high-level feature/workflow overview;
- installation requirements and setup;
- upgrade/update instructions;
- operational/troubleshooting basics;
- links to roadmap, architecture, changelog, and detailed release documentation.

The README should not become the canonical roadmap or a full historical changelog.

### `ROADMAP.md`

`ROADMAP.md` is the canonical product roadmap. It records:

- released milestones;
- the active release family;
- committed near-term releases;
- directional longer-term work.

Roadmap decisions should be updated when they are made, not after implementation is finished.

### `CHANGELOG.md`

`CHANGELOG.md` is the canonical concise top-level release history. Each stable production release should receive an entry describing user-visible changes, migration range, validation status, and a link to the detailed release document where one exists.

### `RELEASE_NOTES.md`

`RELEASE_NOTES.md` remains the retained detailed historical release record for older releases that predate the canonical changelog. Do not duplicate the entire historical file into the README or changelog.

### `docs/releases/<version>.md`

Each substantial release should have a focused release document containing implementation detail, migration lists, validation notes, operational changes, and upgrade considerations.

### `ARCHITECTURE.md`

Update architecture documentation whenever a release changes domain boundaries, ownership, permission/publication models, identity/relationship structures, data flow, or compatibility strategy.

### Release checklist

No release is complete until code, tests, presentation, version identity, README, roadmap, changelog, architecture, and applicable release documents agree with one another.

## Development checklist for new pages/features

Before considering a page or workflow complete, confirm:

1. It uses established ArenaLine branding and component patterns.
2. Desktop, tablet, and mobile behavior have been considered.
3. Dark/light presentation is correct where applicable.
4. Role, relationship, tenant, and privacy boundaries are enforced server-side.
5. Public exposure uses explicit publication/allow-list services.
6. Empty, loading/error, and no-data states are intentional.
7. Tests cover critical authorization and regression behavior.
8. README/roadmap/changelog/architecture/release docs are updated as appropriate.

These requirements are release gates, not optional polish.
