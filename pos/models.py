"""
POS Models - Point of Sale
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone


class POSSession(models.Model):
    """POS Session linked to a cash shift."""
    
    STATUS_CHOICES = [
        ('active', 'Activo'),
        ('closed', 'Cerrado'),
    ]
    
    cash_shift = models.ForeignKey(
        'cashregister.CashShift',
        on_delete=models.PROTECT,
        related_name='pos_sessions',
        verbose_name='Turno de Caja'
    )
    opened_at = models.DateTimeField(
        'Apertura',
        auto_now_add=True
    )
    closed_at = models.DateTimeField(
        'Cierre',
        null=True,
        blank=True
    )
    status = models.CharField(
        'Estado',
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    class Meta:
        verbose_name = 'Sesión POS'
        verbose_name_plural = 'Sesiones POS'
        ordering = ['-opened_at']
    
    def __str__(self):
        return f'Sesión {self.pk} - {self.cash_shift}'
    
    @property
    def total_transactions(self):
        return self.transactions.filter(status='completed').count()
    
    @property
    def total_amount(self):
        from django.db.models import Sum
        result = self.transactions.filter(status='completed').aggregate(
            total=Sum('total')
        )
        return result['total'] or Decimal('0.00')


class POSTransaction(models.Model):
    """POS Transaction (sale)."""
    
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
        ('suspended', 'Suspendida'),
    ]
    
    TRANSACTION_TYPE_CHOICES = [
        ('sale', 'Venta'),
        ('cost_sale', 'Venta al Costo'),
        ('internal_consumption', 'Consumo Interno'),
    ]
    
    session = models.ForeignKey(
        POSSession,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Sesión'
    )
    ticket_number = models.CharField(
        'Número de Ticket',
        max_length=50,
        unique=True,
        help_text='Formato: CAJA-XX-YYYYMMDD-NNNN'
    )
    status = models.CharField(
        'Estado',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    transaction_type = models.CharField(
        'Tipo de Transacción',
        max_length=30,
        choices=TRANSACTION_TYPE_CHOICES,
        default='sale'
    )
    
    # Totals
    subtotal = models.DecimalField(
        'Subtotal',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    discount_total = models.DecimalField(
        'Total Descuentos',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    tax_total = models.DecimalField(
        'Total Impuestos',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total = models.DecimalField(
        'Total',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    items_count = models.PositiveIntegerField(
        'Cantidad de Ítems',
        default=0
    )
    
    # Payment info
    amount_paid = models.DecimalField(
        'Monto Pagado',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    change_given = models.DecimalField(
        'Vuelto',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        'Creación',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'Actualización',
        auto_now=True
    )
    completed_at = models.DateTimeField(
        'Completada',
        null=True,
        blank=True
    )
    cancelled_at = models.DateTimeField(
        'Cancelada',
        null=True,
        blank=True
    )
    suspended_at = models.DateTimeField(
        'Suspendida',
        null=True,
        blank=True
    )
    
    notes = models.TextField(
        'Notas',
        blank=True
    )
    
    class Meta:
        verbose_name = 'Transacción POS'
        verbose_name_plural = 'Transacciones POS'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket_number']),
            models.Index(fields=['status']),
            models.Index(fields=['completed_at']),
        ]
    
    def __str__(self):
        return f'{self.ticket_number} - ${self.total}'
    
    def calculate_totals(self):
        """Recalculate transaction totals from items."""
        from django.db.models import Sum, F, DecimalField, Case, When, Value

        # Use output_field to handle mixed types (DecimalField * PositiveIntegerField)
        result = self.items.aggregate(
            subtotal=Sum(
                F('unit_price') * F('quantity'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            manual_discount=Sum('discount'),
            promo_discount=Sum('promotion_discount'),
            # Granel: quantity es gramos (250, 500…), contar como 1 item.
            # No-granel: quantity es unidades reales.
            count=Sum(
                Case(
                    When(product__is_granel=True, then=Value(1)),
                    default=F('quantity'),
                    output_field=DecimalField(max_digits=12, decimal_places=3),
                )
            ),
        )

        self.subtotal = result['subtotal'] or Decimal('0.00')
        manual = result['manual_discount'] or Decimal('0.00')
        promo = result['promo_discount'] or Decimal('0.00')
        self.discount_total = manual + promo
        self.total = self.subtotal - self.discount_total + self.tax_total
        self.items_count = int(result['count'] or 0)
        self.save()


class POSTransactionItem(models.Model):
    """Item in a POS transaction."""
    
    transaction = models.ForeignKey(
        POSTransaction,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Transacción'
    )
    product = models.ForeignKey(
        'stocks.Product',
        on_delete=models.PROTECT,
        related_name='pos_items',
        verbose_name='Producto'
    )
    packaging = models.ForeignKey(
        'stocks.ProductPackaging',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pos_items',
        verbose_name='Empaque',
        help_text='Empaque vendido (unidad/display/bulto). Si es null, se vende 1 unidad.'
    )
    packaging_units = models.PositiveIntegerField(
        'Unidades por Empaque',
        default=1,
        help_text='Cuántas unidades base se descuentan por cada unidad vendida de este empaque'
    )
    quantity = models.DecimalField(
        'Cantidad',
        max_digits=10,
        decimal_places=3,
        default=Decimal('1.000'),
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    unit_price = models.DecimalField(
        'Precio Unitario',
        max_digits=10,
        decimal_places=2,
        help_text='Precio al momento de la venta'
    )
    unit_cost = models.DecimalField(
        'Costo Unitario',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Costo del producto al momento de la venta (para cálculo de ganancia)'
    )
    discount = models.DecimalField(
        'Descuento Manual',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Descuento manual ingresado por el cajero (independiente de la promo)'
    )
    promotion_discount = models.DecimalField(
        'Descuento por Promoción',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Descuento aplicado automáticamente por una promoción activa'
    )
    subtotal = models.DecimalField(
        'Subtotal',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Promotion info
    promotion = models.ForeignKey(
        'promotions.Promotion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transaction_items',
        verbose_name='Promoción'
    )
    promotion_name = models.CharField(
        'Nombre Promoción',
        max_length=200,
        blank=True,
        help_text='Guardado para histórico'
    )
    promotion_group_name = models.CharField(
        'Grupo de Promoción',
        max_length=200,
        blank=True,
        help_text='Nombre del grupo si la promo está enlazada con otras'
    )
    
    class Meta:
        verbose_name = 'Ítem de Transacción'
        verbose_name_plural = 'Ítems de Transacción'
        ordering = ['id']
    
    def __str__(self):
        pkg_label = f' ({self.packaging.get_packaging_type_display()})' if self.packaging else ''
        return f'{self.product.name}{pkg_label} x {self.quantity}'
    
    @property
    def total_units_deducted(self):
        """Total base units to deduct from stock."""
        return self.quantity * self.packaging_units
    
    def save(self, *args, **kwargs):
        # Calculate subtotal (never negative): resta tanto descuento manual como promo
        gross = self.unit_price * self.quantity
        total_discount = (self.discount or Decimal('0.00')) + (self.promotion_discount or Decimal('0.00'))
        self.subtotal = max(gross - total_discount, Decimal('0.00'))
        super().save(*args, **kwargs)


class POSPayment(models.Model):
    """Payment for a POS transaction."""
    
    transaction = models.ForeignKey(
        POSTransaction,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Transacción'
    )
    payment_method = models.ForeignKey(
        'cashregister.PaymentMethod',
        on_delete=models.PROTECT,
        related_name='pos_payments',
        verbose_name='Método de Pago'
    )
    amount = models.DecimalField(
        'Monto',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    reference = models.CharField(
        'Referencia',
        max_length=100,
        blank=True,
        help_text='Últimos 4 dígitos de tarjeta, etc.'
    )
    created_at = models.DateTimeField(
        'Fecha',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Pago POS'
        verbose_name_plural = 'Pagos POS'
        ordering = ['created_at']
    
    def __str__(self):
        return f'{self.payment_method.name} - ${self.amount}'


class POSKeyboardShortcut(models.Model):
    """Configurable keyboard shortcut for POS actions."""

    ACTION_CHOICES = [
        # Navegación
        ('search_focus',          'Enfocar Búsqueda'),
        ('help',                  'Mostrar Ayuda'),
        ('dashboard',             'Ir al Dashboard'),
        # Carrito
        ('clear_cart',            'Vaciar Carrito'),
        ('discount',              'Aplicar Descuento'),
        # Transacción
        ('hold',                  'Apartar Venta'),
        ('suspended',             'Ver Apartados'),
        ('cancel',                'Cancelar Venta'),
        # Cobro
        ('checkout',              'Cobrar (abrir modal)'),
        ('pay_cash',              'Cobrar Directo — Efectivo'),
        ('pay_mercadopago',       'Cobrar Directo — Mercado Pago'),
        ('pay_debit',             'Cobrar Directo — Débito'),
        ('pay_credit',            'Cobrar Directo — Crédito'),
        ('pay_transfer',          'Cobrar Directo — Transferencia'),
        ('pay_mixed',             'Cobrar Directo — Mixto (MP + Efectivo)'),
        # Especiales
        ('cost_sale',             'Venta al Costo'),
        ('internal_consumption',  'Consumo Interno'),
        ('reprint',               'Reimprimir Último Ticket'),
        ('sales_history',         'Historial de Ventas del Turno'),
    ]

    KEY_CHOICES = [
        ('F1', 'F1'), ('F2', 'F2'), ('F3', 'F3'), ('F4', 'F4'),
        ('F5', 'F5'), ('F6', 'F6'), ('F7', 'F7'), ('F8', 'F8'),
        ('F9', 'F9'), ('F10', 'F10'), ('F11', 'F11'), ('F12', 'F12'),
        ('Escape', 'Escape'),
        ('Alt+1', 'Alt+1'), ('Alt+2', 'Alt+2'), ('Alt+3', 'Alt+3'),
        ('Alt+4', 'Alt+4'), ('Alt+5', 'Alt+5'), ('Alt+6', 'Alt+6'),
        ('Alt+7', 'Alt+7'), ('Alt+8', 'Alt+8'), ('Alt+9', 'Alt+9'),
        ('none', '(Sin atajo)'),
    ]

    action = models.CharField(
        'Acción',
        max_length=60,
        choices=ACTION_CHOICES,
        unique=True,
    )
    key = models.CharField(
        'Tecla',
        max_length=10,
        choices=KEY_CHOICES,
        default='none',
        help_text='Tecla asignada a esta acción. Evite duplicados.',
    )
    is_enabled = models.BooleanField(
        'Habilitado',
        default=True,
    )
    order = models.PositiveSmallIntegerField(
        'Orden de visualización',
        default=0,
    )

    class Meta:
        verbose_name = 'Atajo de Teclado POS'
        verbose_name_plural = 'Atajos de Teclado POS'
        ordering = ['order', 'action']

    def __str__(self):
        label = dict(self.ACTION_CHOICES).get(self.action, self.action)
        return f'{self.key} → {label}'

    @classmethod
    def get_defaults(cls):
        """Return default shortcut configuration."""
        return [
            {'action': 'help',                 'key': 'F1',  'order': 1},
            {'action': 'search_focus',          'key': 'F2',  'order': 2},
            {'action': 'clear_cart',            'key': 'F3',  'order': 3},
            {'action': 'hold',                  'key': 'F4',  'order': 4},
            {'action': 'suspended',             'key': 'F5',  'order': 5},
            {'action': 'discount',              'key': 'F6',  'order': 6},
            {'action': 'cancel',                'key': 'F7',  'order': 7},
            {'action': 'checkout',              'key': 'F8',  'order': 8},
            {'action': 'reprint',               'key': 'F9',  'order': 9},
            {'action': 'cost_sale',             'key': 'F10', 'order': 10},
            {'action': 'internal_consumption',  'key': 'F11', 'order': 11},
            {'action': 'dashboard',             'key': 'F12', 'order': 12},
            {'action': 'pay_cash',              'key': 'none', 'order': 13},
            {'action': 'pay_mercadopago',       'key': 'none', 'order': 14},
            {'action': 'pay_debit',             'key': 'none', 'order': 15},
            {'action': 'pay_credit',            'key': 'none', 'order': 16},
            {'action': 'pay_transfer',          'key': 'none', 'order': 17},
            {'action': 'pay_mixed',             'key': 'none', 'order': 18},
            {'action': 'sales_history',         'key': 'none', 'order': 19},
        ]

    @classmethod
    def ensure_defaults(cls):
        """Create default shortcuts if they don't exist yet."""
        for d in cls.get_defaults():
            cls.objects.get_or_create(action=d['action'], defaults={
                'key': d['key'],
                'is_enabled': True,
                'order': d['order'],
            })

    def to_dict(self):
        return {
            'action': self.action,
            'key': self.key,
            'label': dict(self.ACTION_CHOICES).get(self.action, self.action),
            'is_enabled': self.is_enabled,
        }


class QuickAccessButton(models.Model):
    """Quick access button for POS."""
    
    product = models.OneToOneField(
        'stocks.Product',
        on_delete=models.CASCADE,
        related_name='quick_button',
        verbose_name='Producto'
    )
    name = models.CharField(
        'Nombre en Botón',
        max_length=50,
        blank=True,
        help_text='Nombre corto para el botón. Si vacío, usa el nombre del producto.'
    )
    color = models.CharField(
        'Color',
        max_length=7,
        default='#3498db',
        help_text='Código hexadecimal'
    )
    icon = models.CharField(
        'Icono',
        max_length=50,
        default='fa-box',
        help_text='Clase Font Awesome'
    )
    position = models.PositiveIntegerField(
        'Posición',
        default=0
    )
    is_active = models.BooleanField(
        'Activo',
        default=True
    )
    
    class Meta:
        verbose_name = 'Botón de Acceso Rápido'
        verbose_name_plural = 'Botones de Acceso Rápido'
        ordering = ['position', 'product__name']
    
    def __str__(self):
        return self.display_name
    
    @property
    def display_name(self):
        return self.name or self.product.name
