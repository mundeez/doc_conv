import os
from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from . import views_list_and_api as _list_api
from .models import ConversionTask
from .formats import SUPPORTED_OUTPUTS, allowed_outputs as get_allowed_outputs

# re-export for urls.py
list_conversions = _list_api.list_conversions

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
        return render(request, "md2docx/home.html", {
            "convert_url": reverse("md2docx:convert"),
            "supported_outputs": SUPPORTED_OUTPUTS,
            "default_outputs": get_allowed_outputs('md'),
        })
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
        return render(request, "md2docx/convert.html", {"allowed_outputs": SUPPORTED_OUTPUTS.get('md')})

    # POST: create a DB-backed ConversionTask and enqueue it for background processing.
    uploaded = request.FILES.get("file")
    markdown_text = request.POST.get("markdown", "")

    if not uploaded and not markdown_text:
        return render(request, "md2docx/convert.html", {
            "error": "Please provide a file or paste markdown.",
            "allowed_outputs": SUPPORTED_OUTPUTS.get('md'),
            "task": None,
            "task_id": None,
        }, status=400)

    original_name = getattr(uploaded, 'name', '') if uploaded else ''
    input_ext = ''
    if uploaded and '.' in original_name:
        input_ext = original_name.rsplit('.', 1)[-1].lower()
    elif uploaded:
        input_ext = ''
    else:
        input_ext = 'md'

    allowed_outputs = get_allowed_outputs(input_ext)
    chosen_output = request.POST.get('output_format', 'docx').lower()
    if chosen_output not in allowed_outputs:
        return render(request, "md2docx/convert.html", {
            "error": f"Unsupported output format '{chosen_output}' for input type '{input_ext or 'unknown'}'.",
            "allowed_outputs": allowed_outputs,
            "task": None,
            "task_id": None,
        }, status=400)

    task = ConversionTask.objects.create(
        status=ConversionTask.STATUS_PENDING,
        output_format=chosen_output,
        original_filename=original_name,
    )

    dest_ext = input_ext or 'md'
    saved_path = None
    if uploaded:
        dest = UPLOADS_DIR / f"{task.id}.{dest_ext}"
        with dest.open("wb") as fh:
            for chunk in uploaded.chunks():
                fh.write(chunk)
        saved_path = str(dest)
    else:
        dest = UPLOADS_DIR / f"{task.id}.{dest_ext}"
        dest.write_text(markdown_text, encoding="utf-8")
        saved_path = str(dest)

    # persist metadata
    if saved_path:
        task.input_markdown = ''  # we store file on disk; input_markdown field kept blank
        task.progress = 0
        task.save()

    # Build links for the confirmation page
    status_url = reverse("md2docx:status", args=[task.id])
    download_url = reverse("md2docx:download", args=[task.id])

    context = {
        "task": task,
        "task_id": str(task.id),
        "status_url": status_url,
        "download_url": download_url,
        "output_format": chosen_output,
    }

    # Render an HTML confirmation page instead of JSON so users get clickable links
    context["allowed_outputs"] = allowed_outputs
    return render(request, "md2docx/convert.html", context, status=202)


def status(request, task_id):
    """
    Return a minimal JSON status for the given UUID task_id.
    Real implementations should look up persistent task state.
    """
    # Report DB-backed task state when available
    try:
        task = ConversionTask.objects.get(pk=task_id)
    except ConversionTask.DoesNotExist:
        docx_path = EXPORTS_DIR / f"{task_id}.docx"
        if docx_path.exists():
            payload = {"status": "done", "task_id": str(task_id), "download_url": reverse("md2docx:download", args=[task_id])}
        else:
            payload = {"status": "pending", "task_id": str(task_id)}
        return JsonResponse(payload)

    payload = {
        "status": task.status,
        "task_id": str(task.id),
        "progress": task.progress,
        "original_filename": task.original_filename,
        "output_format": task.output_format,
    }
    if task.status == ConversionTask.STATUS_DONE and task.result_file:
        payload["download_url"] = reverse("md2docx:download", args=[task.id])
    if task.status == ConversionTask.STATUS_FAILED:
        payload["error"] = task.error_message

    # Response type: default to JSON (backward compatible). Render HTML when explicitly requested.
    wants_html = request.GET.get("format") == "html"
    if not wants_html:
        return JsonResponse(payload)

    context = {
        "task": task,
        "task_id": str(task.id),
        "status_url": reverse("md2docx:status", args=[task.id]) + "?format=html",
        "download_url": payload.get("download_url"),
        "error_message": payload.get("error"),
        "output_format": task.output_format,
    }
    return render(request, "md2docx/status.html", context)


def download_docx(request, task_id):
    """
    Stream the generated .docx file for the given task_id.
    Raises 404 if the file does not exist.
    """
    # Prefer DB-backed stored file if available
    try:
        task = ConversionTask.objects.get(pk=task_id)
        if task.result_file and task.result_file.name:
            filename = os.path.basename(task.result_file.name)
            return FileResponse(task.result_file.open('rb'), as_attachment=True, filename=filename)
        # fallback path based on requested output_format
        fallback_ext = task.output_format or 'docx'
        candidate = EXPORTS_DIR / f"{task_id}.{fallback_ext}"
        if candidate.exists():
            return FileResponse(candidate.open('rb'), as_attachment=True, filename=f"{task_id}.{fallback_ext}")
    except ConversionTask.DoesNotExist:
        pass

    # final fallback: legacy .docx path
    docx_path = EXPORTS_DIR / f"{task_id}.docx"
    if not docx_path.exists():
        raise Http404("Document not found. Conversion may still be pending.")

    response = FileResponse(open(docx_path, "rb"), as_attachment=True, filename=f"{task_id}.docx")
    return response


@require_POST
def delete_task(request, task_id):
    """Delete a conversion task and its files, then redirect back to list."""
    try:
        task = ConversionTask.objects.get(pk=task_id)
    except ConversionTask.DoesNotExist:
        return redirect(reverse("md2docx:list"))

    # Remove output file
    if task.result_file and task.result_file.name:
        try:
            task.result_file.delete(save=False)
        except Exception:
            pass

    # Remove uploaded markdown file (if present)
    upload_path = UPLOADS_DIR / f"{task.id}.md"
    if upload_path.exists():
        try:
            upload_path.unlink()
        except Exception:
            pass

    task.delete()
    return redirect(reverse("md2docx:list"))


@require_http_methods(["POST"])
@csrf_exempt
def api_upload(request):
    """
    API endpoint for programmatic uploads. Accepts multipart form upload with key 'file'
    or POSTed 'markdown' text. Responds with a task_id and pending status.
    """
    uploaded = request.FILES.get("file")
    markdown_text = request.POST.get("markdown", "")

    if not uploaded and not markdown_text:
        return JsonResponse({"error": "No file or markdown provided"}, status=400)

    original_name = getattr(uploaded, 'name', '') if uploaded else ''
    input_ext = ''
    if uploaded and '.' in original_name:
        input_ext = original_name.rsplit('.', 1)[-1].lower()
    elif uploaded:
        input_ext = ''
    else:
        input_ext = 'md'

    allowed_outputs = get_allowed_outputs(input_ext)
    chosen_output = request.POST.get('output_format', 'docx').lower()
    if chosen_output not in allowed_outputs:
        return JsonResponse({
            "error": f"Unsupported output format '{chosen_output}' for input type '{input_ext or 'unknown'}'.",
            "allowed_outputs": allowed_outputs,
        }, status=400)

    task = ConversionTask.objects.create(
        status=ConversionTask.STATUS_PENDING,
        output_format=chosen_output,
        original_filename=original_name,
    )

    dest_ext = input_ext or 'md'
    saved_path = None
    if uploaded:
        dest = UPLOADS_DIR / f"{task.id}.{dest_ext}"
        with dest.open("wb") as fh:
            for chunk in uploaded.chunks():
                fh.write(chunk)
        saved_path = str(dest)
    else:
        dest = UPLOADS_DIR / f"{task.id}.{dest_ext}"
        dest.write_text(markdown_text, encoding="utf-8")
        saved_path = str(dest)

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