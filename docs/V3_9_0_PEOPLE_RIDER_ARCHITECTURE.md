# ArenaLine v3.9.0 — People & Rider Architecture Contract

**Preview 1 — Architecture Contract**  
**Baseline:** v3.8.0  
**Status:** Locked for implementation

## Purpose

v3.9.0 completes the People architecture begun in v3.2 by establishing `Person` as ArenaLine's single canonical human identity.

The legacy `Rider` model currently combines human identity, IEA competitor identity, participation/history, and presentation concerns. ArenaLine now spans lessons, IEA, horse management, finance, barn operations, facilities, and future general horse-show management. A separate Rider identity no longer represents the product correctly.

> **Create the Person once. Add roles, relationships, and participation as their involvement with the organization changes.**

A rider is a Person participating in equestrian activities, not a separate kind of human.

## Core rules

1. `Person` is the sole canonical human identity within an organization.
2. Django `User` authenticates a Person; not every Person requires an account.
3. Rider is participation/capability, not a human identity model.
4. Roles such as parent/guardian, rider, trainer, boarder, staff, and volunteer do not create identities.
5. A Person may participate simultaneously in Lessons, IEA, general shows, Boarding, committees, and other programs.
6. IEA-specific facts remain in the IEA domain rather than being placed directly on Person.
7. Family, horse, finance, account, and program relationships remain independent and explicit.
8. Historical competition facts are preserved in their historical context.
9. Public Rider Cards are explicit privacy-safe projections of Person plus approved riding records.
10. No new ArenaLine feature introduced after v3.9.0 may use legacy `Rider` as its human identity.

## Target identity model

```text
Person
├── User account (optional)
├── PersonRelationship
├── OrganizationRoleAssignment
├── OrganizationGroupMembership
├── Lesson participation
├── IEA participation
├── General show participation
├── HorsePersonRelationship
├── ReceivableAccountPerson
└── Rider Card (projection)
```

No branch creates another Person-like identity.

## Program membership

v3.9 introduces a durable Person-to-program/group membership concept. The provisional model is:

```text
OrganizationGroupMembership
    team
    group
    person
    status
    start_date
    end_date
    active
    role/label (optional)
    notes
```

This answers “where does this Person participate?” It does not replace domain records.

Examples:

- Lesson Program membership is not LessonSeries enrollment.
- IEA Program membership is not IEA SeasonMembership.
- Boarding membership is not financial responsibility.
- Committee membership remains CommitteeMembership.

## Lessons

Lessons remain Person-native:

```text
LessonProgram
└── LessonSeries
    ├── LessonEnrollment → Person
    └── LessonOccurrence
        ├── Attendance → Person
        └── Assignment → Person / Horse
```

The missing durable Lesson Program membership is supplied by the program/group membership layer. A Person can remain a Lesson Program rider while not currently enrolled in a particular series.

## IEA

IEA becomes a domain attached to Person rather than the reason a Rider identity exists.

Conceptually:

```text
Person
└── IEA Participation
    ├── persistent IEA identity
    │   └── IEA member number
    └── Season Membership
        ├── season
        ├── team level
        ├── home barn
        ├── division
        ├── class level
        └── classes
```

Implementation will determine whether persistent IEA identity warrants a small `IEAParticipant` model or another Person-linked structure.

IEA membership describes a Person's participation in IEA. It does not create the Person.

## Historical IEA data

Historical season and competition facts must never be reconstructed from current Person attributes. Team level, grade/class context, entries, results, points, and qualifications remain tied to their historical season/competition context.

Changing a Person today must not rewrite who they were in a prior season.

## General shows

General horse-show participation is Person-based from inception:

```text
Show Participation
├── Person
├── Horse
├── Class
├── Entry
└── Result
```

IEA may layer season eligibility, team level, IEA class catalog, points-rider designation, qualification, VOC, and other IEA rules over common competition concepts.

Both IEA and general-show participation contribute to the same Rider Card.

## Rider Card

The Rider Card is a projection of Person, not a database identity.

It aggregates:

- overview/current participation;
- Lesson Program and lesson history;
- IEA seasons, classes, results, points, and qualifications;
- general show entries/results;
- horse relationships;
- awards and accomplishments;
- unified chronological riding/show history.

A Person can have a Rider Card without ever joining IEA.

A former rider can retain meaningful historical Rider Card information even when no longer actively riding.

## Public Rider Card

The existing privacy-safe Person public-profile approach is retained and expanded.

Public information is explicitly allow-listed. It may include approved name, photo, bio, selected riding history/results, awards, selected horse relationships, IEA accomplishments, and approved social/profile links.

It must not implicitly expose email, phone, birth date, private family relationships, financial data, internal notes, attendance records, private horse-care information, or account information.

Public profile opt-in remains explicit, with particular care for youth riders.

## Family

`PersonRelationship` is authoritative for family relationships.

A Person who is a parent/guardian may independently also be a rider, boarder, horse owner, billing contact, volunteer, trainer, or ArenaLine user without another Person record.

Legacy `GuardianContact` and `RiderGuardian` remain compatibility structures during migration.

## Horse relationships

Horse relationships remain Person-based and answer ownership, lease, riding, training, care, and similar horse-specific questions.

Horse ownership must not imply Boarding membership or financial responsibility.

The existing ambiguous “Boarder / Responsible Party” horse relationship semantics must be reviewed and separated where necessary.

## Finance

Finance remains independently authoritative through explicit account relationships.

```text
ReceivableAccount
└── ReceivableAccountPerson
    ├── Participant
    ├── Responsible Party
    └── Billing Contact
```

Financial responsibility is never inferred from parenthood, horse ownership, rider status, lesson enrollment, or Boarding membership.

## Unified Person creation

The target administrator workflow creates a Person once and then configures involvement.

### Person

Capture core identity/profile information.

### Involvement

Allow selection of relevant contexts such as:

- Rider
  - Lesson Program
  - IEA
  - General Shows
- Parent / Guardian
- Boarder
- Horse Owner / Lessee
- Trainer
- Staff
- Volunteer

Only relevant subsequent sections are shown.

### Domain setup

IEA selection can capture member number/current season/team/classes.

Lesson selection can add program membership and optionally an initial Lesson Series enrollment.

Parent/Guardian selection links an existing Person where possible rather than creating a duplicate.

### ArenaLine access

Account creation/invitation is optional and independent from Person creation.

### Public Rider Card

Eligible riders can explicitly opt into an approved public Rider Card.

## Existing Person gains rider participation

An existing Person must never be recreated to become a rider.

For example, a Person who already exists as a parent can later join Lessons. ArenaLine adds the relevant rider/program participation while preserving their existing Person, User, family, finance, horse, and historical relationships.

## Legacy Rider migration strategy

Migration is additive and staged.

### Preview 1 — Architecture
Lock this contract, migration rules, and regression requirements. No destructive model changes.

### Preview 2 — Person participation foundation
Introduce missing Person-native structures, beginning with generalized program/group membership and the minimum required IEA Person-participation foundation. Add regression tests first.

### Preview 3 — Person-native Rider Card
Create a Rider Card aggregation/service layer. It may initially combine Person-native and legacy Rider-backed records.

### Preview 4 — IEA migration
Move SeasonMembership and IEA participation toward Person. Backfill only through deterministic identity links and validate all migrated records.

### Preview 5 — Competition migration
Move IEA show entries/results and scoring/qualification consumers toward Person while retaining compatibility adapters.

### Preview 6 — Generic participation migration
Move generic Rider-dependent operational features, including RSVP and similar surfaces, to Person.

**Implementation status: complete for active architecture.**

Completed Person-native operational surfaces include event RSVP, volunteer credit/progress/export, rider awards and development history, and show availability UI. Each has explicit regression coverage for canonical Person records without a legacy Rider where applicable.

The modern Lesson Program architecture is already Person-native through LessonEnrollment, LessonOccurrence participation, attendance records, and assignments. The older LessonGroup / Lesson / LessonAttendance stack remains Rider-backed compatibility architecture and is intentionally deferred to Preview 8 rather than migrated into a second Person-native lesson implementation.

### Preview 7 — Creation/UI consolidation
Replace separate Add Rider/Add Guardian-style identity workflows with unified Person onboarding and participation management.

**Implementation status: complete.**

The canonical creation path is now Person onboarding. It can assign multiple organization roles and create Person-native IEA participation in one atomic workflow; selecting an IEA season also establishes Rider involvement. Legacy Add Rider and Add Parent/Guardian routes remain only as compatibility entry points and redirect to Add Person rather than creating new Rider or GuardianContact identities.

Rider Card management now routes profile editing, IEA season participation, login creation, and family management through the bridged Person and canonical Person relationships. The parent directory/export, ShowEntry creation, and Show Availability management likewise use Person/IEAParticipant-native paths, with narrow legacy adapters retained where old URLs or records still require them.

Preview 7 therefore closes new legacy identity creation and removes normal UI write paths that treat Rider or GuardianContact as separate human identities. Remaining legacy models, edit endpoints, old lesson-stack dependencies, and compatibility bridges are Preview 8 audit/closeout work.

### Preview 8 — Compatibility closeout
Audit remaining Rider, GuardianContact, RiderGuardian, and LegacyPersonLink dependencies. Removal is considered only after they cease to be authoritative.

## Migration safety

No Person may be matched to a legacy Rider merely because names or email-like values appear similar.

Existing `LegacyPersonLink` mappings are deterministic and authoritative for migration. Shared existing account identity may be used only where it proves the relationship unambiguously.

Ambiguous records are surfaced for reconciliation rather than silently merged.

Every preview must reduce legacy Rider dependence; no new Rider-as-identity dependency may be introduced.

## Communications boundary

Communications audiences resolve to Person sets, not Rider or User sets.

Examples include Everyone, Lesson Program, IEA Program, Futures, Upper, Boarding, Staff, Committees, specific People, Show participants, Lesson participants, and parents/guardians of selected People.

Delivery is separate:

```text
Audience
→ People
→ User inbox / Email / future SMS
```

Authorization to view something and selection as a communication recipient remain separate concepts.

## Required acceptance matrix

v3.9 regression coverage must include at least:

- youth lesson-only rider;
- youth IEA rider with guardian;
- youth IEA + lesson rider;
- adult lesson rider;
- adult IEA rider;
- rider who is also a parent;
- existing parent who begins riding;
- general-show-only rider;
- IEA + general-show rider with unified history;
- horse owner who does not ride;
- rider who does not own a horse;
- youth rider whose parent owns the horse;
- parent financially responsible for child;
- separate billing contact;
- boarder who does not ride;
- rider + boarder;
- Person without User;
- Person later receiving a User account;
- public rider with privacy-safe Rider Card;
- private rider absent from anonymous public surfaces;
- former rider with retained history;
- former IEA rider still active in Lessons.

## v3.9.0 completion criteria

The People foundation is complete when ArenaLine can truthfully guarantee:

- one canonical Person represents a human within an organization;
- a Person participates in multiple programs without duplicate identities;
- a rider need not participate in IEA;
- IEA does not define core human identity;
- Lessons, IEA, and general shows share the same Person;
- Rider Card presents unified equestrian history;
- public Rider Cards expose only explicitly approved information;
- family, horse, program, finance, and account relationships remain explicit and independent;
- historical IEA records survive migration intact;
- existing installations migrate without manually recreating People;
- no new feature depends on legacy Rider as human identity.

## v3.9.x sequence

- **v3.9.0** — People & Rider Architecture, participation, program membership, IEA Person transition, Rider Card, unified Person creation
- **v3.9.1** — Community / Posts
- **v3.9.2** — Conversations / Chat
- **v3.9.3** — Delivery / Notifications / Email
- **v3.9.4** — Operational Communications + Boarding Completion
