"""
Stocks Models - Products, Categories, Units of Measure, Stock Movements
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
import random
import string


class ProductCategory(models.Model):
    """Product category model."""
    
    name = models.CharField(
        'Nombre',
        max_length=100,
        unique=True
    )
    description = models.TextField(
        'Descripción',
        blank=True
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories',
        verbose_name='Categoría Padre'
    )
    default_margin_percent = models.DecimalField(
        'Margen por defecto (%)',
        max_digits=8,
        decimal_places=2,
        default=30.00,
        validators=[MinValueValidator(Decimal('0'))]
    )
    color = models.CharField(
        'Color',
        max_length=7,
        default='#3498db',
        help_text='Código hexadecimal del color'
    )
    is_active = models.BooleanField(
        'Activo',
        default=True
    )
    created_at = models.DateTimeField(
        'Fecha de creación',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'Última actualización',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['name']
    
    def __str__(self):
        if self.parent:
            return f'{self.parent.name} > {self.name}'
        return self.name
    
    @property
    def full_path(self):
        """Return full category path."""
        if self.parent:
            return f'{self.parent.full_path} > {self.name}'
        return self.name
    
    @property
    def product_count(self):
        """Return number of products in this category."""
        return self.products.filter(is_active=True).count()


class UnitOfMeasure(models.Model):
    """Unit of measure model."""
    
    UNIT_TYPES = [
        ('unit', 'Unidad'),
        ('weight', 'Peso'),
        ('volume', 'Volumen'),
        ('length', 'Longitud'),
    ]
    
    name = models.CharField(
        'Nombre',
        max_length=50,
        unique=True
    )
    abbreviation = models.CharField(
        'Abreviatura',
        max_length=10
    )
    symbol = models.CharField(
        'Símbolo',
        max_length=5,
        blank=True
    )
    unit_type = models.CharField(
        'Tipo',
        max_length=20,
        choices=UNIT_TYPES,
        default='unit'
    )
    is_active = models.BooleanField(
        'Activo',
        default=True
    )
    
    class Meta:
        verbose_name = 'Unidad de Medida'
        verbose_name_plural = 'Unidades de Medida'
        ordering = ['name']
    
    def __str__(self):
        return f'{self.name} ({self.abbreviation})'


class Product(models.Model):
    """Product model."""
    
    sku = models.CharField(
        'SKU',
        max_length=50,
        unique=True,
        blank=True
    )
    barcode = models.CharField(
        'Código de Barras',
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )
    name = models.CharField(
        'Nombre',
        max_length=200
    )
    description = models.TextField(
        'Descripción',
        blank=True
    )
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Categoría'
    )
    unit_of_measure = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Unidad de Medida'
    )
    
    # Prices
    purchase_price = models.DecimalField(
        'Precio de Compra',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    sale_price = models.DecimalField(
        'Precio de Venta',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    sale_price_250g = models.DecimalField(
        'Precio por 250g',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        help_text='Precio de venta por 250g (1/4 kg)'
    )
    cost_price = models.DecimalField(
        'Costo Promedio',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Stock
    current_stock = models.DecimalField(
        'Stock Actual',
        max_digits=12,
        decimal_places=3,
        default=0
    )
    min_stock = models.PositiveIntegerField(
        'Stock Mínimo',
        default=0,
        help_text='Alerta cuando el stock llegue a este nivel'
    )
    max_stock = models.PositiveIntegerField(
        'Stock Máximo',
        null=True,
        blank=True
    )
    
    # Additional info
    location = models.CharField(
        'Ubicación',
        max_length=50,
        blank=True,
        help_text='Ubicación física en el almacén'
    )
    image = models.ImageField(
        'Imagen',
        upload_to='products/',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        'Activo',
        default=True
    )
    is_quick_access = models.BooleanField(
        'Acceso Rápido POS',
        default=False,
        help_text='Mostrar como botón de acceso rápido en el POS'
    )
    quick_access_color = models.CharField(
        'Color Acceso Rápido',
        max_length=7,
        default='#3498db',
        help_text='Código hexadecimal del color para botón POS'
    )
    quick_access_icon = models.CharField(
        'Icono Acceso Rápido',
        max_length=50,
        default='fa-box',
        help_text='Clase de icono Font Awesome'
    )
    quick_access_position = models.PositiveIntegerField(
        'Posición Acceso Rápido',
        default=0
    )
    
    # Bulk / Weight selling options
    # is_bulk: producto que se VENDE por peso (ej: fiambre, queso, gomitas)
    # is_granel: producto COMODÍN que RECIBE stock de bultos abiertos (ej: caramelera)
    # Un producto puede tener ambos en True (caramelera que se vende por peso)
    # weight_per_unit_grams: para BULTOS (cuántos gramos tiene cada unidad del bulto cerrado)
    # granel_price_weight_grams: para CARAMELERAS (el sale_price es "cada X gramos")
    is_bulk = models.BooleanField(
        'Producto a Granel',
        default=False,
        help_text='Productos que se venden por peso (gomitas, fiambres, etc)'
    )
    allow_sell_by_amount = models.BooleanField(
        'Permite Venta por Monto',
        default=False,
        help_text='Permite ingresar "$500 de gomitas" y calcular la cantidad'
    )
    bulk_unit = models.CharField(
        'Unidad de Granel',
        max_length=10,
        choices=[
            ('kg', 'Kilogramo'),
            ('g', 'Gramo'),
            ('lt', 'Litro'),
            ('ml', 'Mililitro'),
        ],
        default='kg',
        blank=True
    )

    # Granel (candy jar / caramelera) fields
    is_granel = models.BooleanField(
        'Producto Comodín Granel',
        default=False,
        help_text='Producto comodín que recibe stock de bultos abiertos (ej: Gomitas Surtidas)'
    )
    granel_price_weight_grams = models.PositiveIntegerField(
        'Precio por X gramos',
        default=100,
        help_text='El sale_price es "por cada X gramos" (ej: 100 = $2500/100g)'
    )
    weighted_avg_cost_per_gram = models.DecimalField(
        'Costo Ponderado por Gramo',
        max_digits=12,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text='Costo promedio ponderado por gramo, calculado automáticamente'
    )
    weight_per_unit_grams = models.DecimalField(
        'Peso por Unidad (gramos)',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        blank=True,
        help_text='Para bultos: gramos que contiene cada unidad (ej: 2000 para bolsa de 2kg)'
    )

    # Caramelera deposit product
    es_deposito_caramelera = models.BooleanField(
        'Es producto para caramelera',
        default=False,
        help_text='Marca este producto como un bulto que puede abrirse en una caramelera'
    )
    marca = models.CharField(
        'Marca',
        max_length=200,
        blank=True,
        help_text='Marca del producto (útil para diferenciar bultos en carameleras)'
    )

    granel_caramelera = models.ForeignKey(
        'granel.Caramelera',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='producto_pos',
        verbose_name='Caramelera vinculada',
        help_text='Caramelera del sistema granel asociada a este producto POS'
    )

    # Parent-child relationship for presentations
    parent_product = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_products',
        verbose_name='Producto Padre',
        help_text='Para cajas/bultos, indica el producto individual que contiene'
    )
    units_per_package = models.PositiveIntegerField(
        'Unidades por Paquete',
        default=1,
        help_text='Cuántas unidades del producto hijo contiene (ej: 24 para caja de 24)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        'Fecha de creación',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'Última actualización',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['barcode']),
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['current_stock']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Auto-generate SKU if not provided
        if not self.sku:
            self.sku = self.generate_sku()
        # Empty barcode must be None for PostgreSQL unique constraint
        if not self.barcode:
            self.barcode = None
        # Ensure weight_per_unit_grams is never None (PostgreSQL NOT NULL)
        if self.weight_per_unit_grams is None:
            self.weight_per_unit_grams = Decimal('0.00')
        super().save(*args, **kwargs)
    
    def generate_sku(self):
        """Generate a unique SKU."""
        prefix = 'PRD'
        suffix = ''.join(random.choices(string.digits, k=6))
        return f'{prefix}{suffix}'
    
    @property
    def costo_por_gramo(self):
        """Para productos de depósito de caramelera: costo por gramo.
        Usa cost_price (lo que el usuario ingresa en el formulario) con fallback a purchase_price.
        """
        precio = self.cost_price or self.purchase_price
        if self.weight_per_unit_grams and self.weight_per_unit_grams > 0 and precio:
            return (precio / self.weight_per_unit_grams).quantize(Decimal('0.000001'))
        return Decimal('0')

    @property
    def margin_percent(self):
        """Calculate profit margin percentage using weighted average cost."""
        cost = self.cost_price or self.purchase_price
        if cost and cost > 0:
            margin = ((self.sale_price - cost) / cost) * 100
            return round(margin, 2)
        return 0

    @property
    def profit(self):
        """Calculate profit per unit using weighted average cost."""
        cost = self.cost_price or self.purchase_price
        return self.sale_price - cost
    
    @property
    def is_low_stock(self):
        """Check if stock is below minimum."""
        return self.current_stock <= self.min_stock
    
    @property
    def stock_value(self):
        """Calculate total stock value at cost."""
        return self.current_stock * self.cost_price
    
    @property
    def stock_value_sale(self):
        """Calculate total stock value at sale price."""
        return self.current_stock * self.sale_price
    
    @property
    def has_children(self):
        """Check if this product has child products (is a container/package)."""
        return self.child_products.exists()
    
    @property
    def is_child(self):
        """Check if this product is a child of another product."""
        return self.parent_product is not None
    
    def calculate_quantity_for_amount(self, amount):
        """
        Calculate quantity that can be purchased for a given amount.
        Used for bulk products sold by weight.
        Returns: (quantity, actual_total)
        """
        if self.sale_price <= 0:
            return Decimal('0'), Decimal('0')
        
        quantity = Decimal(str(amount)) / self.sale_price
        
        # Round to 3 decimals for weight products
        if self.is_bulk:
            quantity = quantity.quantize(Decimal('0.001'))
        else:
            quantity = quantity.quantize(Decimal('1'))
        
        actual_total = quantity * self.sale_price
        return quantity, actual_total
    
    def get_unit_display(self):
        """Get display string for the unit."""
        if self.is_bulk and self.bulk_unit:
            units = {
                'kg': 'kg',
                'g': 'gr',
                'lt': 'lt',
                'ml': 'ml',
            }
            return units.get(self.bulk_unit, 'unid')
        elif self.unit_of_measure:
            return self.unit_of_measure.abbreviation
        return 'unid'
    
    def convert_to_child_units(self, parent_quantity):
        """
        Convert parent quantity to child units.
        e.g.: 2 boxes of 24 = 48 units
        """
        if self.has_children:
            first_child = self.child_products.first()
            if first_child:
                return parent_quantity * self.units_per_package
        return parent_quantity
    
    def convert_to_parent_units(self, child_quantity):
        """
        Convert child quantity to parent units.
        e.g.: 48 units = 2 boxes of 24
        """
        if self.parent_product and self.parent_product.units_per_package > 0:
            return child_quantity / self.parent_product.units_per_package
        return child_quantity


class StockMovement(models.Model):
    """Stock movement model."""
    
    MOVEMENT_TYPES = [
        ('purchase', 'Compra'),
        ('sale', 'Venta'),
        ('adjustment_in', 'Ajuste Entrada'),
        ('adjustment_out', 'Ajuste Salida'),
        ('transfer_in', 'Transferencia Entrada'),
        ('transfer_out', 'Transferencia Salida'),
        ('return_in', 'Devolución Entrada'),
        ('return_out', 'Devolución Salida'),
    ]
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_movements',
        verbose_name='Producto'
    )
    movement_type = models.CharField(
        'Tipo de Movimiento',
        max_length=20,
        choices=MOVEMENT_TYPES
    )
    quantity = models.DecimalField(
        'Cantidad',
        max_digits=12,
        decimal_places=3
    )
    unit_cost = models.DecimalField(
        'Costo Unitario',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    stock_before = models.DecimalField(
        'Stock Antes',
        max_digits=12,
        decimal_places=3,
        default=0
    )
    stock_after = models.DecimalField(
        'Stock Después',
        max_digits=12,
        decimal_places=3,
        default=0
    )
    reference = models.CharField(
        'Referencia',
        max_length=100,
        blank=True,
        help_text='Ej: Compra #123, Venta #456'
    )
    reference_id = models.PositiveIntegerField(
        'ID Referencia',
        null=True,
        blank=True
    )
    notes = models.TextField(
        'Notas',
        blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Creado por'
    )
    created_at = models.DateTimeField(
        'Fecha',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Movimiento de Stock'
        verbose_name_plural = 'Movimientos de Stock'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.get_movement_type_display()} - {self.product.name} ({self.quantity})'


class StockBatch(models.Model):
    """
    Lote de compra individual para cualquier producto.
    Cada ingreso de stock (compra, ajuste de entrada) puede generar un batch.
    Se consume por FIFO (el más antiguo primero).
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='batches',
        verbose_name='Producto'
    )
    purchase = models.ForeignKey(
        'purchase.Purchase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_batches',
        verbose_name='Compra'
    )
    supplier_name = models.CharField(
        'Proveedor',
        max_length=200,
        blank=True,
    )
    quantity_purchased = models.DecimalField(
        'Cantidad Comprada',
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    quantity_remaining = models.DecimalField(
        'Cantidad Restante',
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0'))]
    )
    purchase_price = models.DecimalField(
        'Costo Unitario',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    purchased_at = models.DateTimeField(
        'Fecha de Compra',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_stock_batches',
        verbose_name='Creado por'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField('Notas', blank=True)

    class Meta:
        verbose_name = 'Lote de Stock'
        verbose_name_plural = 'Lotes de Stock'
        ordering = ['purchased_at', 'created_at']  # FIFO order

    def __str__(self):
        return f'Lote {self.pk} - {self.product.name} ({self.quantity_remaining}/{self.quantity_purchased})'

    @property
    def is_depleted(self):
        return self.quantity_remaining <= 0

    @property
    def total_cost(self):
        return self.quantity_purchased * self.purchase_price

    @property
    def remaining_cost(self):
        """Costo del stock restante en este lote."""
        return self.quantity_remaining * self.purchase_price

    @property
    def unit_cost(self):
        """Alias para compatibilidad con código granel existente."""
        return self.purchase_price

    @unit_cost.setter
    def unit_cost(self, value):
        self.purchase_price = value

    @property
    def margin_if_sold_at_list(self):
        """Margen porcentual si se vendiera al precio de lista del producto."""
        if self.purchase_price and self.purchase_price > 0 and self.product.sale_price:
            return ((self.product.sale_price - self.purchase_price) / self.purchase_price * 100).quantize(Decimal('0.01'))
        return None

    @property
    def profit_per_unit(self):
        """Ganancia por unidad vs precio de venta."""
        if self.purchase_price and self.product.sale_price:
            diff = self.product.sale_price - self.purchase_price
            return diff.quantize(Decimal('0.01')) if diff >= 0 else Decimal('0')
        return Decimal('0')

    @property
    def loss_per_unit(self):
        """Pérdida por unidad vs precio de venta."""
        if self.purchase_price and self.product.sale_price:
            diff = self.purchase_price - self.product.sale_price
            return diff.quantize(Decimal('0.01')) if diff > 0 else Decimal('0')
        return Decimal('0')


class ProductPresentation(models.Model):
    """Product presentation (different packaging).
    # TODO: evaluar consolidación con ProductPackaging tipo 'unit'.
    # Este modelo se usa activamente en services.py (barcode lookup).
    # No eliminar sin migrar esa lógica primero.
    """
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='presentations',
        verbose_name='Producto'
    )
    name = models.CharField(
        'Nombre',
        max_length=100,
        help_text='Ej: Pack x 6, Caja x 12'
    )
    quantity = models.PositiveIntegerField(
        'Cantidad de Unidades',
        validators=[MinValueValidator(1)]
    )
    barcode = models.CharField(
        'Código de Barras',
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )
    sale_price = models.DecimalField(
        'Precio de Venta',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    is_active = models.BooleanField(
        'Activo',
        default=True
    )
    
    class Meta:
        verbose_name = 'Presentación'
        verbose_name_plural = 'Presentaciones'
        ordering = ['product', 'quantity']
    
    def __str__(self):
        return f'{self.product.name} - {self.name}'
    
    @property
    def unit_price(self):
        """Calculate unit price for this presentation."""
        if self.quantity > 0:
            return self.sale_price / self.quantity
        return Decimal('0.00')


class ProductPackaging(models.Model):
    """
    Modelo jerárquico para empaques de productos.
    Define la relación Unidad → Display → Bulto con códigos de barras anidados.
    """
    
    PACKAGING_TYPES = [
        ('unit', 'Unidad'),
        ('display', 'Display/Paquete'),
        ('bulk', 'Bulto/Caja'),
    ]
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='packagings',
        verbose_name='Producto'
    )
    packaging_type = models.CharField(
        'Tipo de Empaque',
        max_length=20,
        choices=PACKAGING_TYPES
    )
    barcode = models.CharField(
        'Código de Barras',
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text='Código de barras para este empaque'
    )
    name = models.CharField(
        'Nombre',
        max_length=100,
        help_text='Ej: Unidad, Display x 12, Bulto x 144'
    )
    
    # Cantidad de unidades base que contiene
    units_quantity = models.PositiveIntegerField(
        'Cantidad de Unidades',
        default=1,
        help_text='Cuántas unidades base contiene este empaque'
    )
    
    # Para displays: cuántas unidades tiene
    # Para bultos: cuántos displays tiene
    units_per_display = models.PositiveIntegerField(
        'Unidades por Display',
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Cuántas unidades contiene cada display'
    )
    displays_per_bulk = models.PositiveIntegerField(
        'Displays por Bulto',
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Cuántos displays contiene cada bulto'
    )
    
    # Precios
    purchase_price = models.DecimalField(
        'Precio de Compra',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    sale_price = models.DecimalField(
        'Precio de Venta',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Configuración de cálculo de ganancia
    calculate_margin_on = models.CharField(
        'Calcular Ganancia Sobre',
        max_length=20,
        choices=PACKAGING_TYPES,
        default='bulk',
        help_text='Sobre qué empaque se calcula el porcentaje de ganancia'
    )
    margin_percent = models.DecimalField(
        'Margen de Ganancia (%)',
        max_digits=8,
        decimal_places=2,
        default=Decimal('30.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    is_default = models.BooleanField(
        'Empaque por Defecto',
        default=False,
        help_text='Usar por defecto en POS'
    )
    is_active = models.BooleanField(
        'Activo',
        default=True
    )
    
    current_stock = models.DecimalField(
        'Stock Actual',
        max_digits=12,
        decimal_places=3,
        default=0
    )
    min_stock = models.PositiveIntegerField(
        'Stock Mínimo',
        default=0
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Empaque de Producto'
        verbose_name_plural = 'Empaques de Productos'
        ordering = ['product', 'packaging_type']
    
    def __str__(self):
        return f'{self.product.name} - {self.get_packaging_type_display()} ({self.name})'
    
    def save(self, *args, **kwargs):
        # Calcular units_quantity automáticamente
        if self.packaging_type == 'unit':
            self.units_quantity = 1
        elif self.packaging_type == 'display':
            self.units_quantity = self.units_per_display
        elif self.packaging_type == 'bulk':
            self.units_quantity = self.units_per_display * self.displays_per_bulk
        
        super().save(*args, **kwargs)
    
    @property
    def unit_purchase_price(self):
        """Precio de compra por unidad."""
        if self.units_quantity > 0:
            return self.purchase_price / self.units_quantity
        return Decimal('0.00')
    
    @property
    def unit_sale_price(self):
        """Precio de venta por unidad."""
        if self.units_quantity > 0:
            return self.sale_price / self.units_quantity
        return Decimal('0.00')
    
    @property
    def display_purchase_price(self):
        """Precio de compra por display."""
        if self.packaging_type == 'bulk' and self.displays_per_bulk > 0:
            return self.purchase_price / self.displays_per_bulk
        elif self.packaging_type == 'display':
            return self.purchase_price
        return self.purchase_price
    
    @property
    def display_sale_price(self):
        """Precio de venta por display."""
        if self.packaging_type == 'bulk' and self.displays_per_bulk > 0:
            return self.sale_price / self.displays_per_bulk
        elif self.packaging_type == 'display':
            return self.sale_price
        return self.sale_price
    
    def calculate_total_units(self, quantity):
        """Calcula el total de unidades base."""
        return quantity * self.units_quantity
    
    def calculate_displays(self, quantity):
        """Calcula cantidad de displays (para bultos)."""
        if self.packaging_type == 'bulk':
            return quantity * self.displays_per_bulk
        return 0
    
    def calculate_prices_from_margin(self):
        """
        Calcula los precios de venta basado en el margen configurado.
        Retorna dict con precios por unidad, display y bulto.
        """
        if self.purchase_price <= 0:
            return None
        
        margin_multiplier = 1 + (self.margin_percent / 100)
        
        # Precio de venta del bulto
        bulk_sale = self.purchase_price * margin_multiplier
        
        # Calcular precios derivados
        unit_purchase = self.purchase_price / self.units_quantity if self.units_quantity > 0 else Decimal('0')
        unit_sale = bulk_sale / self.units_quantity if self.units_quantity > 0 else Decimal('0')
        
        display_purchase = self.purchase_price / self.displays_per_bulk if self.displays_per_bulk > 0 else Decimal('0')
        display_sale = bulk_sale / self.displays_per_bulk if self.displays_per_bulk > 0 else Decimal('0')
        
        return {
            'unit_purchase': unit_purchase.quantize(Decimal('0.01')),
            'unit_sale': unit_sale.quantize(Decimal('0.01')),
            'display_purchase': display_purchase.quantize(Decimal('0.01')),
            'display_sale': display_sale.quantize(Decimal('0.01')),
            'bulk_purchase': self.purchase_price,
            'bulk_sale': bulk_sale.quantize(Decimal('0.01')),
            'profit_per_unit': (unit_sale - unit_purchase).quantize(Decimal('0.01')),
            'profit_per_display': (display_sale - display_purchase).quantize(Decimal('0.01')),
            'profit_per_bulk': (bulk_sale - self.purchase_price).quantize(Decimal('0.01')),
        }
