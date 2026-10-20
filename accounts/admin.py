from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "department",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "role",
        "department",
        "is_staff",
        "is_active",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "matric_number",
        "staff_number",
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "Academic and Staff Information",
            {
                "fields": (
                    "role",
                    "matric_number",
                    "staff_number",
                    "department",
                    "phone_number",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Academic and Staff Information",
            {
                "fields": (
                    "role",
                    "matric_number",
                    "staff_number",
                    "department",
                    "phone_number",
                )
            },
        ),
    )
