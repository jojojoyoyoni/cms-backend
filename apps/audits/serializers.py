from rest_framework import serializers
from .models import AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField() # Returns the username
    
    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'action', 'changes', 'timestamp']