# ArenaLine v3.2.2 — Station Foundation

## Purpose

ArenaLine Station is the shared-device mode for barn operations. It is intentionally separate from the normal authenticated portal session so a tablet mounted in a barn can support limited actions without asking people to enter their ArenaLine password on a shared device.

## Security boundary

Station uses two distinct credentials:

1. A registered `StationDevice` has a generated device key and a separately hashed device secret.
2. A `StationCredential` belongs to one canonical `Person` and stores a separately hashed 4–8 digit PIN.

Neither credential reuses a Django login password. A Person does not need a Django `auth.User` account in order to have a Station credential.

All Station records are organization-scoped and validate that Person, device, work shift, and approver remain inside the same ArenaLine organization.

Successful Station activation explicitly ends any normal Django login session on that browser before establishing the limited Station device session. This prevents a manager from provisioning a shared tablet and accidentally leaving a full ArenaLine account authenticated behind the kiosk.

Person-level Station identity is intentionally short-lived. After successful PIN verification, the limited Person context expires after two minutes and is cleared immediately after clock-in or clock-out.

Repeated incorrect PIN attempts are throttled per Person/per Station browser session. Five incorrect attempts temporarily lock that Person's PIN on that Station for five minutes. The lock does not expose or store the PIN and produces an operational audit event.

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

## Implemented manager workflow

Managers can open **People → ArenaLine Station** to:

- register a shared Station device;
- view active/inactive devices and last-seen time;
- receive the generated device key and one-time raw secret after registration;
- rotate a device secret when needed;
- set or reset a Person's 4–8 digit Station PIN;
- enable or disable a Person's Station credential;
- review recent Station shifts;
- correct role, clock-in, clock-out, and notes;
- approve completed shifts;
- view completed-shift, total, approved, and Working Student hours by Person;
- export the complete organization-scoped shift history to CSV.

The raw device secret is displayed only during registration/rotation and is not stored in clear text.

Open shifts cannot be approved. Corrections and approvals create `AuditEvent` records. Correction events capture before/after values so the operational history remains traceable.

The CSV export includes Person, role, local clock times, minutes/hours, approval state, approver, Station, and notes. Export activity itself is audited.

## Implemented kiosk workflow

A shared tablet is activated once using its device key and one-time secret.

After activation:

1. Station displays only active Station identities in that device's organization.
2. The person taps their name.
3. The person enters their separately hashed Station PIN.
4. ArenaLine creates a short-lived limited Person context.
5. If an open shift exists, Station offers **Clock out**.
6. If no shift is open, Station offers only the person's active work roles that map to Station shifts.
7. A Person with multiple active work roles chooses the role for that particular shift.
8. Clock-in/out clears the Person context and returns the device to shared-kiosk mode.

PINs are not used as reversible lookup keys and do not need to be globally unique. Station identifies the Person first, then verifies that Person's hashed PIN.

The kiosk presentation is optimized for mounted tablets with larger identity cards, larger clock actions, simplified PIN entry, responsive layout, and clearer completion/lockout states.

## Audit coverage

ArenaLine Station now emits operational `AuditEvent` records for:

- device registration and device setting changes;
- device secret rotation;
- Station device activation/deactivation;
- Station PIN setup/reset state changes, without recording the raw PIN;
- successful Station PIN authentication;
- temporary PIN lockouts;
- Station clock-in and clock-out;
- manager shift correction and approval;
- staff-hours CSV export.

Device secrets and Person PINs are deliberately excluded from audit details.

## Multi-role People behavior

ArenaLine's canonical Person model is explicitly multi-role. `Parent / Guardian` is now included alongside Rider, Boarder, Trainer, Assistant Trainer, Barn Manager, Barn Staff, Working Student, and Board Member.

The Person profile uses a checkbox-based **Manage roles** workflow. Multiple roles may be active simultaneously; for example, one Person can be Parent / Guardian, Rider, and Boarder at the same time.

Each role remains a separate dated `OrganizationRoleAssignment` so history and notes are preserved. The individual role detail editor manages dates/status/notes but does not present a role dropdown that can mutate one assignment into another.

Migration `0070_v322_person_multi_roles.py` adds Parent / Guardian to the canonical role choices and backfills it for people with active parent/guardian relationships.

## IEA committee compatibility UI

Committee memberships mirrored from legacy IEA `CommitteeAssignment` records are visibly labeled **Managed by IEA assignment** on the Person profile.

Those mirrored memberships are read-only in the generalized membership editor. The legacy IEA assignment remains authoritative during the compatibility period, preventing a user from editing a mirror that will later be overwritten by the compatibility sync.

## Regression coverage

`portal/tests/test_v322_station_foundation.py` protects Station credential hashing, tenant boundaries, one-open-shift rules, valid clock ordering, and approver organization safety.

`portal/tests/test_v322_station_ui.py` protects manager-only setup, one-time device provisioning, PIN creation, full-session logout on Station activation, organization-scoped kiosk identities, wrong-PIN rejection, multi-role shift selection, clock-in, and clock-out.

`portal/tests/test_v322_station_review.py` protects manager-only shift review, tenant isolation, completed-shift approval, open-shift rejection, manager corrections, and audit-event creation.

`portal/tests/test_v322_station_hardening.py` protects temporary PIN lockout, device/PIN audit safety, clock-in/out audit creation, and tenant-scoped CSV export.

## Remaining v3.2.2 boundary

The core Station/staff-time workflow is now implemented. Remaining v3.2.2 work should focus on stabilization and presentation rather than expanding the domain: full focused regression, live tablet review, and any small usability fixes discovered during staging. Lesson check-in/out remains deferred until the Lesson Program domain is ready.
