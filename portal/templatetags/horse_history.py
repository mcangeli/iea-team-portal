from django import template
from django.db.models import Count, Min, Max

from portal.horse_models import Horse, HorseShowAward

register = template.Library()


def _horse_rows(team, season=None):
    rows = []
    for horse in Horse.objects.filter(team=team):
        assignments = horse.show_assignments.all()
        awards = HorseShowAward.objects.filter(assignment__horse=horse)
        if season is not None:
            assignments = assignments.filter(show__season=season)
            awards = awards.filter(show__season=season)

        show_count = assignments.values("show_id").distinct().count()
        award_count = awards.count()
        if not show_count and not award_count:
            continue

        dates = assignments.aggregate(first=Min("show__show_date"), last=Max("show__show_date"))
        sessions = {
            row["session"]: row["count"]
            for row in awards.values("session").annotate(count=Count("id"))
        }
        class_count = assignments.values("show_classes").exclude(show_classes__isnull=True).distinct().count()
        rows.append({
            "horse": horse,
            "shows": show_count,
            "classes": class_count,
            "hotd": award_count,
            "full_day": sessions.get(HorseShowAward.Session.FULL_DAY, 0),
            "morning": sessions.get(HorseShowAward.Session.MORNING, 0),
            "afternoon": sessions.get(HorseShowAward.Session.AFTERNOON, 0),
            "first_show": dates["first"],
            "last_show": dates["last"],
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
    }


@register.simple_tag
def horse_record_book_for_user(user):
    team = getattr(getattr(user, "profile", None), "team", None)
    return _summary(_horse_rows(team)) if team else _summary([])


@register.simple_tag
def season_horse_history(season):
    return _summary(_horse_rows(season.team, season=season))
