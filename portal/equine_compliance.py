from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from .model_modules.equine_compliance_requirements import HorseComplianceRequirement


_STATUS_PRIORITY = {"attention": 0, "warning": 1, "current": 2}


@dataclass(frozen=True)
class HorseComplianceItem:
    category: str
    label: str
    status: str
    status_label: str
    detail: str = ""
    object: object = None


@dataclass(frozen=True)
class HorseComplianceSummary:
    items: tuple
    overall_status: str
    requirements_configured: bool = False

    @property
    def overall_status_label(self):
        return {"attention": "Compliance attention needed", "warning": "Compliance items expiring soon", "current": "Compliance current"}[self.overall_status]

    @property
    def attention_items(self):
        return tuple(item for item in self.items if item.status == "attention")

    @property
    def warning_items(self):
        return tuple(item for item in self.items if item.status == "warning")


def _latest_document_for_type(documents, document_type):
    matches = [document for document in documents if document.document_type == document_type]
    if not matches:
        return None
    return max(matches, key=lambda document: (document.effective_date or document.created_at.date(), document.pk))


def _dated_status(expiration_date, as_of_date):
    """Return compliance status relative to the date the record must remain valid through."""
    if expiration_date is None:
        return "current", "Current"
    if expiration_date < as_of_date:
        return "attention", "Not valid through date"
    today = timezone.localdate()
    if expiration_date <= today + timedelta(days=30):
        return "warning", "Expiring soon"
    return "current", "Current"


def compliance_summary_for_horse(horse, as_of_date=None):
    """Evaluate active organization requirements through ``as_of_date``.

    Registry/profile callers omit ``as_of_date`` and retain today's compliance
    behavior. Show workflows pass the show date so a record that is current now
    but expires before the event cannot make the horse show-ready.
    """
    as_of_date = as_of_date or timezone.localdate()
    prefetched = getattr(horse, "_prefetched_objects_cache", {}).get("documents")
    documents = list(prefetched if prefetched is not None else horse.documents.all())
    requirements = list(HorseComplianceRequirement.objects.filter(team=horse.team, active=True))
    items = []

    if requirements:
        for requirement in requirements:
            if requirement.requirement_type == HorseComplianceRequirement.RequirementType.COGGINS:
                record = horse.latest_coggins
                if record is None:
                    items.append(HorseComplianceItem("coggins", requirement.name, "attention", "Missing", "No Coggins record on file."))
                else:
                    status, status_label = _dated_status(record.expiration_date, as_of_date)
                    items.append(HorseComplianceItem("coggins", requirement.name, status, status_label, f"Expires {record.expiration_date:%b %d, %Y}", record))
            else:
                document = _latest_document_for_type(documents, requirement.document_type)
                if document is None:
                    items.append(HorseComplianceItem("document", requirement.name, "attention", "Missing", f"Required {requirement.get_document_type_display()} is not on file."))
                else:
                    status, status_label = _dated_status(document.expiration_date, as_of_date)
                    detail = document.title
                    if document.expiration_date:
                        detail += f" · Expires {document.expiration_date:%b %d, %Y}"
                    items.append(HorseComplianceItem("document", requirement.name, status, status_label, detail, document))
    else:
        coggins = horse.latest_coggins
        if coggins is None:
            items.append(HorseComplianceItem("coggins", "Coggins", "attention", "Missing", "No Coggins record on file."))
        else:
            status, status_label = _dated_status(coggins.expiration_date, as_of_date)
            items.append(HorseComplianceItem("coggins", "Coggins", status, status_label, f"Expires {coggins.expiration_date:%b %d, %Y}", coggins))
        for document in documents:
            status, status_label = _dated_status(document.expiration_date, as_of_date)
            if status == "current":
                continue
            detail = document.get_document_type_display()
            if document.expiration_date:
                detail += f" · Expires {document.expiration_date:%b %d, %Y}"
            items.append(HorseComplianceItem("document", document.title, status, status_label, detail, document))

    items.sort(key=lambda item: (_STATUS_PRIORITY[item.status], item.label.lower()))
    if any(item.status == "attention" for item in items):
        overall = "attention"
    elif any(item.status == "warning" for item in items):
        overall = "warning"
    else:
        overall = "current"
    return HorseComplianceSummary(items=tuple(items), overall_status=overall, requirements_configured=bool(requirements))
