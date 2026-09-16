from dataclasses import dataclass, field
from datetime import timedelta

from django.db import transaction
from django.db.models import Q

from portal.model_modules.horses import Horse
from portal.model_modules.lessons import (
    IEALessonSeriesContext,
    LessonAssignment,
    LessonAttendanceRecord,
    LessonOccurrence,
    LessonProgram,
    LessonSeries,
)
from portal.model_modules.people import LegacyPersonLink, Person
from portal.models import Lesson, LessonAttendance, SeasonMembership


@dataclass(frozen=True)
class LegacyIEALessonIssue:
    lesson_id: int
    message: str


@dataclass
class LegacyIEALessonConversionReport:
    lessons_scanned: int = 0
    lessons_convertible: int = 0
    programs_created: int = 0
    series_created: int = 0
    occurrences_created: int = 0
    occurrences_existing: int = 0
    attendance_created: int = 0
    attendance_existing: int = 0
    assignments_created: int = 0
    assignments_existing: int = 0
    issues: list[LegacyIEALessonIssue] = field(default_factory=list)

    @property
    def issue_count(self):
        return len(self.issues)


_STATUS_MAP = {
    LessonAttendance.Status.EXPECTED: LessonAttendanceRecord.Status.EXPECTED,
    LessonAttendance.Status.PRESENT: LessonAttendanceRecord.Status.PRESENT,
    LessonAttendance.Status.ABSENT: LessonAttendanceRecord.Status.ABSENT,
    LessonAttendance.Status.EXCUSED: LessonAttendanceRecord.Status.EXCUSED,
    LessonAttendance.Status.MAKEUP: LessonAttendanceRecord.Status.MAKEUP,
}


def _person_for_user(user, team_id):
    if not user:
        return None
    return Person.objects.filter(user=user, team_id=team_id).first()


def _person_for_rider(rider):
    link = LegacyPersonLink.objects.filter(rider=rider).select_related("person").first()
    return link.person if link else None


def _membership_level_for_rider(rider, season):
    return (
        SeasonMembership.objects.filter(rider=rider, season=season)
        .values_list("team_level", flat=True)
        .first()
    )


def _derive_team_level(lesson):
    if lesson.group_id and lesson.group.team_level in {
        SeasonMembership.TeamLevel.FUTURES,
        SeasonMembership.TeamLevel.UPPER,
    }:
        return lesson.group.team_level, None

    rider_ids = set()
    if lesson.group_id:
        rider_ids.update(lesson.group.riders.values_list("id", flat=True))
    rider_ids.update(lesson.attendance.values_list("rider_id", flat=True))

    levels = set(
        SeasonMembership.objects.filter(season=lesson.season, rider_id__in=rider_ids)
        .exclude(team_level="")
        .values_list("team_level", flat=True)
    )
    levels &= {SeasonMembership.TeamLevel.FUTURES, SeasonMembership.TeamLevel.UPPER}
    if len(levels) == 1:
        return levels.pop(), None
    if not levels:
        return None, "Could not determine Futures/Upper team level from the lesson group or roster."
    return None, "Legacy lesson contains both Futures and Upper riders and cannot map to one IEA lesson series."


def _series_name(lesson, team_level):
    if lesson.group_id:
        return lesson.group.name
    return "Futures Team Lessons" if team_level == SeasonMembership.TeamLevel.FUTURES else "Upper Team Lessons"


def _program_name(season):
    return f"IEA Team Lessons — {season.name}"


def _canonical_horse(team_id, horse_name):
    name = (horse_name or "").strip()
    if not name:
        return None
    return Horse.objects.filter(team_id=team_id).filter(Q(name__iexact=name) | Q(show_name__iexact=name)).first()


def _convert_one(lesson, report, *, dry_run):
    team_level, issue = _derive_team_level(lesson)
    if issue:
        report.issues.append(LegacyIEALessonIssue(lesson.id, issue))
        return

    legacy_attendance = list(lesson.attendance.select_related("rider").all())
    missing_people = [row.rider for row in legacy_attendance if _person_for_rider(row.rider) is None]
    if missing_people:
        names = ", ".join(str(rider) for rider in missing_people)
        report.issues.append(
            LegacyIEALessonIssue(lesson.id, f"Attendance contains rider(s) without canonical Person links: {names}.")
        )
        return

    report.lessons_convertible += 1
    if dry_run:
        return

    program, program_created = LessonProgram.objects.get_or_create(
        team=lesson.team,
        name=_program_name(lesson.season),
        defaults={"description": "IEA team lesson scheduling container created from the legacy lesson workflow."},
    )
    report.programs_created += int(program_created)

    series, series_created = LessonSeries.objects.get_or_create(
        program=program,
        name=_series_name(lesson, team_level),
        defaults={
            "instructor": _person_for_user(lesson.group.coach if lesson.group_id else lesson.coach, lesson.team_id),
            "default_location": lesson.group.default_location if lesson.group_id else lesson.location,
            "start_date": lesson.season.start_date,
            "end_date": lesson.season.end_date,
            "active": lesson.group.active if lesson.group_id else True,
        },
    )
    report.series_created += int(series_created)
    context, context_created = IEALessonSeriesContext.objects.get_or_create(
        series=series,
        defaults={"season": lesson.season, "team_level": team_level},
    )
    if not context_created and (context.season_id != lesson.season_id or context.team_level != team_level):
        report.issues.append(
            LegacyIEALessonIssue(lesson.id, "Existing converted series has conflicting IEA season/team-level context.")
        )
        return

    instructor = _person_for_user(lesson.coach, lesson.team_id)
    occurrence, occurrence_created = LessonOccurrence.objects.get_or_create(
        series=series,
        starts_at=lesson.starts_at,
        defaults={
            "title": lesson.title,
            "instructor": instructor,
            "ends_at": lesson.ends_at,
            "location": lesson.location,
            "status": LessonOccurrence.Status.CANCELLED if lesson.cancelled else LessonOccurrence.Status.SCHEDULED,
            "notes": lesson.notes,
        },
    )
    if occurrence_created:
        report.occurrences_created += 1
    else:
        report.occurrences_existing += 1

    for legacy_row in legacy_attendance:
        person = _person_for_rider(legacy_row.rider)
        attendance, created = LessonAttendanceRecord.objects.get_or_create(
            occurrence=occurrence,
            person=person,
            defaults={"status": _STATUS_MAP[legacy_row.status], "notes": legacy_row.notes},
        )
        if created:
            report.attendance_created += 1
        else:
            report.attendance_existing += 1

        horse = _canonical_horse(lesson.team_id, legacy_row.horse_name)
        assignment_notes = ""
        if legacy_row.horse_name and not horse:
            assignment_notes = f"Legacy horse: {legacy_row.horse_name.strip()}"
        assignment, created = LessonAssignment.objects.get_or_create(
            occurrence=occurrence,
            person=person,
            role=LessonAssignment.Role.PARTICIPANT,
            defaults={"horse": horse, "notes": assignment_notes},
        )
        if created:
            report.assignments_created += 1
        else:
            report.assignments_existing += 1


def convert_legacy_iea_lessons(*, team=None, season=None, dry_run=True):
    """Report or convert legacy IEA lessons into the v3.4 lesson engine.

    The legacy Lesson/LessonAttendance rows are never modified. Repeated apply runs
    are additive and idempotent. Ambiguous mixed-team lessons and missing canonical
    Person bridges are reported rather than guessed.
    """
    lessons = Lesson.objects.select_related("team", "season", "group", "group__coach", "coach").order_by("starts_at", "id")
    if team is not None:
        lessons = lessons.filter(team=team)
    if season is not None:
        lessons = lessons.filter(season=season)

    report = LegacyIEALessonConversionReport()
    with transaction.atomic():
        for lesson in lessons:
            report.lessons_scanned += 1
            _convert_one(lesson, report, dry_run=dry_run)
        if dry_run:
            transaction.set_rollback(True)
    return report
