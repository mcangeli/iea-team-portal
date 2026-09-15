from dataclasses import dataclass


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

    @property
    def overall_status_label(self):
        return {
            "attention": "Compliance attention needed",
            "warning": "Compliance items expiring soon",
            "current": "Compliance current",
        }[self.overall_status]

    @property
    def attention_items(self):
        return tuple(item for item in self.items if item.status == "attention")

    @property
    def warning_items(self):
        return tuple(item for item in self.items if item.status == "warning")


def compliance_summary_for_horse(horse):
    """Combine specialized Coggins status and generic expiring documents.

    Coggins remains its own source of truth. Generic documents contribute only
    their own expiration intelligence; this helper does not create duplicate
    Coggins records or assume that every document type is required.
    """
    items = []
    coggins = horse.latest_coggins
    if coggins is None:
        items.append(HorseComplianceItem(
            category="coggins", label="Coggins", status="attention",
            status_label="Missing", detail="No Coggins record on file.",
        ))
    else:
        status = {"expired": "attention", "expiring": "warning", "current": "current"}[coggins.status]
        items.append(HorseComplianceItem(
            category="coggins", label="Coggins", status=status,
            status_label=coggins.status_label,
            detail=f"Expires {coggins.expiration_date:%b %d, %Y}", object=coggins,
        ))

    prefetched = getattr(horse, "_prefetched_objects_cache", {}).get("documents")
    documents = prefetched if prefetched is not None else horse.documents.all()
    for document in documents:
        if document.expiration_status == "expired":
            status = "attention"
        elif document.expiration_status == "expiring":
            status = "warning"
        else:
            continue
        items.append(HorseComplianceItem(
            category="document", label=document.title, status=status,
            status_label=document.expiration_status_label,
            detail=f"{document.get_document_type_display()} · Expires {document.expiration_date:%b %d, %Y}",
            object=document,
        ))

    items.sort(key=lambda item: (_STATUS_PRIORITY[item.status], item.label.lower()))
    if any(item.status == "attention" for item in items):
        overall = "attention"
    elif any(item.status == "warning" for item in items):
        overall = "warning"
    else:
        overall = "current"
    return HorseComplianceSummary(items=tuple(items), overall_status=overall)
