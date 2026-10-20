from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from academics.models import AcademicSession, Course, Department, Programme, Semester, StudentProfile, CourseRegistration
from results.models import Result, ResultAuditLog


class ApprovalWorkflowAccessTests(TestCase):
    def setUp(self):
        self.lecturer = User.objects.create_user(
            username="lecturer1",
            password="secret123",
            role=User.Role.LECTURER,
            staff_number="L-001",
        )
        self.exam_officer = User.objects.create_user(
            username="examofficer1",
            password="secret123",
            role=User.Role.EXAM_OFFICER,
            staff_number="EO-001",
        )
        self.hod = User.objects.create_user(
            username="hod1",
            password="secret123",
            role=User.Role.HOD,
            staff_number="HOD-001",
        )

        self.department = Department.objects.create(
            name="Computer Science",
            code="CS",
        )
        self.session = AcademicSession.objects.create(
            name="2026/2027",
            start_date="2026-09-01",
            end_date="2027-06-30",
            is_current=True,
        )
        self.semester = Semester.objects.create(
            session=self.session,
            name=Semester.SemesterType.FIRST,
            start_date="2026-09-01",
            end_date="2026-12-31",
            is_current=True,
        )
        self.programme = Programme.objects.create(
            department=self.department,
            name="Computer Science",
            code="CS-BSC",
            degree_type=Programme.DegreeType.BSC,
        )
        self.course = Course.objects.create(
            programme=self.programme,
            lecturer=self.lecturer,
            code="CSC101",
            title="Introduction to Computing",
            credit_units=3,
            level=100,
            semester=self.semester,
        )
        self.alt_course = Course.objects.create(
            programme=self.programme,
            lecturer=self.lecturer,
            code="CSC102",
            title="Programming Fundamentals",
            credit_units=3,
            level=100,
            semester=self.semester,
        )
        self.student_user = User.objects.create_user(
            username="student1",
            password="secret123",
            role=User.Role.STUDENT,
            matric_number="CSC/2026/001",
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            programme=self.programme,
            admission_session=self.session,
            current_level=100,
        )
        self.registration = CourseRegistration.objects.create(
            student=self.student_profile,
            course=self.course,
            status=CourseRegistration.RegistrationStatus.REGISTERED,
        )
        self.alt_registration = CourseRegistration.objects.create(
            student=self.student_profile,
            course=self.alt_course,
            status=CourseRegistration.RegistrationStatus.REGISTERED,
        )

    def test_hod_review_route_requires_hod(self):
        self.client.login(username="examofficer1", password="secret123")
        response = self.client.get(reverse("hod_review_results"))
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.login(username="hod1", password="secret123")
        response = self.client.get(reverse("hod_review_results"))
        self.assertEqual(response.status_code, 200)

    def test_student_dashboard_only_shows_approved_results(self):
        self.client.login(username="student1", password="secret123")
        result = Result.objects.create(
            course_registration=self.registration,
            entered_by=self.lecturer,
            ca_score=20,
            exam_score=40,
            status=Result.Status.VERIFIED,
            verified_by=self.exam_officer,
        )
        result2 = Result.objects.create(
            course_registration=self.alt_registration,
            entered_by=self.lecturer,
            ca_score=25,
            exam_score=65,
            status=Result.Status.APPROVED,
            verified_by=self.exam_officer,
            approved_by=self.hod,
        )
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approved Results")
        self.assertContains(response, result2.grade)
        self.assertNotContains(response, f"{result.total_score:.2f}")

    def test_exam_officer_verification_sets_verified_by_and_audit(self):
        result = Result.objects.create(
            course_registration=self.registration,
            entered_by=self.lecturer,
            ca_score=20,
            exam_score=60,
            status=Result.Status.SUBMITTED,
        )

        self.client.login(username="examofficer1", password="secret123")
        response = self.client.post(
            reverse("review_results"),
            {"action": "verify", "result_id": result.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        result.refresh_from_db()
        self.assertEqual(result.status, Result.Status.VERIFIED)
        self.assertEqual(result.verified_by, self.exam_officer)
        self.assertTrue(
            ResultAuditLog.objects.filter(
                result=result,
                action=ResultAuditLog.Action.VERIFIED,
                performed_by=self.exam_officer,
            ).exists()
        )
        self.assertTrue(
            ResultAuditLog.objects.filter(
                result=result,
                action=ResultAuditLog.Action.FORWARDED,
                performed_by=self.exam_officer,
            ).exists()
        )

    def test_hod_approval_sets_approved_by_and_audit(self):
        result = Result.objects.create(
            course_registration=self.registration,
            entered_by=self.lecturer,
            ca_score=20,
            exam_score=60,
            status=Result.Status.VERIFIED,
            verified_by=self.exam_officer,
        )

        self.client.login(username="hod1", password="secret123")
        response = self.client.post(
            reverse("hod_review_results"),
            {"action": "approve", "result_id": result.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        result.refresh_from_db()
        self.assertEqual(result.status, Result.Status.APPROVED)
        self.assertEqual(result.approved_by, self.hod)
        self.assertTrue(
            ResultAuditLog.objects.filter(
                result=result,
                action=ResultAuditLog.Action.APPROVED,
                performed_by=self.hod,
            ).exists()
        )

    def test_rejected_result_can_be_resubmitted_manually(self):
        result = Result.objects.create(
            course_registration=self.registration,
            entered_by=self.lecturer,
            ca_score=10,
            exam_score=20,
            status=Result.Status.REJECTED,
        )

        self.client.login(username="lecturer1", password="secret123")
        response = self.client.post(
            reverse("course_results", kwargs={"course_id": self.course.id}),
            {"action": "save", f"ca_{self.registration.id}": "15", f"exam_{self.registration.id}": "35"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        result.refresh_from_db()
        self.assertEqual(result.status, Result.Status.DRAFT)

    def test_rejected_result_can_be_resubmitted_with_excel_like_flow(self):
        result = Result.objects.create(
            course_registration=self.registration,
            entered_by=self.lecturer,
            ca_score=10,
            exam_score=20,
            status=Result.Status.REJECTED,
        )

        ResultAuditLog.objects.create(
            result=result,
            action=ResultAuditLog.Action.REJECTED,
            performed_by=self.exam_officer,
            details="Incorrect marks.",
        )

        self.client.login(username="lecturer1", password="secret123")
        response = self.client.post(
            reverse("course_results", kwargs={"course_id": self.course.id}),
            {"action": "submit", f"ca_{self.registration.id}": "18", f"exam_{self.registration.id}": "45"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        result.refresh_from_db()
        self.assertEqual(result.status, Result.Status.SUBMITTED)
        self.assertTrue(
            ResultAuditLog.objects.filter(
                result=result,
                action=ResultAuditLog.Action.CORRECTED,
                performed_by=self.lecturer,
            ).exists()
        )

    def test_rejection_requires_reason_and_status_is_validated(self):
        result = Result.objects.create(
            course_registration=self.registration,
            entered_by=self.lecturer,
            ca_score=20,
            exam_score=60,
            status=Result.Status.SUBMITTED,
        )

        self.client.login(username="examofficer1", password="secret123")
        response = self.client.post(
            reverse("review_results"),
            {"action": "reject", "result_id": result.id, "reason": ""},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        result.refresh_from_db()
        self.assertEqual(result.status, Result.Status.SUBMITTED)

    def test_hod_rejection_requires_reason(self):
        result = Result.objects.create(
            course_registration=self.registration,
            entered_by=self.lecturer,
            ca_score=20,
            exam_score=60,
            status=Result.Status.VERIFIED,
            verified_by=self.exam_officer,
        )

        self.client.login(username="hod1", password="secret123")
        response = self.client.post(
            reverse("hod_review_results"),
            {"action": "reject", "result_id": result.id, "reason": ""},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        result.refresh_from_db()
        self.assertEqual(result.status, Result.Status.VERIFIED)
