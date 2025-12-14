"""Signal handlers for md2docx app.

Automatically process ConversionTask entries when created using Django signals.
This keeps the view non-blocking while still handling conversion in the background.
"""
import threading
import time
import subprocess
import os
from pathlib import Path

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import ConversionTask


MEDIA_ROOT = Path(getattr(settings, 'MEDIA_ROOT', settings.BASE_DIR))
EXPORTS_DIR = MEDIA_ROOT / 'exports'
UPLOADS_DIR = MEDIA_ROOT / 'uploads'
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


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

        md_path = UPLOADS_DIR / f'{task.id}.md'
        output_path = EXPORTS_DIR / f'{task.id}.docx'

        # Update progress
        task.progress = 40
        task.save()

        # Run pandoc
        cmd = f"pandoc -o {output_path} -f markdown -t docx {md_path}"
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

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
    if 'test' in settings.DATABASES.get('default', {}).get('NAME', ''):
        return
    
    if created and instance.status == ConversionTask.STATUS_PENDING:
        # Start conversion in a background thread so HTTP response returns quickly
        thread = threading.Thread(target=_process_task, args=(instance.id,), daemon=True)
        thread.start()
