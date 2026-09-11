from django.contrib import admin
from .models import (
    Announcement, CalendarEvent, GuardianContact, Rider, RiderGuardian, Season,
    SeasonClass, SeasonMembership, SeasonScoringConfig, QualificationOverride, Show, ShowClass, ShowEntry, ShowResult, Team, UserProfile,
    LessonGroup, Lesson, LessonAttendance, ShowAvailability, VolunteerLog, Notification,
    CommitteeAssignment, ShowLeadAssignment, ShowPlanningItem, ShowDayUpdate, RiderDevelopmentNote, RiderAward,
    FinancialAccount, FinancialCategory, FinancialTransaction, SeasonBudget,
    HomeBarn, MembershipDuesRate, FamilyCharge, FamilyCredit, ServiceAgreementCredit,
    FinancialAssistanceAward, AssistanceClaim, FamilyPayment,
)

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "discipline")

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "start_date", "end_date", "is_active", "is_closed", "futures_volunteer_hours_required", "upper_volunteer_hours_required")
    list_filter = ("team", "is_active", "is_closed")

@admin.register(SeasonClass)
class SeasonClassAdmin(admin.ModelAdmin):
    list_display = ("name", "season", "team_level", "discipline", "active")
    list_filter = ("season", "team_level", "discipline", "active")
    search_fields = ("name",)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "role", "must_change_password")
    list_filter = ("role", "team", "must_change_password")

class RiderGuardianInline(admin.TabularInline):
    model = RiderGuardian
    extra = 0

@admin.register(GuardianContact)
class GuardianContactAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "team", "email", "phone", "user")
    list_filter = ("team",)
    search_fields = ("first_name", "last_name", "email", "phone")

@admin.register(Rider)
class RiderAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "team", "email", "school", "grade", "active")
    list_filter = ("team", "active", "grade")
    search_fields = ("first_name", "last_name", "email", "school", "iea_member_number")
    inlines = [RiderGuardianInline]

@admin.register(SeasonMembership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("rider", "season", "team_level")
    list_filter = ("season", "team_level")
    filter_horizontal = ("classes",)

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "team", "audience", "priority", "published", "created_at")
    list_filter = ("team", "audience", "priority", "published")
    filter_horizontal = ("selected_users",)

@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("title", "team", "kind", "starts_at", "all_day", "location")
    list_filter = ("team", "kind")

class ShowClassInline(admin.TabularInline):
    model = ShowClass
    extra = 0

@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "season", "show_date", "status", "venue")
    list_filter = ("team", "season", "status")
    search_fields = ("name", "venue", "host_team")
    inlines = [ShowClassInline]

@admin.register(ShowClass)
class ShowClassAdmin(admin.ModelAdmin):
    list_display = ("show", "season_class", "class_number")
    list_filter = ("show", "season_class__team_level")

@admin.register(ShowEntry)
class ShowEntryAdmin(admin.ModelAdmin):
    list_display = ("rider", "show_class", "entry_type", "is_point_rider", "status")
    list_filter = ("entry_type", "is_point_rider", "status")
    search_fields = ("rider__first_name", "rider__last_name", "show_class__name")

@admin.register(ShowResult)
class ShowResultAdmin(admin.ModelAdmin):
    list_display = ("entry", "place", "points", "horse_name")


@admin.register(SeasonScoringConfig)
class SeasonScoringConfigAdmin(admin.ModelAdmin):
    list_display = ("season", "individual_qualification_points", "team_qualification_points")

@admin.register(QualificationOverride)
class QualificationOverrideAdmin(admin.ModelAdmin):
    list_display = ("membership", "season_class", "status")
    list_filter = ("status", "season_class__season")


@admin.register(LessonGroup)
class LessonGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "season", "team_level", "coach", "active")
    list_filter = ("season", "team_level", "active")
    filter_horizontal = ("riders",)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "season", "starts_at", "group", "coach", "cancelled")
    list_filter = ("season", "cancelled", "group")

@admin.register(LessonAttendance)
class LessonAttendanceAdmin(admin.ModelAdmin):
    list_display = ("lesson", "rider", "status", "horse_name")
    list_filter = ("status", "lesson__season")

@admin.register(ShowAvailability)
class ShowAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("show", "rider", "status", "responded_at")
    list_filter = ("status", "show__season")

@admin.register(VolunteerLog)
class VolunteerLogAdmin(admin.ModelAdmin):
    list_display = ("rider", "season", "service_date", "hours", "category", "status")
    list_filter = ("season", "status", "category")
    search_fields = ("rider__first_name", "rider__last_name", "performed_by", "description")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "created_at", "read_at")
    list_filter = ("created_at", "read_at")
    search_fields = ("user__username", "user__first_name", "user__last_name", "title")


@admin.register(RiderDevelopmentNote)
class RiderDevelopmentNoteAdmin(admin.ModelAdmin):
    list_display = ("rider", "season", "author", "family_visible", "created_at")
    list_filter = ("season", "family_visible")


@admin.register(RiderAward)
class RiderAwardAdmin(admin.ModelAdmin):
    list_display = ("title", "rider", "season", "published", "presentation_date")
    list_filter = ("season", "published")


@admin.register(FinancialAccount)
class FinancialAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "account_type", "opening_balance", "active")
    list_filter = ("team", "account_type", "active")


@admin.register(FinancialCategory)
class FinancialCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "kind", "active", "sort_order")
    list_filter = ("team", "kind", "active")


@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_date", "team", "kind", "category", "amount", "description", "updated_by")
    list_filter = ("team", "season", "kind", "category")
    search_fields = ("description", "payee", "reference")


@admin.register(SeasonBudget)
class SeasonBudgetAdmin(admin.ModelAdmin):
    list_display = ("season", "category", "amount", "updated_by", "updated_at")
    list_filter = ("season", "category")


@admin.register(HomeBarn)
class HomeBarnAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "active")
    list_filter = ("team", "active")


@admin.register(MembershipDuesRate)
class MembershipDuesRateAdmin(admin.ModelAdmin):
    list_display = ("season", "home_barn", "amount", "due_date")
    list_filter = ("season", "home_barn")


@admin.register(FamilyCharge)
class FamilyChargeAdmin(admin.ModelAdmin):
    list_display = ("membership", "charge_type", "description", "amount", "due_date", "status")
    list_filter = ("membership__season", "charge_type", "status")
    search_fields = ("membership__rider__first_name", "membership__rider__last_name", "description")


@admin.register(FamilyCredit)
class FamilyCreditAdmin(admin.ModelAdmin):
    list_display = ("charge", "credit_type", "amount", "status", "source")
    list_filter = ("credit_type", "status")


@admin.register(ServiceAgreementCredit)
class ServiceAgreementCreditAdmin(admin.ModelAdmin):
    list_display = ("membership", "description", "amount", "status", "completed_date")
    list_filter = ("membership__season", "status")
    filter_horizontal = ("required_shows",)


@admin.register(FinancialAssistanceAward)
class FinancialAssistanceAwardAdmin(admin.ModelAdmin):
    list_display = ("membership", "provider", "program_name", "approved_maximum", "status")
    list_filter = ("membership__season", "provider", "status")


@admin.register(AssistanceClaim)
class AssistanceClaimAdmin(admin.ModelAdmin):
    list_display = ("award", "charge", "amount_requested", "reimbursed_amount", "status", "received_date")
    list_filter = ("status", "award__membership__season")


@admin.register(FamilyPayment)
class FamilyPaymentAdmin(admin.ModelAdmin):
    list_display = ("membership", "charge", "amount", "received_date", "account")
    list_filter = ("membership__season", "received_date")


@admin.register(ShowDayUpdate)
class ShowDayUpdateAdmin(admin.ModelAdmin):
    list_display = ("title", "show", "audience", "published", "send_email", "created_by", "created_at")
    list_filter = ("audience", "published", "send_email", "show__season")
    search_fields = ("title", "body", "show__name")
