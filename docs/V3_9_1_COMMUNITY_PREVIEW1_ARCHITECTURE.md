# v3.9.1 Preview 1 — Community authorization and data contract

Status: architecture baseline; no schema or production behavior changes yet.

## Existing contracts to preserve

- `portal.models.Announcement` is an IEA/team communication record with season, Futures/Upper, coach, parent, rider, and selected-user audiences.
- `portal.people_communications.announcement_recipients` is the canonical recipient resolver for those legacy announcements.
- `portal.models.Notification` is user-addressed, with announcement and show-day update links.
- `portal.view_modules.communications_helpers._deliver_announcement` currently deletes/recreates linked notifications on redelivery and sends optional email according to `UserProfile.email_announcements`. Do not reuse this delivery method for community posts.
- `portal.model_modules.people.Person` is canonical identity; `OrganizationGroup` and `OrganizationGroupMembership` represent generic groups without conferring authorization.
- Existing tests in `portal/tests/test_v323_people_communications.py` protect family relationship effective dates and Futures/Upper boundaries.

## Proposed additive domain model

1. `CommunityPost`: organization, author Person, acting User, title/body, status (draft/published/archived/removed), publication/expiry timestamps, creation/update timestamps, optional source domain link.
2. `CommunityPostAudience`: explicit audience entries. Initial scopes: organization-wide, selected Person, selected OrganizationGroup. IEA season/team audiences remain served by legacy Announcement until a separate migration is designed.
3. `CommunityComment`: organization, post, author Person, acting User, body, moderation status, timestamps.
4. `CommunityAttachment`: organization, post, uploader Person, file metadata, protected storage reference, moderation status. No public storage URLs.

All cross-record organization invariants require service-level validation and model validation; foreign keys alone do not guarantee same-tenant ownership.

## Authorization rules

- Feed/detail/comment/attachment access must resolve an active organization and current Person identity, then evaluate current audience membership at request time.
- Organization-wide audience means authenticated, authorized members of that organization, not anonymous visitors.
- Selected Person is matched by canonical Person identity, never by display name or arbitrary role labels.
- Group audience uses active, effective membership; group membership alone does not grant management or moderation rights.
- Drafts are visible only to author and explicitly authorized moderators; removed content is not available to ordinary viewers.
- Replies inherit parent post visibility. Post visibility must be rechecked on every comment or attachment request.
- Management rights are separate from audience membership. Role labels do not automatically authorize publishing, editing, or moderation.
- Private data and youth information must never be included in public/anonymous payloads.
- Posting does not imply notification or email. Notification delivery is an independent, durable workflow with preference enforcement and idempotency.

## Preview 1 regression gate (write tests before UI)

- Organization A cannot see or mutate posts/comments/files belonging to B, even by guessed IDs.
- Selected Person visibility is limited to selected Persons.
- Group audience changes take effect on the next request; inactive or expired memberships do not retain access.
- Unpublished/removed posts are not visible in feed, detail, attachments, or comments to ordinary users.
- A user without a canonical Person cannot impersonate an author.
- Cross-tenant author, group, recipient, comment, and attachment associations are rejected.
- Readers cannot publish, edit, moderate, or delete merely because they can read.
- Legacy announcement audiences and notification delivery remain unchanged.
- Public/spectator endpoints never expose community content by default.

## Implementation order

1. Confirm membership effective-date semantics and existing permission service APIs.
2. Add domain models and additive migration, with model-level validation.
3. Add audience resolver/service and negative authorization tests.
4. Add views and templates only after regression gate passes.
5. Build notification integration separately; never call legacy redelivery as a community-post notification mechanism.

No migration or release promotion is authorized by this document.
