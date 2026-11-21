from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.core.feedback import FeedbackView
from apps.core.health import HealthView

urlpatterns = [
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/feedback/", FeedbackView.as_view(), name="feedback"),
    path("api/v1/admin/", include("apps.staff.urls")),
    path("api/v1/", include("apps.conversions.urls")),
    path("api/v1/", include("apps.users.urls")),
]

if settings.DJANGO_ADMIN_URL:
    urlpatterns.insert(0, path(settings.DJANGO_ADMIN_URL, admin.site.urls))
