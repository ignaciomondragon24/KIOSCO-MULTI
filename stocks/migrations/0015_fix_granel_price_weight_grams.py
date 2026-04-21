"""
Corrige granel_price_weight_grams=100 en todos los productos POS de carameleras.
El sistema siempre usa precio por 100g como base.
"""
from django.db import migrations


def fix_granel_price_weight(apps, schema_editor):
    Product = apps.get_model('stocks', 'Product')
    updated = Product.objects.filter(
        is_granel=True,
        granel_caramelera__isnull=False,
    ).exclude(granel_price_weight_grams=100).update(granel_price_weight_grams=100)
    if updated:
        print(f'  Corregidos {updated} productos granel a granel_price_weight_grams=100')


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0014_add_caramelera_fields'),
    ]

    operations = [
        migrations.RunPython(fix_granel_price_weight, migrations.RunPython.noop),
    ]
