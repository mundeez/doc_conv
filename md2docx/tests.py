"""Unit tests for md2docx format-aware conversion."""

from pathlib import Path
from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse
from django.db.models.signals import post_save

from .models import ConversionTask
from .signals import process_conversion_on_create


class BaseTestCase(TestCase):
	"""Common setup: disable signal threads and provide client."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		post_save.disconnect(process_conversion_on_create, sender=ConversionTask)

	def setUp(self):
		self.client = Client()


class ApiUploadFormatTest(BaseTestCase):
	def test_accepts_valid_output_format(self):
		response = self.client.post(
			reverse('md2docx:api_upload'),
			{'markdown': '# Test', 'output_format': 'pdf'},
			format='multipart'
		)
		self.assertEqual(response.status_code, 201)
		task_id = response.json()['task_id']
		task = ConversionTask.objects.get(pk=task_id)
		self.assertEqual(task.output_format, 'pdf')

	def test_rejects_invalid_output_format(self):
		response = self.client.post(
			reverse('md2docx:api_upload'),
			{'markdown': '# Test', 'output_format': 'exe'},
			format='multipart'
		)
		self.assertEqual(response.status_code, 400)
		self.assertIn('unsupported', response.json()['error'].lower())


class ConvertViewFormatTest(BaseTestCase):
	def test_sets_output_format_and_stores_task(self):
		response = self.client.post(
			reverse('md2docx:convert'),
			{'markdown': '# Hello', 'output_format': 'html'},
			format='multipart'
		)
		self.assertEqual(response.status_code, 202)
		task = ConversionTask.objects.latest('created_at')
		self.assertEqual(task.output_format, 'html')

	def test_blocks_unsupported_output(self):
		response = self.client.post(
			reverse('md2docx:convert'),
			{'markdown': '# Hello', 'output_format': 'xyz'},
			format='multipart'
		)
		self.assertEqual(response.status_code, 400)


class StatusAndDownloadTest(BaseTestCase):
	def setUp(self):
		super().setUp()
		self.task = ConversionTask.objects.create(status=ConversionTask.STATUS_PENDING, output_format='pdf')

	def test_status_includes_output_format(self):
		response = self.client.get(reverse('md2docx:status', args=[self.task.id]))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['output_format'], 'pdf')

	def test_download_prefers_output_extension(self):
		media_root = Path(getattr(settings, 'MEDIA_ROOT', settings.BASE_DIR))
		exports = media_root / 'exports'
		exports.mkdir(parents=True, exist_ok=True)
		output_path = exports / f"{self.task.id}.pdf"
		output_path.write_bytes(b"dummy")
		self.task.result_file.name = output_path.relative_to(media_root).as_posix()
		self.task.status = ConversionTask.STATUS_DONE
		self.task.save()

		response = self.client.get(reverse('md2docx:download', args=[self.task.id]))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response['Content-Disposition'].split('filename=')[1].strip('"'), f"{self.task.id}.pdf")
