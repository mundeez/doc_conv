from django.shortcuts import render
import os
import uuid
from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .views_list_and_api import list_conversions
from .models import ConversionTask

# Create your views here.
# Minimal, importable view stubs for md2docx.urls
# These are intentionally simple and suitable for local development.
# Long-running conversion/background processing is not implemented here;
# views return a UUID task id and simple statuses so the front-end can poll.

MEDIA_ROOT = Path(getattr(settings, "MEDIA_ROOT", settings.BASE_DIR))  # fallback to BASE_DIR if MEDIA_ROOT missing
EXPORTS_DIR = MEDIA_ROOT / "exports"
UPLOADS_DIR = MEDIA_ROOT / "uploads"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def home(request):
    """
    Render a simple home page. Template is optional; if not present this will
    return a very small HTML response linking to the convert endpoint.
    """
    try:
        return render(request, "md2docx/home.html", {"convert_url": reverse("md2docx:convert")})
    except Exception:
        # Fallback minimal HTML so server is runnable without templates
        html = f"""
        <html><body>
          <h1>md2docx</h1>
          <p>Convert Markdown to DOCX</p>
                    <form action="{reverse('md2docx:convert')}" method="post" enctype="multipart/form-data">
            <textarea name="markdown" rows="10" cols="60"></textarea><br/>
            <input type="file" name="file"/><br/>
            <button type="submit">Convert</button>
          </form>
        </body></html>
        """
        return HttpResponse(html)


@require_http_methods(["GET", "POST"])
def convert_markdown(request):
    """
    Accepts a POST with either:
      - 'markdown' text field, or
      - file upload in 'file'
    Creates a UUID task id and returns a JSON response with status "pending".
    In a real implementation this would enqueue a background job to produce the .docx.
    """
    if request.method == "GET":
        # Simple form for manual testing / browser use
        return home(request)

    # POST: create a DB-backed ConversionTask and enqueue it for background processing.
    task = ConversionTask.objects.create(status=ConversionTask.STATUS_PENDING)

    uploaded = request.FILES.get("file")
    saved_path = None
    original_name = ""
    if uploaded:
        original_name = getattr(uploaded, 'name', '')
        dest = UPLOADS_DIR / f"{task.id}.md"
        with dest.open("wb") as fh:
            for chunk in uploaded.chunks():
                fh.write(chunk)
        saved_path = str(dest)
    else:
        markdown_text = request.POST.get("markdown", "")
        if markdown_text:
            dest = UPLOADS_DIR / f"{task.id}.md"
            dest.write_text(markdown_text, encoding="utf-8")
            saved_path = str(dest)

    # persist metadata
    if saved_path:
        task.input_markdown = ''  # we store file on disk; input_markdown field kept blank
        task.original_filename = original_name
        task.progress = 0
        task.save()

    # Return immediate response with task id and endpoints so a worker can pick it up.
    status_payload = {
        "status": task.status,
        "task_id": str(task.id),
        "saved_input": saved_path,
        "status_url": reverse("md2docx:status", args=[task.id]),
        "download_url": reverse("md2docx:download", args=[task.id]),
    }

    return JsonResponse(status_payload, status=202)


def status(request, task_id):
    """
    Return a minimal JSON status for the given UUID task_id.
    Real implementations should look up persistent task state.
    """
    # Report DB-backed task state when available
    try:
        task = ConversionTask.objects.get(pk=task_id)
    except ConversionTask.DoesNotExist:
        # fall back to file-based check
        docx_path = EXPORTS_DIR / f"{task_id}.docx"
        if docx_path.exists():
            return JsonResponse({"status": "finished", "task_id": str(task_id), "download_url": reverse("md2docx:download", args=[task_id])})
        return JsonResponse({"status": "pending", "task_id": str(task_id)})

    payload = {
        "status": task.status,
        "task_id": str(task.id),
        "progress": task.progress,
        "original_filename": task.original_filename,
    }
    if task.status == ConversionTask.STATUS_DONE and task.result_file:
        payload["download_url"] = reverse("md2docx:download", args=[task.id])
    if task.status == ConversionTask.STATUS_FAILED:
        payload["error"] = task.error_message
    return JsonResponse(payload)


def download_docx(request, task_id):
    """
    Stream the generated .docx file for the given task_id.
    Raises 404 if the file does not exist.
    """
    # Prefer DB-backed stored file if available
    try:
        task = ConversionTask.objects.get(pk=task_id)
        if task.result_file and task.result_file.name:
            return FileResponse(task.result_file.open('rb'), as_attachment=True, filename=os.path.basename(task.result_file.name))
    except ConversionTask.DoesNotExist:
        pass

    docx_path = EXPORTS_DIR / f"{task_id}.docx"
    if not docx_path.exists():
        raise Http404("Document not found. Conversion may still be pending.")

    response = FileResponse(open(docx_path, "rb"), as_attachment=True, filename=f"{task_id}.docx")
    return response


@require_http_methods(["POST"])
def api_upload(request):
    """
    API endpoint for programmatic uploads. Accepts multipart form upload with key 'file'
    or POSTed 'markdown' text. Responds with a task_id and pending status.
    """
    uploaded = request.FILES.get("file")
    task = ConversionTask.objects.create(status=ConversionTask.STATUS_PENDING)
    saved_path = None
    original_name = ""

    if uploaded:
        original_name = getattr(uploaded, 'name', '')
        dest = UPLOADS_DIR / f"{task.id}.md"
        with dest.open("wb") as fh:
            for chunk in uploaded.chunks():
                fh.write(chunk)
        saved_path = str(dest)
    else:
        markdown_text = request.POST.get("markdown", "")
        if markdown_text:
            dest = UPLOADS_DIR / f"{task.id}.md"
            dest.write_text(markdown_text, encoding="utf-8")
            saved_path = str(dest)
        else:
            return JsonResponse({"error": "No file or markdown provided"}, status=400)

    task.original_filename = original_name
    task.progress = 0
    task.save()

    payload = {
        "status": task.status,
        "task_id": str(task.id),
        "saved_input": saved_path,
        "status_url": reverse("md2docx:status", args=[task.id]),
        "download_url": reverse("md2docx:download", args=[task.id]),
    }
    return JsonResponse(payload, status=201)