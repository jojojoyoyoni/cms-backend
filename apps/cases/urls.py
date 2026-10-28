# cases/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CaseViewSet

router = DefaultRouter()
# Add basename='case' here ↓
router.register(r'', CaseViewSet, basename='case')

urlpatterns = [
    path('', include(router.urls)),
]