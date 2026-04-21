"""
Sales URL Configuration - Reports and Analytics
"""
from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Reports Dashboard
    path('', views.reports_dashboard, name='dashboard'),
    path('sales/', views.sale_list, name='sale_list'),
    path('balance/', views.balance_consolidado, name='balance_consolidado'),

    # Reports
    path('reports/daily/', views.daily_report, name='daily_report'),
    path('reports/period/', views.period_report, name='period_report'),
    path('reports/products/', views.products_report, name='products_report'),
    path('reports/categories/', views.categories_report, name='categories_report'),
    path('reports/cashiers/', views.cashiers_report, name='cashiers_report'),
    
    # Export
    path('export/excel/', views.export_excel, name='export_excel'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
    
    # API endpoints
    path('api/today-stats/', views.api_today_stats, name='api_today_stats'),
]
