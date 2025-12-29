import time
import subprocess
import os
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

from md2docx.models import ConversionTask
from md2docx.formats import input_reader_for, DEFAULT_OUTPUT
import re


MEDIA_ROOT = Path(getattr(settings, 'MEDIA_ROOT', settings.BASE_DIR))
EXPORTS_DIR = MEDIA_ROOT / 'exports'
UPLOADS_DIR = MEDIA_ROOT / 'uploads'
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _safe_output_name(task):
    ext = (task.output_format or DEFAULT_OUTPUT).lstrip('.')
    if task.original_filename:
        stem = Path(task.original_filename).name
        stem = Path(stem).stem
        stem = stem.strip()
        stem = re.sub(r"[^A-Za-z0-9_-]+", '_', stem)
        if stem:
            return f"{stem}.{ext}"
    return f"{task.id}.{ext}"


def _find_input_file(task):
    matches = list(UPLOADS_DIR.glob(f"{task.id}.*"))
    if matches:
        return matches[0]
    return UPLOADS_DIR / f"{task.id}.md"


class Command(BaseCommand):
    help = 'Process pending md2docx ConversionTask entries and run pandoc to produce .docx files.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Process pending tasks once and exit')
        parser.add_argument('--poll', type=int, default=5, help='Poll interval in seconds when running continuously')

    def handle(self, *args, **options):
        once = options.get('once')
        poll = options.get('poll', 5)

        self.stdout.write(self.style.NOTICE('Starting task processor (pandoc worker)'))

        while True:
            pending = ConversionTask.objects.filter(status=ConversionTask.STATUS_PENDING).order_by('created_at')
            if not pending.exists():
                if once:
                    self.stdout.write('No pending tasks, exiting')
                    return
                time.sleep(poll)
                continue

            for task in pending:
                try:
                    self.stdout.write(f'Processing task {task.id}...')
                    task.status = ConversionTask.STATUS_PROCESSING
                    task.progress = 5
                    task.save()

                    input_path = _find_input_file(task)
                    input_ext = input_path.suffix.lstrip('.').lower()
                    reader = input_reader_for(input_ext)
                    output_filename = _safe_output_name(task)
                    output_path = EXPORTS_DIR / output_filename

                    # mark progress
                    task.progress = 20
                    task.save()

                    output_fmt = (task.output_format or DEFAULT_OUTPUT).lstrip('.').lower()

                    def _pandoc_command(inp, outp, reader_name, fmt):
                        cmd = [
                            'pandoc',
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
                    proc = subprocess.run(cmd, capture_output=True, text=True)

                    if proc.returncode == 0 and output_path.exists():
                        # attach file path to model (relative to MEDIA_ROOT)
                        rel = os.path.relpath(output_path, MEDIA_ROOT)
                        task.result_file.name = rel
                        task.status = ConversionTask.STATUS_DONE
                        task.progress = 100
                        task.error_message = ''
                        task.save()
                        self.stdout.write(self.style.SUCCESS(f'Task {task.id} finished'))
                    else:
                        task.status = ConversionTask.STATUS_FAILED
                        task.progress = 0
                        task.error_message = proc.stderr or proc.stdout or 'pandoc failed'
                        task.save()
                        self.stdout.write(self.style.ERROR(f'Task {task.id} failed: {task.error_message}'))

                except Exception as exc:
                    task.status = ConversionTask.STATUS_FAILED
                    task.error_message = str(exc)
                    task.progress = 0
                    task.save()
                    self.stdout.write(self.style.ERROR(f'Unexpected error processing {task.id}: {exc}'))

            if once:
                return
            time.sleep(poll)
