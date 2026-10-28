from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.core.mixins import TenantQuerySetMixin
from .models import User, Organization, Department
from .serializers import UserSerializer, CreateUserSerializer, OrganizationSerializer, DepartmentSerializer
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class UserViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # SUPERADMINS see all users in the entire system
        if user.role == 'SUPERADMIN':
            pass
        # ORG_ADMINS see all users in their organization
        elif user.role == 'ORG_ADMIN':
            pass
        # TEAM_LEADERS see users in their department
        elif user.role == 'TEAM_LEADER':
            queryset = queryset.filter(department_id=user.department_id)
        # ANALYSTS only see themselves
        else:
            queryset = queryset.filter(id=user.id)
            
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateUserSerializer
        return UserSerializer

    def perform_create(self, serializer):
        # Force the new user to be in the same org as the creator
        serializer.save(organization=self.request.user.organization)