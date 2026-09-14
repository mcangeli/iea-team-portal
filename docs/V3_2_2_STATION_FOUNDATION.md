# ArenaLine v3.2.2 — Station Foundation

## Purpose

ArenaLine Station is the shared-device mode for barn operations. It is intentionally separate from the normal authenticated portal session so a tablet mounted in a barn can support limited actions without asking people to enter their ArenaLine password on a shared device.

## Security boundary

Station uses two distinct credentials:

1. A registered `StationDevice` has a generated device key and a separately hashed device secret.
2. A `StationCredential` belongs to one canonical `Person` and stores a separately hashed 4–8 digit PIN.

Neither credential reuses a Django login password. A Person does not need a Django `auth.User` account in order to have a Station credential.

All Station records are organization-scoped and validate that Person, device, work shift, and approver remain inside the same ArenaLine organization.

## Initial models

### StationDevice

Represents a registered shared device such as a barn iPad.

Fields include organization, display name, generated device key, hashed secret, active state, notes, last-seen timestamp, and audit timestamps.

### StationCredential

Represents limited Station identity for one Person.

The PIN is never stored in clear text. One Person may have one active Station credential record.

### WorkShiftEntry

Provides the first operational Station record for work-shift clock-in/out.

Initial shift roles are Working Student, Barn Staff, Barn Manager, Trainer, Assistant Trainer, and Other.

Only one open shift per Person is allowed at the database level. Clock-out cannot precede clock-in. Station devices and approvers must belong to the same organization as the Person and shift.

## Multi-role People behavior

ArenaLine's canonical Person model is explicitly multi-role. `Parent / Guardian` is now included alongside Rider, Boarder, Trainer, Assistant Trainer, Barn Manager, Barn Staff, Working Student, and Board Member.

The Person profile uses a checkbox-based **Manage roles** workflow. Multiple roles may be active simultaneously; for example, one Person can be Parent / Guardian, Rider, and Boarder at the same time.

Each role remains a separate dated `OrganizationRoleAssignment` so history and notes are preserved. The individual role detail editor manages dates/status/notes but does not present a role dropdown that can mutate one assignment into another.

Migration `0070_v322_person_multi_roles.py` adds Parent / Guardian to the canonical role choices and backfills it for people with active parent/guardian relationships.

## IEA committee compatibility UI

Committee memberships mirrored from legacy IEA `CommitteeAssignment` records are visibly labeled **Managed by IEA assignment** on the Person profile.

Those mirrored memberships are read-only in the generalized membership editor. The legacy IEA assignment remains authoritative during the compatibility period, preventing a user from editing a mirror that will later be overwritten by the compatibility sync.

## Next Station slices

The next v3.2.2 work should add:

- manager registration/activation of Station devices;
- manager creation/reset of Person Station PINs;
- kiosk-oriented Station landing/PIN flow;
- limited Person session after successful PIN verification;
- clock-in and clock-out actions;
- automatic timeout/return-to-kiosk behavior;
- event/audit logging and rate-limiting protections;
- later lesson check-in/out once the lesson-program domain is ready.
