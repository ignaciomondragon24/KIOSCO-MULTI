"""
Stocks URLs
"""
from django.urls import path
from . import views

app_name = 'stocks'

urlpatterns = [
    # Products
    path('', views.product_list, name='product_list'),
    path('add/', views.product_create, name='product_create'),
    path('<int:pk>/', views.product_detail, name='product_detail'),
    path('<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('<int:pk>/conteo/', views.inventory_count, name='inventory_count'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    
    # Movements / Kardex
    path('movements/', views.product_movement_list, name='movement_list'),
    path('<int:pk>/movements/', views.product_movement_list, name='product_movements'),

    # Cost History
    path('costos/', views.cost_history, name='cost_history'),
    path('<int:pk>/costos/', views.cost_history, name='product_costs'),

    # Reports
    path('low-stock/', views.low_stock_products, name='low_stock'),
    path('price-list/', views.price_list, name='price_list'),
    path('export/excel/', views.export_products_excel, name='export_excel'),
    path('import/excel/', views.import_excel, name='import_excel'),
    
    # Packaging
    path('packaging/delete/<int:packaging_id>/', views.packaging_delete, name='packaging_delete'),
    
    # Packaging management
    path('<int:pk>/packaging-manage/', views.product_packaging_view, name='product_packaging'),
    path('packaging-inventory/', views.packaging_inventory_view, name='packaging_inventory'),
    path('<int:pk>/packaging-manage/api/', views.packaging_api, name='packaging_api'),
    
    # API
    path('api/search/', views.api_search_products, name='api_search'),
    path('api/generate-barcode/', views.api_generate_barcode, name='generate_barcode'),
    path('api/packaging/<int:packaging_id>/', views.api_get_packaging, name='api_get_packaging'),
]
