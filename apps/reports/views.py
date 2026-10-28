from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.core.mixins import TenantQuerySetMixin
from apps.cases.models import Case

class DashboardStatsView(TenantQuerySetMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Case.objects.all()

    def get(self, request):
        queryset = self.get_queryset()
        user = request.user

        if user.role == 'SUPERADMIN':
            pass
        elif user.role == 'ORG_ADMIN':
            pass
        elif user.role == 'TEAM_LEADER':
            queryset = queryset.filter(department_id=user.department_id)
        elif user.role == 'ANALYST':
            queryset = queryset.filter(assigned_to_id=user.id)

        stats = {
            'total_cases': queryset.count(),
            'open_cases': queryset.filter(status='OPEN').count(),
            'in_progress_cases': queryset.filter(status='IN_PROGRESS').count(),
            'closed_cases': queryset.filter(status='CLOSED').count(),
        }
        return Response(stats)