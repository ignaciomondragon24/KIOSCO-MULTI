"""
Company Models
"""
from django.db import models


class Company(models.Model):
    """Company information singleton model."""
    
    name = models.CharField(
        'Nombre de la Empresa',
        max_length=200
    )
    legal_name = models.CharField(
        'Razón Social',
        max_length=200,
        blank=True
    )
    cuit = models.CharField(
        'CUIT',
        max_length=20,
        blank=True
    )
    address = models.TextField(
        'Dirección',
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
    website = models.URLField(
        'Sitio Web',
        blank=True
    )
    logo = models.ImageField(
        'Logo',
        upload_to='company/',
        blank=True,
        null=True
    )
    tax_condition = models.CharField(
        'Condición Fiscal',
        max_length=100,
        blank=True,
        help_text='Ej: Responsable Inscripto, Monotributista'
    )
    gross_income = models.CharField(
        'Ingresos Brutos',
        max_length=50,
        blank=True
    )
    start_date = models.DateField(
        'Inicio de Actividades',
        null=True,
        blank=True
    )
    
    # Receipt configuration
    receipt_header = models.TextField(
        'Encabezado de Ticket',
        blank=True,
        help_text='Texto que aparece al inicio del ticket'
    )
    receipt_footer = models.TextField(
        'Pie de Ticket',
        blank=True,
        help_text='Texto que aparece al final del ticket'
    )
    
    # System settings
    currency_symbol = models.CharField(
        'Símbolo de Moneda',
        max_length=10,
        default='$'
    )
    decimal_separator = models.CharField(
        'Separador Decimal',
        max_length=1,
        default=','
    )
    thousands_separator = models.CharField(
        'Separador de Miles',
        max_length=1,
        default='.'
    )
    
    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresa'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Singleton pattern - only allow one company record
        if not self.pk and Company.objects.exists():
            raise ValueError('Solo puede existir un registro de empresa.')
        super().save(*args, **kwargs)
    
    @classmethod
    def get_company(cls):
        """Get or create the company singleton."""
        company, created = cls.objects.get_or_create(
            pk=1,
            defaults={'name': 'CHE GOLOSO'}
        )
        return company


class Branch(models.Model):
    """Branch/store location."""
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='branches',
        verbose_name='Empresa'
    )
    name = models.CharField(
        'Nombre',
        max_length=100
    )
    code = models.CharField(
        'Código',
        max_length=10,
        unique=True
    )
    address = models.TextField(
        'Dirección',
        blank=True
    )
    phone = models.CharField(
        'Teléfono',
        max_length=50,
        blank=True
    )
    is_active = models.BooleanField(
        'Activa',
        default=True
    )
    is_main = models.BooleanField(
        'Sucursal Principal',
        default=False
    )
    
    class Meta:
        verbose_name = 'Sucursal'
        verbose_name_plural = 'Sucursales'
        ordering = ['-is_main', 'name']
    
    def __str__(self):
        return f'{self.code} - {self.name}'
