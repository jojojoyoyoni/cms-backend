from django.utils import timezone

from rest_framework import serializers
from .models import Case, CaseNote, CaseDocument, Task

class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = '__all__'
        read_only_fields = ['organization', 'created_by', 'created_at', 'updated_at', 'case_number', 'is_deleted']  # Make case_number read-only since it's auto-generated

class CaseDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = CaseDocument
        fields = ['id', 'case', 'uploaded_by', 'file', 'file_url', 'created_at']
        read_only_fields = ['uploaded_by', 'created_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return None

class CaseNoteSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()

    class Meta:
        model = CaseNote
        fields = ['id', 'case', 'author', 'content', 'is_internal', 'created_at']
        read_only_fields = ['author', 'created_at']


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    case_number = serializers.SerializerMethodField()
    case_title = serializers.SerializerMethodField()
    due_status = serializers.SerializerMethodField()


    class Meta:
        model = Task
        fields = ['id', 'case', 'case_number', 'case_title', 'title', 'description', 'status', 'priority', 'assigned_to', 'assigned_to_name', 'created_by', 'created_by_name', 'due_date', 'completed_at', 'created_at', 'updated_at', 'due_status']
        read_only_fields = ['created_by', 'completed_at', 'created_at', 'updated_at', 'assigned_to_name', 'created_by_name', 'case_number', 'case_title', 'due_status']

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.username if obj.assigned_to else None

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else None

    def get_case_number(self, obj):
        return obj.case.case_number if obj.case else None

    def get_case_title(self, obj):
        return obj.case.title if obj.case else None

    def get_due_status(self, obj):
        """Calculate due status on the backend"""
        if not obj.due_date or obj.status == 'DONE':
            return None
        now = timezone.now()
        diff_hours = (obj.due_date - now).total_seconds() / 3600
        if diff_hours < 0:
            return 'OVERDUE'
        if diff_hours <= 24:
            return 'DUE_SOON'
        return None