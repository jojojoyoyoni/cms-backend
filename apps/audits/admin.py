from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('case', 'user', 'action', 'timestamp')
    list_filter = ('action', 'organization')