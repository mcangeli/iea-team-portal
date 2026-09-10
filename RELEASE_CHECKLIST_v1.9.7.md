# v1.9.7 Release Candidate Checklist

Use this checklist when publishing and validating the final `v1.9.7` release.

## Upgrade
- `./portalctl upgrade` completes successfully.
- Migration `0029_v197_show_day_planning.py` is applied.
- Existing data from v1.9.6.1 remains intact.
- Shared `/opt/iea-team-portal/.env` is still used.
- Site footer shows `v1.9.7`.

## Mobile show-day flow
- Open Show Day on a phone.
- Rider check-in controls are easy to use.
- Schedule remains readable and scrollable.
- Checklist/volunteer cards are usable without horizontal overflow.
- My Show Day class rows fit cleanly without a horizontal table.
- Show Updates are readable and links/actions are easy to tap.

## Permissions
### Admin / Coach
- Full Show Day roster.
- Full schedule editing.
- Full show planning/checklist.
- Can publish Everyone/Futures/Upper updates.

### Show Lead
- Full operational Show Day view.
- Full schedule editing.
- Full show planning/checklist.
- Can publish show-day updates.

### Points Secretary
- Full-team Show Day context.
- Can enter/edit results.
- Can edit schedule.
- Does not gain rider check-in authority unless another role grants it.

### Futures Team Parent
- Futures operational riders/classes only.
- Can check in Futures riders.
- Can manage Futures planning items.
- Can publish Futures updates only.

### Upper Team Parent
- Upper operational riders/classes only.
- Can check in Upper riders.
- Can manage Upper planning items.
- Can publish Upper updates only.

### Ordinary Parent/Guardian
- My Show Day shows linked rider(s) only.
- Can update linked rider arrival status.
- Sees only applicable schedule/update information.
- Can claim family-visible volunteer/supply items.
- No points-rider or Finance information.

### Rider
- My Show Day shows self only.
- Can update own arrival status.
- No Team Parent/operational authority.
- No points-rider or Finance information.

## Show-day edge cases
- Show with no entries has a useful empty state.
- Linked rider not entered has a useful My Show Day empty state.
- Unlinked parent account has a useful My Show Day empty state.
- Classes with no prize-list time display cleanly.
- Current estimate falls back to prize-list time.
- Schedule shifts do not change the prize-list baseline.
- Reset estimates returns current estimate to prize-list time.
- Running Late / Arrived / Finished status updates persist correctly.
- Operational Scratched status does not silently alter the underlying ShowEntry record.
- Hosted-show starter plan is duplicate-safe.
- Attending-show starter plan is duplicate-safe.
- Claimed volunteer item can be released and completed.
- Archived season blocks new show-day operational mutations.

## Show updates
- Everyone update reaches applicable show families and staff.
- Futures update does not appear to unrelated Upper families.
- Upper update does not appear to unrelated Futures families.
- Silent edit does not create a new notification.
- Re-notify edit creates a new notification.
- Retracted update disappears from public feed.
- Email show-update preference works independently of announcement email preference.

## Final packaging
- Final folder is `iea-team-portal-v1.9.7/`.
- Final ZIP contains exactly that top-level folder.
- `VERSION` contains `1.9.7`.
- README says current version `v1.9.7`.
- Release Notes no longer say “release candidate.”
- GitHub tag `v1.9.7` is published so the footer documentation link resolves.
- Final ZIP SHA-256 is recorded in the release notes or release post.
