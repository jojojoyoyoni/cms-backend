from rest_framework.decorators import action
from django.db.models import Q
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from rest_framework import viewsets
from apps.core.mixins import TenantQuerySetMixin
from rest_framework.permissions import IsAuthenticated

from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from apps.cases.filters import CaseFilter

from apps.users.permissions import HasRolePermission
from .models import Case, CaseNote, CaseDocument
from apps.users.models import User
from .serializers import CaseNoteSerializer, CaseSerializer, CaseDocumentSerializer
from apps.notifications.services import send_notification_to_user

class CaseViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]

        # Add Filtering, Search, and Sorting
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CaseFilter
    search_fields = ['title', 'case_number', 'description']
    ordering_fields = ['created_at', 'due_date', 'priority', 'title', 'case_number']
    ordering = ['-created_at'] # Default sort: newest first

    def get_queryset(self):
        user = self.request.user
        
        # SUPER ADMINS CANNOT SEE CASES AT ALL!
        if user.role == 'SUPERADMIN':
            return Case.objects.none()
            
        queryset = super().get_queryset()
        
        # Apply Hierarchical Role logic
        if user.role == 'ORG_ADMIN':
            pass # Sees all cases in org
        elif user.role == 'TEAM_LEADER':
            queryset = queryset.filter(department_id=user.department_id)
        elif user.role == 'ANALYST':
               # FIX: Analysts can see cases assigned to them OR created by them
            queryset = queryset.filter(Q(assigned_to_id=user.id) | Q(created_by_id=user.id))

        return queryset
    def perform_create(self, serializer):
        # Automatically attach org and creator
        user = self.request.user
        instance = serializer.save(organization=user.organization, created_by=user)
        if instance.assigned_to:
            send_notification_to_user(
                user_id=instance.assigned_to_id,
                message=f"A new case {instance.case_number} has been assigned to you.",
                case_id=instance.id
            )
    def perform_update(self, serialiser):
        instance = serialiser.save()
        if instance.assigned_to:
            send_notification_to_user(
                user_id=instance.assigned_to_id,
                message=f"The case {instance.case_number} has been updated.",
                case_id=instance.id
            )
    def perform_destroy(self, instance):
        # Soft delete instead of hard delete for compliance
        instance.is_deleted = True
        instance.save() 


    @action(detail=True, methods=['post'])
    def request_closure(self, request, pk=None):
        """Analysts request closure. Moves to PENDING_APPROVAL."""
        case = self.get_object()
        if request.user.role not in ['ANALYST', 'TEAM_LEADER', 'ORG_ADMIN']:
            return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        
        case.status = 'PENDING_APPROVAL'
        case.resolution_notes = request.data.get('resolution_notes', '')
        case.save()
        
        # Notify Team Leaders or Org Admins
        if case.department:
            leaders = User.objects.filter(department_id=case.department_id, role='TEAM_LEADER')
            print(f"--- Found {leaders.count()} Team Leaders ---")

            for leader in leaders:
                send_notification_to_user(
                    user_id=leader.id,
                    message=f"Closure requested for case {case.case_number}.",
                    case_id=case.id
                )        
        # ALSO Notify Org Admins (so it never gets lost)
        org_admins = User.objects.filter(organization_id=case.organization_id, role='ORG_ADMIN')
        print(f"--- Sending notification to: {admin.username} ---")

        for admin in org_admins:
            send_notification_to_user(
                user_id=admin.id,
                message=f"Closure requested for case {case.case_number}.",
                case_id=case.id
            )
        return Response({'status': 'closure requested'})


    @action(detail=True, methods=['post'])
    def approve_closure(self, request, pk=None):
        """Team Leaders/Org Admins approve closure."""
        case = self.get_object()
        if request.user.role not in ['TEAM_LEADER', 'ORG_ADMIN', 'SUPERADMIN']:
            return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        
        case.status = 'CLOSED'
        case.approved_by = request.user
        case.approved_at = timezone.now()
        case.save()
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'])
    def reject_closure(self, request, pk=None):
        """Team Leaders/Org Admins reject closure. Reverts to IN_PROGRESS."""
        case = self.get_object()
        if request.user.role not in ['TEAM_LEADER', 'ORG_ADMIN']:
            return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        
        case.status = 'IN_PROGRESS'
        case.save()
        return Response({'status': 'rejected'})

class CaseDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = CaseDocumentSerializer
    queryset = CaseDocument.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.role == 'SUPERADMIN':
            queryset = CaseDocument.objects.all()
        else:
            queryset = CaseDocument.objects.filter(case__organization_id=user.organization_id)
        
        case_id = self.request.query_params.get('case_id')
        if case_id:
            queryset = queryset.filter(case_id=case_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

class CaseNoteViewSet(viewsets.ModelViewSet):
    serializer_class = CaseNoteSerializer
    queryset = CaseNote.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        # Super Admins can see all notes
        if user.role == 'SUPERADMIN':
            queryset = CaseNote.objects.all()
        else:
            # Other users only see notes for cases in their organization
            queryset = CaseNote.objects.filter(case__organization_id=user.organization_id)
        
        # Filter by case_id if provided in the URL
        case_id = self.request.query_params.get('case_id')
        if case_id:
            queryset = queryset.filter(case_id=case_id)
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)