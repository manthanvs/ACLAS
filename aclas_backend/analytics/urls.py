from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('stats/', views.stats_view, name='stats'),
    path('about/', views.about_view, name='about'),
]
