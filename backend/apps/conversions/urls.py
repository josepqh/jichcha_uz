from django.urls import path

from . import views

urlpatterns = [
    path("tools/", views.ToolListView.as_view(), name="tool-list"),
    path("usage/", views.UsageView.as_view(), name="usage"),
    path("tasks/", views.TaskCreateView.as_view(), name="task-create"),
    path("tasks/history/", views.TaskListView.as_view(), name="task-history"),
    path("tasks/<uuid:task_id>/", views.TaskDetailView.as_view(), name="task-detail"),
    path("files/<uuid:file_id>/", views.FileDownloadView.as_view(), name="file-download"),
]
