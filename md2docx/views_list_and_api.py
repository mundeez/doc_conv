"""Additional views: listing conversions and helper functions.

This file keeps the list view separate to keep the primary view file focused
on enqueueing and API endpoints. We'll import the view into urls.py via
placing function in main views module for simplicity; however creating a
separate file reduces merge conflicts in large changes.
"""
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import ConversionTask


def list_conversions(request):
    per_page = int(request.GET.get('per_page', 10))
    if per_page not in (10, 25, 50):
        per_page = 10
    page = int(request.GET.get('page', 1))

    qs = ConversionTask.objects.filter(status=ConversionTask.STATUS_DONE).order_by('-updated_at')
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)

    return render(request, 'md2docx/list.html', {'page_obj': page_obj, 'per_page': per_page})
