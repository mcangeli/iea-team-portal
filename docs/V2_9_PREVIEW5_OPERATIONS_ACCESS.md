# ArenaLine v2.9.0 Preview 5E — Operations Access Audit

## Scope

Preview 5E audits server-side access boundaries for Operations and Communications surfaces after the platform, cross-organization, private-data, Finance, Competition, Hoofprint, and delegated-role security passes.

The slice covers Calendar, RSVP, Action Items, Lessons, Volunteer Hours, Notifications, and representative manager-only mutations.

## Confirmed access model

### Calendar

- Calendar querysets originate from the current organization.
- Non-manager users receive only `visible_to_all=True` events.
- Direct event detail lookup is organization-scoped and rejects a private event for non-managers.
- A foreign-organization event ID fails as `404`.

### RSVP

- The event must belong to the current organization and explicitly request RSVP.
- The rider is resolved through `_visible_riders()` for the authenticated user.
- Parent/Guardian users therefore cannot RSVP for an unrelated rider in the same organization or for a rider in another organization.

### Action Items

- List, claim, and completion operations use `_visible_action_items()` rather than raw primary-key lookup.
- Family-hidden items cannot be claimed through a guessed URL by Parent/Rider accounts.
- Claim and completion mutations separately re-check claimability/ownership or management authority.

### Lessons

- Lesson objects are organization-scoped.
- Non-manager lesson lists/details are constrained by `_visible_riders()`.
- A Parent/Guardian can see a lesson only when a linked rider has attendance in that lesson.
- Attendance edit, lesson create/edit/delete, and lesson-group administration remain management-only.

### Volunteer Hours

- Non-manager volunteer dashboards and submission forms are limited to riders returned by `_visible_riders()`.
- Volunteer review, requirement changes, and exports remain management-only.
- Volunteer review resolves the log through `season__team=current_organization`, so a manager cannot review another organization's log by ID.

### Notifications

- Notification lists originate from `request.user.portal_notifications`.
- Single-notification read mutation resolves by both notification primary key and `user=request.user`.
- Mark-all-read operates only on the authenticated user's notification relation.
- Notification preferences update only the authenticated user's profile.

## Regression coverage

`portal/tests/test_v290_preview5_operations_access.py` adds integration checks for:

- private same-organization calendar event denial for Parent/Guardian;
- foreign calendar event `404`;
- RSVP allowed for a linked rider but denied for unrelated and foreign riders;
- lesson detail allowed only when a linked rider is enrolled;
- foreign lesson `404`;
- Parent/Guardian denial for volunteer review;
- Administrator `404` for a foreign-organization volunteer log;
- hidden Action Item denial and family-visible claim behavior;
- notification ownership enforcement on read mutation.

No schema or permission broadening is introduced in this slice.

## Validation

Run the focused Preview 5 security set and then the full `portal` test suite. Preview 5E is complete only after both gates pass on staging.
