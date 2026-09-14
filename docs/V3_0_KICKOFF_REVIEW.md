# ArenaLine 3.0 Kickoff Review

This note captures architectural and cleanup items deferred from the v2.9 ArenaLine transition and records their v3.0 disposition.

## 1. IEA Rulebook & Class Catalog Foundation — Complete

ArenaLine now has versioned official IEA competition reference data for Hunt Seat, Dressage, and Western.

The catalog is versioned by rulebook/competition season so historical seasons retain the definitions that applied when they were created.

Implemented catalog metadata includes:

- discipline;
- class code / number;
- official class name;
- team level / eligibility grouping;
- ability and class family;
- individual-points applicability;
- team-points applicability;
- season-assignable status;
- active status;
- rulebook season/version;
- source rule / revision metadata;
- display/sort order.

`SeasonClass` remains the organization-specific season record. Normal Show Setup selects from valid season classes, while official show-only offerings such as warm-ups and VOC link directly from `ShowClass` to the catalog so they do not pollute rider season assignments.

Catalog scoring metadata is now authoritative where available. H8/H14, W8/W14, D8/D14, official warm-ups, VOC, and future catalog classes use `individual_points_enabled` and `team_points_enabled` rather than accumulating new code-specific exclusions. Historical unlinked rows retain narrowly scoped compatibility fallbacks.

The catalog and associated rule logic remain inside the `competition_iea` boundary rather than ArenaLine core.

## 2. Legacy Presentation Cleanup — Active / Near Complete

The first known presentation target, `templates/portal/calendar_v2.html`, no longer owns a substantial inline `<style>` block. Calendar month, agenda, filter, responsive, and mobile-switch behavior remain in the template while presentation rules now live in the shared Operations stylesheet.

Cleanup principles for the remaining sweep:

1. remove template-local presentation only where behavior remains unchanged;
2. use established ArenaLine surface, control, typography, and theme variables;
3. preserve light/dark behavior and organization branding;
4. avoid visual rewrites inside business-rule changes;
5. keep domain-specific IEA terminology where it is genuinely part of the competition workflow.

## 3. Architecture Housekeeping — Complete for v3.0 foundation

The view layer remains modularized by functional domain under `portal/view_modules/`, with `portal/views.py` retained as a compatibility namespace.

Additional v3 competition services now keep rulebook-specific concerns out of generic views and models where practical, including:

- season catalog configuration and generation;
- deterministic legacy class reconciliation;
- VOC ranking/eligibility;
- catalog-driven scoring policy;
- show-only IEA catalog behavior.

No broad rewrite of the persisted `Team` tenant model or public URL namespace is planned as part of v3.0 cleanup. Those compatibility layers are intentionally preserved while the product evolves around the organization service boundary.

## 4. Public-facing work — Next phase

Public pages begin only after the cleanup/regression pass is green.

The public architecture must follow these rules:

- nothing is public merely because it exists inside ArenaLine;
- publication is explicit and allow-listed;
- authenticated internal views are never reused by weakening permissions;
- spectator-facing presentation is a separate access boundary;
- rider/team/show information is exposed only when deliberately approved for publication;
- internal financial, family, contact, volunteer, administrative, and private rider data remains private by default.

The first public-facing implementation should therefore establish publication settings and public route/view boundaries before expanding into richer live or spectator experiences.

## Guardrail

All v3.0 migration, catalog, scoring, cleanup, and public-boundary work is validated on staging before production promotion. Historical records must remain intact throughout compatibility cleanup.
