from django.db import models
import uuid


class ConversionTask(models.Model):
	"""Represents a Markdown -> DOCX conversion task.

	This minimal model is discoverable from the routes in `md2docx/urls.py`:
	status and task_id (UUID) are required by the status/download endpoints.
	"""

	STATUS_PENDING = 'pending'
	STATUS_PROCESSING = 'processing'
	STATUS_DONE = 'done'
	STATUS_FAILED = 'failed'

	STATUS_CHOICES = [
		(STATUS_PENDING, 'Pending'),
		(STATUS_PROCESSING, 'Processing'),
		(STATUS_DONE, 'Done'),
		(STATUS_FAILED, 'Failed'),
	]

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	input_markdown = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	result_file = models.FileField(upload_to='exports/', null=True, blank=True)
	error_message = models.TextField(blank=True)
	original_filename = models.CharField(max_length=255, blank=True)
	progress = models.IntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self) -> str:  # pragma: no cover - trivial
		return f"ConversionTask({self.id}) {self.status}"
