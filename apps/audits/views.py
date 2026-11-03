from rest_framework import viewsets
from apps.core.mixins import TenantQuerySetMixin
from .models import AuditLog
from .serializers import AuditLogSerializer

class AuditLogViewSet(TenantQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all()
    ordering = ['-timestamp'] 
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.role == 'SUPERADMIN':
            queryset = AuditLog.objects.all()
        else:
            queryset = AuditLog.objects.filter(organization_id=user.organization_id)
        
        case_id = self.request.query_params.get('case_id')
        if case_id:
            queryset = queryset.filter(case_id=case_id)
            
        return queryset