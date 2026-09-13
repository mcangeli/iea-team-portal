# ArenaLine 3.0 Kickoff Review

This note captures architectural and cleanup items intentionally deferred from the v2.9 ArenaLine transition so they are reviewed before substantive 3.0 feature work begins.

## 1. IEA Rulebook & Class Catalog Foundation

Create versioned source/reference data for official IEA competition classes rather than requiring each organization administrator to type class definitions manually.

Initial scope should include the official class structure for:

- Hunt Seat
- Dressage
- Western

The catalog should be versioned by IEA rulebook / competition season so historical seasons retain the definitions that were valid when they were created.

A likely source model should capture at least:

- discipline;
- class code / number;
- official class name;
- division / level;
- applicable team level or eligibility grouping;
- individual/team applicability;
- whether the class counts toward team scoring;
- active status;
- rulebook season/version;
- display/sort order.

`SeasonClass` should remain the organization-specific season instance derived from the catalog. Show-class creation should then select from valid season classes instead of relying on free-form class entry.

This foundation should also be reviewed as the future home for rules that are currently represented in application logic, including exclusions such as H8/H14 from team scoring, where appropriate and supported by the applicable IEA rulebook.

The catalog belongs to the `competition_iea` module, not ArenaLine core, so future competition modules can provide their own catalogs independently.

## 2. Legacy Presentation Cleanup

Review the remaining template-local presentation from pre-ArenaLine UI generations and move reusable styling into the shared ArenaLine presentation layers.

The first known candidate is `templates/portal/calendar_v2.html`, which still contains a substantial inline `<style>` block. v2.9 Preview 4F intentionally uses scoped ArenaLine overrides in `static/css/operations-v290.css` rather than rewriting the calendar during a presentation-stability release.

At the beginning of 3.0:

1. inventory all remaining template-local `<style>` blocks;
2. identify rules that are obsolete after the v2.9 presentation layers;
3. move reusable calendar/operations rules into shared CSS;
4. remove duplicate/legacy rules only after visual and responsive regression checks;
5. preserve calendar month/agenda behavior and mobile switching while doing so.

## 3. Architecture Housekeeping Reminder

The first 3.x architecture pass should also revisit any deferred structural cleanup from v2.9 before large feature additions, including further modularization of oversized view modules where it materially improves ownership boundaries.

## Guardrail

These are kickoff review items, not automatic migrations. Confirm the current IEA rulebook/source data, historical-data implications, and regression baseline before implementing schema or domain changes.
