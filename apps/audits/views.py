from rest_framework import viewsets
from apps.core.mixins import TenantQuerySetMixin
from .models import AuditLog
from .serializers import AuditLogSerializer

class AuditLogViewSet(TenantQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        case_id = self.request.query_params.get('case_id')
        if case_id:
            queryset = queryset.filter(case_id=case_id)
        return queryset