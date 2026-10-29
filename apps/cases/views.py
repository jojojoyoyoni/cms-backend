from rest_framework import viewsets
from apps.core.mixins import TenantQuerySetMixin
from rest_framework.permissions import IsAuthenticated
from .models import Case, CaseNote, CaseDocument
from .serializers import CaseNoteSerializer, CaseSerializer, CaseDocumentSerializer

class CaseViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = CaseSerializer

    def get_queryset(self):
        # Start with the TenantQuerySetMixin logic (filters by Org, unless SuperAdmin)
        # queryset = super().get_queryset()
        queryset = Case.objects.all()  

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

    def perform_destroy(self, instance):
        # Soft delete instead of hard delete for compliance
        instance.is_deleted = True
        instance.save() 

# ... existing CaseNoteViewSet ...

class CaseDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = CaseDocumentSerializer
    queryset = CaseDocument.objects.all()
    permission_classes = [IsAuthenticated]

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