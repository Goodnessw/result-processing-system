from django.contrib import admin

from .models import (
    AcademicSession,
    Course,
    CourseRegistration,
    Department,
    Programme,
    Semester,
    StudentProfile,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("name",)


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "department",
        "degree_type",
        "duration_years",
        "is_active",
    )
    list_filter = ("degree_type", "department", "is_active")
    search_fields = ("code", "name", "department__name")
    autocomplete_fields = ("department",)
    ordering = ("name",)


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "start_date",
        "end_date",
        "is_current",
        "is_active",
    )
    list_filter = ("is_current", "is_active")
    search_fields = ("name",)
    ordering = ("-start_date",)


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = (
        "session",
        "name",
        "start_date",
        "end_date",
        "is_current",
        "is_active",
    )
    list_filter = ("session", "name", "is_current", "is_active")
    search_fields = ("session__name",)
    autocomplete_fields = ("session",)
    ordering = ("-session__start_date", "start_date")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "programme",
        "lecturer",
        "level",
        "credit_units",
        "semester",
        "is_active",
    )
    list_filter = (
        "level",
        "semester",
        "programme",
        "lecturer",
        "is_active",
    )
    search_fields = (
        "code",
        "title",
        "programme__name",
        "programme__code",
        "lecturer__username",
        "lecturer__first_name",
        "lecturer__last_name",
        "lecturer__staff_number",
    )
    autocomplete_fields = ("programme", "semester", "lecturer")
    list_select_related = ("programme", "semester", "lecturer")
    ordering = ("level", "code")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "get_student",
        "get_matric_number",
        "programme",
        "admission_session",
        "current_level",
        "status",
    )
    list_filter = (
        "programme",
        "admission_session",
        "current_level",
        "status",
    )
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "user__matric_number",
        "programme__name",
    )
    autocomplete_fields = ("user", "programme", "admission_session")
    list_select_related = ("user", "programme", "admission_session")

    @admin.display(description="Student", ordering="user__username")
    def get_student(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description="Matric Number", ordering="user__matric_number")
    def get_matric_number(self, obj):
        return obj.user.matric_number or "-"


@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "course",
        "get_session",
        "status",
        "registered_at",
    )
    list_filter = (
        "status",
        "course__semester__session",
        "course__level",
    )
    search_fields = (
        "student__user__username",
        "student__user__first_name",
        "student__user__last_name",
        "student__user__matric_number",
        "course__code",
        "course__title",
    )
    autocomplete_fields = ("student", "course")
    list_select_related = (
        "student__user",
        "course",
        "course__semester__session",
    )

    @admin.display(description="Academic Session")
    def get_session(self, obj):
        return obj.course.semester.session.name
