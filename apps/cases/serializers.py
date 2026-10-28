from rest_framework import serializers
from .models import Case

class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = '__all__'
        read_only_fields = ['organization', 'created_by', 'created_at', 'updated_at', 'case_number', 'is_deleted']  # Make case_number read-only since it's auto-generated