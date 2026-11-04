from django.urls import path
from .views import DashboardStatsView, SendReportView

urlpatterns = [
    path('dashboard/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('send-report/', SendReportView.as_view(), name='send-report'),
]