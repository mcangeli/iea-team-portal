"""Compatibility fix for reimbursement form model validation.

ReimbursementRequest.clean() validates that the selected category/show/season belong
 to the request team. Django ModelForm model validation runs before the create view
 assigns obj.team, so new reimbursement forms must seed instance.team during form
 construction. Keep this narrow compatibility patch until the finance forms are
 normalized in the planned 2.9.x cleanup.
"""

from .forms import ReimbursementRequestForm


_original_init = ReimbursementRequestForm.__init__


def _team_bound_init(self, *args, team=None, user=None, **kwargs):
    _original_init(self, *args, team=team, user=user, **kwargs)
    if team is not None:
        self.instance.team = team


ReimbursementRequestForm.__init__ = _team_bound_init
