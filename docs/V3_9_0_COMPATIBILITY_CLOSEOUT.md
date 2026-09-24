# ArenaLine v3.9.0 — Preview 8 Compatibility Closeout

Preview 8 audits the remaining legacy human-identity dependencies after Person-native creation and participation became authoritative.

## Closeout rule

A remaining reference to `Rider`, `GuardianContact`, `RiderGuardian`, or `LegacyPersonLink` is not automatically removed. Each dependency is classified before code changes:

- **Compatibility required** — historical records, deterministic migration bridges, or old architecture still needed to preserve data.
- **Adapt/redirect** — a legacy route or API may remain, but normal reads/writes must resolve through Person-native state.
- **Remove from active path** — the legacy dependency is no longer needed by normal product behavior and can be retired with regression coverage.

No destructive model removal happens until active consumers and historical-data requirements are proven clear.

## Initial inventory

### Canonical migration bridges — compatibility required

`portal/people_compat.py` and `LegacyPersonLink` remain the deterministic bridge between pre-v3.9 Rider/Guardian records and Person. They are still required for migration/backfill, historical compatibility, and records that predate Person-native participation. These are not removal targets in the first closeout slice.

### IEA and competition records — compatibility required, Person-native authoritative

`SeasonMembership`, `ShowEntry`, `ShowAvailability`, and `ShowDayRiderStatus` retain nullable legacy Rider references while their active v3.9 paths use `IEAParticipant`/Person. The Rider columns remain compatibility data until a later schema-removal decision is supported by a complete data audit.

### Generic participation records — compatibility required, Person-native authoritative

Event RSVP, development notes, awards, and volunteer logs retain legacy Rider references for historical compatibility. Their active v3.9 behavior is Person-native. Do not remove the columns merely because current UI no longer writes them.

### Legacy lesson stack — compatibility required

`LessonGroup.riders` and legacy `LessonAttendance.rider` belong to the pre-v3.4 lesson architecture. The modern Lesson Program stack is Person-native. Preview 8 should isolate the old stack rather than migrate it into a duplicate modern implementation.

### Roster and family UI — adapt/redirect

Legacy `rider_edit`, `rider_membership_edit`, `rider_guardian_edit`, legacy user-create Rider/Guardian routes, and RiderGuardian unlink behavior remain compatibility endpoints. Normal Rider Card actions already use Person-native profile, IEA participation, login, and PersonRelationship management. These endpoints are candidates for explicit compatibility redirects/adapters so stale bookmarks cannot create divergent legacy state.

### Legacy account forms — adapt/retire from normal UI

`forms_legacy.py` still exposes Rider/Guardian choices in legacy user creation/editing. Person-native login creation is authoritative. Preview 8 must verify which routes still instantiate those forms before changing them.

### Financial references — audit before change

Legacy financial transaction Rider references remain in the model. Financial responsibility in ArenaLine is explicitly represented through Person-native receivable-account relationships and must never be inferred from Rider or family relationships. These legacy transaction references require a separate historical/reporting audit before removal.

## Preview 8 sequence

1. Lock this inventory and add regression coverage around compatibility boundaries.
2. Redirect/adapt stale Rider profile, season, guardian, and account-management write routes to Person-native equivalents where deterministic bridges exist.
3. Audit legacy user forms and remove Rider/Guardian identity selection from normal account workflows.
4. Isolate legacy lesson-stack consumers and prove modern lesson paths do not depend on Rider identity.
5. Audit historical/reporting/finance consumers before considering any schema removal.
6. Run migration-readiness and full regression suites.
7. Only then decide whether any legacy columns/models can be removed in v3.9.0 or must remain deprecated compatibility storage for a later release.
