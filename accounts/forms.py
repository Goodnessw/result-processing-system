from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from academics.models import AcademicSession, Course, Department, Programme, Semester, StudentProfile

User = get_user_model()


class StudentRegistrationForm(forms.Form):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    matric_number = forms.CharField(max_length=30)
    programme = forms.ModelChoiceField(queryset=Programme.objects.filter(is_active=True).order_by("name"))
    admission_session = forms.ModelChoiceField(queryset=AcademicSession.objects.filter(is_active=True).order_by("-start_date"))
    current_level = forms.ChoiceField(choices=[(100, "100 Level"), (200, "200 Level"), (300, "300 Level"), (400, "400 Level"), (500, "500 Level"), (600, "600 Level")])
    status = forms.ChoiceField(choices=StudentProfile.StudyStatus.choices)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with this username already exists.")
        return username

    def clean_matric_number(self):
        matric_number = self.cleaned_data["matric_number"].strip()
        if User.objects.filter(matric_number__iexact=matric_number).exists():
            raise ValidationError("This matriculation number is already assigned.")
        return matric_number

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["username"].strip(),
            email=self.cleaned_data["email"].strip() or "",
            password=self.cleaned_data["password"],
            first_name=self.cleaned_data["first_name"].strip(),
            last_name=self.cleaned_data["last_name"].strip(),
            role=User.Role.STUDENT,
            matric_number=self.cleaned_data["matric_number"].strip(),
            is_active=True,
        )
        profile = StudentProfile.objects.create(
            user=user,
            programme=self.cleaned_data["programme"],
            admission_session=self.cleaned_data["admission_session"],
            current_level=int(self.cleaned_data["current_level"]),
            status=self.cleaned_data["status"],
        )
        return user, profile


class LecturerRegistrationForm(forms.Form):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    staff_number = forms.CharField(max_length=30)
    department = forms.CharField(max_length=150, required=False)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with this username already exists.")
        return username

    def clean_staff_number(self):
        staff_number = self.cleaned_data["staff_number"].strip()
        if User.objects.filter(staff_number__iexact=staff_number).exists():
            raise ValidationError("This staff number already exists.")
        return staff_number

    def save(self):
        return User.objects.create_user(
            username=self.cleaned_data["username"].strip(),
            email=self.cleaned_data["email"].strip() or "",
            password=self.cleaned_data["password"],
            first_name=self.cleaned_data["first_name"].strip(),
            last_name=self.cleaned_data["last_name"].strip(),
            role=User.Role.LECTURER,
            staff_number=self.cleaned_data["staff_number"].strip(),
            department=self.cleaned_data["department"].strip(),
            is_active=True,
        )


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "description", "is_active"]


class ProgrammeForm(forms.ModelForm):
    class Meta:
        model = Programme
        fields = ["department", "name", "code", "degree_type", "duration_years", "is_active"]


class AcademicSessionForm(forms.ModelForm):
    class Meta:
        model = AcademicSession
        fields = ["name", "start_date", "end_date", "is_current", "is_active"]
        labels = {
            "name": "Name",
            "start_date": "Start date",
            "end_date": "End date",
            "is_current": "Is current",
            "is_active": "Is active",
        }
        help_texts = {"name": "Example: 2026/2027"}
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class SemesterForm(forms.ModelForm):
    class Meta:
        model = Semester
        fields = ["session", "name", "start_date", "end_date", "is_current", "is_active"]
        labels = {
            "session": "Session",
            "name": "Name",
            "start_date": "Start date",
            "end_date": "End date",
            "is_current": "Is current",
            "is_active": "Is active",
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["programme", "code", "title", "credit_units", "level", "semester", "lecturer", "description", "is_active"]

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip()
        if not code:
            return code
        qs = Course.objects.filter(code__iexact=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A course with this code already exists.")
        return code
