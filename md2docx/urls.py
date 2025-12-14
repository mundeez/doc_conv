from django.urls import path
from . import views

app_name = "md2docx"

urlpatterns = [
    # UI
    path("", views.home, name="home"),
    path("convert/", views.convert_markdown, name="convert"),

    # Status & download by task id (use UUIDs for async operations)
    path("status/<uuid:task_id>/", views.status, name="status"),
    path("download/<uuid:task_id>/", views.download_docx, name="download"),

    # API endpoints (optional)
    path("api/upload/", views.api_upload, name="api_upload"),
]