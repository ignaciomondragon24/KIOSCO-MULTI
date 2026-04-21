"""
Granel Models - Carameleras, depósito de bultos, aperturas, ventas y auditorías.

Los modelos legacy (BulkToGranelTransfer, CarameleraComponent, ShrinkageAudit)
se mantienen para no romper migraciones existentes, pero ya no reciben nuevas
funcionalidades.
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
import math

# StockBatch re-exportado para compatibilidad con código legacy
from stocks.models import StockBatch  # noqa: F401


# ============================================================
# NUEVOS MODELOS
# ============================================================

class ProductoDeposito(models.Model):
    """
    Bulto cerrado en depósito: bolsa de gomitas, caja de caramelos, etc.
    Representa el inventario de origen antes de abrir hacia una caramelera.
    """
    nombre = models.CharField('Nombre', max_length=200)
    marca = models.CharField('Marca', max_length=200, blank=True)
    costo_bulto = models.DecimalField(
        'Costo del Bulto ($)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Cuánto costó la bolsa/bulto completa'
    )
    gramos_por_bulto = models.DecimalField(
        'Gramos por Bulto (g)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Cuántos gramos tiene cada bolsa'
    )
    stock_unidades = models.IntegerField(
        'Stock (unidades)',
        default=0,
        help_text='Cuántas bolsas quedan en depósito'
    )
    is_active = models.BooleanField('Activo', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Producto Depósito'
        verbose_name_plural = 'Productos Depósito'
        ordering = ['nombre']

    def __str__(self):
        marca_str = f' ({self.marca})' if self.marca else ''
        return f'{self.nombre}{marca_str}'

    @property
    def costo_por_gramo(self):
        """Costo por gramo calculado del bulto."""
        if self.gramos_por_bulto and self.gramos_por_bulto > 0:
            return (self.costo_bulto / self.gramos_por_bulto).quantize(Decimal('0.000001'))
        return Decimal('0')


class Caramelera(models.Model):
    """
    Contenedor de golosinas mezcladas. Mantiene su propio stock en gramos
    y el costo ponderado que se recalcula en cada apertura de bulto.
    """
    nombre = models.CharField('Nombre', max_length=200)
    productos_autorizados = models.ManyToManyField(
        'stocks.Product',
        blank=True,
        limit_choices_to={'es_deposito_caramelera': True},
        verbose_name='Productos Autorizados',
        help_text='Productos del inventario marcados como "para caramelera" que pueden entrar en este mix'
    )
    precio_100g = models.DecimalField(
        'Precio por 100g ($)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    precio_cuarto = models.DecimalField(
        'Precio por Kilo Oferta ($)',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        help_text='Precio por kilo. Se aplica desde 250g en adelante por regla de tres.'
    )
    stock_gramos_actual = models.DecimalField(
        'Stock Actual (g)',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    costo_ponderado_gramo = models.DecimalField(
        'Costo Ponderado por Gramo ($/g)',
        max_digits=12,
        decimal_places=6,
        default=Decimal('0'),
        help_text='Costo promedio ponderado, recalculado en cada apertura'
    )
    is_active = models.BooleanField('Activa', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Caramelera'
        verbose_name_plural = 'Carameleras'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def save(self, **kwargs):
        super().save(**kwargs)
        # Sincronizar precios y nombre al producto POS vinculado
        self.producto_pos.filter(is_granel=True).update(
            name=self.nombre,
            sale_price=self.precio_100g,
            sale_price_250g=self.precio_cuarto,
            is_active=self.is_active,
        )

    @property
    def precio_por_gramo(self):
        if self.precio_100g > 0:
            return (self.precio_100g / Decimal('100')).quantize(Decimal('0.000001'))
        return Decimal('0')

    def calcular_precio(self, gramos):
        """
        Calcula el precio de venta para una cantidad de gramos.
        < 250g → proporcional: (gramos / 100) × precio_100g.
        >= 250g con precio_cuarto (kilo oferta) > 0 → regla de tres: (gramos / 1000) × precio_cuarto.
        >= 250g sin precio_cuarto → proporcional al precio/100g.
        """
        gramos = Decimal(str(gramos))
        if self.precio_cuarto > 0 and gramos >= Decimal('250'):
            return (gramos / Decimal('1000')) * self.precio_cuarto
        return (gramos / Decimal('100')) * self.precio_100g

    @property
    def margen_100g(self):
        """Margen porcentual estimado sobre 100g al precio de venta."""
        if self.precio_100g > 0 and self.costo_ponderado_gramo > 0:
            costo_100g = self.costo_ponderado_gramo * Decimal('100')
            margen = ((self.precio_100g - costo_100g) / self.precio_100g * Decimal('100'))
            return margen.quantize(Decimal('0.01'))
        return Decimal('0')


class AperturaBulto(models.Model):
    """
    Log de cada apertura de una bolsa del depósito hacia una caramelera.
    Captura el snapshot completo antes/después para trazabilidad.
    """
    caramelera = models.ForeignKey(
        Caramelera,
        on_delete=models.CASCADE,
        related_name='aperturas',
        verbose_name='Caramelera'
    )
    producto = models.ForeignKey(
        'stocks.Product',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='aperturas_caramelera',
        verbose_name='Producto'
    )
    gramos_agregados = models.DecimalField(
        'Gramos Agregados',
        max_digits=10,
        decimal_places=2
    )
    costo_por_gramo_al_abrir = models.DecimalField(
        'Costo/g al Abrir',
        max_digits=12,
        decimal_places=6
    )
    costo_ponderado_antes = models.DecimalField(
        'Costo Ponderado Antes ($/g)',
        max_digits=12,
        decimal_places=6
    )
    costo_ponderado_despues = models.DecimalField(
        'Costo Ponderado Después ($/g)',
        max_digits=12,
        decimal_places=6
    )
    stock_gramos_antes = models.DecimalField(
        'Stock Gramos Antes',
        max_digits=12,
        decimal_places=2
    )
    stock_gramos_despues = models.DecimalField(
        'Stock Gramos Después',
        max_digits=12,
        decimal_places=2
    )
    unidades_restantes_deposito = models.IntegerField(
        'Unidades Restantes en Depósito',
        help_text='Snapshot del stock del depósito después de abrir'
    )
    abierto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aperturas_bulto',
        verbose_name='Abierto por'
    )
    abierto_en = models.DateTimeField(auto_now_add=True)
    notas = models.TextField('Notas', blank=True)

    class Meta:
        verbose_name = 'Apertura de Bulto'
        verbose_name_plural = 'Aperturas de Bulto'
        ordering = ['-abierto_en']

    def __str__(self):
        return (
            f'{self.producto.name} → {self.caramelera.nombre} '
            f'({self.gramos_agregados}g)'
        )


class VentaGranel(models.Model):
    """
    Registro de cada venta granel completada en el POS.
    Permite calcular el margen real acumulado por caramelera.
    """
    TIPO_CHOICES = [
        ('kilo', 'Precio por kilo'),
        ('cuarto', '1/4 kg (250g)'),
        ('libre', 'Gramos libres'),
    ]

    caramelera = models.ForeignKey(
        Caramelera,
        on_delete=models.PROTECT,
        related_name='ventas',
        verbose_name='Caramelera'
    )
    gramos_vendidos = models.DecimalField('Gramos Vendidos', max_digits=10, decimal_places=2)
    tipo_venta = models.CharField(
        'Tipo de Venta',
        max_length=10,
        choices=TIPO_CHOICES,
        default='libre'
    )
    precio_cobrado = models.DecimalField('Precio Cobrado ($)', max_digits=10, decimal_places=2)
    costo_gramo_al_vender = models.DecimalField(
        'Costo/g al Vender',
        max_digits=12,
        decimal_places=6,
        help_text='Snapshot del costo ponderado al momento de la venta'
    )
    costo_total = models.DecimalField('Costo Total ($)', max_digits=10, decimal_places=2)
    ganancia = models.DecimalField('Ganancia ($)', max_digits=10, decimal_places=2)
    vendido_en = models.DateTimeField(auto_now_add=True)
    pos_transaction_id = models.IntegerField(
        'ID Transacción POS',
        null=True,
        blank=True,
        help_text='Referencia a la transacción POS que originó esta venta'
    )

    class Meta:
        verbose_name = 'Venta Granel'
        verbose_name_plural = 'Ventas Granel'
        ordering = ['-vendido_en']

    def __str__(self):
        return f'{self.caramelera.nombre}: {self.gramos_vendidos}g — ${self.precio_cobrado}'


class AuditoriaCaramelera(models.Model):
    """
    Auditoría física de una caramelera: comparar stock sistema vs peso real en balanza.
    Registra la diferencia (merma) y opcionalmente ajusta el stock.
    """
    caramelera = models.ForeignKey(
        Caramelera,
        on_delete=models.CASCADE,
        related_name='auditorias',
        verbose_name='Caramelera'
    )
    stock_sistema_gramos = models.DecimalField(
        'Stock Sistema (g)',
        max_digits=12,
        decimal_places=2
    )
    peso_real_balanza_gramos = models.DecimalField(
        'Peso Real Balanza (g)',
        max_digits=12,
        decimal_places=2
    )
    diferencia_gramos = models.DecimalField(
        'Diferencia (g)',
        max_digits=12,
        decimal_places=2,
        help_text='sistema - real; positivo = merma'
    )
    porcentaje_merma = models.DecimalField(
        'Merma %',
        max_digits=5,
        decimal_places=2
    )
    ajuste_aplicado = models.BooleanField(
        'Ajuste Aplicado',
        default=True,
        help_text='Si se actualizó el stock de la caramelera al peso real'
    )
    motivo = models.CharField('Motivo', max_length=200, blank=True)
    auditado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auditorias_caramelera',
        verbose_name='Auditado por'
    )
    auditado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Auditoría de Caramelera'
        verbose_name_plural = 'Auditorías de Caramelera'
        ordering = ['-auditado_en']

    def __str__(self):
        return (
            f'Auditoría {self.caramelera.nombre}: '
            f'dif. {self.diferencia_gramos}g ({self.porcentaje_merma}%)'
        )


# ============================================================
# MODELOS LEGACY — se mantienen para no romper migraciones
# ============================================================

class BulkToGranelTransfer(models.Model):
    """LEGACY — Log de transferencias del sistema anterior. No usar para nuevas operaciones."""
    bulk_product = models.ForeignKey(
        'stocks.Product',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='granel_transfers_out',
        verbose_name='Producto Bulto (origen)'
    )
    granel_product = models.ForeignKey(
        'stocks.Product',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='granel_transfers_in',
        verbose_name='Producto Granel (destino)'
    )
    source_batch = models.ForeignKey(
        StockBatch,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='granel_transfers',
        verbose_name='Lote Origen'
    )
    grams_transferred = models.DecimalField('Gramos Transferidos', max_digits=10, decimal_places=2)
    bulk_cost_per_gram = models.DecimalField('Costo por Gramo (bulto)', max_digits=12, decimal_places=4)
    granel_stock_before = models.DecimalField('Stock Granel Antes (g)', max_digits=12, decimal_places=2)
    granel_weighted_cost_before = models.DecimalField('Costo Ponderado Antes', max_digits=12, decimal_places=4)
    granel_stock_after = models.DecimalField('Stock Granel Después (g)', max_digits=12, decimal_places=2)
    granel_weighted_cost_after = models.DecimalField('Costo Ponderado Después', max_digits=12, decimal_places=4)
    transferred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granel_transfers',
        verbose_name='Transferido por'
    )
    transferred_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField('Notas', blank=True)

    class Meta:
        verbose_name = 'Transferencia Bulto a Granel (legacy)'
        verbose_name_plural = 'Transferencias Bulto a Granel (legacy)'
        ordering = ['-transferred_at']

    def __str__(self):
        return (f'{self.bulk_product.name} -> {self.granel_product.name} '
                f'({self.grams_transferred}g)')


class CarameleraComponent(models.Model):
    """LEGACY — Componentes del sistema anterior. No usar para nuevas operaciones."""
    caramelera = models.ForeignKey(
        'stocks.Product',
        on_delete=models.CASCADE,
        related_name='components',
        limit_choices_to={'is_granel': True},
        verbose_name='Caramelera',
    )
    bulk_product = models.ForeignKey(
        'stocks.Product',
        on_delete=models.CASCADE,
        related_name='used_in_carameleras',
        verbose_name='Producto Bulto',
    )
    proportion_grams = models.DecimalField(
        'Gramos en receta',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0')
    )
    notes = models.CharField('Notas', max_length=200, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Componente de Caramelera (legacy)'
        verbose_name_plural = 'Componentes de Caramelera (legacy)'
        unique_together = ('caramelera', 'bulk_product')
        ordering = ['bulk_product__name']

    def __str__(self):
        return f'{self.bulk_product.name} → {self.caramelera.name}'


class ShrinkageAudit(models.Model):
    """LEGACY — Auditorías del sistema anterior. No usar para nuevas operaciones."""
    REASON_CHOICES = [
        ('picoteo', 'Picoteo/Degustación'),
        ('humedad', 'Humedad/Evaporación'),
        ('pesaje', 'Error de Pesaje'),
        ('otro', 'Otro'),
    ]
    granel_product = models.ForeignKey(
        'stocks.Product',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='shrinkage_audits',
        verbose_name='Producto Granel'
    )
    theoretical_grams = models.DecimalField('Stock Teórico (g)', max_digits=12, decimal_places=2)
    actual_grams = models.DecimalField('Peso Real (g)', max_digits=12, decimal_places=2)
    shrinkage_grams = models.DecimalField('Diferencia (g)', max_digits=12, decimal_places=2)
    shrinkage_percent = models.DecimalField('Merma %', max_digits=5, decimal_places=2)
    reason = models.CharField('Motivo', max_length=20, choices=REASON_CHOICES, default='otro')
    notes = models.TextField('Notas', blank=True)
    stock_adjusted = models.BooleanField('Stock Ajustado', default=False)
    audited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='shrinkage_audits',
        verbose_name='Auditado por'
    )
    audited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Auditoría de Merma (legacy)'
        verbose_name_plural = 'Auditorías de Merma (legacy)'
        ordering = ['-audited_at']

    def __str__(self):
        return (f'Merma {self.granel_product.name}: '
                f'{self.shrinkage_grams}g ({self.shrinkage_percent}%)')
