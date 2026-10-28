# core/mixins.py
from rest_framework.permissions import IsAuthenticated

class TenantQuerySetMixin:
    """
    Automatically filters querysets based on the user's role and organization.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated:
            return queryset.none()

        if user.role == 'SUPERADMIN':
            return queryset # Super Admin sees everything
            
        # For all other roles, restrict to their organization
        if hasattr(queryset.model, 'organization'):
            queryset = queryset.filter(organization_id=user.organization_id)
            
        return queryset