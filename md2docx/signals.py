"""Signal handlers for md2docx app.

Automatically process ConversionTask entries when created using Django signals.
This keeps the view non-blocking while still handling conversion in the background.
"""
import threading
import subprocess
import os
from pathlib import Path

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import ConversionTask
from .formats import input_reader_for, DEFAULT_OUTPUT
import re


MEDIA_ROOT = Path(getattr(settings, 'MEDIA_ROOT', settings.BASE_DIR))
EXPORTS_DIR = MEDIA_ROOT / 'exports'
UPLOADS_DIR = MEDIA_ROOT / 'uploads'
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Allow overriding pandoc binary/command (e.g., dockerized pandoc wrapper)
PANDOC_BIN = os.getenv('PANDOC_BIN', 'pandoc')


def _safe_output_name(task):
    """Determine output filename based on original filename and desired format."""
    ext = (task.output_format or DEFAULT_OUTPUT).lstrip('.')
    if task.original_filename:
        stem = Path(task.original_filename).name  # strip any path components
        stem = Path(stem).stem  # drop extension
        stem = stem.strip()
        # sanitize: allow letters, numbers, underscore and hyphen
        stem = re.sub(r"[^A-Za-z0-9_-]+", '_', stem)
        if stem:
            return f"{stem}.{ext}"
    return f"{task.id}.{ext}"


def _find_input_file(task):
    """Locate the uploaded input file for a task, regardless of extension."""
    matches = list(UPLOADS_DIR.glob(f"{task.id}.*"))
    if matches:
        # Prefer exact name match (uuid.ext) — only one is expected
        return matches[0]
    # fallback to legacy .md path
    return UPLOADS_DIR / f"{task.id}.md"


def _process_task(task_id):
    """Background task processor: convert markdown to docx using pandoc.

    This function runs in a background thread so the HTTP response returns quickly.
    It updates the task record with progress and status.
    """
    try:
        task = ConversionTask.objects.get(pk=task_id)
    except ConversionTask.DoesNotExist:
        return

    try:
        task.status = ConversionTask.STATUS_PROCESSING
        task.progress = 20
        task.save()

        input_path = _find_input_file(task)
        input_ext = input_path.suffix.lstrip('.').lower()
        reader = input_reader_for(input_ext)
        output_filename = _safe_output_name(task)
        output_path = EXPORTS_DIR / output_filename

        # Update progress
        task.progress = 40
        task.save()

        # Run pandoc with Unicode-friendly PDF engine
        output_fmt = (task.output_format or DEFAULT_OUTPUT).lstrip('.').lower()

        def _pandoc_command(inp, outp, reader_name, fmt):
            cmd = [
                PANDOC_BIN,
                '-o', str(outp),
                '-f', reader_name,
                '-t', fmt,
                str(inp),
            ]
            if fmt == 'pdf':
                cmd.extend([
                    '--pdf-engine=xelatex',
                    '-V', 'mainfont=DejaVu Sans',
                    '-V', 'sansfont=DejaVu Sans',
                    '-V', 'monofont=DejaVu Sans Mono',
                ])
            return cmd

        cmd = _pandoc_command(input_path, output_path, reader, output_fmt)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if proc.returncode == 0 and output_path.exists():
            # Success: mark as done and attach file
            rel = os.path.relpath(output_path, MEDIA_ROOT)
            task.result_file.name = rel
            task.status = ConversionTask.STATUS_DONE
            task.progress = 100
            task.error_message = ''
            task.save()
        else:
            # Failure: record error message
            task.status = ConversionTask.STATUS_FAILED
            task.progress = 0
            task.error_message = proc.stderr or proc.stdout or 'pandoc failed with no output'
            task.save()

    except Exception as exc:
        task.status = ConversionTask.STATUS_FAILED
        task.error_message = str(exc)
        task.progress = 0
        task.save()


@receiver(post_save, sender=ConversionTask)
def process_conversion_on_create(sender, instance, created, **kwargs):
    """Process a ConversionTask in a background thread when it's first created.

    This handler fires when ConversionTask.objects.create() is called.
    Only process if the task is in PENDING status (not an update).
    
    Note: Skips processing during tests to avoid SQLite locking issues.
    """
    from django.conf import settings

    # Skip signal processing in test environment
    db_name = settings.DATABASES.get('default', {}).get('NAME', '')
    if isinstance(db_name, (Path, str)) and 'test' in str(db_name):
        return
    
    if created and instance.status == ConversionTask.STATUS_PENDING:
        # Start conversion in a background thread so HTTP response returns quickly
        thread = threading.Thread(target=_process_task, args=(instance.id,), daemon=True)
        thread.start()
