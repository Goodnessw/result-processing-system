from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from academics.models import AcademicSession, Course, CourseRegistration, Department, Programme, Semester, StudentProfile
from complaints.models import Complaint, ComplaintHistory
from results.models import Result


class ComplaintWorkflowTests(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            username="student1",
            password="secret123",
            role=User.Role.STUDENT,
            matric_number="CSC/2026/001",
        )
        self.other_student = User.objects.create_user(
            username="student2",
            password="secret123",
            role=User.Role.STUDENT,
            matric_number="CSC/2026/002",
        )
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
            department="Computer Science",
        )
        self.hod = User.objects.create_user(
            username="hod1",
            password="secret123",
            role=User.Role.HOD,
            staff_number="HOD-001",
            department="Computer Science",
        )

        self.department = Department.objects.create(name="Computer Science", code="CS")
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

        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            programme=self.programme,
            admission_session=self.session,
            current_level=100,
        )
        self.other_profile = StudentProfile.objects.create(
            user=self.other_student,
            programme=self.programme,
            admission_session=self.session,
            current_level=100,
        )

        self.registration = CourseRegistration.objects.create(
            student=self.student_profile,
            course=self.course,
            status=CourseRegistration.RegistrationStatus.REGISTERED,
        )
        self.other_registration = CourseRegistration.objects.create(
            student=self.other_profile,
            course=self.course,
            status=CourseRegistration.RegistrationStatus.REGISTERED,
        )

        self.result = Result.objects.create(
            course_registration=self.registration,
            entered_by=self.lecturer,
            ca_score=20,
            exam_score=60,
            status=Result.Status.APPROVED,
            verified_by=self.exam_officer,
            approved_by=self.hod,
        )
        self.other_result = Result.objects.create(
            course_registration=self.other_registration,
            entered_by=self.lecturer,
            ca_score=22,
            exam_score=58,
            status=Result.Status.APPROVED,
            verified_by=self.exam_officer,
            approved_by=self.hod,
        )

    def test_student_can_submit_complaint_for_own_result(self):
        self.client.login(username="student1", password="secret123")
        response = self.client.post(
            reverse("complaint_submit"),
            {
                "result": self.result.id,
                "category": Complaint.Category.GRADE_DISCREPANCY,
                "subject": "Grade mismatch",
                "description": "The grade shown is different from what was expected for this result.",
                "contact_preference": "Email",
                "contact_details": "student1@example.com",
                "requested_resolution": "Please review the score entry.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        complaint = Complaint.objects.get(student=self.student_user, result=self.result)
        self.assertTrue(complaint.reference_number.startswith("CMP-"))
        self.assertEqual(complaint.status, Complaint.Status.SUBMITTED)
        self.assertTrue(ComplaintHistory.objects.filter(complaint=complaint).exists())

    def test_student_cannot_submit_complaint_for_other_student_result(self):
        self.client.login(username="student1", password="secret123")
        response = self.client.post(
            reverse("complaint_submit"),
            {
                "result": self.other_result.id,
                "category": Complaint.Category.GRADE_DISCREPANCY,
                "subject": "Another student's result",
                "description": "Should not be allowed.",
                "contact_preference": "Email",
                "contact_details": "student1@example.com",
                "requested_resolution": "Review",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You can only submit a complaint for one of your own results")
        self.assertFalse(Complaint.objects.filter(result=self.other_result).exists())

    def test_duplicate_active_complaint_is_blocked(self):
        Complaint.objects.create(
            student=self.student_user,
            result=self.result,
            category=Complaint.Category.GRADE_DISCREPANCY,
            subject="Duplicate test",
            description="Initial complaint.",
            contact_details="student1@example.com",
            status=Complaint.Status.SUBMITTED,
        )

        self.client.login(username="student1", password="secret123")
        response = self.client.post(
            reverse("complaint_submit"),
            {
                "result": self.result.id,
                "category": Complaint.Category.GRADE_DISCREPANCY,
                "subject": "Duplicate test",
                "description": "Second complaint.",
                "contact_preference": "Phone",
                "contact_details": "08000000000",
                "requested_resolution": "Please review.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An active complaint for this result and issue already exists")
        self.assertEqual(Complaint.objects.filter(student=self.student_user, result=self.result).count(), 1)

    def test_staff_must_have_role_access_and_reason_required_for_rejection(self):
        complaint = Complaint.objects.create(
            student=self.student_user,
            result=self.result,
            category=Complaint.Category.GRADE_DISCREPANCY,
            subject="Review request",
            description="Need review.",
            contact_details="student1@example.com",
            status=Complaint.Status.SUBMITTED,
            lecturer=self.lecturer,
            exam_officer=self.exam_officer,
            hod=self.hod,
        )

        self.client.login(username="student1", password="secret123")
        response = self.client.post(
            reverse("complaint_detail", kwargs={"reference": complaint.reference_number}),
            {"action": "reject", "decision": ""},
            follow=True,
        )
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.login(username="examofficer1", password="secret123")
        response = self.client.post(
            reverse("complaint_detail", kwargs={"reference": complaint.reference_number}),
            {"action": "reject", "decision": ""},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.SUBMITTED)

    def test_staff_can_resolve_and_history_is_logged(self):
        complaint = Complaint.objects.create(
            student=self.student_user,
            result=self.result,
            category=Complaint.Category.RESULT_ERROR,
            subject="Result mismatch",
            description="Need correction.",
            contact_details="student1@example.com",
            status=Complaint.Status.UNDER_REVIEW,
            lecturer=self.lecturer,
            exam_officer=self.exam_officer,
            hod=self.hod,
        )

        self.client.login(username="examofficer1", password="secret123")
        response = self.client.post(
            reverse("complaint_detail", kwargs={"reference": complaint.reference_number}),
            {"action": "resolve", "decision": "The result was rechecked and is correct. No change was made to the approved result."},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.RESOLVED)
        self.assertTrue(
            ComplaintHistory.objects.filter(
                complaint=complaint,
            ).exists()
        )
        self.assertEqual(Result.objects.get(pk=self.result.pk).status, Result.Status.APPROVED)

    def test_student_sees_public_history_but_not_internal_notes(self):
        complaint = Complaint.objects.create(
            student=self.student_user,
            result=self.result,
            category=Complaint.Category.GRADE_DISCREPANCY,
            subject="Need details",
            description="Detailed explanation.",
            contact_details="student1@example.com",
            status=Complaint.Status.SUBMITTED,
            lecturer=self.lecturer,
            exam_officer=self.exam_officer,
            hod=self.hod,
        )
        complaint.record_history(
            actor=self.exam_officer,
            previous_status=Complaint.Status.SUBMITTED,
            new_status=Complaint.Status.RESOLVED,
            message="Complaint resolved.",
            decision_message="Approved result remains unchanged.",
            is_internal_note=False,
        )
        complaint.add_note(self.exam_officer, "Internal investigation note", is_internal=True)

        self.client.login(username="student1", password="secret123")
        response = self.client.get(reverse("complaint_detail", kwargs={"reference": complaint.reference_number}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approved result remains unchanged")
        self.assertNotContains(response, "Internal investigation note")

    def test_resolved_complaint_cannot_be_forwarded_to_exam_officer(self):
        complaint = Complaint.objects.create(
            student=self.student_user,
            result=self.result,
            category=Complaint.Category.GRADE_DISCREPANCY,
            subject="Resolved complaint",
            description="This complaint has already been resolved.",
            contact_details="student1@example.com",
            status=Complaint.Status.RESOLVED,
            lecturer=self.lecturer,
            exam_officer=self.exam_officer,
            hod=self.hod,
        )
        complaint.record_history(
            actor=self.exam_officer,
            previous_status=Complaint.Status.AWAITING_EXAM_OFFICER,
            new_status=Complaint.Status.RESOLVED,
            message="Complaint resolved.",
            decision_message="The result was rechecked and is correct.",
            is_internal_note=False,
        )

        self.client.login(username="examofficer1", password="secret123")
        response = self.client.post(
            reverse("complaint_detail", kwargs={"reference": complaint.reference_number}),
            {"action": "await_exam_officer", "decision": "Please review again."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.RESOLVED)
        self.assertEqual(complaint.history.filter(new_status=Complaint.Status.AWAITING_EXAM_OFFICER).count(), 0)

    def test_duplicate_forwarding_action_is_not_logged_twice(self):
        complaint = Complaint.objects.create(
            student=self.student_user,
            result=self.result,
            category=Complaint.Category.GRADE_DISCREPANCY,
            subject="Duplicate forward test",
            description="The same forward action should not be duplicated.",
            contact_details="student1@example.com",
            status=Complaint.Status.AWAITING_EXAM_OFFICER,
            lecturer=self.lecturer,
            exam_officer=self.exam_officer,
            hod=self.hod,
        )
        complaint.record_history(
            actor=self.exam_officer,
            previous_status=Complaint.Status.UNDER_REVIEW,
            new_status=Complaint.Status.AWAITING_EXAM_OFFICER,
            message="Complaint was forwarded to the examination officer.",
            decision_message="Please verify the grade.",
            is_internal_note=True,
        )

        self.client.login(username="examofficer1", password="secret123")
        response = self.client.post(
            reverse("complaint_detail", kwargs={"reference": complaint.reference_number}),
            {"action": "await_exam_officer", "decision": "Please verify the grade."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            complaint.history.filter(
                actor=self.exam_officer,
                previous_status=Complaint.Status.UNDER_REVIEW,
                new_status=Complaint.Status.AWAITING_EXAM_OFFICER,
            ).count(),
            1,
        )

    def test_existing_complaint_is_hydrated_with_recipients_and_notifications(self):
        complaint = Complaint.objects.create(
            student=self.student_user,
            result=self.result,
            category=Complaint.Category.GRADE_DISCREPANCY,
            subject="Historical complaint",
            description="This complaint existed before recipient tracking was added.",
            contact_details="student1@example.com",
            status=Complaint.Status.AWAITING_EXAM_OFFICER,
            lecturer=self.lecturer,
            exam_officer=self.exam_officer,
            hod=self.hod,
        )
        complaint.ensure_recipients()

        self.assertEqual(complaint.recipients.filter(user=self.lecturer).count(), 1)
        self.assertEqual(complaint.recipients.filter(user=self.exam_officer).count(), 1)
        self.assertEqual(complaint.recipients.filter(user=self.hod).count(), 1)
        self.assertTrue(
            complaint.recipients.filter(
                user=self.exam_officer,
                delivered_at__isnull=False,
            ).exists()
        )
        self.assertTrue(
            complaint.notifications.filter(recipient=self.exam_officer).exists()
        )
