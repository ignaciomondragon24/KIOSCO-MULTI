"""
Fix weight_per_unit_grams: set DB-level default and convert NULLs to 0.
"""
from django.db import migrations, models
from decimal import Decimal


def fix_null_values(apps, schema_editor):
    Product = apps.get_model('stocks', 'Product')
    updated = Product.objects.filter(weight_per_unit_grams__isnull=True).update(
        weight_per_unit_grams=Decimal('0.00')
    )
    if updated:
        print(f'  Fixed {updated} products with NULL weight_per_unit_grams')


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0016_make_sku_optional'),
    ]

    operations = [
        # First: fill any existing NULLs
        migrations.RunPython(fix_null_values, migrations.RunPython.noop),
        # Then: re-apply the field with explicit default to ensure DB column has DEFAULT
        migrations.AlterField(
            model_name='product',
            name='weight_per_unit_grams',
            field=models.DecimalField(
                verbose_name='Peso por Unidad (gramos)',
                max_digits=10,
                decimal_places=2,
                default=Decimal('0.00'),
                blank=True,
                help_text='Para bultos: gramos que contiene cada unidad (ej: 2000 para bolsa de 2kg)',
            ),
        ),
    ]
