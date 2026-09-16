from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Q

from portal.model_modules.horses import Horse
from portal.model_modules.lessons import IEALessonSeriesContext, LessonAssignment, LessonAttendanceRecord, LessonOccurrence, LessonProgram, LessonSeries
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
_VALID_LEVELS = {SeasonMembership.TeamLevel.FUTURES, SeasonMembership.TeamLevel.UPPER}


def _person_for_user(user, team_id):
    if not user:
        return None
    return Person.objects.filter(user=user, team_id=team_id).first()


def _person_for_rider(rider):
    link = LegacyPersonLink.objects.filter(rider=rider).select_related("person").first()
    return link.person if link else None


def _membership_level_for_rider(rider, season):
    return SeasonMembership.objects.filter(rider=rider, season=season).values_list("team_level", flat=True).first()


def _legacy_rows_by_level(lesson):
    rows_by_level = {SeasonMembership.TeamLevel.FUTURES: [], SeasonMembership.TeamLevel.UPPER: []}
    issues = []
    for row in lesson.attendance.select_related("rider").all():
        level = _membership_level_for_rider(row.rider, lesson.season)
        if level not in _VALID_LEVELS:
            issues.append(f"{row.rider} has no Futures/Upper membership for {lesson.season.name}")
            continue
        if _person_for_rider(row.rider) is None:
            issues.append(f"{row.rider} has no canonical Person link")
            continue
        rows_by_level[level].append(row)
    return rows_by_level, issues


def _conversion_levels(lesson, rows_by_level):
    populated = [level for level in (SeasonMembership.TeamLevel.FUTURES, SeasonMembership.TeamLevel.UPPER) if rows_by_level[level]]
    if populated:
        return populated
    if lesson.group_id and lesson.group.team_level in _VALID_LEVELS:
        return [lesson.group.team_level]
    rider_ids = set(lesson.group.riders.values_list("id", flat=True)) if lesson.group_id else set()
    levels = set(SeasonMembership.objects.filter(season=lesson.season, rider_id__in=rider_ids).exclude(team_level="").values_list("team_level", flat=True)) & _VALID_LEVELS
    return [level for level in (SeasonMembership.TeamLevel.FUTURES, SeasonMembership.TeamLevel.UPPER) if level in levels]


def _series_name(lesson, team_level, *, split=False):
    level_label = "Futures" if team_level == SeasonMembership.TeamLevel.FUTURES else "Upper"
    if lesson.group_id:
        base = lesson.group.name
        if split or lesson.group.team_level not in _VALID_LEVELS:
            return f"{base} — {level_label}"
        return base
    return f"{level_label} Team Lessons"


def _program_name(season):
    return f"IEA Team Lessons — {season.name}"


def _canonical_horse(team_id, horse_name):
    name = (horse_name or "").strip()
    if not name:
        return None
    return Horse.objects.filter(team_id=team_id).filter(Q(name__iexact=name) | Q(show_name__iexact=name)).first()


def _convert_partition(lesson, team_level, legacy_rows, report, *, split):
    program, program_created = LessonProgram.objects.get_or_create(
        team=lesson.team,
        name=_program_name(lesson.season),
        defaults={"description": "IEA team lesson scheduling container created from the legacy lesson workflow."},
    )
    report.programs_created += int(program_created)
    series, series_created = LessonSeries.objects.get_or_create(
        program=program,
        name=_series_name(lesson, team_level, split=split),
        defaults={
            "instructor": _person_for_user(lesson.group.coach if lesson.group_id else lesson.coach, lesson.team_id),
            "default_location": lesson.group.default_location if lesson.group_id else lesson.location,
            "start_date": lesson.season.start_date,
            "end_date": lesson.season.end_date,
            "active": lesson.group.active if lesson.group_id else True,
        },
    )
    report.series_created += int(series_created)
    context, context_created = IEALessonSeriesContext.objects.get_or_create(series=series, defaults={"season": lesson.season, "team_level": team_level})
    if not context_created and (context.season_id != lesson.season_id or context.team_level != team_level):
        report.issues.append(LegacyIEALessonIssue(lesson.id, "Existing converted series has conflicting IEA season/team-level context."))
        return

    occurrence, occurrence_created = LessonOccurrence.objects.get_or_create(
        series=series,
        starts_at=lesson.starts_at,
        defaults={
            "title": lesson.title,
            "instructor": _person_for_user(lesson.coach, lesson.team_id),
            "ends_at": lesson.ends_at,
            "origin": LessonOccurrence.Origin.LEGACY,
            "scheduled_for": None,
            "location": lesson.location,
            "status": LessonOccurrence.Status.CANCELLED if lesson.cancelled else LessonOccurrence.Status.SCHEDULED,
            "notes": lesson.notes,
        },
    )
    report.occurrences_created += int(occurrence_created)
    report.occurrences_existing += int(not occurrence_created)

    for legacy_row in legacy_rows:
        person = _person_for_rider(legacy_row.rider)
        _, created = LessonAttendanceRecord.objects.get_or_create(occurrence=occurrence, person=person, defaults={"status": _STATUS_MAP[legacy_row.status], "notes": legacy_row.notes})
        report.attendance_created += int(created)
        report.attendance_existing += int(not created)
        horse = _canonical_horse(lesson.team_id, legacy_row.horse_name)
        assignment_notes = f"Legacy horse: {legacy_row.horse_name.strip()}" if legacy_row.horse_name and not horse else ""
        _, created = LessonAssignment.objects.get_or_create(occurrence=occurrence, person=person, role=LessonAssignment.Role.PARTICIPANT, defaults={"horse": horse, "notes": assignment_notes})
        report.assignments_created += int(created)
        report.assignments_existing += int(not created)


def _convert_one(lesson, report, *, dry_run):
    rows_by_level, row_issues = _legacy_rows_by_level(lesson)
    if row_issues:
        report.issues.append(LegacyIEALessonIssue(lesson.id, "Attendance roster issue(s): " + "; ".join(row_issues) + "."))
        return
    levels = _conversion_levels(lesson, rows_by_level)
    if not levels:
        report.issues.append(LegacyIEALessonIssue(lesson.id, "Could not determine Futures/Upper team level from the lesson group or roster."))
        return
    report.lessons_convertible += 1
    if dry_run:
        return
    split = len(levels) > 1
    for team_level in levels:
        _convert_partition(lesson, team_level, rows_by_level[team_level], report, split=split)


def convert_legacy_iea_lessons(*, team=None, season=None, dry_run=True):
    """Report or convert legacy IEA lessons into the v3.4 lesson engine."""
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
