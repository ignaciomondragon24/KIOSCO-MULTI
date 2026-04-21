from django.urls import path
from . import views

app_name = 'signage'

urlpatterns = [
    path('', views.template_list, name='template_list'),
    path('eliminar/<int:pk>/', views.template_delete, name='template_delete'),
    path('generar/<int:pk>/', views.generate, name='generate'),
    path('generar-todo/', views.generate_all, name='generate_all'),
    path('lotes/', views.batch_list, name='batch_list'),
    path('imprimir/', views.print_view, name='print_view'),

    # API endpoints (AJAX)
    path('api/product-data/', views.api_product_data, name='api_product_data'),
    path('api/save-batch/', views.save_batch, name='save_batch'),
    path('api/generate-all-data/', views.api_generate_all_data, name='api_generate_all_data'),
]
