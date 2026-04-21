"""
Expenses URL Configuration
"""
from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    # Expenses
    path('', views.expense_list, name='expense_list'),
    path('create/', views.expense_create, name='expense_create'),
    path('<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    
    # Recurring
    path('recurring/', views.recurring_list, name='recurring_list'),
    path('recurring/create/', views.recurring_create, name='recurring_create'),
    
    # Reports
    path('report/', views.expense_report, name='expense_report'),
    
    # API
    path('api/by-category/', views.api_expenses_by_category, name='api_expenses_by_category'),
]
