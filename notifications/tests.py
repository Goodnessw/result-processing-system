from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from notifications.models import Notification


class NotificationViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='notifyuser', password='pass')
        self.user.save()

    def test_notification_open_marks_read_and_redirects(self):
        n = Notification.objects.create(
            recipient=self.user,
            title='Test',
            message='Message',
            link='/some-path/',
        )
        self.client.login(username='notifyuser', password='pass')
        resp = self.client.get(reverse('notification_open', args=[n.id]))
        self.assertEqual(resp.status_code, 302)
        n.refresh_from_db()
        self.assertTrue(n.is_read)
        self.assertIn('/some-path/', resp['Location'])

    def test_result_verification_notification_flow(self):
        # Create minimal objects for result verification notification
        from academics.models import Department, Programme, AcademicSession, Semester, Course, StudentProfile, CourseRegistration
        from results.models import Result

        dept = Department.objects.create(name='Test Dept', code='TD')
        prog = Programme.objects.create(department=dept, name='Test Prog', code='TP', degree_type='BSC')
        start = timezone.now().date()
        end = start + timezone.timedelta(days=120)
        session = AcademicSession.objects.create(name='2026/2027', start_date=start, end_date=end)
        sem = Semester.objects.create(session=session, name='FIRST', start_date=start, end_date=end)

        # create users
        student_user = User.objects.create_user(username='stud', password='pw')
        lecturer = User.objects.create_user(username='lect', password='pw')
        eo = User.objects.create_user(username='eo', password='pw', role=User.Role.EXAM_OFFICER)

        # student profile
        sp = StudentProfile.objects.create(user=student_user, programme=prog, admission_session=session, current_level=100)
        course = Course.objects.create(programme=prog, lecturer=lecturer, code='CSC100', title='Test Course', credit_units=2, level=100, semester=sem)
        reg = CourseRegistration.objects.create(student=sp, course=course)
        result = Result.objects.create(course_registration=reg, ca_score=10, exam_score=20, status=Result.Status.SUBMITTED, entered_by=lecturer)

        # verify as EO
        self.client.login(username='eo', password='pw')
        resp = self.client.post(reverse('review_results'), {'action': 'verify', 'result_id': result.id})
        self.assertEqual(resp.status_code, 302)
        # check notification for student
        self.assertTrue(Notification.objects.filter(recipient=student_user, title__icontains='Result verified').exists())

    def test_hod_approval_creates_student_notification(self):
        from academics.models import Department, Programme, AcademicSession, Semester, Course, StudentProfile, CourseRegistration
        from results.models import Result

        dept = Department.objects.create(name='Test Dept 2', code='TD2')
        prog = Programme.objects.create(department=dept, name='Test Prog 2', code='TP2', degree_type='BSC')
        start = timezone.now().date()
        end = start + timezone.timedelta(days=120)
        session = AcademicSession.objects.create(name='2027/2028', start_date=start, end_date=end)
        sem = Semester.objects.create(session=session, name='FIRST', start_date=start, end_date=end)

        student_user = User.objects.create_user(username='stud2', password='pw')
        lecturer = User.objects.create_user(username='lect2', password='pw')
        hod = User.objects.create_user(username='hod', password='pw', role=User.Role.HOD)

        sp = StudentProfile.objects.create(user=student_user, programme=prog, admission_session=session, current_level=100)
        course = Course.objects.create(programme=prog, lecturer=lecturer, code='CSC200', title='Test Course 2', credit_units=2, level=100, semester=sem)
        reg = CourseRegistration.objects.create(student=sp, course=course)
        result = Result.objects.create(course_registration=reg, ca_score=15, exam_score=25, status=Result.Status.VERIFIED, entered_by=lecturer)

        self.client.login(username='hod', password='pw')
        resp = self.client.post(reverse('hod_review_results'), {'action': 'approve', 'result_id': result.id})
        self.assertEqual(resp.status_code, 302)
        result.refresh_from_db()
        self.assertEqual(result.status, Result.Status.APPROVED)
        self.assertTrue(Notification.objects.filter(recipient=student_user, title__icontains='Result approved').exists())

from django.test import TestCase

# Create your tests here.
