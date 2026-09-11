from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _display_pref(value):
    return {"yes": "Yes", "no": "No", "optional": "Optional"}.get(value, value or "—")


def _display_change(value):
    return {"flying": "Flying", "simple": "Simple", "either": "Either", "none": "None"}.get(value, value or "—")


def build_hoofprint_payload(show, cleaned_data=None):
    cleaned_data = cleaned_data or {}
    assignments = show.horse_assignments.select_related("horse").prefetch_related("show_classes__season_class", "horse__coggins_records")
    horses = []
    for assignment in assignments:
        horse = assignment.horse
        coggins = horse.latest_coggins
        horses.append({
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
            "classes": [
                {"number": c.class_number, "name": c.display_name, "team_level": c.team_level}
                for c in assignment.show_classes.all()
            ],
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
        "horses_contributed": cleaned_data.get("horses_contributed") if cleaned_data.get("horses_contributed") is not None else sum(1 for h in horses if h["available"]),
        "notes": cleaned_data.get("notes", ""),
        "horses": horses,
    }


def render_hoofprint_pdf(payload):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=0.35*inch, leftMargin=0.35*inch, topMargin=0.35*inch, bottomMargin=0.35*inch)
    styles = getSampleStyleSheet()
    story = [Paragraph("IEA HOOFPRINT", styles["Title"])]
    show = payload["show"]
    story.append(Paragraph(f"<b>Show:</b> {show['name']} &nbsp;&nbsp; <b>Date:</b> {show['date']} &nbsp;&nbsp; <b>Team:</b> {show['team_name']}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Coach:</b> {payload.get('coach_name') or '—'} &nbsp;&nbsp; <b>Phone:</b> {payload.get('coach_phone') or '—'} &nbsp;&nbsp; <b>Horses contributed:</b> {payload.get('horses_contributed', 0)}", styles["BodyText"]))
    story.append(Spacer(1, 0.12*inch))
    data = [["Horse", "Breed / Size", "Ht", "Classes", "Crop", "Spurs", "Changes", "Restrictions", "Riding description"]]
    for horse in payload.get("horses", []):
        classes = ", ".join((f"#{c['number']} " if c.get("number") else "") + c["name"] for c in horse.get("classes", [])) or "—"
        restrictions = "; ".join(filter(None, [horse.get("height_restriction"), horse.get("weight_restriction")])) or "—"
        data.append([
            horse["name"],
            " / ".join(filter(None, [horse.get("breed"), horse.get("size_type")])) or "—",
            horse.get("height_hands") or "—",
            classes,
            horse.get("crop") or "—",
            horse.get("spurs") or "—",
            horse.get("lead_change") or "—",
            restrictions,
            horse.get("riding_description") or "—",
        ])
    table = Table(data, repeatRows=1, colWidths=[0.9*inch, 1.0*inch, 0.45*inch, 2.15*inch, 0.55*inch, 0.55*inch, 0.65*inch, 1.2*inch, 2.0*inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#222222")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#999999")),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(table)
    if payload.get("notes"):
        story.append(Spacer(1, 0.12*inch))
        story.append(Paragraph(f"<b>Notes:</b> {payload['notes']}", styles["BodyText"]))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
