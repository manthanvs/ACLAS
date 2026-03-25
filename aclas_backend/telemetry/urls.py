from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    path('settings/', views.settings_view, name='settings'),
    path('manager-dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('heartbeats/', api_views.HeartbeatAPIView.as_view(), name='api_heartbeats'),
]
