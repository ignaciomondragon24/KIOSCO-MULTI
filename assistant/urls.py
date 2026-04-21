"""
URL patterns for the Assistant app.
"""
from django.urls import path
from . import views

app_name = 'assistant'

urlpatterns = [
    # Main chat interface
    path('', views.assistant_home, name='home'),
    
    # Invoice scanning
    path('scan/', views.scan_invoice_page, name='scan_invoice'),
    path('api/scan-invoice/', views.api_scan_invoice, name='api_scan_invoice'),
    path('api/confirm-invoice/', views.api_confirm_invoice, name='api_confirm_invoice'),
    path('api/create-product/', views.api_create_product_from_scan, name='api_create_product'),
    
    # API endpoints
    path('api/send/', views.send_message, name='send_message'),
    path('api/new/', views.new_conversation, name='new_conversation'),
    path('api/history/', views.conversation_history, name='history'),
    path('api/conversation/<int:conversation_id>/', views.load_conversation, name='load_conversation'),
    path('api/insights/', views.get_insights, name='insights'),
    
    # Admin pages
    path('settings/', views.assistant_settings, name='settings'),
    path('logs/', views.query_logs, name='logs'),
]
