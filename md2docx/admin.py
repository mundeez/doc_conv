from django.contrib import admin

from .models import ConversionTask


@admin.register(ConversionTask)
class ConversionTaskAdmin(admin.ModelAdmin):
	list_display = ("id", "status", "progress", "output_format", "created_at")
	readonly_fields = ("id", "created_at", "updated_at", "result_file", "error_message")
