# ArenaLine Changelog

This is the canonical concise release history for ArenaLine. Detailed implementation and validation notes for substantial releases live under `docs/releases/`.

Older detailed release notes that predate this changelog remain available in `RELEASE_NOTES.md` and are preserved as historical documentation.

## v3.1.0 — Public / Live Spectator Experience

Released September 2026.

Highlights:

- explicit public organization/show publication controls and allow-listed anonymous payloads;
- public program/show pages, schedules, live status, and class-level results;
- stable reusable public live URL;
- show/class lifecycle controls and structured multi-ring operation;
- spectator-safe announcements and ring delays;
- responsive authenticated Show Day and polished public spectator presentation;
- privacy-safe family/squad visibility behavior.

Migrations: `0057` through `0065`.

Validation: clean Django system/migration checks and **486 portal tests passing**.

Detailed notes: `docs/releases/v3.1.0.md`.

## v3.0.0 — IEA Class Catalog & Competition Foundation

Released 2026.

Highlights:

- versioned official IEA Hunt Seat, Western, and Dressage class catalog;
- catalog-linked season/show classes;
- show-only warm-ups and Hunt Seat VOC;
- catalog-driven scoring eligibility;
- architecture/presentation cleanup ahead of public work.

Validation: **425 portal tests passing** before production promotion.

Detailed notes: `docs/releases/v3.0.0.md`.

## Earlier releases

The 2.x release history, including Horse/Hoofprint, Show Host Operations, finance, communications, and the ArenaLine platform transition, is retained in `RELEASE_NOTES.md` and related documents under `docs/`.

## Changelog rule

Every stable production release must add or update its entry here before promotion to `main`. The changelog should remain concise and user-facing; detailed engineering notes belong in the version-specific release document.
