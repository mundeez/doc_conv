<!-- Short, actionable instructions for AI coding agents working in this repo -->
# Copilot instructions — doc_conv

Concise, discoverable patterns to be productive quickly. Keep edits small, aligned with existing behavior.

## Big picture
- Django project with single app `md2docx`: converts uploaded/pasted Markdown → DOCX (and PDF/other outputs supported by pandoc readers/writers).
- Views create `ConversionTask` rows (UUID PK, status/progress). A `post_save` signal spawns a daemon thread to run `pandoc`, writing outputs to `MEDIA_ROOT/exports/`.
- Files: uploads to `MEDIA_ROOT/uploads/<uuid>.<ext>`; outputs to `MEDIA_ROOT/exports/<uuid or sanitized name>.<ext>`. Fallback to `BASE_DIR` when `MEDIA_ROOT` missing.

## Key files
- `md2docx/models.py` — `ConversionTask` (UUID id, status pending/processing/done/failed, progress, result_file, error_message, output_format, original_filename).
- `md2docx/views.py` — UI/API: `home`, `convert_markdown`, `status`, `download_docx`, `delete_task`, `api_upload`.
- `md2docx/signals.py` — `post_save` handler starts background thread `_process_task` (pandoc subprocess; progress 20/40/100; skips when DB name contains "test").
- `md2docx/views_list_and_api.py` — `list_conversions` paginated (10/25/50 per page; shows done tasks).
- `md2docx/apps.py` — imports signals in `ready()`; best-effort pandoc capability check (logs warnings, non-fatal).
- `md2docx/management/commands/process_tasks.py` — optional CLI worker instead of signals (polling loop / --once).

## Conventions & gotchas
- Treat task IDs as UUID strings; URL converters use `<uuid:task_id>`.
- Always include `progress` and `status` in status responses; add `download_url` when done, `error` when failed.
- Sanitized output names: signals use original filename stem when safe; otherwise `<uuid>.<ext>`.
- Test DBs: signal processing is skipped (name contains `test`), so tests won't spawn pandoc threads.
- Default output format is `docx`; `output_format` is stored on the task.

## Run & test locally
```bash
pip install -r requirements.txt
sudo apt install pandoc            # or brew install pandoc (macOS)
python manage.py makemigrations
python manage.py migrate
pip install ruff                   # linting (local/dev)
ruff check .
python manage.py test
python manage.py runserver
```

## Docker / Compose
- Build & run dev stack: `docker compose up --build`
- Web listens on `http://localhost:8000`; volumes mount `./uploads` and `./exports` for persistence.
- Pandoc binary can be overridden via `PANDOC_BIN` env (e.g., point to a wrapper that runs `docker run --rm pandoc/core ...`).
  - Example wrapper: set `PANDOC_BIN=./scripts/pandoc_docker.sh` (runs `docker run --rm -v "$PWD":/data -w /data pandoc/core:3.1 ...`).


## API / UX snippets
- Upload via API (multipart): `curl -F "file=@example.md" -F "output_format=docx" http://localhost:8000/md2docx/api/upload/`
- Status polling: `curl http://localhost:8000/md2docx/status/<uuid>/`
- Render status as HTML: `GET /md2docx/status/<uuid>/?format=html`
- Download: `GET /md2docx/download/<uuid>/`

## Minimal test template (Django TestCase)
```python
from django.test import TestCase
from django.urls import reverse

class StatusViewTests(TestCase):
    def test_status_pending(self):
        resp = self.client.get(reverse('md2docx:status', args=['00000000-0000-0000-0000-000000000000']))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'pending')
```

## Contributor checklist (pre-PR)
- Format not enforced; keep style consistent with existing files.
- Ensure pandoc is available locally if touching conversion logic.
- Lint: `ruff check .`
- Run tests: `python manage.py test` (signals are skipped in tests, so no pandoc needed for unit tests).
- If you add new commands/endpoints, document them here and/or in `README.md`.

## CI (GitHub Actions)
- Workflow: `.github/workflows/ci.yml` (Python 3.11). Steps: checkout → install Python → `apt-get install pandoc` → `pip install -r requirements.txt` → `pip install ruff` → `ruff check .` → `python manage.py test`.
- If you add deps or commands, update the workflow and this file.

## Safety constraints
- `doc_conv/settings.py` has hard-coded `SECRET_KEY`, `DEBUG=True` for dev. Do not add production secrets; prefer env vars if adjusting.
- CSRF is exempt on `/api/upload/`; keep UUID task IDs and validations intact when modifying API.

## Debug tips
- Inspect `uploads/` and `exports/` paths under `MEDIA_ROOT` (or project root fallback).
- Signal failures write `error_message` on the task; see `md2docx/signals.py` pandoc stderr/stdout handling.

If you need more depth (e.g., extending tests, PDF defaults, or CLI worker usage), ask to expand the relevant section.<!-- Short, actionable instructions for AI coding agents working on this repo -->
# Copilot instructions — doc_conv (condensed)

This file contains only the immediately useful, discoverable rules and patterns for making small, safe changes to the repository.

## Big picture (one paragraph)
- Small Django app `doc_conv` with a single app `md2docx` that converts Markdown → DOCX.
- Views create `ConversionTask` DB rows (UUID primary key). A `post_save` signal spawns a daemon thread to run `pandoc` and write outputs to `MEDIA_ROOT/exports/`.

## Key files (quick map)
- `md2docx/models.py` — `ConversionTask` (UUID id, status, progress, result_file, error_message).
- `md2docx/views.py` — UI + API endpoints: `home`, `convert_markdown`, `status`, `download_docx`, `delete_task`, `api_upload`.
- `md2docx/signals.py` — `post_save` handler that starts `_process_task` in a background thread; uses `pandoc` via subprocess.
- `md2docx/apps.py` — imports signals in `ready()` and does a best-effort pandoc capability check.
- `md2docx/views_list_and_api.py` — paginated `list_conversions` (10/25/50 per page).

## Patterns & conventions agents must follow
- Task lifecycle: views create a `ConversionTask` with status `pending`; signal processing will set `processing/done/failed` and update `progress` (20/40/100).
- Files: uploads → `MEDIA_ROOT/uploads/<uuid>.<ext>`; outputs → `MEDIA_ROOT/exports/<uuid>.<ext>` (or sanitized original filename). Use `settings.MEDIA_ROOT` fallback to `BASE_DIR` when reading/writing files.
- Identifiers: always treat task IDs as UUID strings (URL converters use `<uuid:task_id>`).
- Tests: signal processing is skipped for SQLite test DBs (signals check for 'test' in DB name). Tests can be run with `python manage.py test`.

## How to run locally (exact commands)
1. Install deps: `pip install -r requirements.txt`
2. Ensure pandoc is installed (system package). Example: `sudo apt install pandoc`.
3. Migrate and run server:
   - `python manage.py makemigrations`
   - `python manage.py migrate`
   - `python manage.py runserver`

## Quick examples for agents making edits
- Adding/changes to status API: return at minimum `{"status": "pending|processing|done|failed", "task_id": "<uuid>"}` and include `progress` when available. See `md2docx/views.py::status`.
- When changing background behavior, prefer adding or updating `management/commands/process_tasks.py` (CLI worker) rather than altering signal threading logic — signals are the default production-suitable approach here.

## Safety & repo constraints
- `doc_conv/settings.py` contains a hard-coded SECRET_KEY and `DEBUG = True`. Do not commit production secrets—use env-based changes only if you also update docs here.
- No CI is present. If adding checks, document how to run them locally in this file.

## Where to look next (when stuck)
- Reproduce conversions by creating a `ConversionTask` via `api_upload` or `convert_markdown` then inspect `uploads/` and `exports/` directories.
- Check `md2docx/signals.py` for pandoc command and error messages (the signal writes `error_message` on failure).

If any part of this condensed guide is unclear or you want a longer, example-rich version (templates, test snippets, or CI commands), tell me which section to expand and I will iterate.
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
