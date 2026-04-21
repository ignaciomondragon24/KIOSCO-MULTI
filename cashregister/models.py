"""
Cash Register Models
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone


class PaymentMethod(models.Model):
    """Payment method model."""
    
    code = models.CharField(
        'Código',
        max_length=20,
        unique=True
    )
    name = models.CharField(
        'Nombre',
        max_length=50
    )
    is_cash = models.BooleanField(
        'Es Efectivo',
        default=False,
        help_text='Si es efectivo, se incluye en arqueo de caja'
    )
    requires_counting = models.BooleanField(
        'Requiere Conteo',
        default=False,
        help_text='Si requiere conteo de billetes/monedas al cierre'
    )
    icon = models.CharField(
        'Icono',
        max_length=50,
        default='fa-money-bill',
        help_text='Clase Font Awesome'
    )
    color = models.CharField(
        'Color',
        max_length=7,
        default='#198754',
        help_text='Color para gráficos'
    )
    is_active = models.BooleanField(
        'Activo',
        default=True
    )
    position = models.PositiveIntegerField(
        'Posición',
        default=0
    )
    
    class Meta:
        verbose_name = 'Método de Pago'
        verbose_name_plural = 'Métodos de Pago'
        ordering = ['position', 'name']
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_default_methods(cls):
        """Create default payment methods."""
        defaults = [
            {'code': 'cash', 'name': 'Efectivo', 'is_cash': True, 'requires_counting': True, 'icon': 'fas fa-money-bill-wave', 'color': '#198754', 'position': 1},
            {'code': 'debit', 'name': 'Débito', 'is_cash': False, 'requires_counting': False, 'icon': 'fas fa-credit-card', 'color': '#0dcaf0', 'position': 2},
            {'code': 'credit', 'name': 'Crédito', 'is_cash': False, 'requires_counting': False, 'icon': 'fas fa-credit-card', 'color': '#6f42c1', 'position': 3},
            {'code': 'transfer', 'name': 'Transferencia', 'is_cash': False, 'requires_counting': False, 'icon': 'fas fa-building-columns', 'color': '#0d6efd', 'position': 4},
            {'code': 'mercadopago', 'name': 'MercadoPago', 'is_cash': False, 'requires_counting': False, 'icon': 'fas fa-wallet', 'color': '#00b1ea', 'position': 5},
        ]
        for method_data in defaults:
            cls.objects.get_or_create(code=method_data['code'], defaults=method_data)


class CashRegister(models.Model):
    """Cash register (physical cash drawer)."""
    
    code = models.CharField(
        'Código',
        max_length=20,
        unique=True,
        help_text='Ej: CAJA-01'
    )
    name = models.CharField(
        'Nombre',
        max_length=100
    )
    location = models.CharField(
        'Ubicación',
        max_length=100,
        blank=True
    )
    is_active = models.BooleanField(
        'Activo',
        default=True
    )
    created_at = models.DateTimeField(
        'Fecha de creación',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Caja Registradora'
        verbose_name_plural = 'Cajas Registradoras'
        ordering = ['code']
    
    def __str__(self):
        return f'{self.code} - {self.name}'
    
    @property
    def current_shift(self):
        """Get current open shift for this register."""
        return self.shifts.filter(status='open').first()
    
    @property
    def is_available(self):
        """Check if register is available (no open shift)."""
        return not self.shifts.filter(status='open').exists()


class CashShift(models.Model):
    """Cash shift (turno de caja)."""
    
    STATUS_CHOICES = [
        ('open', 'Abierto'),
        ('closed', 'Cerrado'),
    ]
    
    cash_register = models.ForeignKey(
        CashRegister,
        on_delete=models.PROTECT,
        related_name='shifts',
        verbose_name='Caja'
    )
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cash_shifts',
        verbose_name='Cajero'
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
        default='open'
    )
    
    # Money amounts
    initial_amount = models.DecimalField(
        'Monto Inicial',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Efectivo inicial en caja'
    )
    expected_amount = models.DecimalField(
        'Monto Esperado',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Calculado automáticamente'
    )
    actual_amount = models.DecimalField(
        'Monto Real',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Conteo real al cierre'
    )
    difference = models.DecimalField(
        'Diferencia',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Sobrante (+) o Faltante (-)'
    )
    
    notes = models.TextField(
        'Notas',
        blank=True
    )
    
    class Meta:
        verbose_name = 'Turno de Caja'
        verbose_name_plural = 'Turnos de Caja'
        ordering = ['-opened_at']
    
    def __str__(self):
        return f'{self.cash_register.code} - {self.cashier.username} - {self.opened_at.strftime("%d/%m/%Y %H:%M")}'
    
    def calculate_expected(self):
        """Calculate expected cash amount."""
        # Start with initial amount
        expected = self.initial_amount
        
        # Add cash movements
        from django.db.models import Sum
        
        movements = self.movements.filter(payment_method__is_cash=True).aggregate(
            income=Sum('amount', filter=models.Q(movement_type='income')),
            expense=Sum('amount', filter=models.Q(movement_type='expense'))
        )
        
        income = movements['income'] or Decimal('0.00')
        expense = movements['expense'] or Decimal('0.00')
        
        expected += income - expense
        return expected
    
    @property
    def duration(self):
        """timedelta desde apertura hasta cierre (o ahora si sigue abierto).

        Siempre calculado desde el DB contra `timezone.now()` — no depende de
        que un cliente tenga la pestana abierta. Si un turno quedo abierto por
        olvido, este valor refleja el tiempo real transcurrido.
        """
        from django.utils import timezone
        end = self.closed_at or timezone.now()
        return end - self.opened_at

    @property
    def hours_open(self):
        """Total de horas (float) que lleva abierto o duro el turno."""
        return self.duration.total_seconds() / 3600

    @property
    def duration_display(self):
        """String legible tipo "2h 15m" o "5d 3h" para mostrar en UI."""
        total = int(self.duration.total_seconds())
        days, rem = divmod(total, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        if days > 0:
            return f'{days}d {hours}h {minutes}m'
        if hours > 0:
            return f'{hours}h {minutes}m'
        return f'{minutes}m'

    def close(self, actual_amount, notes=''):
        """Close the shift."""
        self.expected_amount = self.calculate_expected()
        self.actual_amount = actual_amount
        self.difference = actual_amount - self.expected_amount
        self.closed_at = timezone.now()
        self.status = 'closed'
        self.notes = notes
        self.save()
    
    @property
    def total_sales(self):
        """Get total sales amount."""
        from django.db.models import Sum
        result = self.movements.filter(
            movement_type='income',
            description__startswith='Venta'
        ).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')
    
    @property
    def transactions_count(self):
        """Get number of transactions."""
        from pos.models import POSTransaction
        return POSTransaction.objects.filter(
            session__cash_shift=self,
            status='completed'
        ).count()
    
    @property
    def total_income(self):
        """Get total income amount from all payment methods."""
        from django.db.models import Sum
        result = self.movements.filter(
            movement_type='income'
        ).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')
    
    @property
    def total_expense(self):
        """Get total expense amount."""
        from django.db.models import Sum
        result = self.movements.filter(
            movement_type='expense'
        ).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')
    
    @property
    def manual_movements_count(self):
        """Get count of manual movements (not from POS sales)."""
        return self.movements.exclude(
            description__startswith='Venta '
        ).exclude(
            description__startswith='Venta al costo'
        ).count()
    
    def get_totals_by_payment_method(self):
        """Get sales totals grouped by payment method."""
        from django.db.models import Sum
        
        totals = self.movements.filter(
            movement_type='income'
        ).values(
            'payment_method__code',
            'payment_method__name',
            'payment_method__icon',
            'payment_method__color',
            'payment_method__is_cash'
        ).annotate(
            total=Sum('amount'),
            count=models.Count('id')
        ).order_by('payment_method__position')
        
        return list(totals)
    
    def get_cash_total(self):
        """Get total cash (efectivo) amount."""
        from django.db.models import Sum
        result = self.movements.filter(
            movement_type='income',
            payment_method__is_cash=True
        ).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')
    
    def get_non_cash_total(self):
        """Get total non-cash amount (tarjetas, transferencias, etc)."""
        from django.db.models import Sum
        result = self.movements.filter(
            movement_type='income',
            payment_method__is_cash=False
        ).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')
    
    def get_bill_count_total(self, count_type='closing'):
        """Get total from bill count."""
        total = Decimal('0.00')
        for bc in self.bill_counts.filter(count_type=count_type):
            total += Decimal(bc.denomination) * bc.quantity
        return total


class CashMovement(models.Model):
    """Cash movement (ingreso/egreso)."""
    
    MOVEMENT_TYPES = [
        ('income', 'Ingreso'),
        ('expense', 'Egreso'),
    ]
    
    cash_shift = models.ForeignKey(
        CashShift,
        on_delete=models.CASCADE,
        related_name='movements',
        verbose_name='Turno'
    )
    movement_type = models.CharField(
        'Tipo',
        max_length=20,
        choices=MOVEMENT_TYPES
    )
    amount = models.DecimalField(
        'Monto',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name='Método de Pago'
    )
    description = models.CharField(
        'Descripción',
        max_length=200
    )
    reference = models.CharField(
        'Referencia',
        max_length=100,
        blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cash_movements',
        verbose_name='Registrado por'
    )
    created_at = models.DateTimeField(
        'Fecha',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Movimiento de Caja'
        verbose_name_plural = 'Movimientos de Caja'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.get_movement_type_display()} - ${self.amount} - {self.description}'


class BillCount(models.Model):
    """Conteo de billetes/monedas para arqueo de caja."""
    
    DENOMINATION_CHOICES = [
        # Billetes
        (1000, '$1.000'),
        (2000, '$2.000'),
        (5000, '$5.000'),
        (10000, '$10.000'),
        (20000, '$20.000'),
        # Monedas
        (1, '$1'),
        (2, '$2'),
        (5, '$5'),
        (10, '$10'),
        (20, '$20'),
        (50, '$50'),
        (100, '$100'),
        (200, '$200'),
        (500, '$500'),
    ]
    
    cash_shift = models.ForeignKey(
        CashShift,
        on_delete=models.CASCADE,
        related_name='bill_counts',
        verbose_name='Turno'
    )
    denomination = models.IntegerField(
        'Denominación',
        choices=DENOMINATION_CHOICES
    )
    quantity = models.PositiveIntegerField(
        'Cantidad',
        default=0
    )
    count_type = models.CharField(
        'Tipo de Conteo',
        max_length=20,
        choices=[
            ('opening', 'Apertura'),
            ('closing', 'Cierre'),
        ],
        default='closing'
    )
    created_at = models.DateTimeField(
        'Fecha',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Conteo de Billetes'
        verbose_name_plural = 'Conteos de Billetes'
        ordering = ['-denomination']
        unique_together = ['cash_shift', 'denomination', 'count_type']
    
    def __str__(self):
        return f'{self.get_denomination_display()} x {self.quantity}'
    
    @property
    def subtotal(self):
        """Calculate subtotal for this denomination."""
        return self.denomination * self.quantity


class ShiftPaymentSummary(models.Model):
    """Resumen de ventas por método de pago por turno."""
    
    cash_shift = models.ForeignKey(
        CashShift,
        on_delete=models.CASCADE,
        related_name='payment_summaries',
        verbose_name='Turno'
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='shift_summaries',
        verbose_name='Método de Pago'
    )
    total_amount = models.DecimalField(
        'Total',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    transaction_count = models.PositiveIntegerField(
        'Cantidad de Transacciones',
        default=0
    )
    
    class Meta:
        verbose_name = 'Resumen por Método de Pago'
        verbose_name_plural = 'Resúmenes por Método de Pago'
        unique_together = ['cash_shift', 'payment_method']
    
    def __str__(self):
        return f'{self.cash_shift} - {self.payment_method}: ${self.total_amount}'
