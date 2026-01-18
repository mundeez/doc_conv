import logging
import subprocess

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class Md2DocxConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'md2docx'

    def ready(self):
        """Import signals when the app is ready."""
        from . import signals  # noqa: F401

        # Best-effort pandoc/pdf availability check (non-fatal)
        self._check_pandoc_capabilities()

    def _check_pandoc_capabilities(self):
        """Log warnings if pandoc or pdf engine is unavailable."""
        from .formats import REQUIRED_OUTPUTS, REQUIRED_INPUTS
        import os

        pandoc_bin = os.getenv('PANDOC_BIN', 'pandoc')

        try:
            out = subprocess.run(
                [pandoc_bin, '--list-output-formats'],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            outputs = set(out.stdout.split())
            missing = [fmt for fmt in REQUIRED_OUTPUTS if fmt not in outputs]
            if missing:
                logger.warning("pandoc missing output formats: %s", ', '.join(missing))
            if 'pdf' not in outputs:
                logger.warning("pandoc PDF engine not available; install LaTeX (texlive) to enable PDF output")
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("pandoc output formats check failed: %s", exc)

        try:
            out = subprocess.run(
                [pandoc_bin, '--list-input-formats'],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            inputs = set(out.stdout.split())
            missing_in = [fmt for fmt in REQUIRED_INPUTS if fmt not in inputs]
            if missing_in:
                logger.warning("pandoc missing input readers: %s", ', '.join(missing_in))
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("pandoc input formats check failed: %s", exc)
