from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from notifications.models import Notification
from results.models import Result

from .forms import ComplaintSubmissionForm
from .models import Complaint


def _assign_staff_for_complaint(complaint):
    result = complaint.result
    if result:
        course = result.course_registration.course
        department_name = course.programme.department.name
    else:
        department_name = ""
        student_profile = getattr(complaint.student, "student_profile", None)
        if student_profile and student_profile.programme_id:
            department_name = student_profile.programme.department.name
        elif complaint.student:
            department_name = (getattr(complaint.student, "department", "") or "").strip()

    if result:
        complaint.lecturer = course.lecturer
    elif complaint.student and getattr(complaint.student, "student_profile", None):
        complaint.lecturer = (
            User.objects.filter(
                role=User.Role.LECTURER,
                department__iexact=complaint.student.student_profile.programme.department.name,
            )
            .order_by("id")
            .first()
            or User.objects.filter(role=User.Role.LECTURER).order_by("id").first()
        )
    else:
        complaint.lecturer = (
            User.objects.filter(role=User.Role.LECTURER, department__iexact=department_name)
            .order_by("id")
            .first()
            or User.objects.filter(role=User.Role.LECTURER).order_by("id").first()
        )

    complaint.exam_officer = (
        User.objects.filter(
            role=User.Role.EXAM_OFFICER,
            department__iexact=department_name,
        )
        .order_by("id")
        .first()
        or User.objects.filter(role=User.Role.EXAM_OFFICER).order_by("id").first()
    )

    complaint.hod = (
        User.objects.filter(
            role=User.Role.HOD,
            department__iexact=department_name,
        )
        .order_by("id")
        .first()
        or User.objects.filter(role=User.Role.HOD).order_by("id").first()
    )


def _allowed_actions_for_role(user_role, complaint_status):
    if user_role == User.Role.LECTURER:
        return {
            "review",
            "await_exam_officer",
            "note",
        }
    if user_role == User.Role.EXAM_OFFICER:
        return {
            "await_lecturer",
            "await_hod",
            "note",
        }
    if user_role == User.Role.HOD:
        return {
            "resolve",
            "reject",
            "note",
        }
    return {"note"}


def _complaint_transition_allowed(current_status, action, user_role):
    lecturer_actions = {
        Complaint.Status.SUBMITTED: {"review", "await_exam_officer"},
        Complaint.Status.UNDER_REVIEW: {"await_exam_officer"},
        Complaint.Status.AWAITING_LECTURER: {"review", "await_exam_officer"},
    }
    exam_officer_actions = {
        Complaint.Status.SUBMITTED: {"await_lecturer", "await_hod"},
        Complaint.Status.UNDER_REVIEW: {"await_lecturer", "await_hod"},
        Complaint.Status.AWAITING_EXAM_OFFICER: {"await_lecturer", "await_hod"},
    }
    hod_actions = {
        Complaint.Status.AWAITING_HOD: {"resolve", "reject"},
        Complaint.Status.UNDER_REVIEW: {"resolve", "reject"},
    }

    if user_role == User.Role.LECTURER:
        return action in lecturer_actions.get(current_status, set())
    if user_role == User.Role.EXAM_OFFICER:
        return action in exam_officer_actions.get(current_status, set())
    if user_role == User.Role.HOD:
        return action in hod_actions.get(current_status, set())
    return False


@login_required
def complaint_submit(request):
    if request.user.role != User.Role.STUDENT:
        return HttpResponseForbidden("Only students can submit complaints.")

    if request.method == "POST":
        selected_result_id = request.POST.get("result")
        if selected_result_id:
            own_result_ids = set(
                Result.objects.filter(
                    course_registration__student__user=request.user,
                ).values_list("id", flat=True)
            )
            if int(selected_result_id) not in own_result_ids:
                form = ComplaintSubmissionForm(request.user, request.POST)
                form.add_error("result", "You can only submit a complaint for one of your own results.")
                return render(
                    request,
                    "complaints/complaint_submit.html",
                    {"form": form, "page_title": "Submit Complaint"},
                )

        form = ComplaintSubmissionForm(request.user, request.POST)
        if form.is_valid():
            with transaction.atomic():
                complaint = form.save(commit=False)
                complaint.student = request.user
                _assign_staff_for_complaint(complaint)
                complaint.status = Complaint.Status.SUBMITTED
                complaint.save()
                complaint.ensure_recipients()
                complaint.record_history(
                    actor=request.user,
                    previous_status="",
                    new_status=Complaint.Status.SUBMITTED,
                    message="Complaint submitted by the student.",
                )
                for recipient in complaint.recipients.select_related("user"):
                    if recipient.user == request.user:
                        continue
                    _notify_complaint_event(
                        complaint,
                        recipient.user,
                        "Complaint assigned",
                        f"New complaint {complaint.reference_number} requires your review.",
                    )
            messages.success(
                request,
                f"Your complaint has been submitted successfully. Reference: {complaint.reference_number}",
            )
            return redirect("complaint_detail", reference=complaint.reference_number)
    else:
        # Allow semester selection via GET so the results dropdown can refresh
        semester_val = request.GET.get("semester") or None
        if semester_val:
            form = ComplaintSubmissionForm(request.user, request.GET)
        else:
            form = ComplaintSubmissionForm(request.user)

    return render(
        request,
        "complaints/complaint_submit.html",
        {"form": form, "page_title": "Submit Complaint"},
    )


@login_required
def complaint_history(request):
    if request.user.role != User.Role.STUDENT:
        return HttpResponseForbidden("Only students can view their complaint history.")

    complaints = Complaint.objects.filter(student=request.user).select_related(
        "result__course_registration__course",
        "lecturer",
        "exam_officer",
        "hod",
    )
    return render(
        request,
        "complaints/complaint_history.html",
        {"complaints": complaints, "page_title": "Complaint History"},
    )


@login_required
def complaint_queue(request):
    if request.user.role not in [
        User.Role.LECTURER,
        User.Role.EXAM_OFFICER,
        User.Role.HOD,
    ]:
        return HttpResponseForbidden("You do not have access to complaint queues.")

    status_filter = request.GET.get("status", "all")
    queryset = Complaint.objects.select_related(
        "student",
        "result__course_registration__course",
        "lecturer",
        "exam_officer",
        "hod",
    )

    if request.user.role == User.Role.LECTURER:
        queryset = queryset.filter(lecturer=request.user)
    elif request.user.role == User.Role.EXAM_OFFICER:
        queryset = queryset.filter(exam_officer=request.user)
    elif request.user.role == User.Role.HOD:
        queryset = queryset.filter(hod=request.user)

    if status_filter != "all":
        queryset = queryset.filter(status=status_filter)

    return render(
        request,
        "complaints/complaint_queue.html",
        {"complaints": queryset, "status_filter": status_filter, "page_title": "Complaint Queue"},
    )


@login_required
def complaint_detail(request, reference):
    complaint = get_object_or_404(
        Complaint.objects.select_related(
            "student",
            "result__course_registration__course",
            "lecturer",
            "exam_officer",
            "hod",
        ),
        reference_number=reference,
    )

    if request.user.role == User.Role.STUDENT:
        if complaint.student_id != request.user.id:
            return HttpResponseForbidden("You can only view your own complaint.")
        can_manage = False
    elif request.user.role == User.Role.LECTURER:
        if complaint.lecturer_id != request.user.id:
            return HttpResponseForbidden("You are not assigned to this complaint.")
        can_manage = True
    elif request.user.role == User.Role.EXAM_OFFICER:
        if complaint.exam_officer_id != request.user.id:
            return HttpResponseForbidden("You are not assigned to this complaint.")
        can_manage = True
    elif request.user.role == User.Role.HOD:
        if complaint.hod_id != request.user.id:
            return HttpResponseForbidden("You are not assigned to this complaint.")
        can_manage = True
    else:
        return HttpResponseForbidden("You are not permitted to view this complaint.")

    if request.method == "POST":
        action = request.POST.get("action")
        if not can_manage:
            return HttpResponseForbidden("Only assigned staff can update this complaint.")

        if action not in {"review", "await_lecturer", "await_exam_officer", "await_hod", "resolve", "reject", "note"}:
            messages.error(request, "Invalid complaint action.")
            return redirect("complaint_detail", reference=complaint.reference_number)

        decision = (request.POST.get("decision") or "").strip()
        note = (request.POST.get("note") or "").strip()

        if action in {"resolve", "reject"} and not decision:
            messages.error(request, "A reason or explanation is required.")
            return redirect("complaint_detail", reference=complaint.reference_number)

        if action == "note" and not note:
            messages.error(request, "A note is required.")
            return redirect("complaint_detail", reference=complaint.reference_number)

        with transaction.atomic():
            previous_status = complaint.status
            if action == "note":
                complaint.add_note(request.user, note, is_internal=True)
                complaint.record_history(
                    actor=request.user,
                    previous_status=previous_status,
                    new_status=complaint.status,
                    message=note,
                    is_internal_note=True,
                )
                messages.success(request, "Internal note added.")
                return redirect("complaint_detail", reference=complaint.reference_number)

            if previous_status in {Complaint.Status.RESOLVED, Complaint.Status.REJECTED}:
                messages.error(request, "This complaint is closed and cannot be forwarded or edited again.")
                return redirect("complaint_detail", reference=complaint.reference_number)

            if not _complaint_transition_allowed(previous_status, action, request.user.role):
                messages.error(request, "This complaint cannot be moved into that status from its current state.")
                return redirect("complaint_detail", reference=complaint.reference_number)

            target_status = {
                "review": Complaint.Status.UNDER_REVIEW,
                "await_lecturer": Complaint.Status.AWAITING_LECTURER,
                "await_exam_officer": Complaint.Status.AWAITING_EXAM_OFFICER,
                "await_hod": Complaint.Status.AWAITING_HOD,
                "resolve": Complaint.Status.RESOLVED,
                "reject": Complaint.Status.REJECTED,
            }.get(action)

            latest_history = complaint.history.order_by("-created_at").first()
            if latest_history and latest_history.actor_id == request.user.id and latest_history.new_status == target_status and latest_history.previous_status == previous_status:
                messages.info(request, "This complaint action was already recorded.")
                return redirect("complaint_detail", reference=complaint.reference_number)

            if action == "review":
                complaint.status = Complaint.Status.UNDER_REVIEW
                complaint.save()
                complaint.record_history(
                    actor=request.user,
                    previous_status=previous_status,
                    new_status=Complaint.Status.UNDER_REVIEW,
                    message="Complaint moved to under review.",
                    is_internal_note=True,
                )
                # notify student that complaint moved under review
                if complaint.student:
                    _notify_complaint_event(
                        complaint,
                        complaint.student,
                        "Complaint updated",
                        f"Your complaint {complaint.reference_number} is under review.",
                    )
            elif action == "await_lecturer":
                complaint.status = Complaint.Status.AWAITING_LECTURER
                complaint.save()
                complaint.record_history(
                    actor=request.user,
                    previous_status=previous_status,
                    new_status=Complaint.Status.AWAITING_LECTURER,
                    message="Complaint was returned to the lecturer for review.",
                    decision_message=decision,
                    is_internal_note=True,
                )
                if complaint.student:
                    _notify_complaint_event(
                        complaint,
                        complaint.student,
                        "Complaint updated",
                        f"Your complaint {complaint.reference_number} has been returned to the lecturer.",
                    )
            elif action == "await_exam_officer":
                complaint.status = Complaint.Status.AWAITING_EXAM_OFFICER
                complaint.save()
                complaint.record_history(
                    actor=request.user,
                    previous_status=previous_status,
                    new_status=Complaint.Status.AWAITING_EXAM_OFFICER,
                    message="Complaint was forwarded to the examination officer.",
                    decision_message=decision,
                    is_internal_note=True,
                )
                if complaint.student:
                    _notify_complaint_event(
                        complaint,
                        complaint.student,
                        "Complaint updated",
                        f"Your complaint {complaint.reference_number} has been forwarded to the examination officer.",
                    )
            elif action == "await_hod":
                complaint.status = Complaint.Status.AWAITING_HOD
                complaint.save()
                complaint.record_history(
                    actor=request.user,
                    previous_status=previous_status,
                    new_status=Complaint.Status.AWAITING_HOD,
                    message="Complaint was escalated to the Head of Department.",
                    decision_message=decision,
                    is_internal_note=True,
                )
                if complaint.student:
                    _notify_complaint_event(
                        complaint,
                        complaint.student,
                        "Complaint updated",
                        f"Your complaint {complaint.reference_number} has been escalated to the Head of Department.",
                    )
            elif action == "resolve":
                complaint.status = Complaint.Status.RESOLVED
                complaint.save()
                complaint.record_history(
                    actor=request.user,
                    previous_status=previous_status,
                    new_status=Complaint.Status.RESOLVED,
                    message="Complaint resolved.",
                    decision_message=decision,
                    is_internal_note=False,
                )
                if complaint.student:
                    _notify_complaint_event(
                        complaint,
                        complaint.student,
                        "Complaint resolved",
                        f"Your complaint {complaint.reference_number} has been resolved.",
                    )
            elif action == "reject":
                complaint.status = Complaint.Status.REJECTED
                complaint.save()
                complaint.record_history(
                    actor=request.user,
                    previous_status=previous_status,
                    new_status=Complaint.Status.REJECTED,
                    message="Complaint rejected.",
                    decision_message=decision,
                    is_internal_note=False,
                )
                if complaint.student:
                    _notify_complaint_event(
                        complaint,
                        complaint.student,
                        "Complaint rejected",
                        f"Your complaint {complaint.reference_number} has been rejected.",
                    )

        messages.success(request, "Complaint status updated successfully.")
        return redirect("complaint_detail", reference=complaint.reference_number)

    visible_history = complaint.history.filter(is_internal_note=False) if not can_manage else complaint.history.all()
    visible_notes = complaint.notes.filter(is_internal=False) if not can_manage else complaint.notes.all()

    if request.user.role != User.Role.STUDENT:
        complaint.track_as_read(request.user)

    return render(
        request,
        "complaints/complaint_detail.html",
        {
            "complaint": complaint,
            "notes": visible_notes,
            "history": visible_history,
            "can_manage": can_manage,
            "allowed_actions": _allowed_actions_for_role(request.user.role, complaint.status),
            "page_title": f"Complaint {complaint.reference_number}",
        },
    )


def _notify_complaint_event(complaint, recipient, title, message):
    return Notification.create_for(
        recipient=recipient,
        title=title,
        message=message,
        link=f"/complaints/{complaint.reference_number}/",
        complaint=complaint,
    )


def _seed_complaint_recipients_and_notifications(complaint):
    if not complaint:
        return []

    recipients = complaint.ensure_recipients()
    for recipient in recipients:
        if recipient.user == complaint.student:
            continue
        if not Notification.objects.filter(
            complaint=complaint,
            recipient=recipient.user,
        ).exists():
            _notify_complaint_event(
                complaint,
                recipient.user,
                "Complaint assigned",
                f"New complaint {complaint.reference_number} requires your review.",
            )
    return recipients
