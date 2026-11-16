from django.contrib import admin
from django.urls import include, path

from apps.core.health import HealthView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/", include("apps.conversions.urls")),
    path("api/v1/", include("apps.users.urls")),
]
