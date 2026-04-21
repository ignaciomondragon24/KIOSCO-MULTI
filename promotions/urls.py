"""
Promotions URLs
"""
from django.urls import path
from . import views

app_name = 'promotions'

urlpatterns = [
    path('', views.promotion_list, name='promotion_list'),
    path('create/', views.promotion_create, name='promotion_create'),
    path('<int:pk>/', views.promotion_detail, name='promotion_detail'),
    path('<int:pk>/edit/', views.promotion_edit, name='promotion_edit'),
    path('<int:pk>/delete/', views.promotion_delete, name='promotion_delete'),
    path('<int:pk>/activate/', views.promotion_activate, name='promotion_activate'),
    path('<int:pk>/pause/', views.promotion_pause, name='promotion_pause'),
    
    # API
    path('api/calculate/', views.api_calculate, name='api_calculate'),
]
