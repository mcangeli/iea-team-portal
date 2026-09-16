# ArenaLine v3.4.0 — Lesson Program Foundation

## Preview 1: architecture and data-model contract

v3.4.0 begins from the released v3.3.0 baseline and introduces a generic ArenaLine lesson-program architecture while preserving the existing `LessonGroup`, `Lesson`, and legacy `LessonAttendance` records until a later compatibility/backfill preview explicitly migrates them.

```text
LessonProgram
  └── LessonSeries
       ├── LessonEnrollment → Person
       └── LessonOccurrence
            ├── LessonAttendanceRecord → Person
            └── LessonAssignment → Person / Horse
```

The core rule is: **programs describe the offering, series describe recurring instructional groups, occurrences describe what actually happened, and attendance/assignments describe participation in that occurrence.**

`LessonProgram` is the organization-scoped lesson offering. It may optionally reference an existing `OrganizationGroup` of type Program, but it is not itself an organizational membership model.

`LessonSeries` is the recurring instructional group. It owns normal schedule metadata, instructor (`Person`), capacity, location, date range, and active state. Preview 1 stores recurrence metadata but does not auto-generate occurrences.

`LessonEnrollment` records who normally belongs in a series and supports active, waitlisted, withdrawn, and completed states. Enrollment is deliberately separate from attendance.

`LessonOccurrence` is one durable scheduled instance. It snapshots title, instructor, location, capacity, start/end timestamps, and operational status so later series edits do not rewrite history.

`LessonAttendanceRecord` records one canonical Person's participation in one occurrence and supports expected, present, absent, excused, no-show, cancelled, and makeup states. The distinct class name avoids colliding with the legacy `LessonAttendance` model during compatibility.

`LessonAssignment` records an operational participant or instructor assignment for one occurrence with an optional canonical `Horse`. Horse identity remains in the v3.3 Horse Registry and can vary by occurrence without storing horse names on attendance.

## Integrity rules

- Every relationship remains inside one ArenaLine organization (`Team`).
- An optional OrganizationGroup must belong to the same organization and be a Program group.
- Instructor, enrollment Person, attendance Person, assignment Person, and assigned Horse must belong to the same organization as the lesson hierarchy.
- Date/time windows must be ordered correctly.
- Capacity values must be positive when supplied.
- Enrollment is unique per Person/Series.
- Attendance is unique per Person/Occurrence.
- Assignment is unique per Person/Occurrence/role.
- Existing occurrences are historical snapshots and are not rewritten by later series edits.
- Canonical Person and Horse references use protected deletion where lesson history depends on them.

## Compatibility boundary

Preview 1 does **not** delete, rename, backfill, or redirect the existing `LessonGroup`, `Lesson`, or legacy `LessonAttendance` models or UI. A later preview will define deterministic backfill and UI cutover rules.

No v3.4 lesson UI is introduced in Preview 1.

## Regression gate

The focused `test_v340_*` suite must prove model registration, organization isolation, date/time validation, canonical Person/Horse references, uniqueness, occurrence snapshot independence, deletion protection, and coexistence with legacy lesson records. The v3.3.0 baseline must continue to pass alongside the new tests, with clean Django system and migration checks before UI work begins.
