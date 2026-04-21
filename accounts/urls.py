"""
Accounts URLs
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('', views.home_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # User management
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('users/<int:pk>/toggle/', views.user_toggle, name='user_toggle'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
]
