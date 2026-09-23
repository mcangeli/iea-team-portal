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

`portal/views.py` remains a compatibility namespace so existing URL configuration/imports continue to work while implementations live in smaller domain modules. v3.4 lesson-program views use dedicated modules for program/series/occurrence, lesson-day operations, and rider My Lessons surfaces while legacy lesson views remain available during compatibility.

## IEA competition boundary

IEA rulebook reference data and rule-specific behavior live under the competition boundary rather than on generic platform models whenever practical.

The v3 competition chain is:

```text
Official IEA rulebook
        ↓
IEAClassCatalogEntry
        ↓
SeasonClass
        ↓
ShowClass
        ↓
ShowEntry / ShowResult
        ↓
Scoring / qualification
```

Official show-only offerings may link directly from catalog to ShowClass. Catalog metadata remains authoritative for scoring eligibility where available, while legacy heuristics are compatibility fallbacks only.

## Public-facing boundary

The v3.1 public layer uses explicit publication records and deliberately allow-listed payload builders. Anonymous routes do not reuse authenticated portal views.

Private-by-default data includes rider/guardian contact information, private notes, horse medical/Coggins/internal records, horse care/compliance documents, finance data, committee/admin records, points-rider strategy, internal entry notes, and private operational files.

## v3.2 identity and organization direction

The canonical People direction separates Person identity, relationships/participation, authorization, and public identity.

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

A single Person may hold multiple simultaneous roles. Role labels must not automatically become permissions.

## v3.3 equine care and compliance boundary

v3.3 keeps `Horse` as the durable generic equine identity and layers operational records around it rather than expanding the Horse row into a mutable snapshot of current care state.

```text
Horse
 ├── HorseIdentifier
 ├── HorsePersonRelationship → Person
 ├── HorseCareRecord
 ├── HorseDocument
 ├── HorseCogginsRecord
 ├── HorseSeasonProfile
 ├── HorseShowAssignment
 └── HorseShowAward / historical activity
```

The design principle is **Horse describes the horse; records describe what happened**. Completed care and historical show records are preserved instead of overwritten by current status.

Generic equine compliance feeds IEA Show Readiness and Hoofprint without moving IEA-specific terminology/rules into generic Horse models.

## v3.4 lesson-program boundary

v3.4 establishes a generic lesson architecture on top of canonical Person and Horse identity:

```text
LessonProgram
  └── LessonSeries
       ├── LessonEnrollment → Person
       └── LessonOccurrence
            ├── LessonAttendanceRecord → Person
            └── LessonAssignment → Person / Horse
```

The core rule is **programs describe the offering, series describe recurring instructional groups, occurrences describe the scheduled/historical lesson, enrollment describes normal membership, and attendance/assignments describe what happened in that occurrence.**

### Occurrence history and recurrence identity

`LessonOccurrence` is a durable operational snapshot. It stores title, instructor, location, capacity, start/end time, status, origin, and—when recurrence-generated—an immutable `scheduled_for` identity. Rescheduling changes the operational time without changing the original recurrence slot. Later edits to a parent series do not rewrite historical occurrences.

Generated, manual, and legacy-converted occurrences are explicitly distinguishable. Recurrence generation and roster preparation are idempotent.

### Barn lesson domain

Barn Lesson Programs use `LessonEnrollment` for normal series membership. Barn instructor eligibility comes from active canonical Trainer / Assistant Trainer role assignments. Administrators may manage the domain but are not automatically valid instructors merely because they are administrators.

### IEA Team Lesson specialization

IEA-specific lesson behavior is layered onto a generic `LessonSeries` through `IEALessonSeriesContext`, which supplies Season context. For new v3.6.2 scheduling, the series is an organizational container and may use mixed team context: `SeasonMembership` determines Futures/Upper eligibility, while `IEALessonOccurrenceParticipant` records who is actually scheduled for each occurrence. An explicit roster may intentionally be empty. Older occurrences retain the season/team fallback when no explicit roster has been configured. IEA instructor eligibility is Coach-specific.

This avoids a generic `lesson_type=IEA` switch and keeps IEA season/team behavior outside the generic lesson core.

### Attendance and assignments

Enrollment is not attendance. Attendance is occurrence-specific and unique per Person/Occurrence. `LessonAssignment` records operational participant or instructor assignment and may carry a canonical Horse for participant assignments. Instructor assignments cannot carry a Horse.

Lesson preparation can materialize expected participant attendance and instructor assignments without creating instructor attendance.

### Participant move / make-up boundary

`LessonParticipantMove` represents moving one Person from a source occurrence to a compatible destination occurrence. It is separate from whole-occurrence rescheduling.

The source occurrence retains history and the destination receives make-up participation. Barn moves remain inside the same Lesson Program; IEA moves remain inside the same Season/team level. Capacity, operational history, occurrence state, duplicate moves, and attendance conflicts are validated. Staff/rider initiation is retained for audit, and a rider may self-reschedule only their own eligible participation.

### Completion boundary

Occurrence completion is an operational state transition. Cancelled occurrences cannot be completed, and unresolved EXPECTED attendance blocks completion. Completion is idempotent. v3.4 does not invent a horse-assignment requirement for completion.

### Calendar projection

The unified Calendar is a projection, not an ownership model. Lesson occurrences remain owned by the lesson domain; calendar items route back to their owning record. Legacy IEA provenance prevents converted legacy lessons from appearing alongside their new occurrence as duplicates.

### Legacy compatibility

Existing `LessonGroup`, `Lesson`, and legacy `LessonAttendance` structures remain available. Legacy IEA conversion is deterministic/idempotent and stores explicit provenance while leaving original records unchanged. Compatibility removal requires a future explicit migration/cutover decision and regression coverage.

## v3.5 finance boundary

v3.5 establishes ArenaLine Finance as the generic operational-finance boundary. Lessons, boarding, horse care, shows, programs, and IEA workflows may supply operational facts through explicit services; they do not own parallel ledgers.

The receivables architecture is:

```text
ReceivableAccount
  ├── ReceivableCharge
  ├── ReceivableCredit
  ├── ReceivablePayment
  └── ReceivableAllocation
          ↓
     Balance / aging / reporting
```

General Barn and IEA finance are separate `FinanceDomain` values. Authorization is resolved through finance capabilities and domain-scoped services rather than template visibility or broad organizational roles. IEA-only finance authority must never expose General Barn finance.

Posted `FinancialTransaction` records drive realized income/expense and cash-activity reporting. Receivable records drive open-balance and aging reporting. These are related operational views but are not silently collapsed into one accounting concept.

Bank imports are staged external observations. Import profiles map CSV/XLSX columns into `ImportedBankTransaction` records; candidate matching does not reconcile automatically, confirmation is explicit, and completing a reviewed bank batch is an explicit user action. Reconciliation does not rewrite matched ledger transactions.

Accounting exports are read-only projections of authorized posted ledger activity. Configurable CSV/XLSX profiles support QuickBooks-friendly workflows, but external accounting/general-ledger systems remain outside ArenaLine's ownership boundary. ArenaLine does not treat an export as synchronization state.

Reporting remains domain-, organization-, date-, season-, and permission-scoped. An `as_of` receivable report excludes charges created after that date; historical balances still reflect the persisted allocation state rather than pretending ArenaLine has a separate historical general ledger.


## v3.6 dashboard and account-security boundary

v3.6 makes the navigation semantics explicit: the root Dashboard is the generic ArenaLine barn/program operational home, while My Team owns IEA team context and the specialized Coach, Team Parent, Points Secretary, Treasurer, Show Lead, and Show Manager workspaces. Organizational/admin authority may broaden what a user can see or switch into, but it does not change those surface meanings. IEA announcements remain team-domain content and are not projected onto the general Barn Dashboard.

Dashboard presentation uses separate Barn and IEA Team hero branding. The Barn hero is additive and falls back to the Team hero when unset; legacy Team-photo CSS must not override a configured Barn hero.

Account identity now distinguishes the active login email from a pending replacement email. Email replacement is completed only through an account-bound signed verification flow after current-password confirmation. Existing compatibility contact records are synchronized only after verification succeeds.

MFA is optional per account and uses TOTP plus hashed single-use recovery codes. Password authentication for an MFA-enabled account creates only a pending challenge; authenticated session state is established after the second factor succeeds. MFA secrets/recovery material belong to account security and are not Person/profile presentation data.

Mail delivery is deployment infrastructure rather than an ArenaLine domain. The default target is a local Postfix listener. Container deployments must explicitly provide a restricted route from the web container to the host MTA; loopback inside the container is not the host.

## v3.8 facility, resource, and inventory boundary

v3.8 adds a canonical physical-operations layer without creating a new owner for lesson, horse, calendar, show, inventory, or finance facts.

`Facility` is the organization-scoped physical site/property identity. `FacilitySpace` is a durable, nestable place within a Facility. Space capabilities determine whether a space may be reserved, used for stall housing, used for pasture/turnout, or used for inventory storage. Parent/child relationships remain inside the same organization and Facility and may not form cycles.

Horse housing and turnout are intentionally independent. `HorseStallAssignment` and `HorsePastureAssignment` are effective-dated relationships to capable Facility Spaces and preserve history. A horse may have both, only a pasture assignment, or temporarily neither; ArenaLine does not model a stall as owning or implying a pasture.

`ResourceReservation` reserves a reservable Facility Space for a time interval and retains source/provenance. The reservation layer protects shared physical capacity but does not become authoritative for the activity that uses it. Lesson occurrences remain lesson-domain records; reservation synchronization is a supporting service. The Calendar remains an aggregation/projection surface.

Existing free-text locations and external show venues remain valid compatibility/history surfaces. Canonical FacilitySpace links are additive and ambiguous historical strings are not automatically converted.

Inventory is a separate operational domain. `InventoryItem` and `InventoryStock` own item and quantity facts; stock is located in inventory-storage-capable Facility Spaces. `InventoryTransaction` preserves receive, use, adjustment, and transfer history. Facilities own the storage-place identity, while Finance/AP continues to own vendors, obligations, payments, and financial transactions. Inventory does not introduce a parallel ledger.

## Presentation boundary

Shared presentation belongs in static stylesheets and common components rather than template-local style blocks. `docs/PRODUCT_AND_UI_GUIDE.md` is the standing presentation/product guide.

Presentation review is part of feature completion: desktop/tablet/mobile behavior, authenticated light/dark modes, touch usability, designed empty/error states, and server-side authorization remain required.

## Compatibility rule

Compatibility layers are deliberate and should be removed only when their callers are known and covered by tests. Current examples include:

- `portal.views` re-exporting domain views;
- nullable catalog links on historical competition rows;
- organization helpers wrapping persisted `Team`;
- legacy scoring heuristics used only without catalog metadata;
- v3.2 Person abstractions coexisting with Rider/Guardian/UserProfile/SeasonMembership/finance/competition structures;
- v3.3 equine records coexisting with existing Horse/Coggins/show/Hoofprint/history structures;
- v3.4 generic Lesson Program records coexisting with legacy lesson records, with explicit provenance for converted IEA occurrences;
- v3.6.2 explicit IEA occurrence rosters coexisting with the older season/team roster fallback for historical occurrences.

A cleanup should reduce duplicate behavior without rewriting historical records or breaking stable URLs.

## Development rules

- Keep generic platform behavior separate from IEA-specific rules.
- Preserve explicit public publication boundaries.
- Follow `docs/PRODUCT_AND_UI_GUIDE.md` for every new/materially redesigned page.
- Prefer domain services/helpers over adding more behavior to monolithic modules.
- Preserve historical data and stable URLs during refactors.
- Separate organizational roles/relationships from authorization decisions.
- Keep horse identity separate from historical care/activity records.
- Keep lesson enrollment, occurrence, attendance, assignment, and billing concepts separate.
- Do not duplicate Finance logic inside Lessons.
- Protect sensitive horse documents at both application and deployment boundaries.
- Add or expand regression tests before removing compatibility behavior.
- Update README, roadmap, changelog, architecture, and release docs as the product changes.
- Run migrations and validation on staging before production promotion.
