import re
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _display_pref(value):
    return {"yes": "Yes", "no": "No", "optional": "Optional"}.get(value, value or "—")


def _display_change(value):
    return {"flying": "Flying", "simple": "Simple", "either": "Either", "none": "None"}.get(value, value or "—")


def _p(value, style):
    return Paragraph(escape(str(value or "—")), style)


def _short_class_code(value):
    text = (value or "").strip().upper()
    if not text:
        return ""
    match = re.search(r"\b([A-Z]{1,3}\s*\d{1,3}[A-Z]?)\b", text)
    if match:
        return re.sub(r"\s+", "", match.group(1))
    return text.split()[0]


def _class_report_label(class_data):
    for value in (class_data.get("number"), class_data.get("name")):
        code = _short_class_code(value)
        if code:
            return code
    return "—"


def _class_payload(show_class):
    return {
        "number": _short_class_code((
            (getattr(show_class.season_class, "class_code", "") or "").strip()
            if show_class.season_class_id
            else ""
        ) or show_class.class_number),
        "name": show_class.display_name,
        "team_level": show_class.team_level,
    }


def build_hoofprint_payload(show, cleaned_data=None):
    cleaned_data = cleaned_data or {}
    assignments = (
        show.horse_assignments.filter(available=True)
        .select_related("horse")
        .prefetch_related("show_classes__season_class", "horse__coggins_records")
    )
    leased_horses = (
        show.leased_horses.filter(available=True)
        .prefetch_related("show_classes__season_class")
    )

    horses = []
    for assignment in assignments:
        horse = assignment.horse
        coggins = horse.latest_coggins
        horses.append({
            "source_type": "registry",
            "assignment_id": assignment.pk,
            "horse_id": horse.pk,
            "name": horse.display_name,
            "barn_name": horse.name,
            "breed": horse.breed,
            "sex": horse.get_sex_display() if horse.sex else "",
            "size_type": horse.size_type,
            "height_hands": str(horse.height_hands) if horse.height_hands is not None else "",
            "available": assignment.available,
            "crop": _display_pref(assignment.effective_crop_preference),
            "spurs": _display_pref(assignment.effective_spur_preference),
            "lead_change": _display_change(assignment.effective_lead_change),
            "height_restriction": horse.height_restriction_notes if horse.has_height_restriction else "",
            "weight_restriction": horse.weight_restriction_notes if horse.has_weight_restriction else "",
            "riding_description": horse.riding_description,
            "show_notes": assignment.notes,
            "coggins_status": coggins.status_label if coggins else "Missing",
            "coggins_expiration": coggins.expiration_date.isoformat() if coggins else "",
            "classes": [_class_payload(c) for c in assignment.show_classes.all()],
        })

    for leased in leased_horses:
        horses.append({
            "source_type": "leased",
            "leased_horse_id": leased.pk,
            "horse_id": None,
            "assignment_id": None,
            "name": leased.show_name or leased.barn_name,
            "barn_name": leased.barn_name,
            "breed": leased.breed,
            "sex": leased.get_sex_display() if leased.sex else "",
            "size_type": leased.size_type,
            "height_hands": str(leased.height_hands) if leased.height_hands is not None else "",
            "available": leased.available,
            "crop": _display_pref(leased.crop_preference),
            "spurs": _display_pref(leased.spur_preference),
            "lead_change": _display_change(leased.lead_change),
            "height_restriction": "",
            "weight_restriction": "",
            "riding_description": leased.riding_description,
            "show_notes": leased.restriction_notes or leased.notes,
            "coggins_status": leased.coggins_status or "Verify",
            "coggins_expiration": "",
            "provider": leased.provider,
            "classes": [_class_payload(c) for c in leased.show_classes.all()],
        })

    return {
        "show": {
            "id": show.pk,
            "name": show.name,
            "date": show.show_date.isoformat(),
            "venue": show.venue,
            "host_team": show.host_team,
            "zone": show.iea_zone,
            "region": show.iea_region,
            "team_name": show.team.name,
            "season": show.season.name,
        },
        "coach_name": cleaned_data.get("coach_name", ""),
        "coach_phone": cleaned_data.get("coach_phone", ""),
        "horses_contributed": cleaned_data.get("horses_contributed") if cleaned_data.get("horses_contributed") is not None else len(horses),
        "notes": cleaned_data.get("notes", ""),
        "horses": horses,
    }


def render_hoofprint_pdf(payload):
    buffer = BytesIO()
    page_width, page_height = landscape(letter)
    margin = 0.28 * inch
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(page_width, page_height),
        rightMargin=margin,
        leftMargin=margin,
        topMargin=0.24 * inch,
        bottomMargin=0.24 * inch,
        title="IEA Hoofprint",
        author="IEA Team Portal",
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle("HoofprintTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=14, leading=15, alignment=TA_CENTER, spaceAfter=4)
    label = ParagraphStyle("HoofprintLabel", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.2, leading=8.2)
    body = ParagraphStyle("HoofprintBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.2, leading=8.4, alignment=TA_LEFT)
    small = ParagraphStyle("HoofprintSmall", parent=body, fontSize=6.4, leading=7.3)
    class_code = ParagraphStyle("HoofprintClassCode", parent=small, fontName="Helvetica-Bold", fontSize=7.0, leading=8.0, alignment=TA_CENTER)
    header_cell = ParagraphStyle("HoofprintHeaderCell", parent=body, fontName="Helvetica-Bold", textColor=colors.white, fontSize=6.7, leading=7.4, alignment=TA_CENTER)

    show = payload.get("show", {})
    story = [Paragraph("IEA HOOFPRINT", title)]
    zone_region = " / ".join(part for part in [f"Zone {show.get('zone')}" if show.get("zone") else "", f"Region {show.get('region')}" if show.get("region") else ""] if part) or "—"

    header_data = [
        [_p("Show", label), _p(show.get("name"), body), _p("Date", label), _p(show.get("date"), body), _p("Season", label), _p(show.get("season"), body)],
        [_p("Team", label), _p(show.get("team_name"), body), _p("Venue", label), _p(show.get("venue"), body), _p("Zone / Region", label), _p(zone_region, body)],
        [_p("Coach", label), _p(payload.get("coach_name"), body), _p("Phone", label), _p(payload.get("coach_phone"), body), _p("Horses contributed", label), _p(payload.get("horses_contributed", 0), body)],
    ]
    header = Table(header_data, colWidths=[0.55*inch, 2.45*inch, 0.48*inch, 1.45*inch, 0.78*inch, 2.93*inch], hAlign="LEFT")
    header.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#9a9a9a")),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#eeeeee")),
        ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#eeeeee")),
        ("BACKGROUND", (4,0), (4,-1), colors.HexColor("#eeeeee")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 2.5), ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
    ]))
    story.extend([header, Spacer(1, 0.10*inch)])

    table_rows = [[Paragraph(x, header_cell) for x in ["Horse", "Breed / Size", "Ht", "Class ID", "Crop", "Spurs", "Changes", "Restrictions / Show notes", "Riding description"]]]

    for horse in payload.get("horses", []):
        class_labels = [_class_report_label(c) for c in horse.get("classes", [])]
        classes = "<br/>".join(escape(item) for item in class_labels) or "—"
        restrictions_parts = []
        if horse.get("height_restriction"): restrictions_parts.append(f"Height: {horse['height_restriction']}")
        if horse.get("weight_restriction"): restrictions_parts.append(f"Weight: {horse['weight_restriction']}")
        if horse.get("show_notes"): restrictions_parts.append(f"Show: {horse['show_notes']}")
        if horse.get("source_type") == "leased" and horse.get("provider"): restrictions_parts.append(f"Leased: {horse['provider']}")
        restrictions = "<br/>".join(escape(x) for x in restrictions_parts) or "—"

        show_name = (horse.get("name") or "").strip()
        barn_name = (horse.get("barn_name") or "").strip()
        primary_name = barn_name or show_name or "—"
        horse_label = "<b>" + escape(primary_name) + "</b>"
        if horse.get("source_type") == "leased": horse_label += "<br/><font size='5.6'>LEASED</font>"
        if show_name and show_name.casefold() != primary_name.casefold(): horse_label += "<br/><font size='5.6'>Show: " + escape(show_name) + "</font>"
        if horse.get("sex"): horse_label += "<br/>" + escape(horse["sex"])

        breed_size = " / ".join(x for x in [horse.get("breed"), horse.get("size_type")] if x) or "—"
        table_rows.append([
            Paragraph(horse_label, small), _p(breed_size, small), _p(horse.get("height_hands"), small), Paragraph(classes, class_code),
            _p(horse.get("crop"), small), _p(horse.get("spurs"), small), _p(horse.get("lead_change"), small), Paragraph(restrictions, small), _p(horse.get("riding_description"), small),
        ])

    available_width = page_width - (2 * margin)
    fixed_width = (0.90 + 0.95 + 0.38 + 0.62 + 0.48 + 0.48 + 0.60 + 1.55) * inch
    col_widths = [0.90*inch, 0.95*inch, 0.38*inch, 0.62*inch, 0.48*inch, 0.48*inch, 0.60*inch, 1.55*inch, available_width - fixed_width]
    horse_table = Table(table_rows, repeatRows=1, colWidths=col_widths, hAlign="LEFT")
    horse_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2f342f")), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#9a9a9a")), ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 2.5), ("RIGHTPADDING", (0,0), (-1,-1), 2.5),
        ("TOPPADDING", (0,0), (-1,-1), 2.7), ("BOTTOMPADDING", (0,0), (-1,-1), 2.7),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f7f7f5")]),
    ]))
    story.append(horse_table)

    footer_parts = []
    if payload.get("notes"): footer_parts.append(Paragraph(f"<b>Submission notes:</b> {escape(str(payload['notes']))}", body))
    footer_parts.append(Paragraph("Horse information reflects the finalized show roster. Verify class assignments, restrictions, crop/spur preferences, lead changes, and riding descriptions before submission.", small))
    story.extend([Spacer(1, 0.08*inch), KeepTogether(footer_parts)])
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
