# doc_conv — Django Markdown-to-DOCX Converter

A lightweight Django web application that converts Markdown files to Microsoft Word (.docx) format. Features a REST API, background task processing, real-time progress tracking, and a paginated results dashboard.

## Features

- **Web UI**: Upload markdown files via form or paste text
- **REST API**: Programmatic access via `/api/upload/` endpoint (CSRF-exempt)
- **Background Processing**: Asynchronous conversion using Django signals + threading
- **Progress Tracking**: Real-time progress bar (0-100%) via polling
- **File Management**: Automatic storage in `MEDIA_ROOT` with download links
- **Results List**: Paginated dashboard showing all converted files (10/25/50 per page)
- **Error Handling**: Graceful failure tracking and error messages in task records

## Quick Start

### Prerequisites

- Python 3.x (tested on 3.9+)
- Django 4.2.11
- Pandoc (for markdown→DOCX conversion)

### Install Pandoc

**Ubuntu/Debian:**
```bash
sudo apt install pandoc
```

**macOS:**
```bash
brew install pandoc
```

**Windows:**
Download from [pandoc.org](https://pandoc.org/)

### Setup Django Project

```bash
# Install dependencies
pip install -r requirements.txt

# Create/apply database migrations
python manage.py makemigrations
python manage.py migrate

# Run development server
python manage.py runserver
```

Visit http://localhost:8000/md2docx/

### Docker / Compose

```bash
docker compose up --build
```

- Web: http://localhost:8000
- Volumes: `./uploads` and `./exports` are mounted for persistence.
- Default (compose): `PANDOC_BIN=./scripts/pandoc_docker.sh` to run pandoc inside `pandoc/core:3.1` via Docker. Requires host Docker socket mounted at `/var/run/docker.sock` (already mounted in compose).
- To use native pandoc instead, set `PANDOC_BIN=pandoc`.

## Usage

### Web Interface

1. **Home** (http://localhost:8000/md2docx/)
   - Paste markdown text or upload a `.md` file
   - Click "Convert" to enqueue task
   
2. **Status** (http://localhost:8000/md2docx/status/<uuid>/)
   - View real-time progress bar
   - Download `.docx` when complete
   
3. **List** (http://localhost:8000/md2docx/list/)
   - Browse all converted files
   - Select 10/25/50 results per page
   - Download files directly

### REST API

**Upload markdown:**
```bash
curl -X POST http://localhost:8000/md2docx/api/upload/ \
  -F "file=@example.md"
```

**Response (JSON):**
```json
{
  "status": "pending",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status_url": "/md2docx/status/550e8400-e29b-41d4-a716-446655440000/"
}
```

**Check status:**
```bash
curl http://localhost:8000/md2docx/api/status/550e8400-e29b-41d4-a716-446655440000/
```

## Architecture

### How It Works

1. **Task Enqueueing**: View receives upload → creates `ConversionTask` record (status: "pending") → returns task UUID
2. **Auto-Processing**: Django `post_save` signal fires → spawns daemon thread → runs pandoc conversion
3. **Progress Tracking**: Background thread updates task progress (20% → 40% → 100%) in database
4. **Result Storage**: Converted `.docx` saved to `MEDIA_ROOT/exports/<uuid>.docx`
5. **User Polling**: Frontend polls `/status/<uuid>/` endpoint for progress; downloads when complete

### Key Components

| File | Purpose |
|------|---------|
| `md2docx/models.py` | `ConversionTask` model with status/progress/error tracking |
| `md2docx/views.py` | HTTP endpoints (home, convert, status, download, API) |
| `md2docx/signals.py` | `post_save` handler spawning background conversion thread |
| `md2docx/urls.py` | URL routing (`/md2docx/`, `/api/upload/`, etc.) |
| `md2docx/views_list_and_api.py` | Paginated list view for completed conversions |
| `md2docx/management/commands/process_tasks.py` | Optional CLI worker (alternative to signal-based processing) |
| `md2docx/templates/` | HTML templates (base, home, status with progress bar, list) |
| `md2docx/tests.py` | Unit test suite (11 tests covering models, views, signals) |

## Testing

Run the complete test suite:

```bash
python manage.py test md2docx --verbosity=2
```

**Expected output:** 11 tests pass in ~0.2s

Tests cover:
- Task model creation and string representation
- API upload endpoint
- Status endpoint (pending/done/failed states)
- List view pagination (10/25/50 per page)
- Error message tracking
- Home page rendering

## Database

Default: **SQLite** (`db.sqlite3`)

### ConversionTask Model

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key (auto-generated) |
| `status` | Enum | "pending", "processing", "done", "failed" |
| `progress` | Integer | 0-100 (updated by background thread) |
| `original_filename` | String | Preserved for UI display |
| `result_file` | FileField | Path to `.docx` output (null if failed) |
| `error_message` | Text | Filled if status == "failed" |
| `created_at` | DateTime | Task creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

## File Storage

- **Uploads**: `MEDIA_ROOT/uploads/<uuid>.md`
- **Outputs**: `MEDIA_ROOT/exports/<uuid>.docx`
- **Fallback**: Project root directory (if `MEDIA_ROOT` not configured)

Configure in `doc_conv/settings.py`:
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

Serve uploads in development (`doc_conv/urls.py`):
```python
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## Configuration

### Environment Variables (optional)

Create `.env` file (not in repo):
```
SECRET_KEY=your-secret-key-here
DEBUG=False  # for production
ALLOWED_HOSTS=localhost,yourdomain.com
```

Load with `python-decouple`:
```bash
pip install python-decouple
```

Update `doc_conv/settings.py`:
```python
from decouple import config
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
```

### Alternative: Manual Task Processing

If you prefer not to use signals, disable them and manually process tasks:

```bash
# Process pending tasks once
python manage.py process_tasks --once

# Continuous worker (polls every 5s)
python manage.py process_tasks
```

(Signals are preferred for simplicity; process_tasks is useful for distributed setups.)

## Troubleshooting

**"pandoc not found" error**
- Ensure pandoc is installed and in `PATH`
- Test: `pandoc --version`

**Task stuck on "processing"**
- Check error_message field in admin or database
- Review `md2docx/signals.py` for exception handling
- Run `python manage.py process_tasks --once` manually to retry

**Files not downloading**
- Verify `MEDIA_ROOT` exists and is writable
- Check that `.docx` file exists at `MEDIA_ROOT/exports/<uuid>.docx`
- Ensure `result_file` field is populated in database

**Template not found errors**
- Confirm `md2docx` is in `INSTALLED_APPS` in `settings.py`
- Run `python manage.py collectstatic` (production)

## Deployment

### Production Checklist

1. **Settings**
   - Set `DEBUG = False`
   - Update `ALLOWED_HOSTS`
   - Use environment variables for `SECRET_KEY`
   - Use PostgreSQL instead of SQLite

2. **Concurrency**
   - Current: Single-threaded signal processing (good for small scale)
   - Consider: Celery + Redis for distributed task queue (production scale)

3. **Security**
   - API endpoint `/api/upload/` is CSRF-exempt (documented in code)
   - Review file upload size limits
   - Add rate limiting for API

4. **File Storage**
   - Use S3/cloud storage instead of local disk
   - Set up cleanup job for old files (Django-cleanup)

5. **Monitoring**
   - Log conversion errors to sentry/datadog
   - Monitor background thread exceptions
   - Track failed task rates

## Contributing
1. Create a new branch: `git checkout -b feature/my-feature`
2. Install deps and lint: `pip install -r requirements.txt && pip install ruff==0.14.13 && ruff check .`
3. Run tests: `python manage.py test md2docx`
4. Submit pull request

## License

[Your License Here]

## Support

See `.github/copilot-instructions.md` for AI agent implementation guidance.

---

**Latest Update**: All features complete, test suite passing (11/11), ready for deployment.
