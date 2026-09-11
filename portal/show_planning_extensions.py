from .models import ShowPlanningItem


if not hasattr(ShowPlanningItem, "owner_id"):
    ShowPlanningItem.owner_id = property(
        lambda self: self.claimed_by_id or self.assigned_to_id
    )
