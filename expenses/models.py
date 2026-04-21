"""
Expenses Models
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class ExpenseCategory(models.Model):
    """Category for expenses."""
    
    name = models.CharField(
        'Nombre',
        max_length=100
    )
    description = models.TextField(
        'Descripción',
        blank=True
    )
    color = models.CharField(
        'Color',
        max_length=7,
        default='#6c757d',
        help_text='Código hexadecimal del color'
    )
    is_active = models.BooleanField(
        'Activa',
        default=True
    )
    is_investment = models.BooleanField(
        'Inversión (no resta del balance)',
        default=False,
        help_text=(
            'Marcá esta opción si los gastos de esta categoría representan '
            'inversión y no deben restarse de las ganancias en el balance. '
            'Caso típico: Compras de mercadería — ese dinero se convierte '
            'en productos para revender, no es un gasto puro del negocio.'
        ),
    )

    class Meta:
        verbose_name = 'Categoría de Gasto'
        verbose_name_plural = 'Categorías de Gastos'
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    """Expense record."""
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Efectivo'),
        ('card', 'Tarjeta'),
        ('transfer', 'Transferencia'),
        ('check', 'Cheque'),
        ('other', 'Otro'),
    ]
    
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name='Categoría'
    )
    description = models.CharField(
        'Descripción',
        max_length=255
    )
    amount = models.DecimalField(
        'Monto',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    expense_date = models.DateField(
        'Fecha del Gasto'
    )
    payment_method = models.CharField(
        'Método de Pago',
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    receipt_number = models.CharField(
        'Número de Comprobante',
        max_length=100,
        blank=True
    )
    supplier = models.ForeignKey(
        'purchase.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses',
        verbose_name='Proveedor'
    )
    notes = models.TextField(
        'Notas',
        blank=True
    )
    receipt_image = models.ImageField(
        'Imagen del Comprobante',
        upload_to='expenses/receipts/',
        blank=True,
        null=True
    )
    affects_cash_drawer = models.BooleanField(
        'Sale del cajón de la caja',
        default=False,
        help_text=(
            'Activar solo si este gasto se pagó con efectivo del cajón del POS '
            '(ej: cajero paga el delivery con la plata de la caja). '
            'Gastos operativos generales (alquiler, sueldos, servicios) suelen '
            'pagarse por fuera y deben dejarse desmarcado.'
        )
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='expenses',
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
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'
        ordering = ['-expense_date', '-created_at']
    
    def __str__(self):
        return f'{self.description} - ${self.amount}'


class RecurringExpense(models.Model):
    """Recurring expense template."""
    
    FREQUENCY_CHOICES = [
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensual'),
        ('yearly', 'Anual'),
    ]
    
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='recurring_expenses',
        verbose_name='Categoría'
    )
    description = models.CharField(
        'Descripción',
        max_length=255
    )
    amount = models.DecimalField(
        'Monto',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    frequency = models.CharField(
        'Frecuencia',
        max_length=20,
        choices=FREQUENCY_CHOICES
    )
    next_due_date = models.DateField(
        'Próximo Vencimiento'
    )
    is_active = models.BooleanField(
        'Activo',
        default=True
    )
    notes = models.TextField(
        'Notas',
        blank=True
    )
    
    class Meta:
        verbose_name = 'Gasto Recurrente'
        verbose_name_plural = 'Gastos Recurrentes'
        ordering = ['next_due_date']
    
    def __str__(self):
        return f'{self.description} - {self.get_frequency_display()}'
