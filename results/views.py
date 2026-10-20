from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.models import User
from academics.models import Course, CourseRegistration, Semester, AcademicSession, StudentProfile
from .models import Result, ResultAuditLog
from notifications.models import Notification


@login_required
def review_results(request):
    if request.user.role != User.Role.EXAM_OFFICER:
        return HttpResponseForbidden(
            "Only examination officers can review submitted results."
        )

    filter_name = request.GET.get("status", "pending").strip().lower()
    allowed_statuses = {
        "pending": Result.Status.SUBMITTED,
        "verified": Result.Status.VERIFIED,
        "approved": Result.Status.APPROVED,
        "rejected": Result.Status.REJECTED,
    }

    selected_status = allowed_statuses.get(filter_name, Result.Status.SUBMITTED)
    results = Result.objects.filter(
        status=selected_status,
    ).select_related(
        "course_registration__course",
        "course_registration__student__user",
    ).order_by(
        "course_registration__course__code",
        "course_registration__student__user__last_name",
        "course_registration__student__user__first_name",
    )

    if request.method == "POST":
        action = request.POST.get("action")
        result_id = request.POST.get("result_id")

        if action not in ("verify", "reject"):
            messages.error(request, "Invalid action.")
            return redirect("review_results")

        if not result_id:
            messages.error(request, "No result selected.")
            return redirect("review_results")

        try:
            result_id = int(result_id)
        except (TypeError, ValueError):
            messages.error(request, "Invalid result selected.")
            return redirect("review_results")

        try:
            with transaction.atomic():
                result = (
                    Result.objects.select_for_update()
                    .select_related(
                        "course_registration__course",
                        "course_registration__student__user",
                    )
                    .get(
                        pk=result_id,
                        status__in=[
                            Result.Status.SUBMITTED,
                            Result.Status.VERIFIED,
                        ],
                    )
                )

                if action == "verify":
                    if result.status != Result.Status.SUBMITTED:
                        messages.error(
                            request,
                            "This result is no longer pending verification.",
                        )
                        return redirect("review_results")

                    result.status = Result.Status.VERIFIED
                    result.verified_by = request.user
                    result.approved_by = None
                    result.full_clean()
                    result.save()
                    ResultAuditLog.objects.create(
                        result=result,
                        action=ResultAuditLog.Action.VERIFIED,
                        performed_by=request.user,
                        details=(
                            f"Verified by {request.user.get_full_name() or request.user.username}."
                        ),
                    )
                    ResultAuditLog.objects.create(
                        result=result,
                        action=ResultAuditLog.Action.FORWARDED,
                        performed_by=request.user,
                        details=(
                            "Forwarded to the Head of Department for final approval."
                        ),
                    )
                    # notify student that result was verified and forwarded
                    try:
                        student_user = result.course_registration.student.user
                        Notification.create_for(
                            recipient=student_user,
                            title="Result verified",
                            message=(f"Your result for {result.course_registration.course.code} was verified and forwarded to the HOD."),
                            link=f"/results/my-results/",
                            result=result,
                        )
                    except Exception:
                        pass
                    messages.success(
                        request,
                        f"Result for {result.course_registration.student.user.get_full_name() or result.course_registration.student.user.username} was verified and forwarded to the HOD.",
                    )
                else:
                    reason = (request.POST.get("reason") or "").strip()
                    if not reason:
                        messages.error(
                            request,
                            "A rejection reason is required before rejecting a result.",
                        )
                        return redirect("review_results")

                    result.status = Result.Status.REJECTED
                    result.verified_by = None
                    result.approved_by = None
                    result.full_clean()
                    result.save()
                    ResultAuditLog.objects.create(
                        result=result,
                        action=ResultAuditLog.Action.REJECTED,
                        performed_by=request.user,
                        details=reason,
                    )
                    messages.success(
                        request,
                        f"Result for {result.course_registration.student.user.get_full_name() or result.course_registration.student.user.username} was rejected and returned to the lecturer for correction.",
                    )
                    # notify lecturer about rejection
                    try:
                        course = result.course_registration.course
                        lecturer = course.lecturer
                        if lecturer:
                            Notification.create_for(
                                recipient=lecturer,
                                title="Result rejected",
                                message=(f"A result for {result.course_registration.student.user.get_full_name() or result.course_registration.student.user.username} in {course.code} was rejected and requires correction."),
                                link=f"/results/courses/{course.id}/",
                                result=result,
                            )
                    except Exception:
                        pass

            return redirect("review_results")

        except Result.DoesNotExist:
            messages.error(
                request,
                "This result is no longer pending review.",
            )
            return redirect("review_results")
        except ValidationError as exc:
            messages.error(request, f"Could not update result: {exc}")
            return redirect("review_results")

    return render(
        request,
        "results/review_results.html",
        {
            "results": results,
            "status_filter": filter_name,
            "pending_count": Result.objects.filter(
                status=Result.Status.SUBMITTED,
            ).count(),
            "verified_count": Result.objects.filter(
                status=Result.Status.VERIFIED,
            ).count(),
            "approved_count": Result.objects.filter(
                status=Result.Status.APPROVED,
            ).count(),
            "rejected_count": Result.objects.filter(
                status=Result.Status.REJECTED,
            ).count(),
            "dashboard_url": reverse("dashboard"),
        },
    )


@login_required
def hod_review_results(request):
    if request.user.role != User.Role.HOD:
        return HttpResponseForbidden(
            "Only the Head of Department can approve or reject final results."
        )

    filter_name = request.GET.get("status", "pending").strip().lower()
    allowed_statuses = {
        "pending": Result.Status.VERIFIED,
        "approved": Result.Status.APPROVED,
        "rejected": Result.Status.REJECTED,
    }
    selected_status = allowed_statuses.get(filter_name, Result.Status.VERIFIED)

    results = Result.objects.filter(
        status=selected_status,
    ).select_related(
        "course_registration__course",
        "course_registration__student__user",
    ).order_by(
        "course_registration__course__code",
        "course_registration__student__user__last_name",
        "course_registration__student__user__first_name",
    )

    if request.method == "POST":
        action = request.POST.get("action")
        result_id = request.POST.get("result_id")

        if action not in ("approve", "reject"):
            messages.error(request, "Invalid action.")
            return redirect("hod_review_results")

        if not result_id:
            messages.error(request, "No result selected.")
            return redirect("hod_review_results")

        try:
            result_id = int(result_id)
        except (TypeError, ValueError):
            messages.error(request, "Invalid result selected.")
            return redirect("hod_review_results")

        try:
            with transaction.atomic():
                result = (
                    Result.objects.select_for_update()
                    .select_related(
                        "course_registration__course",
                        "course_registration__student__user",
                    )
                    .get(
                        pk=result_id,
                        status=Result.Status.VERIFIED,
                    )
                )

                if action == "approve":
                    result.status = Result.Status.APPROVED
                    result.approved_by = request.user
                    result.full_clean()
                    result.save()
                    ResultAuditLog.objects.create(
                        result=result,
                        action=ResultAuditLog.Action.APPROVED,
                        performed_by=request.user,
                        details=(
                            f"Approved by {request.user.get_full_name() or request.user.username} after examination officer verification."
                        ),
                    )
                    # notify student that result is approved and published
                    try:
                        student_user = result.course_registration.student.user
                        Notification.create_for(
                            recipient=student_user,
                            title="Result approved",
                            message=(f"Your result for {result.course_registration.course.code} has been approved and published."),
                            link=f"/results/my-results/",
                            result=result,
                        )
                    except Exception:
                        pass
                    messages.success(
                        request,
                        f"Result for {result.course_registration.student.user.get_full_name() or result.course_registration.student.user.username} was approved and published to the student.",
                    )
                else:
                    reason = (request.POST.get("reason") or "").strip()
                    if not reason:
                        messages.error(
                            request,
                            "A rejection reason is required before rejecting a final result.",
                        )
                        return redirect("hod_review_results")

                    result.status = Result.Status.REJECTED
                    result.approved_by = None
                    result.full_clean()
                    result.save()
                    ResultAuditLog.objects.create(
                        result=result,
                        action=ResultAuditLog.Action.REJECTED,
                        performed_by=request.user,
                        details=reason,
                    )
                    messages.success(
                        request,
                        f"Result for {result.course_registration.student.user.get_full_name() or result.course_registration.student.user.username} was rejected and returned to the lecturer.",
                    )
                    # notify lecturer and student about HOD rejection
                    try:
                        course = result.course_registration.course
                        lecturer = course.lecturer
                        if lecturer:
                            Notification.create_for(
                                recipient=lecturer,
                                title="Result rejected by HOD",
                                message=(f"HOD rejected a result for {result.course_registration.student.user.get_full_name() or result.course_registration.student.user.username} in {course.code}. Please correct and resubmit."),
                                link=f"/results/courses/{course.id}/?focus_registration={result.course_registration.id}",
                                result=result,
                            )
                        student_user = result.course_registration.student.user
                        Notification.create_for(
                            recipient=student_user,
                            title="Result correction required",
                            message=(f"Your result for {result.course_registration.course.code} was rejected by HOD and is pending correction."),
                            link=f"/results/my-results/",
                            result=result,
                        )
                    except Exception:
                        pass

            return redirect("hod_review_results")

        except Result.DoesNotExist:
            messages.error(
                request,
                "This result is no longer waiting for final approval.",
            )
            return redirect("hod_review_results")
        except ValidationError as exc:
            messages.error(request, f"Could not update result: {exc}")
            return redirect("hod_review_results")

    return render(
        request,
        "results/hod_review_results.html",
        {
            "results": results,
            "status_filter": filter_name,
            "pending_count": Result.objects.filter(
                status=Result.Status.VERIFIED,
            ).count(),
            "approved_count": Result.objects.filter(
                status=Result.Status.APPROVED,
            ).count(),
            "rejected_count": Result.objects.filter(
                status=Result.Status.REJECTED,
            ).count(),
            "dashboard_url": reverse("dashboard"),
        },
    )


@login_required
def course_results(request, course_id):
    if request.user.role != User.Role.LECTURER:
        return HttpResponseForbidden(
            "Only lecturers can access course result entry."
        )

    from complaints.models import Complaint

    course = get_object_or_404(
        Course,
        pk=course_id,
        lecturer=request.user,
        is_active=True,
    )

    registrations = list(
        CourseRegistration.objects.filter(
            course=course,
            status=CourseRegistration.RegistrationStatus.REGISTERED,
        )
        .select_related("student__user")
        .order_by("student__user__last_name", "student__user__first_name")
    )

    results_by_registration = {
        result.course_registration_id: result
        for result in Result.objects.filter(
            course_registration__in=registrations
        )
    }

    active_complaint_result_ids = set(
        Complaint.objects.filter(
            result__course_registration__course=course,
        )
        .exclude(status__in=[Complaint.Status.RESOLVED, Complaint.Status.REJECTED])
        .values_list("result_id", flat=True)
    )

    def is_result_editable(result):
        if result is None:
            return True
        if result.status == Result.Status.DRAFT:
            return True
        if result.status in (
            Result.Status.SUBMITTED,
            Result.Status.VERIFIED,
            Result.Status.APPROVED,
        ):
            return result.id in active_complaint_result_ids
        return True

    form_values = {}
    errors = []

    if request.method == "POST":
        action = request.POST.get("action")

        if action not in ("save", "submit", "clear"):
            messages.error(request, "Invalid action.")
            return redirect("course_results", course_id=course.id)

        if action == "clear":
            drafts = Result.objects.filter(
                course_registration__in=registrations,
                status=Result.Status.DRAFT,
            )
            with transaction.atomic():
                for draft in drafts.select_related("course_registration"):
                    ResultAuditLog.objects.create(
                        result=draft,
                        action=ResultAuditLog.Action.CLEARED,
                        performed_by=request.user,
                        details="Draft cleared by lecturer.",
                    )
                count = drafts.count()
                drafts.delete()
            messages.success(request, f"{count} draft result(s) cleared.")
            return redirect("course_results", course_id=course.id)

        if action == "save":
            with transaction.atomic():
                for registration in registrations:
                    result = results_by_registration.get(registration.id)

                    if result and not is_result_editable(result):
                        continue

                    ca_raw = request.POST.get(
                        f"ca_{registration.id}", ""
                    ).strip()
                    exam_raw = request.POST.get(
                        f"exam_{registration.id}", ""
                    ).strip()

                    form_values[registration.id] = {
                        "ca_value": ca_raw,
                        "exam_value": exam_raw,
                    }

                    if not ca_raw and not exam_raw:
                        continue

                    if not ca_raw or not exam_raw:
                        errors.append(
                            f"{registration.student}: enter both CA and exam scores."
                        )
                        continue

                    try:
                        ca_score = Decimal(ca_raw)
                        exam_score = Decimal(exam_raw)
                    except InvalidOperation:
                        errors.append(
                            f"{registration.student}: enter valid numeric scores."
                        )
                        continue

                    if not ca_score.is_finite() or not exam_score.is_finite():
                        errors.append(
                            f"{registration.student}: scores must be valid numbers."
                        )
                        continue

                    if not Decimal("0") <= ca_score <= Decimal("30"):
                        errors.append(
                            f"{registration.student}: CA must be between 0 and 30."
                        )
                        continue

                    if not Decimal("0") <= exam_score <= Decimal("70"):
                        errors.append(
                            f"{registration.student}: exam must be between 0 and 70."
                        )
                        continue

                    is_new = result is None

                    if is_new:
                        result = Result(
                            course_registration=registration,
                            entered_by=request.user,
                        )
                    else:
                        result.entered_by = request.user

                    result.ca_score = ca_score
                    result.exam_score = exam_score
                    result.status = Result.Status.DRAFT
                    result.verified_by = None
                    result.approved_by = None

                    try:
                        result.full_clean()
                        result.save()
                    except ValidationError as exc:
                        errors.append(
                            f"{registration.student}: {exc}"
                        )
                        continue

                    ResultAuditLog.objects.create(
                        result=result,
                        action=(
                            ResultAuditLog.Action.CREATED
                            if is_new
                            else ResultAuditLog.Action.UPDATED
                        ),
                        performed_by=request.user,
                        details=(
                            "Result saved as draft."
                            if result.status == Result.Status.DRAFT
                            else "Result updated."
                        ),
                    )

            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                messages.success(request, "Draft results saved successfully.")
                return redirect("course_results", course_id=course.id)

        elif action == "submit":
            if not registrations:
                messages.error(
                    request,
                    "There are no registered students for this course.",
                )
            else:
                missing = [
                    registration
                    for registration in registrations
                    if registration.id not in results_by_registration
                ]

                if missing:
                    messages.error(
                        request,
                        f"{len(missing)} registered student(s) still need results. "
                        "Save results for every student before submitting.",
                    )
                else:
                    with transaction.atomic():
                        submission_errors = []

                        for registration in registrations:
                            result = results_by_registration[registration.id]

                            if not is_result_editable(result):
                                continue

                            result.status = Result.Status.SUBMITTED
                            result.verified_by = None
                            result.approved_by = None

                            try:
                                result.full_clean()
                                result.save()
                            except ValidationError as exc:
                                submission_errors.append(
                                    f"{registration.student}: {exc}"
                                )
                                continue

                            audit_action = (
                                ResultAuditLog.Action.CORRECTED
                                if result.status == Result.Status.SUBMITTED
                                and result.pk is not None
                                and ResultAuditLog.objects.filter(
                                    result=result,
                                    action=ResultAuditLog.Action.REJECTED,
                                ).exists()
                                else ResultAuditLog.Action.SUBMITTED
                            )
                            details = (
                                "Lecturer corrected and resubmitted rejected result for verification."
                                if audit_action == ResultAuditLog.Action.CORRECTED
                                else "Lecturer submitted result for examination officer verification."
                            )
                            ResultAuditLog.objects.create(
                                result=result,
                                action=audit_action,
                                performed_by=request.user,
                                details=details,
                            )

                    if submission_errors:
                        for error in submission_errors:
                            messages.error(request, error)
                    else:
                        messages.success(
                            request,
                            "Results submitted for examination officer verification.",
                        )
                        return redirect(
                            "course_results",
                            course_id=course.id,
                        )

    rows = []
    any_locked_result = False

    for registration in registrations:
        result = results_by_registration.get(registration.id)
        posted_values = form_values.get(registration.id, {})
        complaint_active = bool(result and result.id in active_complaint_result_ids)
        row_can_edit = is_result_editable(result)

        if result and not row_can_edit:
            any_locked_result = True

        rows.append({
            "registration": registration,
            "result": result,
            "complaint_active": complaint_active,
            "can_edit": row_can_edit,
            "ca_value": posted_values.get(
                "ca_value",
                str(result.ca_score) if result else "",
            ),
            "exam_value": posted_values.get(
                "exam_value",
                str(result.exam_score) if result else "",
            ),
        })

    return render(
        request,
        "results/course_results.html",
        {
            "course": course,
            "rows": rows,
            "total_students": len(registrations),
            "result_count": len(results_by_registration),
            "dashboard_url": reverse("dashboard"),
            "submit_locked": any_locked_result,
        },
    )


@login_required
def my_results(request):
    if request.user.role != User.Role.STUDENT:
        return HttpResponseForbidden("Only students can view their results.")

    try:
        student = request.user.student_profile
    except StudentProfile.DoesNotExist:
        return render(request, "results/my_results.html", {"student": None, "results": [], "gpa": 0, "cgpa": 0, "selected_session": None, "selected_level": None, "selected_semester": None, "sessions": [], "levels": [], "semesters": [], "page_title": "My Results"})

    sessions = AcademicSession.objects.filter(is_active=True).order_by("-start_date")
    levels = [100, 200, 300, 400, 500, 600]
    selected_session_id = request.GET.get("session")
    selected_level = request.GET.get("level")
    selected_semester_id = request.GET.get("semester")

    if selected_session_id:
        selected_session = sessions.filter(pk=selected_session_id).first()
    else:
        selected_session = sessions.filter(is_current=True).first() or sessions.first()

    if selected_level:
        try:
            selected_level = int(selected_level)
        except (TypeError, ValueError):
            selected_level = student.current_level
    else:
        selected_level = student.current_level

    if selected_semester_id:
        try:
            selected_semester = Semester.objects.filter(pk=selected_semester_id, session=selected_session).first()
        except (TypeError, ValueError):
            selected_semester = None
    else:
        selected_semester = None

    queryset = Result.objects.filter(
        course_registration__student=student,
        status=Result.Status.APPROVED,
    ).select_related(
        "course_registration__course__semester__session",
        "course_registration__course__programme",
    )

    if selected_session:
        queryset = queryset.filter(course_registration__course__semester__session=selected_session)
    if selected_level:
        queryset = queryset.filter(course_registration__course__level=selected_level)
    if selected_semester:
        queryset = queryset.filter(course_registration__course__semester=selected_semester)

    results = list(queryset.order_by("course_registration__course__code"))

    def compute_gpa(rows):
        total_credits = sum(r.course_registration.course.credit_units for r in rows)
        if total_credits == 0:
            return Decimal("0.00")
        weighted = sum((Decimal(r.grade_point) * Decimal(r.course_registration.course.credit_units)) for r in rows)
        return (weighted / Decimal(total_credits)).quantize(Decimal("0.01"))

    gpa = compute_gpa(results)
    all_approved = Result.objects.filter(
        course_registration__student=student,
        status=Result.Status.APPROVED,
    ).select_related(
        "course_registration__course__semester__session",
        "course_registration__course__programme",
    )
    cgpa = compute_gpa(list(all_approved))

    semesters = list(Semester.objects.filter(session=selected_session).order_by("start_date")) if selected_session else []
    return render(
        request,
        "results/my_results.html",
        {
            "student": student,
            "results": results,
            "gpa": gpa,
            "cgpa": cgpa,
            "selected_session": selected_session,
            "selected_level": selected_level,
            "selected_semester": selected_semester,
            "sessions": sessions,
            "levels": levels,
            "semesters": semesters,
            "page_title": "My Results",
        },
    )