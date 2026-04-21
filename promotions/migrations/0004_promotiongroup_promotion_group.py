# Generated for CHE GOLOSO promotion linking feature

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('promotions', '0003_add_nx_fixed_price_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='PromotionGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True, verbose_name='Nombre')),
                ('description', models.TextField(blank=True, verbose_name='Descripción')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Última actualización')),
            ],
            options={
                'verbose_name': 'Grupo de Promociones',
                'verbose_name_plural': 'Grupos de Promociones',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='promotion',
            name='group',
            field=models.ForeignKey(
                blank=True,
                help_text='Promociones del mismo grupo suman cantidades como si fueran una sola.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='promotions',
                to='promotions.promotiongroup',
                verbose_name='Grupo enlazado',
            ),
        ),
    ]
