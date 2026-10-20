from django import forms

from academics.models import AcademicSession, Semester
from results.models import Result
from .models import Complaint


class ComplaintSubmissionForm(forms.ModelForm):
    # Use semester only (semester implies session) to avoid session/semester mismatch
    semester = forms.ModelChoiceField(
        queryset=Semester.objects.filter(is_active=True).order_by("-session__start_date", "start_date"),
        required=False,
        empty_label="Select semester",
        label="Semester",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    result = forms.ModelChoiceField(
        queryset=Result.objects.none(),
        required=False,
        label="Result / missing result",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Complaint
        fields = [
            "result",
            "category",
            "subject",
            "description",
            "contact_preference",
            "contact_details",
            "requested_resolution",
        ]
        widgets = {
            "result": forms.Select(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "contact_preference": forms.TextInput(attrs={"class": "form-control"}),
            "contact_details": forms.TextInput(attrs={"class": "form-control"}),
            "requested_resolution": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def _apply_result_queryset(self, semester=None):
        qs = Result.objects.filter(course_registration__student__user=self.student)
        if semester:
            qs = qs.filter(course_registration__course__semester=semester)

        qs = qs.select_related(
            "course_registration__course__semester__session",
            "course_registration__course",
            "course_registration__student__user",
        ).order_by("course_registration__course__code")

        self.fields["result"].queryset = qs
        choices = [('', 'Select a result for this complaint')]
        for result in qs:
            course = result.course_registration.course
            grade_label = result.grade or "NR"
            label = f"{course.code} — {course.title} — Grade: {grade_label}"
            choices.append((str(result.pk), label))

        if not choices[1:]:
            choices = [('', 'No results available for the selected session and semester. Choose “Missing result” below if the result is absent.')]

        self.fields["result"].choices = choices

    def __init__(self, student, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.student = student

        selected_semester = None
        semester_value = self.data.get("semester") if self.data else None

        if semester_value:
            try:
                selected_semester = Semester.objects.get(pk=semester_value)
            except (Semester.DoesNotExist, ValueError):
                selected_semester = None

        # If no semester provided, default to the most recent active semester
        if not selected_semester:
            selected_semester = Semester.objects.filter(is_active=True).order_by("-session__start_date", "start_date").first()

        # Populate semester queryset (show active semesters)
        self.fields["semester"].queryset = Semester.objects.filter(is_active=True).order_by("-session__start_date", "start_date")

        if selected_semester:
            self.fields["semester"].initial = selected_semester

        self._apply_result_queryset(semester=selected_semester)

    def clean_result(self):
        result = self.cleaned_data.get("result")
        if result and result.course_registration.student.user != self.student:
            raise forms.ValidationError(
                "You can only submit a complaint for one of your own results."
            )
        return result

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        result = cleaned_data.get("result")

        if not result and category != Complaint.Category.MISSING_RESULT:
            self.add_error("result", "Please select the result you want to report.")

        if result and category == Complaint.Category.MISSING_RESULT:
            self.add_error("category", "Choose the missing-result option only when no result is available for the selected course.")

        if not result:
            return cleaned_data

        active_qs = Complaint.objects.filter(
            student=self.student,
            result=result,
            category=category,
        ).exclude(status__in=[Complaint.Status.RESOLVED, Complaint.Status.REJECTED])

        if self.instance.pk:
            active_qs = active_qs.exclude(pk=self.instance.pk)

        if active_qs.exists():
            raise forms.ValidationError(
                "An active complaint for this result and issue already exists."
            )

        return cleaned_data
