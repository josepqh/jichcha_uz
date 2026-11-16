from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="staff-dashboard"),
    path("load/", views.LoadView.as_view(), name="staff-load"),
    path("users/", views.UserListView.as_view(), name="staff-users"),
    path("users/<uuid:user_id>/block/", views.UserBlockView.as_view(), name="staff-user-block"),
    path("failures/", views.FailureListView.as_view(), name="staff-failures"),
    path("limits/", views.LimitListView.as_view(), name="staff-limits"),
    path("limits/<str:role>/", views.LimitDetailView.as_view(), name="staff-limit"),
    path("tools/", views.ToolSwitchListView.as_view(), name="staff-tools"),
    path("tools/<str:slug>/", views.ToolSwitchView.as_view(), name="staff-tool"),
]
