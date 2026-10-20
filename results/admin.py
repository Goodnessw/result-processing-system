
from django.contrib import admin

from .models import Result, ResultAuditLog


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = (
        "get_student",
        "get_matric_number",
        "get_course",
        "ca_score",
        "exam_score",
        "total_score",
        "grade",
        "grade_point",
        "status",
    )

    list_filter = (
        "status",
        "grade",
        "course_registration__course__level",
        "course_registration__course__semester__session",
    )

    search_fields = (
        "course_registration__student__user__username",
        "course_registration__student__user__matric_number",
        "course_registration__student__user__first_name",
        "course_registration__student__user__last_name",
        "course_registration__course__code",
        "course_registration__course__title",
    )

    autocomplete_fields = (
        "course_registration",
        "entered_by",
        "approved_by",
    )

    list_select_related = (
        "course_registration__student__user",
        "course_registration__course",
        "entered_by",
        "approved_by",
    )

    readonly_fields = (
        "total_score",
        "grade",
        "grade_point",
        "remark",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Student")
    def get_student(self, obj):
        user = obj.course_registration.student.user
        return user.get_full_name() or user.username

    @admin.display(description="Matric Number")
    def get_matric_number(self, obj):
        return obj.course_registration.student.user.matric_number or "-"

    @admin.display(description="Course")
    def get_course(self, obj):
        return obj.course_registration.course.code


@admin.register(ResultAuditLog)
class ResultAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "result",
        "action",
        "performed_by",
        "created_at",
    )

    list_filter = ("action", "created_at")

    search_fields = (
        "result__course_registration__student__user__username",
        "result__course_registration__student__user__matric_number",
        "result__course_registration__course__code",
        "performed_by__username",
    )

    autocomplete_fields = ("result", "performed_by")
    list_select_related = ("result", "performed_by")

    readonly_fields = (
        "result",
        "action",
        "performed_by",
        "details",
        "created_at",
    )
