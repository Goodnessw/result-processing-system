from django.conf import settings
from django.db import models


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    complaint = models.ForeignKey(
        "complaints.Complaint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    result = models.ForeignKey(
        "results.Result",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_as_read(self):
        if not self.is_read:
            from django.utils import timezone

            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])
        return self

    @classmethod
    def unread_count_for(cls, user):
        return cls.objects.filter(recipient=user, is_read=False).count()

    @classmethod
    def create_for(
        cls, recipient, title, message, link="", complaint=None, result=None
    ):
        if not recipient:
            return None
        existing = cls.objects.filter(
            recipient=recipient,
            complaint=complaint,
            result=result,
            title=title,
            message=message,
            is_read=False,
        ).first()
        if existing:
            return existing
        return cls.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            link=link,
            complaint=complaint,
            result=result,
        )

    def __str__(self):
        return f"{self.recipient} - {self.title}"
