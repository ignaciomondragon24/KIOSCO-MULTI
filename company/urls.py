"""
Company URL Configuration
"""
from django.urls import path
from . import views

app_name = 'company'

urlpatterns = [
    path('', views.company_settings, name='home'),
    path('settings/', views.company_settings, name='settings'),
    path('branches/', views.branch_list, name='branch_list'),
    path('branches/create/', views.branch_create, name='branch_create'),
    path('branches/<int:pk>/edit/', views.branch_edit, name='branch_edit'),
    path('branches/<int:pk>/delete/', views.branch_delete, name='branch_delete'),
]
