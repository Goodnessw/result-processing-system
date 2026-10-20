
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.conf import settings


class Department(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Departments"

    def __str__(self):
        return f"{self.code} - {self.name}"


class Programme(models.Model):
    class DegreeType(models.TextChoices):
        ND = "ND", "National Diploma"
        HND = "HND", "Higher National Diploma"
        BSC = "BSC", "Bachelor of Science"
        BENG = "BENG", "Bachelor of Engineering"
        BA = "BA", "Bachelor of Arts"
        MSC = "MSC", "Master of Science"
        MENG = "MENG", "Master of Engineering"
        PHD = "PHD", "Doctor of Philosophy"

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="programmes",
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, unique=True)
    degree_type = models.CharField(
        max_length=10,
        choices=DegreeType.choices,
    )
    duration_years = models.PositiveSmallIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["department", "name"],
                name="unique_programme_name_per_department",
            )
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class AcademicSession(models.Model):
    name = models.CharField(
        max_length=9,
        unique=True,
        help_text="Example: 2026/2027",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Academic Session"
        verbose_name_plural = "Academic Sessions"

    def clean(self):
        super().clean()

        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValidationError({
                    "end_date": "End date must be after start date."
                })

    def save(self, *args, **kwargs):
        self.full_clean()

        with transaction.atomic():
            if self.is_current:
                AcademicSession.objects.exclude(pk=self.pk).update(
                    is_current=False
                )

            super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Semester(models.Model):
    class SemesterType(models.TextChoices):
        FIRST = "FIRST", "First Semester"
        SECOND = "SECOND", "Second Semester"
        SUMMER = "SUMMER", "Summer Semester"

    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name="semesters",
    )
    name = models.CharField(
        max_length=10,
        choices=SemesterType.choices,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["session", "start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "name"],
                name="unique_semester_per_session",
            )
        ]

    def clean(self):
        super().clean()

        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValidationError({
                    "end_date": "End date must be after start date."
                })

        if self.session_id and self.start_date and self.end_date:
            if (
                self.start_date < self.session.start_date
                or self.end_date > self.session.end_date
            ):
                raise ValidationError(
                    "Semester dates must fall within the academic session."
                )

    def save(self, *args, **kwargs):
        self.full_clean()

        with transaction.atomic():
            if self.is_current:
                Semester.objects.exclude(pk=self.pk).update(
                    is_current=False
                )

            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.session.name} - {self.get_name_display()}"


class Course(models.Model):
    class Level(models.IntegerChoices):
        LEVEL_100 = 100, "100 Level"
        LEVEL_200 = 200, "200 Level"
        LEVEL_300 = 300, "300 Level"
        LEVEL_400 = 400, "400 Level"
        LEVEL_500 = 500, "500 Level"
        LEVEL_600 = 600, "600 Level"

    programme = models.ForeignKey(
        Programme,
        on_delete=models.PROTECT,
        related_name="courses",
    )
    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teaching_courses",
        limit_choices_to={"role": "LECTURER"},
    )
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    credit_units = models.PositiveSmallIntegerField(default=2)
    level = models.PositiveSmallIntegerField(choices=Level.choices)
    semester = models.ForeignKey(
        Semester,
        on_delete=models.PROTECT,
        related_name="courses",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["level", "code"]

    def clean(self):
        super().clean()

        if self.credit_units < 1:
            raise ValidationError({
                "credit_units": "Credit units must be at least 1."
            })

        if self.lecturer_id:
            from accounts.models import User

            if self.lecturer.role != User.Role.LECTURER:
                raise ValidationError({
                    "lecturer": "Only users with the Lecturer role can be assigned."
                })

    def __str__(self):
        return f"{self.code} - {self.title}"

    

class StudentProfile(models.Model):
    class StudyStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        DEFERRED = "DEFERRED", "Deferred"
        GRADUATED = "GRADUATED", "Graduated"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="student_profile",
    )
    programme = models.ForeignKey(
        Programme,
        on_delete=models.PROTECT,
        related_name="students",
    )
    admission_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name="admitted_students",
    )
    current_level = models.PositiveSmallIntegerField(
        choices=Course.Level.choices,
        default=100,
    )
    status = models.CharField(
        max_length=12,
        choices=StudyStatus.choices,
        default=StudyStatus.ACTIVE,
    )
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"

    def clean(self):
        super().clean()

        if self.user_id:
            from accounts.models import User

            if self.user.role != User.Role.STUDENT:
                raise ValidationError({
                    "user": "Only student accounts can have a student profile."
                })

    def __str__(self):
        return (
            f"{self.user.get_full_name() or self.user.username} "
            f"- {self.programme.code}"
        )


class CourseRegistration(models.Model):
    class RegistrationStatus(models.TextChoices):
        REGISTERED = "REGISTERED", "Registered"
        DROPPED = "DROPPED", "Dropped"
        COMPLETED = "COMPLETED", "Completed"

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name="course_registrations",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="registrations",
    )
    status = models.CharField(
        max_length=12,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.REGISTERED,
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["student", "course__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_registration",
            )
        ]

    def clean(self):
        super().clean()

        if self.student_id and self.course_id:
            if self.student.programme_id != self.course.programme_id:
                from django.core.exceptions import ValidationError

                raise ValidationError({
                    "course": (
                        "This course does not belong to the student's programme."
                    )
                })

            if self.student.current_level != self.course.level:
                from django.core.exceptions import ValidationError

                raise ValidationError({
                    "course": (
                        "This course does not match the student's current level."
                    )
                })

    def __str__(self):
        return f"{self.student} - {self.course.code}"
