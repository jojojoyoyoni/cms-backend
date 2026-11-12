from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CaseViewSet, CaseNoteViewSet, CaseDocumentViewSet, TaskViewSet

# Router for sub-resources only (NOT CaseViewSet!)
router = DefaultRouter()
router.register(r'notes', CaseNoteViewSet, basename='case-note')
router.register(r'documents', CaseDocumentViewSet, basename='case-document')
router.register(r'tasks', TaskViewSet, basename='task')

# CaseViewSet uses explicit URLs (avoids the r'' router bug)
case_list = CaseViewSet.as_view({'get': 'list', 'post': 'create'})
case_detail = CaseViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

urlpatterns = [
    # Case CRUD (explicit URLs)
    path('', case_list, name='case-list'),
    path('<int:pk>/', case_detail, name='case-detail'),
    path('<int:pk>/request_closure/', CaseViewSet.as_view({'post': 'request_closure'}), name='case-request-closure'),
    path('<int:pk>/approve_closure/', CaseViewSet.as_view({'post': 'approve_closure'}), name='case-approve-closure'),
    path('<int:pk>/reject_closure/', CaseViewSet.as_view({'post': 'reject_closure'}), name='case-reject-closure'),
    # Sub-resources (notes, documents, tasks) via router
    path('', include(router.urls)),
]