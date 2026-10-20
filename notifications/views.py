from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from notifications.models import Notification


@login_required
def notifications_list(request):
    if request.method == "POST":
        notification_id = request.POST.get("notification_id")
        if notification_id:
            try:
                notification = Notification.objects.get(pk=notification_id, recipient=request.user)
                notification.mark_as_read()
                messages.success(request, "Notification marked as read.")
            except Notification.DoesNotExist:
                messages.error(request, "Notification not found.")
        return redirect("notifications")

    notifications = Notification.objects.filter(recipient=request.user).order_by("-created_at")
    unread_count = Notification.unread_count_for(request.user)
    return render(
        request,
        "notifications/notifications.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
            "page_title": "Notifications",
        },
    )


@login_required
def notification_open(request, notification_id):
    try:
        notification = Notification.objects.get(pk=notification_id, recipient=request.user)
    except Notification.DoesNotExist:
        from django.contrib import messages
        messages.error(request, "Notification not found.")
        from django.shortcuts import redirect
        return redirect("notifications")

    # mark as read
    notification.mark_as_read()

    # redirect to the linked resource when present
    if notification.link:
        from django.shortcuts import redirect
        return redirect(notification.link)

    from django.shortcuts import redirect
    return redirect("notifications")
