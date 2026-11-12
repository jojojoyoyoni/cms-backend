from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied


from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.mixins import TenantQuerySetMixin
from apps.users.permissions import ROLE_PERMISSIONS
from .models import User, Organization, Department
from .serializers import ChangePasswordSerializer, UserSerializer, CreateUserSerializer, OrganizationSerializer, DepartmentSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        data = serializer.data
        data['permissions'] = ROLE_PERMISSIONS.get(request.user.role, [])
        return Response(data)

    def patch(self, request):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            data = serializer.data
            data['permissions'] = ROLE_PERMISSIONS.get(user.role, [])
            return Response(data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({'error': 'Incorrect old password.'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'status': 'password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # SUPERADMINS see all users in the entire system
        if user.role == 'SUPERADMIN':
            pass
        # ORG_ADMINS see all users in their organization
        elif user.role == 'ORG_ADMIN':
            pass # TenantQuerySetMixin already filters by organization_id
        # HIGHER_OFFICIALS see users in their organization
        elif user.role in ['ORG_ADMIN', 'HIGHER_OFFICIAL']:  # Add HIGHER_OFFICIAL!
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

class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        if self.request.user.role == 'SUPERADMIN':
            return Organization.objects.all()
        return Organization.objects.none()

    def perform_create(self, serializer):
        manager_id = serializer.validated_data.pop('manager_id', None)
        org = serializer.save()
        if manager_id:
            manager = User.objects.get(id=manager_id)
            manager.organization = org
            manager.role = 'ORG_ADMIN'
            manager.save()

    def perform_update(self, serializer):
        manager_id = serializer.validated_data.pop('manager_id', None)
        org = serializer.save()
        if manager_id:
            manager = User.objects.get(id=manager_id)
            manager.organization = org
            manager.role = 'ORG_ADMIN'
            manager.save()


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    queryset = Department.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.role == 'SUPERADMIN':
            return Department.objects.all()
        return Department.objects.filter(organization_id=user.organization_id)

    def check_manager_permission(self):
        """Only Org Admins can create/edit/assign/remove"""
        if self.request.user.role != 'ORG_ADMIN':
            raise PermissionDenied('Only Organization Admins can manage departments.')

    def perform_create(self, serializer):
        self.check_manager_permission()
        serializer.save(organization=self.request.user.organization)

    def perform_update(self, serializer):
        self.check_manager_permission()
        serializer.save()

    @action(detail=True, methods=['post'])
    def assign_member(self, request, pk=None):
        self.check_manager_permission()
        dept = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
            user.department = dept
            user.save()
            return Response({'status': f'{user.username} assigned to {dept.name}'})
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        self.check_manager_permission()
        dept = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
            user.department = None
            user.save()
            return Response({'status': f'{user.username} removed from {dept.name}'})
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)