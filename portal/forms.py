"""Public form namespace for ArenaLine.

The v2.9 cleanup starts decomposing the legacy monolithic forms module by keeping
its existing forms available while allowing domain forms to be normalized without
startup-time monkey patches.
"""

from .forms_legacy import *  # noqa: F401,F403
from .forms_legacy import ReimbursementRequestForm as _LegacyReimbursementRequestForm


class ReimbursementRequestForm(_LegacyReimbursementRequestForm):
    """Team-bound reimbursement form with explicit model-validation context."""

    def __init__(self, *args, team=None, user=None, **kwargs):
        super().__init__(*args, team=team, user=user, **kwargs)
        if team is not None:
            self.instance.team = team
