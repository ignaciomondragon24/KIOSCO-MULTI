from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0008_alter_postransactionitem_quantity'),
    ]

    operations = [
        migrations.AddField(
            model_name='postransactionitem',
            name='promotion_discount',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='Descuento aplicado automáticamente por una promoción activa',
                max_digits=10,
                verbose_name='Descuento por Promoción',
            ),
        ),
        migrations.AddField(
            model_name='postransactionitem',
            name='promotion_group_name',
            field=models.CharField(
                blank=True,
                help_text='Nombre del grupo si la promo está enlazada con otras',
                max_length=200,
                verbose_name='Grupo de Promoción',
            ),
        ),
        migrations.AlterField(
            model_name='postransactionitem',
            name='discount',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='Descuento manual ingresado por el cajero (independiente de la promo)',
                max_digits=10,
                verbose_name='Descuento Manual',
            ),
        ),
    ]
