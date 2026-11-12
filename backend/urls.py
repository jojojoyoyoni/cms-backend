from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf.urls.static import static
from apps.cases.sla_views import (CaseEscalateView, CaseSlaView,
                                  EscalationListView, EscalationResolveView,
                                  EscalationSummaryView, SlaPolicyListCreateView)


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # JWT Auth
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # App Routes
    path('api/users/', include('apps.users.urls')),
    path('api/cases/', include('apps.cases.urls')),
    path('api/audits/', include('apps.audits.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/notifications/', include('apps.notifications.urls')),

    path("api/cases/<int:pk>/sla/", CaseSlaView.as_view()),
    path("api/cases/<int:pk>/escalate/", CaseEscalateView.as_view()),
    path("api/sla-policies/", SlaPolicyListCreateView.as_view()),
    path("api/escalations/summary/", EscalationSummaryView.as_view()),
    path("api/escalations/<int:pk>/resolve/", EscalationResolveView.as_view()),
    path("api/escalations/", EscalationListView.as_view()),
    
    # Placeholder routes for apps we will build next
    # path('api/audits/', include('apps.audits.urls')),
    # path('api/notifications/', include('apps.notifications.urls')),
    # path('api/reports/', include('apps.reports.urls')),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)