# UNICROSS Result Processing System — Project README and Setup Guide

You are working on the **UNICROSS Result Processing System**, a Django-based academic result processing and complaint management platform developed for the University of Cross River State (UNICROSS).

Your task is to understand the project, set it up locally, test its functionality, and document how it works. Follow the instructions below in order.

## 1. Project Overview

The system manages academic results, course registration, result approvals, and student complaints. It supports five user roles:

1. Student
2. Lecturer
3. Examination Officer
4. Head of Department (HOD)
5. Administrator

The application uses Django for its backend and server-rendered frontend, with HTML, CSS, and JavaScript for its user interface.

## 2. Main Features

The system should support:

- Student records and academic profiles.
- Course registration by academic session and semester.
- Lecturer assignment to courses.
- Result entry and submission by lecturers.
- Automatic computation of total scores, grades, and grade points.
- Examination Officer verification of submitted results.
- HOD review, approval, or rejection of results.
- Publication of approved results to students.
- Student GPA and CGPA calculations.
- Complaint submission for missing, incorrect, or disputed results.
- Complaint reference numbers and status tracking.
- Notifications and complaint read receipts.
- Result correction and approval history.
- Academic session, semester, department, programme, and course management.
- Role-specific dashboards and access permissions.

## 3. Academic Result Workflow

The expected result approval process is:

**Lecturer → Examination Officer → HOD → Student**

### Lecturer
- Views assigned courses.
- Enters continuous assessment and examination scores.
- Submits results for review.
- Corrects and resubmits rejected results.

### Examination Officer
- Reviews submitted results for completeness and accuracy.
- Verifies valid results and forwards them to the HOD.
- Returns incorrect or incomplete results for correction.

### Head of Department (HOD)
- Reviews departmental results.
- Approves or rejects results after examination verification.
- Ensures rejected results return through the appropriate correction process.
- Oversees relevant complaints and result corrections.

### Student
- Registers for approved courses.
- Views results only after the required approval process.
- Checks GPA and CGPA.
- Submits complaints and tracks their status.

The application must not expose unapproved results to students.

## 4. Complaint Management Workflow

Students can submit complaints about missing results, incorrect scores, or other result-related issues.

The complaint workflow should work as follows:

1. A student submits a complaint.
2. The system generates a unique complaint reference and records the submission time.
3. The complaint is routed to the relevant staff members according to the configured workflow, including the Lecturer, Examination Officer, and HOD where applicable.
4. The responsible Lecturer investigates the complaint.
5. If a correction is required, the Lecturer corrects and resubmits the result.
6. The Examination Officer verifies the corrected result.
7. The HOD gives final approval or rejects the correction.
8. The student receives updates and can track the complaint outcome.

The system must preserve the original result and maintain an auditable correction history. A complaint must not change a score directly without the required approval process.

Complaint status and result approval status should be tracked separately. Resolving a complaint must not automatically approve a result.

Where complaint read receipts are implemented, each required staff recipient's delivery and read status should be tracked accurately. Do not mark a complaint as read by everyone until all required recipients have opened it.

## 5. Grading and GPA

Use the following grading scale:

| Score | Grade | Grade Point |
|---|---|---:|
| 70–100 | A | 5 |
| 60–69 | B | 4 |
| 50–59 | C | 3 |
| 45–49 | D | 2 |
| 40–44 | E | 1 |
| 0–39 | F | 0 |

GPA is calculated using the credit units of registered courses:

GPA = Sum of (Grade Point × Course Credit Units) ÷ Sum of Course Credit Units.

CGPA should be calculated from the weighted grade points and credit units across the student's completed semesters.

## 6. Administrator Responsibilities

The Administrator has a separate administrative role from the HOD.

The Administrator manages authorised academic and system records, including:

- Students and lecturers.
- Departments and programmes.
- Courses and course assignments.
- Academic sessions and semesters.
- User accounts and role assignments.
- Other authorised academic configuration.

The HOD handles departmental result oversight, final result approval, and relevant complaints. The HOD should not automatically receive global Administrator permissions.

Django's built-in superuser or staff status is not the same as the application's custom Administrator role. Confirm that the correct role-based permissions are configured.

## 7. Local Development Setup

### Prerequisites

Install Python, pip, Git, and any other dependencies specified by the project.

### Step 1: Open the project

Open a terminal in the project root directory.

For the existing development environment on Kali Linux, the project directory may be:

```bash
cd ~/result-processing-system
```

### Step 2: Activate the virtual environment

If the project already has a virtual environment:

```bash
source venv/bin/activate
```

If it does not, create one:

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

Use a Python version supported by the project's existing dependencies. Do not change the Python version or dependency versions unnecessarily if the current environment already works.

### Step 4: Configure environment variables

Check the project settings and `.env` configuration. Set the required Django secret key, debug setting, allowed hosts, and database configuration.

Never commit `.env` files, secret keys, or private credentials to a public repository.

### Step 5: Apply migrations

```bash
python manage.py migrate
```

Do not delete the database or existing records simply to resolve a migration error.

### Step 6: Check the project

```bash
python manage.py check
```

Check for uncommitted model changes:

```bash
python manage.py makemigrations --check
```

### Step 7: Start the development server

```bash
python manage.py runserver
```

Open the application at:

http://127.0.0.1:8000/

Use the login page configured in the project's URL routes. The existing login route may be `/accounts/login/`, so confirm the actual URL configuration rather than assuming the route.

## 8. Important Application Pages

The following are the expected routes based on the current project structure. Confirm each route in the source code before relying on it.

| Function | Expected URL |
|---|---|
| Student dashboard | `/` |
| Course registration | `/student/course-registration/` |
| Student results | `/results/my-results/` |
| Complaint submission | `/complaints/submit/` |
| Complaint history | `/complaints/history/` |
| Staff complaint queue | `/complaints/queue/` |
| Examination Officer review | `/results/review/` |
| HOD result review | `/results/hod-review/` |
| Administrator dashboard | `/admin-dashboard/` |

The project should use role-specific redirects and navigation. Students, lecturers, Examination Officers, HODs, and Administrators should see the appropriate dashboards and actions for their roles.

Do not assume a route works merely because it appears in the README. Verify the URL configuration, view, template, and permissions.

## 9. Test Accounts

Use the development accounts already configured in the local database. Do not assume that a username or password listed in an old document is still valid.

The previously documented intended test accounts are:

| Role | Username |
|---|---|
| Student | `teststudent` |
| Lecturer | `testlecturer` |
| Examination Officer | `examofficer` |
| HOD | `testhod` |
| Administrator | `wisdom` — verify the actual application role |

Passwords must be verified or reset locally by an authorised developer. Do not publish passwords in the README, commit them to Git, or reuse development credentials in production.

If an account cannot log in, inspect the user record and role before changing application code. Confirm that the account exists, has the intended role, and has a valid password.

## 10. Automated Testing

Run the Django test suite:

```bash
python manage.py test
```

Record the actual number of tests passed, failed, and skipped. Do not invent test results or claim that all tests passed without running them.

Also check:

```bash
python manage.py check
python manage.py makemigrations --check
```

Investigate and resolve genuine errors without deleting existing records or breaking working features.

## 11. Manual Browser Testing

Test the application using a separate account for each role.

### Student
- Log in and confirm the student dashboard appears.
- Register for available courses.
- View registered courses.
- Open the results page.
- Confirm that unapproved results are not visible.
- Submit a complaint.
- Confirm that a unique complaint reference is generated.
- Track the complaint and review its status and notifications.

### Lecturer
- Log in and confirm the Lecturer dashboard appears.
- View assigned courses.
- Enter scores and submit a result.
- Confirm the result enters the correct review stage.
- Correct and resubmit a rejected result.
- Review assigned complaints and update them according to the workflow.

### Examination Officer
- Log in and confirm the Examination Officer dashboard appears.
- Open the result review queue.
- Verify a valid result.
- Return an incorrect result for correction.
- Confirm the result status and history are updated correctly.
- Review relevant complaints.

### HOD
- Log in and confirm the HOD dashboard appears.
- View departmental results awaiting final approval.
- Approve a verified result.
- Reject a result and confirm it returns to the appropriate correction stage.
- Review relevant complaints and corrections.
- Confirm the HOD does not automatically gain unrestricted Administrator access.

### Administrator
- Log in and confirm the separate Administrator dashboard appears.
- Manage authorised users, departments, programmes, courses, sessions, and semesters.
- Confirm that changes persist in the database.
- Confirm that unauthorised roles cannot access administrative actions by entering URLs directly.

### Complaint and Correction Tests
- Submit a complaint for a missing or incorrect result.
- Confirm staff routing and notifications.
- Confirm that the original result is preserved.
- Correct and resubmit the result as the Lecturer.
- Verify it as the Examination Officer.
- Approve or reject it as the HOD.
- Confirm that the student sees the updated result only after approval.
- Confirm that complaint status, result status, correction history, and read receipts remain consistent.

## 12. UI and Access-Control Requirements

The interface should be consistent, readable, responsive, and appropriate for a university academic system.

Verify that:

- Each role has its own dashboard experience.
- Navigation links lead to the correct pages.
- Forms display validation errors clearly.
- Tables are readable and usable.
- Buttons perform the actions their labels describe.
- Empty states and success/error messages are handled.
- Users cannot perform actions outside their permissions by entering a URL directly.
- The Administrator dashboard is distinct from the HOD dashboard.
- The user-facing application does not unnecessarily expose Django's built-in administration interface.

Do not redesign the entire project unnecessarily. Preserve existing working functionality and make targeted fixes where needed.

## 13. Branding and Static Assets

The application should use the approved UNICROSS logo and favicon where referenced by the templates.

Expected file paths include:

```text
static/images/unicross-logo.png
static/images/favicon.png
```

Confirm that the files exist and the templates reference the correct paths. Do not modify official institutional artwork without permission.

Font Awesome may be loaded from a CDN if the templates are configured correctly. Use a valid CDN URL and integrity hash where applicable. Do not include a placeholder integrity value such as `sha512-` in the final production HTML.

## 14. Useful Management Commands

Create a Django superuser if needed:

```bash
python manage.py createsuperuser
```

Run migrations:

```bash
python manage.py migrate
```

Run automated tests:

```bash
python manage.py test
```

Check project configuration:

```bash
python manage.py check
```

Inspect application users and their roles:

```bash
python manage.py shell
```

Then:

```python
from accounts.models import User

for user in User.objects.all():
    print(
        user.username,
        user.role,
        user.is_staff,
        user.is_superuser,
    )
```

Exit the Django shell with:

```python
exit()
```

## 15. Final Deliverables

When you finish, provide:

1. A working local setup with clear instructions.
2. A correctly formatted README.md.
3. A summary of the application's five roles and their permissions.
4. A description of the result approval and complaint workflows.
5. The actual output of the Django system checks and automated tests.
6. A manual testing checklist showing which actions were tested.
7. A list of bugs found and fixed.
8. A list of any remaining issues.
9. Confirmation of whether browser testing was actually completed.
10. Confirmation that existing database records and working features were preserved.

Do not claim a feature works simply because its template or URL exists. Verify the actual behaviour. Do not fabricate test results, passwords, screenshots, or browser-testing evidence.

## 16. Security and Deployment

Before any production deployment:

- Change all development passwords.
- Keep secrets and environment files out of version control.
- Disable Django debug mode.
- Configure allowed hosts and HTTPS.
- Configure secure session and CSRF settings.
- Use an appropriate production database and static-file strategy.
- Back up academic data.
- Verify all role permissions and result approval rules.
- Preserve complaint and result correction audit history.

**The goal is to deliver a functional, tested, well-documented UNICROSS Result Processing System whose implementation follows the required academic workflow, protects student records, and clearly separates the responsibilities of Students, Lecturers, Examination Officers, HODs, and Administrators.**