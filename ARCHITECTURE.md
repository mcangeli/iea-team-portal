# IEA Team Portal Architecture

## v2 View Layer

Beginning with v2.0.0 Preview 1, the Django view layer is organized by functional domain under `portal/view_modules/`.

`portal/views.py` remains a compatibility namespace. Existing URL configuration and code that imports `portal.views.<view_name>` do not need to change immediately.

### Domain modules

| Module | Responsibility |
| --- | --- |
| `roster.py` | Dashboard, team roster, riders, parents/guardians, season membership/classes |
| `communications.py` | Calendar, events/RSVPs, announcements, action items, notifications |
| `competitions.py` | Shows, show classes, entries, and result editing |
| `show_day.py` | My Show Day, rider status, schedule, updates, weekly summary |
| `scoring.py` | Standings, qualification, scoring configuration, points-rider operations |
| `show_planning.py` | Show planning, Show Lead assignments, planning items |
| `lessons.py` | Lessons, attendance, availability, volunteer workflows |
| `history.py` | Season archive/review, historical import/corrections, awards, Record Book |
| `administration.py` | Users, committee assignments, general audit log |
| `finance_core.py` | Finance dashboard, ledger, accounts, categories, budgets |
| `family_finance.py` | Dues, family accounts, payments/charges/credits, assistance |
| `fundraising.py` | Fundraising policy, campaigns, contributions, family fundraising |
| `finance_reports.py` | Financial reporting and CSV exports |
| `show_finance.py` | Show budgets, allocations, funding policy, reimbursements |

Most domains also have a matching `*_helpers.py` containing private logic used only by that domain.

`common.py` is intentionally limited to helpers shared across multiple domains, including common permission checks, audit helpers, team/season visibility helpers, and shared query calculations.

## Compatibility rule

During the v2.0 transition:

```python
from portal import views
views.show_detail
```

continues to work even though the implementation now lives in:

```text
portal/view_modules/competitions.py
```

This lets the project refactor architecture independently from URL routing and feature development.

## v2 direction

The modular view structure is intended to support:
- role-specific dashboards;
- Git-based installation and updating;
- rider lifecycle/alumni handling;
- calendar redesign;
- future horse and Hoofprint management.

Large new features should be added to the appropriate domain module rather than rebuilding a single monolithic view file.
