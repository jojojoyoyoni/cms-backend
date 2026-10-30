from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MeView, OrganizationViewSet, UserViewSet

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('me/', MeView.as_view(), name='me'),
    path('', include(router.urls)),
]