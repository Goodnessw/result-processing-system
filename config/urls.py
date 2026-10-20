from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from accounts.views import (
    admin_courses,
    admin_dashboard,
    admin_departments,
    admin_lecturer_create,
    admin_lecturers,
    admin_programmes,
    admin_sessions,
    admin_semesters,
    admin_student_create,
    admin_students,
    dashboard,
    student_course_registration,
    admin_session_create,
    admin_session_edit,
    admin_semester_create,
    admin_semester_edit,
    admin_course_create,
    admin_course_edit,
    admin_department_create,
    admin_department_edit,
    admin_programme_create,
    admin_programme_edit,
)
from results.views import course_results, hod_review_results, my_results, review_results

from results.bulk_views import (
    download_result_template,
    upload_result_excel,
    preview_result_excel,
)
from notifications.views import notifications_list
from notifications.views import notification_open

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard, name="dashboard"),
    path("student/course-registration/", student_course_registration, name="student_course_registration"),
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/students/", admin_students, name="admin_students"),
    path("admin-dashboard/students/create/", admin_student_create, name="admin_student_create"),
    path("admin-dashboard/lecturers/", admin_lecturers, name="admin_lecturers"),
    path("admin-dashboard/lecturers/create/", admin_lecturer_create, name="admin_lecturer_create"),
    path("admin-dashboard/courses/", admin_courses, name="admin_courses"),
    path("admin-dashboard/courses/create/", admin_course_create, name="admin_course_create"),
    path("admin-dashboard/courses/<int:course_id>/edit/", admin_course_edit, name="admin_course_edit"),
    path("admin-dashboard/sessions/", admin_sessions, name="admin_sessions"),
    path("admin-dashboard/semesters/", admin_semesters, name="admin_semesters"),
    path("admin-dashboard/sessions/create/", admin_session_create, name="admin_session_create"),
    path("admin-dashboard/sessions/<int:session_id>/edit/", admin_session_edit, name="admin_session_edit"),
    path("admin-dashboard/sessions/<int:session_id>/semesters/create/", admin_semester_create, name="admin_semester_create"),
    path("admin-dashboard/semesters/create/", admin_semester_create, name="admin_semester_create_direct"),
    path("admin-dashboard/semesters/<int:semester_id>/edit/", admin_semester_edit, name="admin_semester_edit"),
    path("admin-dashboard/departments/", admin_departments, name="admin_departments"),
    path("admin-dashboard/departments/create/", admin_department_create, name="admin_department_create"),
    path("admin-dashboard/departments/<int:department_id>/edit/", admin_department_edit, name="admin_department_edit"),
    path("admin-dashboard/programmes/", admin_programmes, name="admin_programmes"),
    path("admin-dashboard/programmes/create/", admin_programme_create, name="admin_programme_create"),
    path("admin-dashboard/programmes/<int:programme_id>/edit/", admin_programme_edit, name="admin_programme_edit"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html"
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("complaints/", include("complaints.urls")),
    path("results/my-results/", my_results, name="my_results"),
    path(
        "results/review/",
        review_results,
        name="review_results",
    ),
    path(
        "results/hod-review/",
        hod_review_results,
        name="hod_review_results",
    ),
    path(
        "results/courses/<int:course_id>/",
        course_results,
        name="course_results",
    ),
    path(
        "results/courses/<int:course_id>/excel-template/",
        download_result_template,
        name="download_result_template",
    ),
    path(
        "results/courses/<int:course_id>/excel-upload/",
        upload_result_excel,
        name="upload_result_excel",
    ),
    path(
        "results/courses/<int:course_id>/excel-preview/",
        preview_result_excel,
        name="preview_result_excel",
    ),
    path("notifications/", notifications_list, name="notifications"),
    path("notifications/open/<int:notification_id>/", notification_open, name="notification_open"),
]