from rest_framework import viewsets
from apps.core.mixins import TenantQuerySetMixin
from .models import Case
from .serializers import CaseSerializer

class CaseViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = CaseSerializer

    def get_queryset(self):
        # Start with the TenantQuerySetMixin logic (filters by Org, unless SuperAdmin)
        # queryset = super().get_queryset()
        queryset = Case.objects.all()  # <--- ADD THIS LINE HERE

        user = self.request.user

        # Apply Hierarchical Role logic
        if user.role == 'TEAM_LEADER':
            queryset = queryset.filter(department_id=user.department_id)
        elif user.role == 'ANALYST':
            queryset = queryset.filter(assigned_to_id=user.id)
            
        return queryset

    def perform_create(self, serializer):
        # Automatically attach org and creator
        user = self.request.user
        serializer.save(organization=user.organization, created_by=user)