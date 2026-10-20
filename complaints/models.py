from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from accounts.models import User
from notifications.models import Notification
from results.models import Result


class Complaint(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        AWAITING_LECTURER = "AWAITING_LECTURER", "Awaiting Lecturer"
        AWAITING_EXAM_OFFICER = "AWAITING_EXAM_OFFICER", "Awaiting Exam Officer"
        AWAITING_HOD = "AWAITING_HOD", "Awaiting HOD"
        RESOLVED = "RESOLVED", "Resolved"
        REJECTED = "REJECTED", "Rejected"

    class Category(models.TextChoices):
        RESULT_ERROR = "RESULT_ERROR", "Result error"
        MISSING_RESULT = "MISSING_RESULT", "Missing result"
        GRADE_DISCREPANCY = "GRADE_DISCREPANCY", "Grade discrepancy"
        MISCLASSIFICATION = "MISCLASSIFICATION", "Course or classification issue"
        OTHER = "OTHER", "Other"

    reference_number = models.CharField(max_length=20, unique=True, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_complaints",
        limit_choices_to={"role": "STUDENT"},
    )
    result = models.ForeignKey(
        Result,
        on_delete=models.PROTECT,
        related_name="complaints",
        null=True,
        blank=True,
    )
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.RESULT_ERROR,
    )
    subject = models.CharField(max_length=200)
    description = models.TextField()
    contact_preference = models.CharField(max_length=50, blank=True)
    contact_details = models.CharField(max_length=200, blank=True)
    requested_resolution = models.TextField(blank=True)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lecturer_complaints",
        limit_choices_to={"role": "LECTURER"},
    )
    exam_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exam_officer_complaints",
        limit_choices_to={"role": "EXAM_OFFICER"},
    )
    hod = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hod_complaints",
        limit_choices_to={"role": "HOD"},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Complaint"
        verbose_name_plural = "Complaints"

    def clean(self):
        super().clean()
        errors = {}

        if self.student_id and self.result_id:
            if self.result.course_registration.student.user_id != self.student_id:
                errors["result"] = "You cannot complain about another student's result."

        if self.status in {self.Status.RESOLVED, self.Status.REJECTED} and not self.resolution_reason:
            errors["resolution_reason"] = "A reason is required when resolving or rejecting a complaint."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        if not self.subject:
            self.subject = self.category.replace("_", " ").title()

        super().save(*args, **kwargs)

    @staticmethod
    def generate_reference_number():
        import uuid

        return f"CMP-{uuid.uuid4().hex[:10].upper()}"

    @property
    def resolution_reason(self):
        latest = self.history.order_by("-created_at").first()
        if latest and latest.decision_message:
            return latest.decision_message
        return ""

    @property
    def current_assignee(self):
        if self.status == self.Status.AWAITING_LECTURER:
            return self.lecturer
        if self.status == self.Status.AWAITING_EXAM_OFFICER:
            return self.exam_officer
        if self.status == self.Status.AWAITING_HOD:
            return self.hod
        return None

    def record_history(
        self,
        actor,
        previous_status,
        new_status,
        message="",
        decision_message="",
        is_internal_note=False,
    ):
        actor_id = getattr(actor, "id", None)
        duplicate_entry = self.history.filter(
            actor_id=actor_id,
            previous_status=previous_status,
            new_status=new_status,
            message=message,
            decision_message=decision_message,
            is_internal_note=is_internal_note,
        ).order_by("-created_at").first()

        if duplicate_entry:
            return duplicate_entry

        return ComplaintHistory.objects.create(
            complaint=self,
            actor=actor,
            previous_status=previous_status,
            new_status=new_status,
            message=message,
            decision_message=decision_message,
            is_internal_note=is_internal_note,
        )

    def add_note(self, actor, note, is_internal=True):
        return ComplaintNote.objects.create(
            complaint=self,
            created_by=actor,
            note=note,
            is_internal=is_internal,
        )

    def ensure_recipients(self):
        recipients = []
        for user in [self.lecturer, self.exam_officer, self.hod]:
            if not user:
                continue
            recipient, _ = ComplaintRecipient.objects.get_or_create(
                complaint=self,
                user=user,
                defaults={"role": user.role},
            )
            if recipient.role != user.role:
                recipient.role = user.role
                recipient.save(update_fields=["role"])
            recipient.mark_delivered()
            if self.student_id and user.id != self.student_id:
                Notification.create_for(
                    recipient=user,
                    title="Complaint assigned",
                    message=f"New complaint {self.reference_number} requires your review.",
                    link=f"/complaints/{self.reference_number}/",
                    complaint=self,
                )
            recipients.append(recipient)
        return recipients

    def recipient_status_for(self, user):
        if not user:
            return {"delivered": False, "read": False}
        recipient = self.recipients.filter(user=user).first()
        if not recipient:
            return {"delivered": False, "read": False}
        return {
            "delivered": bool(recipient.delivered_at),
            "read": bool(recipient.first_read_at),
            "first_read_at": recipient.first_read_at,
            "last_read_at": recipient.last_read_at,
        }

    def receipt_summary_for_student(self):
        rows = []
        for label, user in [
            ("Lecturer", self.lecturer),
            ("Examination Officer", self.exam_officer),
            ("HOD", self.hod),
        ]:
            if not user:
                rows.append({"label": label, "delivered": False, "read": False})
                continue
            status = self.recipient_status_for(user)
            rows.append({
                "label": label,
                "delivered": status["delivered"],
                "read": status["read"],
            })
        return rows

    def mark_recipient_read(self, user):
        if not user:
            return None
        recipient, _ = ComplaintRecipient.objects.get_or_create(
            complaint=self,
            user=user,
            defaults={"role": user.role},
        )
        recipient.mark_delivered()
        recipient.mark_read()
        return recipient

    def __str__(self):
        return f"{self.reference_number} - {self.subject}"

    def track_as_read(self, user):
        if not user:
            return None
        recipient = self.recipients.filter(user=user).first()
        if not recipient:
            recipient = ComplaintRecipient.objects.create(
                complaint=self,
                user=user,
                role=getattr(user, "role", ""),
            )
        recipient.mark_delivered()
        recipient.mark_read()
        return recipient


class ComplaintHistory(models.Model):
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="history",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaint_history_actions",
    )
    previous_status = models.CharField(
        max_length=24,
        choices=Complaint.Status.choices,
        blank=True,
    )
    new_status = models.CharField(
        max_length=24,
        choices=Complaint.Status.choices,
    )
    message = models.TextField(blank=True)
    decision_message = models.TextField(blank=True)
    is_internal_note = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.complaint.reference_number} - {self.new_status}"


class ComplaintNote(models.Model):
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaint_notes",
    )
    note = models.TextField()
    is_internal = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note for {self.complaint.reference_number}"


class ComplaintRecipient(models.Model):
    complaint = models.ForeignKey(
        "Complaint",
        on_delete=models.CASCADE,
        related_name="recipients",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="complaint_recipients",
    )
    role = models.CharField(
        max_length=20,
        choices=User.Role.choices,
        blank=True,
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    first_read_at = models.DateTimeField(null=True, blank=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        unique_together = [("complaint", "user")]

    @property
    def is_delivered(self):
        return bool(self.delivered_at)

    @property
    def has_read(self):
        return bool(self.first_read_at)

    def mark_delivered(self):
        if not self.delivered_at:
            self.delivered_at = timezone.now()
            self.save(update_fields=["delivered_at"])
        return self

    def mark_read(self):
        now = timezone.now()
        if not self.first_read_at:
            self.first_read_at = now
        self.last_read_at = now
        self.save(update_fields=["first_read_at", "last_read_at"])
        return self

    def __str__(self):
        return f"{self.user} -> {self.complaint.reference_number}"
