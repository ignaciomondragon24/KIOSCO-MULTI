"""
Fix empty barcode strings to NULL for PostgreSQL unique constraint compatibility.
"""
from django.db import migrations


def fix_empty_barcodes(apps, schema_editor):
    Product = apps.get_model('stocks', 'Product')
    updated = Product.objects.filter(barcode='').update(barcode=None)
    if updated:
        print(f'  Fixed {updated} products with empty barcode -> NULL')


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0017_fix_weight_per_unit_grams_not_null'),
    ]

    operations = [
        migrations.RunPython(fix_empty_barcodes, migrations.RunPython.noop),
    ]
