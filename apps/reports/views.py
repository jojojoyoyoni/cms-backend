from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.core.mixins import TenantQuerySetMixin
from apps.cases.models import Case
from apps.notifications.services import send_notification_to_user
from apps.users.models import User


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

class SendReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        message = request.data.get('message', '')
        
        if not message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find Team Leaders in the user's department
        if user.department:
            leaders = User.objects.filter(department_id=user.department_id, role='TEAM_LEADER')
            if leaders.exists():
                for leader in leaders:
                    send_notification_to_user(
                        user_id=leader.id,
                        message=f"Report submitted by {user.username}: {message}",
                    )
                return Response({'status': 'Report sent to your Team Leader successfully!'})
            else:
                return Response({'error': 'No Team Leader found in your department'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({'error': 'You are not assigned to a department'}, status=status.HTTP_400_BAD_REQUEST)