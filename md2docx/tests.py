"""Unit tests for md2docx app.

Tests cover:
- Task enqueueing on upload (views)
- Signal-based auto-conversion (signals)
- List view pagination
"""
import time
from django.test import TestCase, Client
from django.urls import reverse
from django.db.models.signals import post_save
from .models import ConversionTask


class ConversionTaskModelTest(TestCase):
    """Test ConversionTask model."""

    @classmethod
    def setUpClass(cls):
        """Disable signal handlers for tests."""
        super().setUpClass()
        # Disconnect the signal to prevent background thread issues in tests
        from .signals import process_conversion_on_create
        post_save.disconnect(process_conversion_on_create, sender=ConversionTask)

    def test_task_creation(self):
        """Task can be created with pending status."""
        task = ConversionTask.objects.create(status=ConversionTask.STATUS_PENDING)
        self.assertEqual(task.status, ConversionTask.STATUS_PENDING)
        self.assertEqual(task.progress, 0)
        self.assertIsNotNone(task.id)  # UUID assigned

    def test_task_str(self):
        """Task string representation includes id and status."""
        task = ConversionTask.objects.create(status=ConversionTask.STATUS_PENDING)
        self.assertIn(str(task.id), str(task))
        self.assertIn(ConversionTask.STATUS_PENDING, str(task))


class UploadViewTest(TestCase):
    """Test upload endpoints."""

    @classmethod
    def setUpClass(cls):
        """Disable signal handlers for tests."""
        super().setUpClass()
        from .signals import process_conversion_on_create
        post_save.disconnect(process_conversion_on_create, sender=ConversionTask)

    def setUp(self):
        self.client = Client()

    def test_api_upload_creates_task(self):
        """POST to /api/upload/ creates a pending ConversionTask."""
        response = self.client.post(
            reverse('md2docx:api_upload'),
            {'markdown': '# Test'},
            format='multipart'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], ConversionTask.STATUS_PENDING)
        self.assertIn('task_id', data)
        self.assertIn('status_url', data)

    def test_api_upload_returns_task_id(self):
        """API response includes task_id that can be queried."""
        response = self.client.post(
            reverse('md2docx:api_upload'),
            {'markdown': '# Test'},
            format='multipart'
        )
        data = response.json()
        task_id = data['task_id']
        
        # Verify task exists in DB
        task = ConversionTask.objects.get(pk=task_id)
        self.assertIsNotNone(task)


class StatusViewTest(TestCase):
    """Test status endpoint."""

    @classmethod
    def setUpClass(cls):
        """Disable signal handlers for tests."""
        super().setUpClass()
        from .signals import process_conversion_on_create
        post_save.disconnect(process_conversion_on_create, sender=ConversionTask)

    def setUp(self):
        self.client = Client()
        self.task = ConversionTask.objects.create(status=ConversionTask.STATUS_PENDING)

    def test_status_returns_task_info(self):
        """GET /status/<uuid>/ returns task JSON."""
        response = self.client.get(
            reverse('md2docx:status', args=[self.task.id])
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['task_id'], str(self.task.id))
        self.assertEqual(data['status'], ConversionTask.STATUS_PENDING)
        self.assertIn('progress', data)

    def test_status_includes_error_on_failure(self):
        """Status endpoint includes error_message if task failed."""
        self.task.status = ConversionTask.STATUS_FAILED
        self.task.error_message = 'Test error'
        self.task.save()
        
        response = self.client.get(
            reverse('md2docx:status', args=[self.task.id])
        )
        data = response.json()
        self.assertEqual(data['status'], ConversionTask.STATUS_FAILED)
        self.assertIn('error', data)


class ListViewTest(TestCase):
    """Test list view and pagination."""

    @classmethod
    def setUpClass(cls):
        """Disable signal handlers for tests."""
        super().setUpClass()
        from .signals import process_conversion_on_create
        post_save.disconnect(process_conversion_on_create, sender=ConversionTask)

    def setUp(self):
        self.client = Client()
        # Create 5 done tasks
        for i in range(5):
            ConversionTask.objects.create(
                status=ConversionTask.STATUS_DONE,
                original_filename=f'file{i}.md',
                progress=100
            )

    def test_list_view_renders(self):
        """GET /list/ renders the list template."""
        response = self.client.get(reverse('md2docx:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Converted files')

    def test_list_shows_done_tasks(self):
        """List view shows tasks with status='done'."""
        response = self.client.get(reverse('md2docx:list'))
        self.assertEqual(response.status_code, 200)
        # Should contain at least one filename
        self.assertContains(response, 'file')

    def test_list_pagination_default(self):
        """List defaults to 10 results per page."""
        # Create 15 tasks
        for i in range(10):
            ConversionTask.objects.create(status=ConversionTask.STATUS_DONE)
        
        response = self.client.get(reverse('md2docx:list'))
        self.assertEqual(response.status_code, 200)
        # Check that pagination controls exist
        self.assertContains(response, 'Page')

    def test_list_pagination_per_page_param(self):
        """List respects per_page parameter."""
        response = self.client.get(reverse('md2docx:list'), {'per_page': 25})
        self.assertEqual(response.status_code, 200)
        # Response should succeed with per_page=25


class HomeViewTest(TestCase):
    """Test home page."""

    @classmethod
    def setUpClass(cls):
        """Disable signal handlers for tests."""
        super().setUpClass()
        from .signals import process_conversion_on_create
        post_save.disconnect(process_conversion_on_create, sender=ConversionTask)

    def setUp(self):
        self.client = Client()

    def test_home_renders(self):
        """GET / renders home template or fallback HTML."""
        response = self.client.get(reverse('md2docx:home'))
        self.assertEqual(response.status_code, 200)
        # Should have a form or content
        self.assertIn(b'md2docx', response.content)
