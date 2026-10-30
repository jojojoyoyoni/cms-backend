from rest_framework import viewsets
from apps.core.mixins import TenantQuerySetMixin
from .models import AuditLog
from .serializers import AuditLogSerializer

class AuditLogViewSet(TenantQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all()

    def get_queryset(self):
        user = self.request.user
        
        # Super Admins see all platform logs
        if user.role == 'SUPERADMIN':
            queryset = AuditLog.objects.all()
        else:
            # Org Admins see only their organization's logs
            queryset = AuditLog.objects.filter(organization_id=user.organization_id)
        
        # Filter by case_id if provided
        case_id = self.request.query_params.get('case_id')
        if case_id:
            queryset = queryset.filter(case_id=case_id)
            
        return queryset