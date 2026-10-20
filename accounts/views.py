from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden

from accounts.models import User
from academics.models import (
    StudentProfile,
    Course,
    CourseRegistration,
    AcademicSession,
    Department,
    Programme,
    Semester,
)
from .forms import (
    StudentRegistrationForm,
    LecturerRegistrationForm,
    AcademicSessionForm,
    SemesterForm,
    CourseForm,
    DepartmentForm,
    ProgrammeForm,
)
from complaints.models import Complaint
from results.models import Result


UserModel = get_user_model()


def _is_admin_user(user):
    return user.is_authenticated and (user.role == User.Role.HOD or user.is_superuser)


@login_required
def admin_dashboard(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can access the admin dashboard.")

    students = User.objects.filter(role=User.Role.STUDENT).count()
    lecturers = User.objects.filter(role=User.Role.LECTURER).count()
    courses = Course.objects.filter(is_active=True).count()
    departments = Department.objects.filter(is_active=True).count()
    pending_registrations = CourseRegistration.objects.filter(status=CourseRegistration.RegistrationStatus.REGISTERED).count()
    pending_results = Result.objects.filter(status=Result.Status.SUBMITTED).count()
    hod_results = Result.objects.filter(status=Result.Status.VERIFIED).count()
    unresolved_complaints = Complaint.objects.filter(status__in=[Complaint.Status.SUBMITTED, Complaint.Status.UNDER_REVIEW, Complaint.Status.AWAITING_LECTURER, Complaint.Status.AWAITING_EXAM_OFFICER, Complaint.Status.AWAITING_HOD]).count()

    recent_users = User.objects.order_by('-date_joined')[:8]
    recent_courses = Course.objects.select_related('programme', 'lecturer').order_by('-created_at')[:8]

    return render(
        request,
        'accounts/admin_dashboard.html',
        {
            'total_students': students,
            'total_lecturers': lecturers,
            'total_courses': courses,
            'total_departments': departments,
            'pending_registrations': pending_registrations,
            'pending_results': pending_results,
            'hod_results': hod_results,
            'unresolved_complaints': unresolved_complaints,
            'recent_users': recent_users,
            'recent_courses': recent_courses,
            'page_title': 'Administrator Dashboard',
        },
    )


@login_required
def admin_students(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can manage students.")

    students = User.objects.filter(role=User.Role.STUDENT).select_related('student_profile', 'student_profile__programme', 'student_profile__programme__department').order_by('username')
    return render(request, 'accounts/admin_students.html', {'students': students, 'page_title': 'Student Management'})


@login_required
def admin_student_create(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can create students.")

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user, profile = form.save()
            messages.success(request, f"Student account '{user.username}' created successfully.")
            return redirect('admin_students')
    else:
        form = StudentRegistrationForm()
    return render(request, 'accounts/admin_student_form.html', {'form': form, 'page_title': 'Register Student'})


@login_required
def admin_lecturers(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can manage lecturers.")

    lecturers = User.objects.filter(role=User.Role.LECTURER).order_by('username')
    return render(request, 'accounts/admin_lecturers.html', {'lecturers': lecturers, 'page_title': 'Lecturer Management'})


@login_required
def admin_lecturer_create(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can create lecturers.")

    if request.method == 'POST':
        form = LecturerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Lecturer account '{user.username}' created successfully.")
            return redirect('admin_lecturers')
    else:
        form = LecturerRegistrationForm()
    return render(request, 'accounts/admin_lecturer_form.html', {'form': form, 'page_title': 'Create Lecturer'})


@login_required
def admin_courses(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can manage courses.")

    courses = Course.objects.select_related('programme', 'semester', 'lecturer').order_by('code')
    return render(request, 'accounts/admin_courses.html', {'courses': courses, 'page_title': 'Course Management'})


@login_required
def admin_course_create(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can create courses.")

    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Course created.")
            return redirect('admin_courses')
    else:
        form = CourseForm()

    return render(request, 'accounts/admin_course_form.html', {'form': form, 'page_title': 'Create Course'})


@login_required
def admin_course_edit(request, course_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can edit courses.")

    course = get_object_or_404(Course, pk=course_id)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course updated.")
            return redirect('admin_courses')
    else:
        form = CourseForm(instance=course)

    return render(request, 'accounts/admin_course_form.html', {'form': form, 'page_title': 'Edit Course', 'course': course})


@login_required
def admin_sessions(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can manage academic sessions.")

    sessions = AcademicSession.objects.all().order_by('-start_date')
    return render(request, 'accounts/admin_sessions.html', {'sessions': sessions, 'page_title': 'Academic Sessions'})


@login_required
def admin_semesters(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can manage academic semesters.")

    semesters = Semester.objects.select_related('session').all().order_by('-session__start_date', 'start_date')
    return render(request, 'accounts/admin_semesters.html', {'semesters': semesters, 'page_title': 'Academic Semesters'})


@login_required
def admin_session_create(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can create sessions.")

    if request.method == 'POST':
        form = AcademicSessionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Academic session created.")
            return redirect('admin_sessions')
    else:
        form = AcademicSessionForm()

    return render(request, 'accounts/admin_session_form.html', {'form': form, 'page_title': 'Create Session'})


@login_required
def admin_session_edit(request, session_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can edit sessions.")

    session = get_object_or_404(AcademicSession, pk=session_id)
    if request.method == 'POST':
        form = AcademicSessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, "Academic session updated.")
            return redirect('admin_sessions')
    else:
        form = AcademicSessionForm(instance=session)

    return render(request, 'accounts/admin_session_form.html', {'form': form, 'page_title': 'Edit Session', 'session': session})


@login_required
def admin_departments(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can manage departments.")

    departments = Department.objects.all().order_by('name')
    return render(request, 'accounts/admin_departments.html', {'departments': departments, 'page_title': 'Departments'})


@login_required
def admin_department_create(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can create departments.")

    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department created.")
            return redirect('admin_departments')
    else:
        form = DepartmentForm()

    return render(request, 'accounts/admin_department_form.html', {'form': form, 'page_title': 'Create Department'})


@login_required
def admin_department_edit(request, department_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can edit departments.")

    department = get_object_or_404(Department, pk=department_id)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated.")
            return redirect('admin_departments')
    else:
        form = DepartmentForm(instance=department)

    return render(request, 'accounts/admin_department_form.html', {'form': form, 'page_title': 'Edit Department', 'department': department})


@login_required
def admin_programmes(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can manage programmes.")

    programmes = Programme.objects.select_related('department').all().order_by('name')
    return render(request, 'accounts/admin_programmes.html', {'programmes': programmes, 'page_title': 'Programmes'})


@login_required
def admin_programme_create(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can create programmes.")

    if request.method == 'POST':
        form = ProgrammeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Programme created.")
            return redirect('admin_programmes')
    else:
        form = ProgrammeForm()

    return render(request, 'accounts/admin_programme_form.html', {'form': form, 'page_title': 'Create Programme'})


@login_required
def admin_programme_edit(request, programme_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can edit programmes.")

    programme = get_object_or_404(Programme, pk=programme_id)
    if request.method == 'POST':
        form = ProgrammeForm(request.POST, instance=programme)
        if form.is_valid():
            form.save()
            messages.success(request, "Programme updated.")
            return redirect('admin_programmes')
    else:
        form = ProgrammeForm(instance=programme)

    return render(request, 'accounts/admin_programme_form.html', {'form': form, 'page_title': 'Edit Programme', 'programme': programme})


@login_required
def dashboard(request):
    user = request.user

    if user.role == User.Role.STUDENT:
        try:
            student = StudentProfile.objects.select_related(
                "programme", "programme__department"
            ).get(user=user)
        except StudentProfile.DoesNotExist:
            return render(
                request,
                "accounts/student_dashboard.html",
                {
                    "student": None,
                    "registered_courses": 0,
                    "results_count": 0,
                    "approved_results": [],
                    "complaints_count": 0,
                    "page_title": "Student Dashboard",
                },
            )

        registrations = CourseRegistration.objects.filter(
            student=student,
            status=CourseRegistration.RegistrationStatus.REGISTERED,
        ).select_related(
            "course",
            "course__semester",
            "course__semester__session",
        ).order_by(
            "course__semester__session__start_date",
            "course__semester__start_date",
            "course__code",
        )

        current_session = (
            AcademicSession.objects.filter(pk=student.admission_session_id).first()
            or AcademicSession.objects.filter(is_current=True).first()
            or AcademicSession.objects.filter(is_active=True).order_by("-start_date").first()
        )
        current_semester = None
        if current_session:
            current_semester = (
                Semester.objects.filter(session=current_session, is_current=True).first()
                or Semester.objects.filter(session=current_session, is_active=True).order_by("start_date").first()
            )

        registered_course_ids = set(
            CourseRegistration.objects.filter(
                student=student,
                status=CourseRegistration.RegistrationStatus.REGISTERED,
            ).values_list("course_id", flat=True)
        )

        available_courses = Course.objects.filter(
            programme=student.programme,
            level=student.current_level,
            is_active=True,
        )
        if current_semester:
            available_courses = available_courses.filter(semester=current_semester)
        available_courses = list(
            available_courses.exclude(id__in=registered_course_ids)
            .select_related("semester", "semester__session", "programme", "lecturer")
            .order_by("code")
        )

        results = Result.objects.filter(
            course_registration__student=student,
            status=Result.Status.APPROVED,
        ).select_related("course_registration__course")

        complaints = Complaint.objects.filter(student=user)

        return render(
            request,
            "accounts/student_dashboard.html",
            {
                "student": student,
                "registered_courses": registrations.count(),
                "registered_courses_list": registrations,
                "results_count": results.count(),
                "approved_results": results,
                "complaints_count": complaints.count(),
                "available_courses": available_courses,
                "page_title": "Student Dashboard",
            },
        )

    if user.role == User.Role.LECTURER:
        lecturer_courses = Course.objects.filter(
            lecturer=user,
            is_active=True,
        ).select_related(
            "programme",
            "semester",
            "semester__session",
        )

        lecturer_results = Result.objects.filter(
            course_registration__course__lecturer=user,
        )

        complaints = Complaint.objects.filter(lecturer=user)

        return render(
            request,
            "accounts/lecturer_dashboard.html",
            {
                "total_courses": lecturer_courses.count(),
                "lecturer_courses": lecturer_courses,
                "current_session": AcademicSession.objects.filter(
                    is_current=True
                ).first(),
                "pending_results": lecturer_results.filter(
                    status=Result.Status.DRAFT
                ).count(),
                "submitted_results": lecturer_results.filter(
                    status=Result.Status.SUBMITTED
                ).count(),
                "complaints_count": complaints.count(),
                "page_title": "Lecturer Dashboard",
            },
        )

    if user.role == User.Role.EXAM_OFFICER:
        return render(
            request,
            "accounts/exam_officer_dashboard.html",
            {
                "total_students": StudentProfile.objects.count(),
                "total_courses": Course.objects.filter(
                    is_active=True
                ).count(),
                "pending_results": Result.objects.filter(
                    status=Result.Status.SUBMITTED
                ).count(),
                "verified_results": Result.objects.filter(
                    status=Result.Status.VERIFIED
                ).count(),
                "approved_results": Result.objects.filter(
                    status=Result.Status.APPROVED
                ).count(),
                "rejected_results": Result.objects.filter(
                    status=Result.Status.REJECTED
                ).count(),
                "complaints_count": Complaint.objects.filter(
                    exam_officer=user
                ).count(),
                "page_title": "Examination Office",
            },
        )

    if user.role == User.Role.HOD:
        pending_results = Result.objects.filter(status=Result.Status.VERIFIED).count()
        approved_results = Result.objects.filter(status=Result.Status.APPROVED).count()
        rejected_results = Result.objects.filter(status=Result.Status.REJECTED).count()
        complaints_count = Complaint.objects.filter(hod=request.user).count()

        return render(
            request,
            "accounts/hod_dashboard.html",
            {
                "pending_results": pending_results,
                "approved_results": approved_results,
                "rejected_results": rejected_results,
                "complaints_count": complaints_count,
                "page_title": "Department Dashboard",
            },
        )

    if _is_admin_user(user):
        return redirect("admin_dashboard")

    return redirect("login")


@login_required
def student_course_registration(request):
    if request.user.role != User.Role.STUDENT:
        return HttpResponseForbidden("Only students can register courses.")

    try:
        student = StudentProfile.objects.select_related(
            "programme",
            "programme__department",
        ).get(user=request.user)
    except StudentProfile.DoesNotExist:
        return render(
            request,
            "accounts/course_registration.html",
            {
                "student": None,
                "sessions": [],
                "semesters": [],
                "selected_session": None,
                "selected_semester": None,
                "available_courses": [],
                "registered_courses": [],
                "page_title": "Course Registration",
            },
        )

    sessions = AcademicSession.objects.filter(is_active=True).order_by("-start_date")
    selected_session_id = request.GET.get("session") or request.POST.get("session")
    if selected_session_id:
        selected_session = sessions.filter(pk=selected_session_id).first()
    else:
        selected_session = (
            sessions.filter(pk=student.admission_session_id).first()
            or sessions.filter(is_current=True).first()
            or sessions.first()
        )

    selected_semester_id = request.GET.get("semester") or request.POST.get("semester")
    semesters = Semester.objects.filter(session=selected_session).order_by("start_date") if selected_session else []
    if not selected_session:
        selected_semester = None
    elif selected_semester_id:
        selected_semester = semesters.filter(pk=selected_semester_id).first()
    else:
        selected_semester = (
            semesters.filter(is_active=True).order_by("start_date").first()
            or semesters.filter(is_current=True).first()
            or semesters.first()
        )

    if request.method == "POST":
        selected_course_ids = request.POST.getlist("course_ids")
        if selected_course_ids:
            with transaction.atomic():
                for course_id in selected_course_ids:
                    course = Course.objects.filter(
                        pk=course_id,
                        programme=student.programme,
                        level=student.current_level,
                        is_active=True,
                    ).select_related("semester", "semester__session").first()
                    if not course:
                        continue

                    registration, created = CourseRegistration.objects.get_or_create(
                        student=student,
                        course=course,
                        defaults={"status": CourseRegistration.RegistrationStatus.REGISTERED},
                    )

                    if not created and registration.status != CourseRegistration.RegistrationStatus.REGISTERED:
                        registration.status = CourseRegistration.RegistrationStatus.REGISTERED
                        registration.save(update_fields=["status", "updated_at"])

            messages.success(request, "Selected courses were registered successfully.")
            return redirect("student_course_registration")

        messages.error(request, "Please select at least one course to register.")

    available_courses = []
    if selected_session and selected_semester:
        available_courses = list(
            Course.objects.filter(
                programme=student.programme,
                level=student.current_level,
                is_active=True,
                semester=selected_semester,
            )
            .exclude(
                registrations__student=student,
                registrations__status=CourseRegistration.RegistrationStatus.REGISTERED,
            )
            .select_related("semester", "semester__session", "programme", "lecturer")
            .order_by("code")
        )

    registered_courses = list(
        CourseRegistration.objects.filter(
            student=student,
            status=CourseRegistration.RegistrationStatus.REGISTERED,
        )
        .select_related(
            "course",
            "course__semester",
            "course__semester__session",
            "course__programme",
        )
        .order_by("course__code")
    )

    return render(
        request,
        "accounts/course_registration.html",
        {
            "student": student,
            "sessions": sessions,
            "semesters": semesters,
            "selected_session": selected_session,
            "selected_semester": selected_semester,
            "available_courses": available_courses,
            "registered_courses": registered_courses,
            "page_title": "Course Registration",
        },
    )


@login_required
def admin_semester_create(request, session_id=None):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can create semesters.")

    initial = {}
    if session_id:
        initial['session'] = AcademicSession.objects.filter(pk=session_id).first()

    if request.method == 'POST':
        form = SemesterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Semester created.")
            return redirect('admin_semesters')
    else:
        form = SemesterForm(initial=initial)

    return render(request, 'accounts/admin_semester_form.html', {'form': form, 'page_title': 'Create Semester'})


@login_required
def admin_semester_edit(request, semester_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden("Only administrators can edit semesters.")

    semester = get_object_or_404(Semester, pk=semester_id)
    if request.method == 'POST':
        form = SemesterForm(request.POST, instance=semester)
        if form.is_valid():
            form.save()
            messages.success(request, "Semester updated.")
            return redirect('admin_semesters')
    else:
        form = SemesterForm(instance=semester)

    return render(request, 'accounts/admin_semester_form.html', {'form': form, 'page_title': 'Edit Semester', 'semester': semester})
