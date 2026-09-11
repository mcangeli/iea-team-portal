from django import template
from django.db.models import Count

from portal.horse_models import Horse, HorseShowAward
from portal.post_show_horse_models import ShowHorseHistory

register = template.Library()


def _horse_rows(team, season=None):
    rows = []
    for horse in Horse.objects.filter(team=team):
        final_records = horse.show_history_records.filter(
            history__status=ShowHorseHistory.Status.FINAL,
            actually_used=True,
        ).select_related("history__show")
        assignments = horse.show_assignments.all()
        awards = HorseShowAward.objects.filter(assignment__horse=horse)

        if season is not None:
            final_records = final_records.filter(history__show__season=season)
            assignments = assignments.filter(show__season=season)
            awards = awards.filter(show__season=season)

        final_show_ids = set(final_records.values_list("history__show_id", flat=True))
        if final_show_ids:
            assignments = assignments.exclude(show_id__in=final_show_ids)

        assignment_show_ids = set(assignments.values_list("show_id", flat=True))
        final_dates = list(final_records.values_list("history__show__show_date", flat=True))
        assignment_dates = list(assignments.values_list("show__show_date", flat=True))
        dates = [date for date in final_dates + assignment_dates if date]

        class_keys = set()
        for record in final_records:
            for item in record.class_snapshot or []:
                class_keys.add(item.get("id") or f"{item.get('class_number', '')}:{item.get('name', '')}")
        class_keys.update(
            assignments.values_list("show_classes", flat=True).exclude(show_classes__isnull=True)
        )

        show_count = len(final_show_ids | assignment_show_ids)
        award_count = awards.count()
        if not show_count and not award_count:
            continue

        sessions = {
            row["session"]: row["count"]
            for row in awards.values("session").annotate(count=Count("id"))
        }
        rows.append({
            "horse": horse,
            "shows": show_count,
            "classes": len(class_keys),
            "hotd": award_count,
            "full_day": sessions.get(HorseShowAward.Session.FULL_DAY, 0),
            "morning": sessions.get(HorseShowAward.Session.MORNING, 0),
            "afternoon": sessions.get(HorseShowAward.Session.AFTERNOON, 0),
            "first_show": min(dates) if dates else None,
            "last_show": max(dates) if dates else None,
            "finalized_shows": len(final_show_ids),
        })
    rows.sort(
        key=lambda row: (row["hotd"], row["shows"], row["classes"], row["horse"].display_name.lower()),
        reverse=True,
    )
    return rows


def _summary(rows):
    return {
        "rows": rows,
        "horse_count": len(rows),
        "hotd_total": sum(row["hotd"] for row in rows),
        "show_appearances": sum(row["shows"] for row in rows),
        "finalized_appearances": sum(row["finalized_shows"] for row in rows),
    }


@register.simple_tag
def horse_record_book_for_user(user):
    team = getattr(getattr(user, "profile", None), "team", None)
    return _summary(_horse_rows(team)) if team else _summary([])


@register.simple_tag
def season_horse_history(season):
    return _summary(_horse_rows(season.team, season=season))
