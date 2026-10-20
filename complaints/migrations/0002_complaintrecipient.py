from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("complaints", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ComplaintRecipient",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(blank=True, choices=[("STUDENT", "Student"), ("LECTURER", "Lecturer"), ("EXAM_OFFICER", "Exam Officer"), ("HOD", "Head of Department")], max_length=20)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("first_read_at", models.DateTimeField(blank=True, null=True)),
                ("last_read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("complaint", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recipients", to="complaints.complaint")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="complaint_recipients", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["created_at"],
                "unique_together": {("complaint", "user")},
            },
        ),
    ]
