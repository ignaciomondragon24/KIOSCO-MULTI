from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('promotions', '0004_promotiongroup_promotion_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='promotion',
            name='applies_to_packaging_type',
            field=models.CharField(
                choices=[
                    ('unit', 'Solo unidad suelta'),
                    ('display', 'Solo display / paquete'),
                    ('bulk', 'Solo bulto / caja'),
                    ('any', 'Cualquier empaque'),
                ],
                default='unit',
                help_text='Empaque al que se le aplica la promo. Permite precios distintos por unidad y por display.',
                max_length=20,
                verbose_name='Empaque al que aplica',
            ),
        ),
    ]
