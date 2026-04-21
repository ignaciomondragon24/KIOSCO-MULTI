# Generated manually to force NOT NULL removal in PostgreSQL

from django.db import migrations, connection


def run_postgresql_only(apps, schema_editor):
    """Only run ALTER COLUMN on PostgreSQL (SQLite doesn't support it)."""
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        # Make FK columns nullable
        cursor.execute("""
            ALTER TABLE granel_bulktograneltransfer
                ALTER COLUMN bulk_product_id DROP NOT NULL;
        """)
        cursor.execute("""
            ALTER TABLE granel_bulktograneltransfer
                ALTER COLUMN granel_product_id DROP NOT NULL;
        """)
        cursor.execute("""
            ALTER TABLE granel_aperturabulto
                ALTER COLUMN producto_id DROP NOT NULL;
        """)
        cursor.execute("""
            ALTER TABLE granel_shrinkageaudit
                ALTER COLUMN granel_product_id DROP NOT NULL;
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('granel', '0013_fix_all_protected_fks'),
    ]

    operations = [
        migrations.RunPython(run_postgresql_only, migrations.RunPython.noop),
    ]
