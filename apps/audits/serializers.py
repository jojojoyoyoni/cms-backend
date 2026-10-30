from rest_framework import serializers
from .models import AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    case_number = serializers.SerializerMethodField()
    case_title = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'action', 'changes', 'timestamp', 'case_number', 'case_title']

    def get_case_number(self, obj):
        return obj.case.case_number if obj.case else None

    def get_case_title(self, obj):
        return obj.case.title if obj.case else None