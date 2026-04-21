"""
Purchase Models - Suppliers and Purchases
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class Supplier(models.Model):
    """Supplier model."""
    
    name = models.CharField(
        'Nombre',
        max_length=200
    )
    contact_name = models.CharField(
        'Contacto',
        max_length=200,
        blank=True
    )
    phone = models.CharField(
        'Teléfono',
        max_length=50,
        blank=True
    )
    email = models.EmailField(
        'Email',
        blank=True
    )
    address = models.TextField(
        'Dirección',
        blank=True
    )
    cuit = models.CharField(
        'CUIT',
        max_length=20,
        blank=True
    )
    notes = models.TextField(
        'Notas',
        blank=True
    )
    is_active = models.BooleanField(
        'Activo',
        default=True
    )
    created_at = models.DateTimeField(
        'Fecha de Creación',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Purchase(models.Model):
    """Purchase order model."""
    
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('ordered', 'Pedido'),
        ('received', 'Recibido'),
        ('cancelled', 'Cancelado'),
    ]
    
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchases',
        verbose_name='Proveedor'
    )
    order_number = models.CharField(
        'Número de Orden',
        max_length=50,
        unique=True
    )
    status = models.CharField(
        'Estado',
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    order_date = models.DateField(
        'Fecha de Pedido',
        null=True,
        blank=True
    )
    received_date = models.DateField(
        'Fecha de Recepción',
        null=True,
        blank=True
    )
    subtotal = models.DecimalField(
        'Subtotal',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    tax_percent = models.DecimalField(
        'IVA (%)',
        max_digits=5,
        decimal_places=2,
        default=Decimal('21.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    tax = models.DecimalField(
        'IVA ($)',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total = models.DecimalField(
        'Total',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    notes = models.TextField(
        'Notas',
        blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='purchases',
        verbose_name='Creado por'
    )
    created_at = models.DateTimeField(
        'Fecha de Creación',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'Última Actualización',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.order_number} - {self.supplier.name}'


class PurchaseItem(models.Model):
    """Item in a purchase order."""
    
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Compra'
    )
    product = models.ForeignKey(
        'stocks.Product',
        on_delete=models.PROTECT,
        related_name='purchase_items',
        verbose_name='Producto'
    )
    packaging = models.ForeignKey(
        'stocks.ProductPackaging',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='purchase_items',
        verbose_name='Empaque',
        help_text='Si se indica, quantity es cantidad de este empaque (bulto/display/unidad). Si es null, quantity es en unidades base.',
    )
    quantity = models.PositiveIntegerField(
        'Cantidad',
        validators=[MinValueValidator(1)],
        help_text='Cantidad expresada en la unidad del empaque seleccionado (o unidades base si no hay empaque).',
    )
    unit_cost = models.DecimalField(
        'Costo Unitario',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Costo por unidad del empaque seleccionado (ej: costo del bulto si packaging es bulto).',
    )
    sale_price = models.DecimalField(
        'Precio de Venta',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Si se completa, actualiza el precio de venta del producto al recibir'
    )
    subtotal = models.DecimalField(
        'Subtotal',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    received_quantity = models.PositiveIntegerField(
        'Cantidad Recibida',
        default=0
    )
    
    class Meta:
        verbose_name = 'Ítem de Compra'
        verbose_name_plural = 'Ítems de Compra'
    
    def __str__(self):
        return f'{self.product.name} x {self.quantity}'
    
    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
