from dataclasses import dataclass

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


def compliance_summary_for_horse(horse):
    """Evaluate active organization requirements, preserving 3C fallback behavior."""
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
                    status = {"expired": "attention", "expiring": "warning", "current": "current"}[record.status]
                    items.append(HorseComplianceItem("coggins", requirement.name, status, record.status_label, f"Expires {record.expiration_date:%b %d, %Y}", record))
            else:
                document = _latest_document_for_type(documents, requirement.document_type)
                if document is None:
                    items.append(HorseComplianceItem("document", requirement.name, "attention", "Missing", f"Required {requirement.get_document_type_display()} is not on file."))
                elif document.expiration_status == "expired":
                    items.append(HorseComplianceItem("document", requirement.name, "attention", "Expired", f"{document.title} · Expired {document.expiration_date:%b %d, %Y}", document))
                elif document.expiration_status == "expiring":
                    items.append(HorseComplianceItem("document", requirement.name, "warning", "Expiring soon", f"{document.title} · Expires {document.expiration_date:%b %d, %Y}", document))
                else:
                    detail = document.title
                    if document.expiration_date:
                        detail += f" · Expires {document.expiration_date:%b %d, %Y}"
                    items.append(HorseComplianceItem("document", requirement.name, "current", "Current", detail, document))
    else:
        coggins = horse.latest_coggins
        if coggins is None:
            items.append(HorseComplianceItem("coggins", "Coggins", "attention", "Missing", "No Coggins record on file."))
        else:
            status = {"expired": "attention", "expiring": "warning", "current": "current"}[coggins.status]
            items.append(HorseComplianceItem("coggins", "Coggins", status, coggins.status_label, f"Expires {coggins.expiration_date:%b %d, %Y}", coggins))
        for document in documents:
            if document.expiration_status == "expired": status = "attention"
            elif document.expiration_status == "expiring": status = "warning"
            else: continue
            items.append(HorseComplianceItem("document", document.title, status, document.expiration_status_label, f"{document.get_document_type_display()} · Expires {document.expiration_date:%b %d, %Y}", document))

    items.sort(key=lambda item: (_STATUS_PRIORITY[item.status], item.label.lower()))
    if any(item.status == "attention" for item in items): overall = "attention"
    elif any(item.status == "warning" for item in items): overall = "warning"
    else: overall = "current"
    return HorseComplianceSummary(items=tuple(items), overall_status=overall, requirements_configured=bool(requirements))
