"""
MercadoPago Admin Configuration
"""
from django.contrib import admin
from .models import MPCredentials, PointDevice, PaymentIntent, WebhookLog


@admin.register(MPCredentials)
class MPCredentialsAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'is_sandbox', 'created_at', 'updated_at')
    list_filter = ('is_active', 'is_sandbox')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'is_active', 'is_sandbox')
        }),
        ('Credenciales', {
            'fields': ('access_token', 'public_key'),
            'classes': ('collapse',),
        }),
        ('Webhook', {
            'fields': ('webhook_secret',),
            'classes': ('collapse',),
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


@admin.register(PointDevice)
class PointDeviceAdmin(admin.ModelAdmin):
    list_display = ('device_name', 'device_id', 'cash_register', 'operating_mode', 'status', 'last_sync')
    list_filter = ('status', 'operating_mode', 'cash_register')
    search_fields = ('device_name', 'device_id', 'serial_number')
    readonly_fields = ('device_id', 'serial_number', 'last_sync', 'created_at')
    
    fieldsets = (
        (None, {
            'fields': ('device_name', 'device_id', 'serial_number')
        }),
        ('Asignación', {
            'fields': ('cash_register', 'operating_mode', 'status')
        }),
        ('Sincronización', {
            'fields': ('last_sync', 'created_at'),
        }),
    )


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    list_display = (
        'external_reference', 'amount', 'status', 'device', 
        'payment_method', 'card_brand', 'created_at'
    )
    list_filter = ('status', 'payment_method', 'card_brand', 'device', 'created_at')
    search_fields = (
        'external_reference', 'mp_payment_intent_id', 'mp_payment_id',
        'authorization_code', 'card_last_four'
    )
    readonly_fields = (
        'id', 'external_reference', 'mp_payment_intent_id', 'mp_payment_id',
        'created_at', 'updated_at', 'sent_at', 'completed_at'
    )
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('id', 'external_reference', 'status', 'amount')
        }),
        ('Mercado Pago', {
            'fields': ('mp_payment_intent_id', 'mp_payment_id', 'device'),
        }),
        ('Pago', {
            'fields': ('payment_method', 'card_brand', 'card_last_four', 'installments', 'authorization_code'),
        }),
        ('Relaciones', {
            'fields': ('pos_transaction', 'created_by'),
        }),
        ('Información Adicional', {
            'fields': ('error_reason', 'raw_response'),
            'classes': ('collapse',),
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at', 'sent_at', 'completed_at'),
        }),
    )
    
    def has_add_permission(self, request):
        return False


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'event_id', 'processed', 'ip_address', 'received_at')
    list_filter = ('event_type', 'processed', 'received_at')
    search_fields = ('event_id', 'ip_address', 'processing_result')
    readonly_fields = ('received_at', 'event_type', 'event_id', 'payload', 'headers', 'ip_address')
    date_hierarchy = 'received_at'
    
    fieldsets = (
        (None, {
            'fields': ('event_type', 'event_id', 'ip_address', 'received_at')
        }),
        ('Procesamiento', {
            'fields': ('processed', 'processing_result'),
        }),
        ('Datos', {
            'fields': ('payload', 'headers'),
            'classes': ('collapse',),
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
