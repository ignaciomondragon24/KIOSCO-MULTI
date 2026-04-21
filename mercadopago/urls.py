"""
MercadoPago URLs
"""
from django.urls import path
from . import views

app_name = 'mercadopago'

urlpatterns = [
    # Dashboard y configuración
    path('', views.mp_dashboard, name='dashboard'),
    path('credentials/', views.credentials_form, name='credentials'),
    path('test-connection/', views.test_connection, name='test_connection'),
    path('list-pos/', views.list_pos_view, name='list_pos'),
    path('assign-pos-external-id/', views.assign_pos_external_id_view, name='assign_pos_external_id'),
    
    # Dispositivos
    path('devices/', views.device_list, name='device_list'),
    path('devices/sync/', views.sync_devices, name='sync_devices'),
    path('devices/<int:device_id>/edit/', views.device_edit, name='device_edit'),
    path('devices/<int:device_id>/mode/', views.device_change_mode, name='device_change_mode'),
    
    # Intenciones de pago
    path('intents/', views.payment_intent_list, name='payment_intent_list'),
    path('intents/<uuid:intent_id>/', views.payment_intent_detail, name='payment_intent_detail'),
    path('intents/<uuid:intent_id>/check/', views.payment_intent_check_status, name='payment_intent_check_status'),
    path('intents/<uuid:intent_id>/cancel/', views.payment_intent_cancel, name='payment_intent_cancel'),
    
    # API para POS
    path('api/create-intent/', views.api_create_payment_intent, name='api_create_intent'),
    path('api/create-qr/', views.api_create_qr, name='api_create_qr'),
    path('api/status/<uuid:intent_id>/', views.api_check_payment_status, name='api_check_status'),
    path('api/cancel/<uuid:intent_id>/', views.api_cancel_payment, name='api_cancel'),
    
    # Webhook
    path('webhook/', views.webhook_receiver, name='webhook'),
    
    # Logs
    path('logs/', views.webhook_logs, name='webhook_logs'),
]
