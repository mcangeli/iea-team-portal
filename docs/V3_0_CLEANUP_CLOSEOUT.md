# ArenaLine v3.0 Competition Foundation & Cleanup Closeout

This document closes the ArenaLine v3.0 private-portal foundation work before public/external development begins.

## Status

The v3.0 competition foundation is functionally complete on the staging branch `feature/v3.0.0-iea-class-catalog`.

The current regression baseline is **425 portal tests passing** after the catalog, show-only class, VOC, catalog-driven scoring, and presentation-cleanup work.

Production remains on the stable v2.9 release until the v3 line is intentionally prepared for release.

## Competition foundation completed

ArenaLine now has a versioned IEA competition reference layer for the 2026-2027 rulebook season covering Hunt Seat, Western, and Dressage.

The implemented data flow is:

`IEAClassCatalogEntry -> SeasonClass -> rider season assignments -> ShowClass -> entries/results -> scoring/qualification`

Official show-only classes use a direct catalog relationship instead of creating fake `SeasonClass` rows:

`IEAClassCatalogEntry -> ShowClass -> entries/results`

Completed competition work includes:

- official 42-class youth placement catalog for Hunt Seat, Western, and Dressage;
- season/catalog configuration and catalog-backed Season Setup;
- deterministic reconciliation of compatible legacy season classes;
- catalog-aware season class create/edit/link/sync workflows;
- catalog-aware Show Setup;
- official show-only warm-ups for all three disciplines;
- Hunt Seat VOC as a separate show-only championship workflow;
- warm-up prerequisite and team-level validation;
- same-show VOC eligibility/ranking validation;
- no-points enforcement for warm-ups and VOC;
- catalog-driven `individual_points_enabled` and `team_points_enabled` scoring policy;
- catalog-driven point-rider and postseason Team-track restrictions;
- legacy H8/H14 recognition retained only as a compatibility fallback for unlinked historical rows;
- reconciliation of stale catalog-linked non-team-scoring entry state.

## Architecture boundary

ArenaLine platform concerns remain separate from IEA competition concerns.

Generic platform modules remain:

- `core`
- `people`
- `horses`
- `operations`
- `finance`
- `communications`

IEA rulebook/class/scoring behavior remains owned by `competition_iea`.

The persisted `Team` tenant model remains in place for compatibility; organization-facing service boundaries continue to provide the generic platform abstraction.

No destructive schema rename was performed merely to make internal naming more generic.

## Presentation cleanup completed

The known v2.9 presentation debt in `templates/portal/calendar_v2.html` has been removed.

Calendar layout/presentation now lives in the shared Operations stylesheet instead of a template-local `<style>` block. The cleanup preserved:

- Month view;
- Agenda view;
- event filters;
- previous/next/today navigation;
- mobile agenda switching;
- responsive behavior;
- light/dark ArenaLine presentation.

The v2.9 regression that intentionally required the old inline-style workaround was updated to assert the v3 contract instead.

No additional obvious template-local `<style>` debt was identified in the cleanup sweep that justified risky churn before public-page work.

## Intentionally deferred

The following are not blockers for beginning the public/external work:

- broad renaming of legacy internal models;
- broad rewrites of the compatibility `portal.views` namespace;
- speculative qualification/postseason rule changes not yet tied to verified current rulebook requirements;
- judge-card data needed to resolve the final VOC tie-break beyond combined H1/H2 points and H1 placing;
- further stylesheet filename renaming solely to remove historical `v290` names.

These should be changed only when a concrete feature or maintenance need justifies them.

## Public-facing entry criteria

Public work can now begin, but the private/public boundary remains a release gate.

The first public-facing slice should establish the publication model before designing spectator pages.

Required principles:

1. **Nothing becomes public merely because it exists in ArenaLine.**
2. Public data is selected through an explicit allow-list.
3. Private rider, parent/guardian, horse, finance, contact, internal notes, planning, and operational data remain private by default.
4. Public routes use a dedicated public view/query boundary rather than reusing authenticated templates with permissions removed.
5. Unpublishing removes the external view without deleting internal history.
6. Public URLs must use stable external identifiers/slugs rather than exposing assumptions about private navigation.
7. Publication state and important publication changes should be auditable.
8. Public-page tests must include anonymous-access, unpublished-object, cross-organization, and private-field-leak regressions.

## Recommended next sequence

1. Define publication models/settings and explicit field allow-lists.
2. Establish dedicated anonymous public routes and query services.
3. Add public organization/team landing identity.
4. Add intentionally published show landing pages.
5. Add published schedules/results only after publication controls are proven.
6. Add mobile spectator/live experiences after the static publication model is reliable.

This sequencing keeps ArenaLine private-by-default while allowing the public experience to grow deliberately on top of the now-stable v3 competition foundation.
