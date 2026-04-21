from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0004_expensecategory_is_investment'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='affects_cash_drawer',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Activar solo si este gasto se pagó con efectivo del cajón del POS '
                    '(ej: cajero paga el delivery con la plata de la caja). '
                    'Gastos operativos generales (alquiler, sueldos, servicios) suelen '
                    'pagarse por fuera y deben dejarse desmarcado.'
                ),
                verbose_name='Sale del cajón de la caja',
            ),
        ),
    ]
