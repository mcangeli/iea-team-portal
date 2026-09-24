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


## Preview 8 progress

### Family and account compatibility — closed

Legacy Rider/Guardian profile, season, family-edit, family-unlink, and login-creation entry points now adapt or redirect into canonical Person-native workflows. Person-linked account editing no longer rewires legacy Rider/Guardian identity. RiderGuardian remains compatibility storage only; normal family management is authoritative through PersonRelationship.

### Action items — Person-native authoritative

ActionItem now has a canonical nullable Person participant with the legacy Rider field retained for historical compatibility. Migration 0126 backfills Person deterministically through LegacyPersonLink. Normal ActionItem forms select Person, and family visibility resolves through canonical Person parent/guardian relationships first with Rider visibility retained only for legacy rows.

### Legacy lesson stack — isolated compatibility architecture

The active legacy routes `lesson_list`, `lesson_group_*`, `lesson_*`, and `lesson_attendance_edit` still operate on the pre-v3.4 `LessonGroup`, `Lesson`, and `LessonAttendance` models and therefore retain Rider identity. They are not the canonical lesson architecture and must not be extended for new Person-native behavior.

The v3.4 Lesson Program architecture is canonical for new lesson operations: `LessonProgram`, `LessonSeries`, `LessonEnrollment`, `LessonOccurrence`, `IEALessonOccurrenceParticipant`, `LessonAttendanceRecord`, and `LessonAssignment` are Person-native. IEA lesson screens may still display legacy lessons for historical continuity, but new architecture and new identity work belongs only in the Lesson Program stack.

For v3.9.0 the legacy lesson schema remains intact to preserve historical records and existing compatibility URLs. Physical migration or deletion of `LessonGroup.riders` / `LessonAttendance.rider` is explicitly deferred until those old records and URLs can be retired without duplicating the modern lesson system.

### Finance Rider reference — historical attribution, not financial identity

The v3.7 finance architecture already provides the canonical Person-native financial relationship model through `ReceivableAccount` and `ReceivableAccountPerson`. Those links distinguish `PARTICIPANT`, `RESPONSIBLE_PARTY`, and `BILLING_CONTACT`, and `resolve_participant_account()` intentionally resolves only an explicit active PARTICIPANT link. It does not infer an account from `primary_person`, a responsible party, a billing contact, family relationships, Rider, or any other participation record.

`FinancialTransaction.rider` is therefore not the canonical financial identity or responsibility mechanism. In the legacy general-ledger transaction UI it is optional attribution metadata used for transaction filtering, search, CSV export, and reversal preservation. Existing v3.7 receivable/payable workflows use their own explicit account/party models and may link their generated ledger transaction separately.

For v3.9.0, `FinancialTransaction.rider` remains deprecated compatibility/historical attribution storage. It must not be used to infer who owes money, who receives a statement, who is financially responsible, or which receivable account should be charged. Replacing this field with a new Person field inside v3.9.0 would add another attribution concept without improving the explicit finance architecture and would create unnecessary ledger migration risk.

A future ledger-normalization release may replace the optional Rider attribution with a deliberately designed Person/account attribution after reporting, export, reversal, and historical-ledger requirements are specified. That work is outside the People identity migration.

### Preview 8 substantive audit status

The family/account adapters, generic ActionItem migration, legacy lesson isolation, and finance Rider-reference audit are complete. Remaining closeout work is migration/readiness verification, focused compatibility regression, full-suite regression, and final v3.9.0 documentation/release preparation.
