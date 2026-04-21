"""
MercadoPago Models - Dispositivos Point y Órdenes de Pago
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
import json


class MPCredentials(models.Model):
    """
    Credenciales de Mercado Pago.
    Solo debe existir un registro activo.
    """
    name = models.CharField(
        'Nombre',
        max_length=100,
        default='Producción'
    )
    access_token = models.CharField(
        'Access Token',
        max_length=500,
        help_text='Token de acceso de Mercado Pago'
    )
    public_key = models.CharField(
        'Public Key',
        max_length=500,
        blank=True,
        help_text='Clave pública (opcional)'
    )
    user_id = models.CharField(
        'User ID',
        max_length=50,
        blank=True,
        help_text='ID de usuario de MP'
    )
    is_sandbox = models.BooleanField(
        'Modo Sandbox',
        default=False,
        help_text='Usar ambiente de pruebas'
    )
    is_active = models.BooleanField(
        'Activo',
        default=True
    )
    external_pos_id = models.CharField(
        'External POS ID (QR)',
        max_length=100,
        blank=True,
        help_text='ID del punto de venta para QR estático. Ej: CHEPOS-001. Debe coincidir con el configurado en MP.'
    )
    webhook_secret = models.CharField(
        'Webhook Secret',
        max_length=200,
        blank=True,
        help_text='Clave secreta para validar webhooks'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Credencial MP'
        verbose_name_plural = 'Credenciales MP'
    
    def __str__(self):
        return f"{self.name} ({'Sandbox' if self.is_sandbox else 'Producción'})"
    
    def save(self, *args, **kwargs):
        # Solo puede haber una credencial activa
        if self.is_active:
            MPCredentials.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active(cls):
        """Obtiene las credenciales activas."""
        return cls.objects.filter(is_active=True).first()


class PointDevice(models.Model):
    """
    Dispositivo Point de Mercado Pago vinculado a una caja.
    """
    STATUS_CHOICES = [
        ('active', 'Activo'),
        ('inactive', 'Inactivo'),
        ('disconnected', 'Desconectado'),
    ]
    
    device_id = models.CharField(
        'Device ID',
        max_length=100,
        unique=True,
        help_text='ID del dispositivo en Mercado Pago'
    )
    device_name = models.CharField(
        'Nombre del Dispositivo',
        max_length=100,
        blank=True
    )
    cash_register = models.OneToOneField(
        'cashregister.CashRegister',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='point_device',
        verbose_name='Caja Asociada'
    )
    serial_number = models.CharField(
        'Número de Serie',
        max_length=100,
        blank=True
    )
    status = models.CharField(
        'Estado',
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    operating_mode = models.CharField(
        'Modo de Operación',
        max_length=50,
        default='PDV',
        help_text='PDV = Integrado con sistema'
    )
    last_sync = models.DateTimeField(
        'Última Sincronización',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Dispositivo Point'
        verbose_name_plural = 'Dispositivos Point'
        ordering = ['device_name']
    
    def __str__(self):
        return f"{self.device_name or self.device_id} - {self.cash_register or 'Sin asignar'}"


class PaymentIntent(models.Model):
    """
    Intención de pago enviada al dispositivo Point.
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),          # Creada, esperando envío
        ('processing', 'Procesando'),      # Enviada al Point, esperando pago
        ('approved', 'Aprobada'),          # Pago exitoso
        ('rejected', 'Rechazada'),         # Pago rechazado
        ('cancelled', 'Cancelada'),        # Cancelada por el usuario
        ('error', 'Error'),                # Error en el proceso
        ('expired', 'Expirada'),           # Expiró el tiempo de espera
    ]
    
    # Identificadores
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    external_reference = models.CharField(
        'Referencia Externa',
        max_length=100,
        unique=True,
        help_text='ID único para rastrear el pago'
    )
    mp_payment_intent_id = models.CharField(
        'ID Intent MP',
        max_length=100,
        blank=True,
        help_text='ID del payment intent en MP'
    )
    mp_payment_id = models.CharField(
        'ID Pago MP',
        max_length=100,
        blank=True,
        help_text='ID del pago aprobado en MP'
    )
    
    FLOW_CHOICES = [
        ('qr', 'QR Estático'),
        ('point', 'Point Smart (Tarjeta)'),
    ]

    payment_flow = models.CharField(
        'Flujo de Pago',
        max_length=10,
        choices=FLOW_CHOICES,
        default='qr'
    )

    # Relaciones
    device = models.ForeignKey(
        PointDevice,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payment_intents',
        verbose_name='Dispositivo'
    )
    pos_transaction = models.ForeignKey(
        'pos.POSTransaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mp_payment_intents',
        verbose_name='Transacción POS'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mp_payment_intents',
        verbose_name='Creado por'
    )
    
    # Monto
    amount = models.DecimalField(
        'Monto',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'))]
    )
    
    # Descripción
    description = models.CharField(
        'Descripción',
        max_length=200,
        default='Venta CHE GOLOSO'
    )
    
    # Estado
    status = models.CharField(
        'Estado',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Datos del pago (cuando se aprueba)
    payment_method = models.CharField(
        'Método de Pago',
        max_length=50,
        blank=True,
        help_text='debit_card, credit_card, etc.'
    )
    card_brand = models.CharField(
        'Marca de Tarjeta',
        max_length=50,
        blank=True
    )
    card_last_four = models.CharField(
        'Últimos 4 dígitos',
        max_length=4,
        blank=True
    )
    installments = models.PositiveIntegerField(
        'Cuotas',
        default=1
    )
    authorization_code = models.CharField(
        'Código de Autorización',
        max_length=50,
        blank=True
    )
    
    # Información adicional
    status_detail = models.CharField(
        'Detalle de Estado',
        max_length=200,
        blank=True
    )
    error_message = models.TextField(
        'Mensaje de Error',
        blank=True
    )
    
    # Webhook data (JSONField no disponible en Django 3.0, usamos TextField)
    webhook_data = models.TextField(
        'Datos Webhook',
        blank=True,
        help_text='Datos raw recibidos del webhook (JSON)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        'Creado',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'Actualizado',
        auto_now=True
    )
    sent_at = models.DateTimeField(
        'Enviado al Point',
        null=True,
        blank=True
    )
    completed_at = models.DateTimeField(
        'Completado',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Intención de Pago'
        verbose_name_plural = 'Intenciones de Pago'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['external_reference']),
            models.Index(fields=['mp_payment_intent_id']),
            models.Index(fields=['mp_payment_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.external_reference} - ${self.amount} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        if not self.external_reference:
            # Generar referencia externa única
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.external_reference = f"CHE-{timestamp}-{str(self.id)[:8].upper()}"
        super().save(*args, **kwargs)
    
    @property
    def is_terminal_state(self):
        """Indica si el pago está en un estado final."""
        return self.status in ['approved', 'rejected', 'cancelled', 'error', 'expired']
    
    def mark_approved(self, payment_data):
        """Marcar como aprobado con datos del pago."""
        self.status = 'approved'
        self.completed_at = timezone.now()
        self.mp_payment_id = str(payment_data.get('id', ''))
        self.payment_method = payment_data.get('payment_method_id', '')
        
        # Extraer datos de la tarjeta
        card_data = payment_data.get('card', {})
        self.card_brand = card_data.get('cardholder', {}).get('name', '') or payment_data.get('payment_type_id', '')
        self.card_last_four = card_data.get('last_four_digits', '')
        
        self.installments = payment_data.get('installments', 1)
        self.authorization_code = payment_data.get('authorization_code', '')
        self.status_detail = payment_data.get('status_detail', '')
        
        # Serializar datos para guardar como texto
        try:
            self.webhook_data = json.dumps(payment_data, indent=2, default=str)
        except Exception:
            self.webhook_data = str(payment_data)
        
        self.save()
    
    def mark_rejected(self, reason=''):
        """Marcar como rechazado."""
        self.status = 'rejected'
        self.completed_at = timezone.now()
        self.status_detail = reason
        self.save()
    
    def mark_cancelled(self):
        """Marcar como cancelado."""
        self.status = 'cancelled'
        self.completed_at = timezone.now()
        self.save()
    
    def mark_error(self, message):
        """Marcar como error."""
        self.status = 'error'
        self.error_message = message
        self.completed_at = timezone.now()
        self.save()


class WebhookLog(models.Model):
    """
    Log de webhooks recibidos de Mercado Pago.
    """
    received_at = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(
        'Tipo de Evento',
        max_length=100
    )
    event_id = models.CharField(
        'ID Evento',
        max_length=100,
        blank=True
    )
    resource_id = models.CharField(
        'ID Recurso',
        max_length=100,
        blank=True
    )
    payload = models.TextField(
        'Payload',
        blank=True,
        help_text='JSON payload'
    )
    headers = models.TextField(
        'Headers',
        blank=True,
        help_text='JSON headers'
    )
    processed = models.BooleanField(
        'Procesado',
        default=False
    )
    processing_result = models.TextField(
        'Resultado',
        blank=True
    )
    ip_address = models.GenericIPAddressField(
        'IP',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Log Webhook'
        verbose_name_plural = 'Logs Webhook'
        ordering = ['-received_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.received_at}"
