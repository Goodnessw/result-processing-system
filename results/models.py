from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Result(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        VERIFIED = "VERIFIED", "Verified by Exam Officer"
        APPROVED = "APPROVED", "Approved by HOD"
        REJECTED = "REJECTED", "Rejected"

    course_registration = models.OneToOneField(
        "academics.CourseRegistration",
        on_delete=models.CASCADE,
        related_name="result",
    )

    ca_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(30),
        ],
    )

    exam_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(70),
        ],
    )

    total_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        editable=False,
    )

    grade = models.CharField(max_length=2, blank=True, editable=False)
    grade_point = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        editable=False,
    )
    remark = models.CharField(max_length=20, blank=True, editable=False)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entered_results",
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_results",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_results",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_grade(self):
        score = self.total_score

        if score >= 70:
            return "A", 5, "Excellent"
        elif score >= 60:
            return "B", 4, "Very Good"
        elif score >= 50:
            return "C", 3, "Good"
        elif score >= 45:
            return "D", 2, "Fair"
        elif score >= 40:
            return "E", 1, "Pass"
        return "F", 0, "Fail"

    def clean(self):
        super().clean()

        errors = {}

        if self.ca_score is not None and not 0 <= self.ca_score <= 30:
            errors["ca_score"] = "CA score must be between 0 and 30."

        if self.exam_score is not None and not 0 <= self.exam_score <= 70:
            errors["exam_score"] = "Exam score must be between 0 and 70."

        if self.status == self.Status.VERIFIED and not self.verified_by:
            errors["verified_by"] = (
                "An examination officer is required for a verified result."
            )

        if self.status == self.Status.APPROVED and not self.approved_by:
            errors["approved_by"] = (
                "A Head of Department is required for an approved result."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.total_score = (self.ca_score or 0) + (self.exam_score or 0)
        self.grade, points, self.remark = self.calculate_grade()
        self.grade_point = points
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.course_registration} - "
            f"{self.total_score} ({self.grade})"
        )

    class Meta:
        ordering = ["course_registration"]
        verbose_name = "Result"
        verbose_name_plural = "Results"


class ResultAuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = "CREATED", "Created"
        UPDATED = "UPDATED", "Updated"
        SUBMITTED = "SUBMITTED", "Submitted"
        VERIFIED = "VERIFIED", "Verified"
        FORWARDED = "FORWARDED", "Forwarded"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CLEARED = "CLEARED", "Cleared"
        CORRECTED = "CORRECTED", "Corrected"

    result = models.ForeignKey(
        Result,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    action = models.CharField(
        max_length=10,
        choices=Action.choices,
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="result_audit_logs",
    )

    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} - Result #{self.result_id}"
