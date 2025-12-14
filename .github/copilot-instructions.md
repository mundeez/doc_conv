<!-- Instructions for AI coding agents working in this repository -->
# Copilot instructions for doc_conv

This file gives focused, actionable guidance for AI coding agents working on this Django project. Keep instructions short and concrete — only document patterns discoverable in the codebase.

## Big picture
- This is a small Django project named `doc_conv` with a single app `md2docx`.
- Architecture: Views enqueue `ConversionTask` records; a Django signal handler (`md2docx/signals.py`) spawns a background thread to process tasks synchronously using pandoc. Results are stored in `MEDIA_ROOT/exports/` and linked in the task record.
- URL routing: `doc_conv/urls.py` includes `md2docx.urls` at the `md2docx/` path. Most feature work lives in `md2docx/views.py`, `md2docx/signals.py`, and `md2docx/urls.py`.
- The app exposes UI endpoints (home, convert form, status page) and REST API endpoints (`/api/upload/`, `/status/<uuid>/`, `/download/<uuid>/`, `/list/` paginated list) for markdown → DOCX conversion.

## Key files to inspect
- `doc_conv/settings.py` — project settings (Django 4.2, sqlite DB, md2docx in INSTALLED_APPS).
- `doc_conv/urls.py` — includes `md2docx.urls`.
- `md2docx/urls.py` — routes: `home`, `convert`, `status/<uuid>`, `download/<uuid>`, `list`, `api/upload`.
- `md2docx/models.py` — `ConversionTask` model with UUID pk, status (pending/processing/done/failed), progress (0-100), original_filename, result_file, error_message.
- `md2docx/views.py` — view functions that create/enqueue ConversionTask records. Return JSON or render templates.
- `md2docx/signals.py` — post_save signal handler that spawns background thread on ConversionTask creation to run pandoc conversion.
- `md2docx/views_list_and_api.py` — list_conversions view with paginated results (10/25/50 per page).
- `md2docx/templates/md2docx/` — HTML templates: base.html (with header/footer partials), home.html, convert.html, status.html (with progress bar), list.html.

## Project-specific patterns and conventions
- **Task enqueueing:** Views (`convert_markdown`, `api_upload`) create a `ConversionTask` record with status "pending" and immediately return the task_id and status_url. They do NOT perform conversion.
- **Auto-conversion via signals:** When a task is created, the post_save signal handler in `signals.py` spawns a daemon thread that runs pandoc to convert the markdown file to DOCX, updates task progress/status, and stores the result_file path.
- **UUID task IDs:** All task identifiers are UUIDs. Routes use `<uuid:task_id>` converters. When creating or querying tasks, use UUID objects or string representations.
- **Progress tracking:** Tasks have a progress field (0-100). The signal handler updates it (20/40/100) as conversion progresses. Templates show a progress bar using `{{ task.progress }}%`.
- **Original filename preservation:** `original_filename` field stores the uploaded file name for easy identification in the list view.
- **Database:** SQLite (default in settings.py). Models are auto-discovered from `INSTALLED_APPS` — ensure `md2docx` is listed in settings.py.
- **CSRF exemption:** API endpoint `/api/upload/` is decorated with `@csrf_exempt` for programmatic access (safe because task IDs are UUIDs, not user-controlled).
- **File storage:** Uploads saved to `MEDIA_ROOT/uploads/<uuid>.md`; outputs to `MEDIA_ROOT/exports/<uuid>.docx`. Fallback: project base directory if MEDIA_ROOT not set.

## How to run, test and debug (discoverable commands)
- Install dependencies:
  - `pip install -r requirements.txt`
- Ensure pandoc is installed (for markdown→DOCX conversion):
  - Ubuntu/Debian: `sudo apt install pandoc`
  - macOS: `brew install pandoc`
- Run migrations & dev server:
  - `python manage.py makemigrations`
  - `python manage.py migrate`
  - `python manage.py runserver`
- Run tests: `python manage.py test`
- Manually process pending tasks (alternative to signal-based auto-conversion):
  - `python manage.py process_tasks --once` (process once and exit)
  - `python manage.py process_tasks` (run continuously, polling every 5s)

## Implementation hints with concrete examples
- When adding the `status` endpoint, return a JSON object with at least `status` and `task_id`. Example shape (JSON): `{"status": "pending", "task_id": "<uuid>", "progress": 0}`.
- For the `download` endpoint, return a streaming/file response that uses the `task_id` to look up the stored `.docx` file (store files under `MEDIA_ROOT` or a dedicated `exports/` directory). Reverse the URL using the app namespace: `reverse('md2docx:download', args=[task_id])`.
- Because `md2docx/urls.py` expects views named `home`, `convert_markdown`, `status`, `download_docx`, and `api_upload`, implement or stub those exact names to avoid breaking imports.
- Signal handler pattern: Use Django's `post_save` signal to trigger background work. Import signals in `AppConfig.ready()` so they're loaded when the app starts. Example:
  ```python
  from django.db.models.signals import post_save
  from django.dispatch import receiver
  
  @receiver(post_save, sender=ConversionTask)
  def auto_process(sender, instance, created, **kwargs):
      if created:
          # spawn a thread or enqueue to a task queue
          thread = threading.Thread(target=process_task, args=(instance.id,), daemon=True)
          thread.start()
  ```

## Safety and repository constraints
- `doc_conv/settings.py` contains a hard-coded SECRET_KEY and `DEBUG = True` — do not change production secrets in PRs; instead, add .env-based config if needed and document it.
- No CI config or third-party integrations are present in the repository; if adding them, update this file with how to run relevant checks locally.

## Useful next steps for a contributor or agent
1. Ensure `requirements.txt` is installed and pandoc is available on the system.
2. Run migrations to create the `ConversionTask` table.
3. Start the dev server — conversions will run automatically on upload via the signal handler.
4. Test the UI at http://localhost:8000/md2docx/ or the API at /md2docx/api/upload/.
5. Monitor the list view at http://localhost:8000/md2docx/list/ to see completed conversions with pagination.
6. Optional: add unit tests in `md2docx/tests.py` for task creation, signal handling, and the list view.

## If something is missing
- If you need clarification about background task handling or storage for generated files, ask the maintainers before adding external services (S3, Celery). There are no discoverable configs in this repo for those services.

---
Please review and tell me which parts you want expanded (examples of view implementations, test templates, or CI commands) and I will update this file accordingly.
