"""
Promotions Models
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils import timezone


class PromotionGroup(models.Model):
    """
    Grupo de promociones enlazadas. Cuando varias promos comparten un grupo,
    el motor las trata como UNA sola promo virtual: la lista de productos se
    une, y se aplica la lógica de la promo de mayor prioridad del grupo.

    Caso de uso: dos promos "4 x $1000" sobre productos distintos. Si el
    cliente lleva 2 de cada una, las 4 unidades sumadas activan el precio
    promocional como si fuera una única promo.
    """
    name = models.CharField('Nombre', max_length=200, unique=True)
    description = models.TextField('Descripción', blank=True)
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)

    class Meta:
        verbose_name = 'Grupo de Promociones'
        verbose_name_plural = 'Grupos de Promociones'
        ordering = ['name']

    def __str__(self):
        return self.name


class Promotion(models.Model):
    """Promotion model."""
    
    PROMO_TYPES = [
        ('nxm', 'NxM (Ej: 2x1, 3x2)'),
        ('nx_fixed_price', 'N por Precio Fijo (Ej: 2x$500, 3x$1000)'),
        ('quantity_discount', 'Descuento por Cantidad'),
        ('combo', 'Combo'),
        ('second_unit', 'Segunda Unidad con Descuento'),
        ('simple_discount', 'Descuento Porcentual'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('active', 'Activa'),
        ('paused', 'Pausada'),
        ('finished', 'Finalizada'),
    ]
    
    name = models.CharField(
        'Nombre',
        max_length=200
    )
    description = models.TextField(
        'Descripción',
        blank=True
    )
    promo_type = models.CharField(
        'Tipo de Promoción',
        max_length=30,
        choices=PROMO_TYPES
    )
    status = models.CharField(
        'Estado',
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    
    # Validity
    start_date = models.DateField(
        'Fecha de Inicio',
        null=True,
        blank=True
    )
    end_date = models.DateField(
        'Fecha de Fin',
        null=True,
        blank=True
    )
    
    # Priority
    priority = models.PositiveIntegerField(
        'Prioridad',
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text='Mayor número = Mayor prioridad'
    )
    is_combinable = models.BooleanField(
        'Combinable',
        default=True,
        help_text='¿Se puede combinar con otras promociones?'
    )

    PACKAGING_SCOPE_CHOICES = [
        ('unit', 'Solo unidad suelta'),
        ('display', 'Solo display / paquete'),
        ('bulk', 'Solo bulto / caja'),
        ('any', 'Cualquier empaque'),
    ]
    applies_to_packaging_type = models.CharField(
        'Empaque al que aplica',
        max_length=20,
        choices=PACKAGING_SCOPE_CHOICES,
        default='unit',
        help_text='Empaque al que se le aplica la promo. Permite precios distintos por unidad y por display.'
    )

    # Linking: dos o más promos en el mismo grupo se tratan como una sola
    # virtual al momento de calcular descuentos en el carrito.
    group = models.ForeignKey(
        PromotionGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotions',
        verbose_name='Grupo enlazado',
        help_text='Promociones del mismo grupo suman cantidades como si fueran una sola.'
    )
    
    # Active days
    monday = models.BooleanField('Lunes', default=True)
    tuesday = models.BooleanField('Martes', default=True)
    wednesday = models.BooleanField('Miércoles', default=True)
    thursday = models.BooleanField('Jueves', default=True)
    friday = models.BooleanField('Viernes', default=True)
    saturday = models.BooleanField('Sábado', default=True)
    sunday = models.BooleanField('Domingo', default=True)
    
    # Time restrictions
    hour_start = models.TimeField(
        'Hora Inicio',
        null=True,
        blank=True
    )
    hour_end = models.TimeField(
        'Hora Fin',
        null=True,
        blank=True
    )
    
    # Conditions
    min_quantity = models.PositiveIntegerField(
        'Cantidad Mínima',
        default=1,
        help_text='Cantidad mínima de productos para aplicar'
    )
    min_purchase_amount = models.DecimalField(
        'Monto Mínimo de Compra',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    max_uses_per_sale = models.PositiveIntegerField(
        'Máximo Usos por Venta',
        default=0,
        help_text='0 = Sin límite'
    )
    
    # NxM Configuration (Ej: quantity_required=2, quantity_charged=1 → 2x1)
    quantity_required = models.PositiveIntegerField(
        'Cantidad Requerida',
        default=2,
        help_text='Ej: 2 para promoción 2x1'
    )
    quantity_charged = models.PositiveIntegerField(
        'Cantidad Cobrada',
        default=1,
        help_text='Ej: 1 para promoción 2x1'
    )
    
    # Discount configuration
    discount_percent = models.DecimalField(
        'Descuento (%)',
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    discount_amount = models.DecimalField(
        'Descuento Fijo ($)',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    final_price = models.DecimalField(
        'Precio Final (Combos)',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Precio final del combo'
    )
    second_unit_discount = models.DecimalField(
        'Descuento 2da Unidad (%)',
        max_digits=5,
        decimal_places=2,
        default=Decimal('50.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    
    # Products
    products = models.ManyToManyField(
        'stocks.Product',
        through='PromotionProduct',
        related_name='promotions',
        verbose_name='Productos'
    )
    
    # Statistics
    usages = models.PositiveIntegerField(
        'Usos',
        default=0
    )
    
    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_promotions',
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
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'
        ordering = ['-priority', '-created_at']
    
    def __str__(self):
        return f'{self.name} ({self.get_promo_type_display()})'
    
    def is_valid_today(self):
        """Check if promotion is valid today."""
        today = timezone.now().date()
        weekday = today.weekday()
        
        # Check status
        if self.status != 'active':
            return False
        
        # Check dates
        if self.start_date and today < self.start_date:
            return False
        if self.end_date and today > self.end_date:
            return False
        
        # Check day of week
        day_checks = [
            self.monday, self.tuesday, self.wednesday,
            self.thursday, self.friday, self.saturday, self.sunday
        ]
        if not day_checks[weekday]:
            return False
        
        # Check time (use local time to match TimeField values)
        now = timezone.localtime(timezone.now()).time()
        if self.hour_start and now < self.hour_start:
            return False
        if self.hour_end and now > self.hour_end:
            return False
        
        return True


class PromotionProduct(models.Model):
    """Product in a promotion."""
    
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name='promotion_products'
    )
    product = models.ForeignKey(
        'stocks.Product',
        on_delete=models.CASCADE,
        related_name='product_promotions'
    )
    
    class Meta:
        verbose_name = 'Producto en Promoción'
        verbose_name_plural = 'Productos en Promoción'
        unique_together = ('promotion', 'product')
    
    def __str__(self):
        return f'{self.product.name} en {self.promotion.name}'
