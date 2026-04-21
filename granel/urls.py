from django.urls import path
from . import views

app_name = 'granel'

urlpatterns = [
    # Depósito (los productos se crean/editan desde el inventario estándar)
    path('deposito/', views.deposito_list, name='deposito_list'),
    path('deposito/<int:pk>/editar/', views.deposito_edit, name='deposito_edit'),
    path('api/deposito/<int:pk>/stock/', views.api_deposito_ajustar_stock, name='api_deposito_stock'),

    # Carameleras
    path('carameleras/', views.caramelera_list, name='caramelera_list'),
    path('carameleras/nueva/', views.caramelera_create, name='caramelera_create'),
    path('carameleras/<int:pk>/', views.caramelera_detail, name='caramelera_detail'),
    path('carameleras/<int:pk>/editar/', views.caramelera_edit, name='caramelera_edit'),

    # APIs
    path('api/caramelera/<int:pk>/abrir-paquete/', views.api_abrir_paquete, name='api_abrir_paquete'),
    path('api/caramelera/<int:pk>/auditoria/', views.api_auditoria, name='api_auditoria'),
    path('api/caramelera/<int:pk>/venta/', views.api_venta_granel, name='api_venta_granel'),
    path('api/caramelera/<int:pk>/info/', views.api_caramelera_info, name='api_caramelera_info'),
]
