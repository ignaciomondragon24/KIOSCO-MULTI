"""
Sales Models (Legacy)
This module is kept for backward compatibility.
New sales should use the POS module.
"""
from django.db import models
from django.conf import settings
from decimal import Decimal


class Sale(models.Model):
    """Legacy sale model."""
    
    STATUS_CHOICES = [
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
        ('refunded', 'Reembolsada'),
    ]
    
    sale_number = models.CharField(
        'Número de Venta',
        max_length=50,
        unique=True
    )
    date = models.DateTimeField(
        'Fecha',
        auto_now_add=True
    )
    status = models.CharField(
        'Estado',
        max_length=20,
        choices=STATUS_CHOICES,
        default='completed'
    )
    subtotal = models.DecimalField(
        'Subtotal',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    discount = models.DecimalField(
        'Descuento',
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
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='legacy_sales',
        verbose_name='Cajero'
    )
    
    class Meta:
        verbose_name = 'Venta (Legacy)'
        verbose_name_plural = 'Ventas (Legacy)'
        ordering = ['-date']
    
    def __str__(self):
        return self.sale_number


class SaleItem(models.Model):
    """Legacy sale item model."""
    
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Venta'
    )
    product = models.ForeignKey(
        'stocks.Product',
        on_delete=models.SET_NULL,
        null=True,
        related_name='legacy_sale_items',
        verbose_name='Producto'
    )
    product_name = models.CharField(
        'Nombre del Producto',
        max_length=200
    )
    quantity = models.PositiveIntegerField(
        'Cantidad'
    )
    unit_price = models.DecimalField(
        'Precio Unitario',
        max_digits=10,
        decimal_places=2
    )
    subtotal = models.DecimalField(
        'Subtotal',
        max_digits=12,
        decimal_places=2
    )
    
    class Meta:
        verbose_name = 'Ítem de Venta (Legacy)'
        verbose_name_plural = 'Ítems de Venta (Legacy)'
    
    def __str__(self):
        return f'{self.product_name} x {self.quantity}'
