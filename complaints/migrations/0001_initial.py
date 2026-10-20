from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("results", "0003_result_verified_by_alter_result_status_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Complaint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference_number", models.CharField(editable=False, max_length=20, unique=True)),
                ("category", models.CharField(choices=[("RESULT_ERROR", "Result error"), ("MISSING_RESULT", "Missing result"), ("GRADE_DISCREPANCY", "Grade discrepancy"), ("MISCLASSIFICATION", "Course or classification issue"), ("OTHER", "Other")], default="RESULT_ERROR", max_length=30)),
                ("subject", models.CharField(max_length=200)),
                ("description", models.TextField()),
                ("contact_preference", models.CharField(blank=True, max_length=50)),
                ("contact_details", models.CharField(blank=True, max_length=200)),
                ("requested_resolution", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("SUBMITTED", "Submitted"), ("UNDER_REVIEW", "Under Review"), ("AWAITING_LECTURER", "Awaiting Lecturer"), ("AWAITING_EXAM_OFFICER", "Awaiting Exam Officer"), ("AWAITING_HOD", "Awaiting HOD"), ("RESOLVED", "Resolved"), ("REJECTED", "Rejected")], default="SUBMITTED", max_length=24)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("exam_officer", models.ForeignKey(blank=True, limit_choices_to={"role": "EXAM_OFFICER"}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="exam_officer_complaints", to=settings.AUTH_USER_MODEL)),
                ("hod", models.ForeignKey(blank=True, limit_choices_to={"role": "HOD"}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="hod_complaints", to=settings.AUTH_USER_MODEL)),
                ("lecturer", models.ForeignKey(blank=True, limit_choices_to={"role": "LECTURER"}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="lecturer_complaints", to=settings.AUTH_USER_MODEL)),
                ("result", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="complaints", to="results.result")),
                ("student", models.ForeignKey(blank=True, limit_choices_to={"role": "STUDENT"}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="student_complaints", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Complaint",
                "verbose_name_plural": "Complaints",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ComplaintHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_status", models.CharField(blank=True, choices=[("SUBMITTED", "Submitted"), ("UNDER_REVIEW", "Under Review"), ("AWAITING_LECTURER", "Awaiting Lecturer"), ("AWAITING_EXAM_OFFICER", "Awaiting Exam Officer"), ("AWAITING_HOD", "Awaiting HOD"), ("RESOLVED", "Resolved"), ("REJECTED", "Rejected")], max_length=24)),
                ("new_status", models.CharField(choices=[("SUBMITTED", "Submitted"), ("UNDER_REVIEW", "Under Review"), ("AWAITING_LECTURER", "Awaiting Lecturer"), ("AWAITING_EXAM_OFFICER", "Awaiting Exam Officer"), ("AWAITING_HOD", "Awaiting HOD"), ("RESOLVED", "Resolved"), ("REJECTED", "Rejected")], max_length=24)),
                ("message", models.TextField(blank=True)),
                ("decision_message", models.TextField(blank=True)),
                ("is_internal_note", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="complaint_history_actions", to=settings.AUTH_USER_MODEL)),
                ("complaint", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="history", to="complaints.complaint")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ComplaintNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("note", models.TextField()),
                ("is_internal", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("complaint", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notes", to="complaints.complaint")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="complaint_notes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
