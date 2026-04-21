from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0007_alter_stockmovement_quantity'),
    ]

    operations = [
        migrations.AddField(
            model_name='productpackaging',
            name='current_stock',
            field=models.DecimalField(
                verbose_name='Stock Actual',
                max_digits=12,
                decimal_places=3,
                default=0,
            ),
        ),
        migrations.AddField(
            model_name='productpackaging',
            name='min_stock',
            field=models.PositiveIntegerField(
                verbose_name='Stock Mínimo',
                default=0,
            ),
        ),
    ]
