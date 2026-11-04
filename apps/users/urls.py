from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChangePasswordView, DepartmentViewSet, MeView, OrganizationViewSet, UserViewSet

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('me/', MeView.as_view(), name='me'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'), 
    path('', include(router.urls)),
]