from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        LECTURER = "LECTURER", "Lecturer"
        EXAM_OFFICER = "EXAM_OFFICER", "Examination Officer"
        HOD = "HOD", "Head of Department"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )

    matric_number = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
    )

    staff_number = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
    )

    department = models.CharField(
        max_length=150,
        blank=True,
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
    )

    @property
    def unread_notifications_count(self):
        from notifications.models import Notification

        return Notification.objects.filter(recipient=self, is_read=False).count()

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
