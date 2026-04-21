"""
Fix definitivo: recrea la tabla M2M granel_caramelera_productos_autorizados
desde cero con la columna product_id correcta.

AlterField en M2M no genera SQL de renombrado de columnas en Django.
RemoveField + AddField sí genera DROP TABLE + CREATE TABLE, lo que garantiza
la columna correcta en PostgreSQL.

No hay pérdida de datos: la tabla estaba vacía (0 carameleras en producción).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('granel', '0008_fix_m2m_column_name_postgresql'),
        ('stocks', '0014_add_caramelera_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='caramelera',
            name='productos_autorizados',
        ),
        migrations.AddField(
            model_name='caramelera',
            name='productos_autorizados',
            field=models.ManyToManyField(
                blank=True,
                help_text='Productos del inventario marcados como "para caramelera" que pueden entrar en este mix',
                limit_choices_to={'es_deposito_caramelera': True},
                to='stocks.product',
                verbose_name='Productos Autorizados',
            ),
        ),
    ]
