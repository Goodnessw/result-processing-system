from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from django.contrib.auth import get_user_model

from academics.models import (
    Department,
    Programme,
    AcademicSession,
    Semester,
    Course,
    StudentProfile,
)

User = get_user_model()


class HODCourseCreationFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create department and programme
        self.dept = Department.objects.create(name="Science", code="SCI")
        self.prog = Programme.objects.create(
            department=self.dept, name="Computer Science", code="CS", degree_type="BSC"
        )

        # Create HOD and lecturer users
        self.hod = User.objects.create_user(username="hod", password="pass", role=User.Role.HOD, is_staff=True)
        self.lect = User.objects.create_user(username="lect", password="pass", role=User.Role.LECTURER)

        # Create student user
        self.student_user = User.objects.create_user(username="stud", password="pass", role=User.Role.STUDENT, matric_number="M123")

    def test_hod_creates_session_semester_course_and_student_sees_it(self):
        # HOD logs in
        self.client.login(username="hod", password="pass")

        # Create academic session
        session_data = {
            "name": "2026/2027",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "is_current": "on",
            "is_active": "on",
        }
        resp = self.client.post(reverse('admin_session_create'), session_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        session = AcademicSession.objects.get(name="2026/2027")

        # Create semester for the session
        sem_data = {
            "session": session.id,
            "name": "FIRST",
            "start_date": "2026-01-01",
            "end_date": "2026-06-30",
            "is_current": "on",
            "is_active": "on",
        }
        resp = self.client.post(reverse('admin_semester_create', args=[session.id]), sem_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        semester = Semester.objects.get(session=session, name="FIRST")

        # Create a course assigned to lecturer
        course_data = {
            "programme": self.prog.id,
            "code": "CSC101",
            "title": "Intro to Computing",
            "credit_units": 3,
            "level": 100,
            "semester": semester.id,
            "lecturer": self.lect.id,
            "description": "",
            "is_active": "on",
        }
        resp = self.client.post(reverse('admin_course_create'), course_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        course = Course.objects.get(code="CSC101")

        # Create student profile and login as student
        StudentProfile.objects.create(user=self.student_user, programme=self.prog, admission_session=session, current_level=100)
        self.client.logout()
        self.client.login(username="stud", password="pass")

        # Student requests the registration page with session & semester selected
        resp = self.client.get(reverse('student_course_registration'), {'session': session.id, 'semester': semester.id})
        self.assertEqual(resp.status_code, 200)
        # available_courses should include our created course
        self.assertIn('available_courses', resp.context)
        available = resp.context['available_courses']
        codes = [c.code for c in available]
        self.assertIn('CSC101', codes)
from django.test import TestCase

# Create your tests here.
