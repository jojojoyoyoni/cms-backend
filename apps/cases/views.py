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

from apps.users.permissions import HasRolePermission
from .models import Case, CaseNote, CaseDocument, Task
from apps.users.models import User
from apps.cases.filters import CaseFilter
from .serializers import CaseNoteSerializer, CaseSerializer, CaseDocumentSerializer, TaskSerializer
from apps.notifications.services import send_notification_to_user

class CaseViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CaseFilter
    search_fields = ['title', 'case_number', 'description']
    ordering_fields = ['created_at', 'due_date', 'priority', 'title', 'case_number']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'SUPERADMIN':
            return Case.objects.none()
        queryset = super().get_queryset()
        if user.role in ['ORG_ADMIN', 'HIGHER_OFFICIAL']:
            pass
        elif user.role == 'TEAM_LEADER':
            queryset = queryset.filter(department_id=user.department_id)
        elif user.role == 'ANALYST':
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
        if request.user.role not in ['ANALYST', 'TEAM_LEADER', 'HIGHER_OFFICIAL', 'ORG_ADMIN']:
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
        if request.user.role not in ['TEAM_LEADER', 'HIGHER_OFFICIAL', 'ORG_ADMIN', 'SUPERADMIN']:
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
        if request.user.role not in ['TEAM_LEADER', 'HIGHER_OFFICIAL', 'ORG_ADMIN']:
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


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    queryset = Task.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.role == 'SUPERADMIN':
            return Task.objects.none()
        
        queryset = Task.objects.filter(case__organization_id=user.organization_id)
        
        if user.role == 'TEAM_LEADER':
            queryset = queryset.filter(case__department_id=user.department_id)
        elif user.role == 'ANALYST':
            queryset = queryset.filter(Q(assigned_to_id=user.id) | Q(created_by_id=user.id))
        
        case_id = self.request.query_params.get('case_id')
        if case_id:
            queryset = queryset.filter(case_id=case_id)
        
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        
        # Analysts can only assign tasks to themselves
        if user.role == 'ANALYST':
            instance = serializer.save(created_by=user, assigned_to=user)
        else:
            # Team Leaders & Org Admins can assign to anyone
            instance = serializer.save(created_by=user)
        
        # Send notification to assignee if it's not the creator
        if instance.assigned_to and instance.assigned_to_id != user.id:
            send_notification_to_user(
                user_id=instance.assigned_to_id,
                message=f"New task assigned: '{instance.title}' on Case {instance.case.case_number}",
                case_id=instance.case_id
            )
        
        # Notify Team Leaders when an Analyst creates a task
        if user.role == 'ANALYST' and instance.case.department:
            leaders = User.objects.filter(
                department_id=instance.case.department_id, 
                role='TEAM_LEADER'
            )
            for leader in leaders:
                if leader.id != user.id:
                    send_notification_to_user(
                        user_id=leader.id,
                        message=f"New task created by {user.username}: '{instance.title}' on Case {instance.case.case_number}",
                        case_id=instance.case_id
                    )
    def perform_update(self, serializer):
        user = self.request.user
        old_instance = self.get_object()
        old_status = old_instance.status
        old_assignee = old_instance.assigned_to_id
        
        instance = serializer.save()
        
        # Notify new assignee if assignment changed
        if instance.assigned_to_id != old_assignee and instance.assigned_to and instance.assigned_to_id != user.id:
            send_notification_to_user(
                user_id=instance.assigned_to_id,
                message=f"Task reassigned to you: '{instance.title}' on Case {instance.case.case_number}",
                case_id=instance.case_id
            )
        
        # Notify creator when task is marked as DONE
        if old_status != 'DONE' and instance.status == 'DONE':
            instance.completed_at = timezone.now()
            instance.save()
            
            if instance.created_by and instance.created_by_id != user.id:
                send_notification_to_user(
                    user_id=instance.created_by_id,
                    message=f"Task completed: '{instance.title}' on Case {instance.case.case_number}",
                    case_id=instance.case_id
                )
            
            # Also notify Team Leaders
            if instance.case.department:
                leaders = User.objects.filter(
                    department_id=instance.case.department_id,
                    role='TEAM_LEADER'
                )
                for leader in leaders:
                    if leader.id != user.id:
                        send_notification_to_user(
                            user_id=leader.id,
                            message=f"✅ Task completed by {user.username}: '{instance.title}' on Case {instance.case.case_number}",
                            case_id=instance.case_id
                        )

    def destroy(self, request, *args, **kwargs):
        if request.user.role not in ['ORG_ADMIN', 'TEAM_LEADER']:
            return Response(
                {'error': 'You do not have permission to delete tasks.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)