<!-- Instructions for AI coding agents working in this repository -->
# Copilot instructions for doc_conv

This file gives focused, actionable guidance for AI coding agents working on this Django project. Keep instructions short and concrete — only document patterns discoverable in the codebase.

## Big picture
- This is a small Django project named `doc_conv` with a single app `md2docx`.
- URL routing: `doc_conv/urls.py` includes `md2docx.urls` at the `md2docx/` path. Most feature work will live in `md2docx/views.py` and its URL patterns in `md2docx/urls.py`.
- The app exposes UI and API endpoints for converting Markdown to DOCX and for retrieving conversion status/results.

## Key files to inspect
- `doc_conv/settings.py` — project settings (Django 4.2, default sqlite DB).
- `doc_conv/urls.py` — includes `md2docx.urls`.
- `md2docx/urls.py` — defines routes the app expects (home, convert, status/<uuid:task_id>/, download/<uuid:task_id>/, api/upload/).
- `md2docx/views.py` — implement view functions referenced by `md2docx/urls.py` (currently empty).
- `md2docx/models.py`, `md2docx/tests.py` — currently minimal/empty; add models/tests close to the implementation.

## Project-specific patterns and conventions
- Use app URL namespace: `app_name = "md2docx"` in `md2docx/urls.py`. When building links or reversing, use the namespace, e.g. `reverse('md2docx:download', args=[task_id])`.
- Task identifiers are UUIDs: the `status` and `download` routes expect `<uuid:task_id>` — so any task IDs returned by background workers or APIs should be UUID objects/strings.
- The comments in `md2docx/urls.py` indicate async/background processing is expected: use a task queue (Celery, RQ) or native async views if implementing long-running conversions. This repo currently has no external worker configuration — document any added integration.
- Database: default sqlite configured in `doc_conv/settings.py`. Do not assume other DBs unless a requirements or settings file is added.

## How to run, test and debug (discoverable commands)
- Run migrations & dev server:
  - `python manage.py migrate`
  - `python manage.py runserver`
- Run tests: `python manage.py test`
- Use `manage.py` to inspect or run ad-hoc commands. There is no `requirements.txt` in the repo; if you need dependencies, add a `requirements.txt` and document pinned versions.

## Implementation hints with concrete examples
- When adding the `status` endpoint, return a JSON object with at least `status` and `task_id`. Example shape (JSON): `{"status": "pending", "task_id": "<uuid>"}`.
- For the `download` endpoint, return a streaming/file response that uses the `task_id` to look up the stored `.docx` file (store files under `MEDIA_ROOT` or a dedicated `exports/` directory). Reverse the URL using the app namespace: `reverse('md2docx:download', args=[task_id])`.
- Because `md2docx/urls.py` expects views named `home`, `convert_markdown`, `status`, `download_docx`, and `api_upload`, implement or stub those exact names to avoid breaking imports.

## Safety and repository constraints
- `doc_conv/settings.py` contains a hard-coded SECRET_KEY and `DEBUG = True` — do not change production secrets in PRs; instead, add .env-based config if needed and document it.
- No CI config or third-party integrations are present in the repository; if adding them, update this file with how to run relevant checks locally.

## Useful next steps for a contributor or agent
1. Implement view stubs in `md2docx/views.py` matching the routes in `md2docx/urls.py` to make the app importable and the dev server runnable.
2. Add a minimal `requirements.txt` with `Django==4.2.11` if you will install dependencies.
3. Add tests in `md2docx/tests.py` that assert the URL endpoints resolve and return expected status codes.

## If something is missing
- If you need clarification about background task handling or storage for generated files, ask the maintainers before adding external services (S3, Celery). There are no discoverable configs in this repo for those services.

---
Please review and tell me which parts you want expanded (examples of view implementations, test templates, or CI commands) and I will update this file accordingly.
