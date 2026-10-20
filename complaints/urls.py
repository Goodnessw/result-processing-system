from django.urls import path

from .views import (
    complaint_detail,
    complaint_history,
    complaint_queue,
    complaint_submit,
)

urlpatterns = [
    path("submit/", complaint_submit, name="complaint_submit"),
    path("history/", complaint_history, name="complaint_history"),
    path("queue/", complaint_queue, name="complaint_queue"),
    path("<str:reference>/", complaint_detail, name="complaint_detail"),
]
