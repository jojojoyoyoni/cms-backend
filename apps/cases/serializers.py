from rest_framework import serializers
from .models import Case, CaseNote, CaseDocument

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