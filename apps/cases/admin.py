from django.contrib import admin
from .models import Case

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'organization', 'department', 'assigned_to', 'created_at')
    list_filter = ('status', 'organization', 'department')
    search_fields = ('title', 'description')