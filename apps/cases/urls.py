# cases/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CaseDocumentViewSet, CaseNoteViewSet, CaseViewSet

router = DefaultRouter()
# Add basename='case' here ↓
router.register(r'notes', CaseNoteViewSet, basename='case-note')
router.register(r'documents', CaseDocumentViewSet, basename='case-document')

router.register(r'', CaseViewSet, basename='case')

urlpatterns = [
    path('', include(router.urls)),
]