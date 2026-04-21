"""
Fix: AperturaBulto.producto FK still references granel_productodeposito in PostgreSQL.

Migration 0008 tried to fix this by searching for constraint names LIKE '%productodeposito%',
but Django truncated the constraint name to 'granel_aperturabulto_producto_id_9137c725_fk_granel_pr'
so the LIKE didn't match. This migration finds ALL FK constraints on that column and replaces
them with the correct FK to stocks_product.
"""
from django.db import migrations


def fix_aperturabulto_fk(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    with schema_editor.connection.cursor() as cursor:
        # Find ALL FK constraints on granel_aperturabulto.producto_id
        cursor.execute("""
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_attribute att ON att.attrelid = con.conrelid
                AND att.attnum = ANY(con.conkey)
            WHERE rel.relname = 'granel_aperturabulto'
              AND att.attname = 'producto_id'
              AND con.contype = 'f'
        """)
        fk_names = [row[0] for row in cursor.fetchall()]

        for fk_name in fk_names:
            cursor.execute(
                f'ALTER TABLE granel_aperturabulto DROP CONSTRAINT "{fk_name}"'
            )

        # Create correct FK to stocks_product
        cursor.execute("""
            ALTER TABLE granel_aperturabulto
            ADD CONSTRAINT granel_aperturabulto_producto_id_fk_stocks_product
            FOREIGN KEY (producto_id) REFERENCES stocks_product(id)
            DEFERRABLE INITIALLY DEFERRED
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('granel', '0014_force_nullable_fks_sql'),
        ('stocks', '0015_fix_granel_price_weight_grams'),
    ]

    operations = [
        migrations.RunPython(fix_aperturabulto_fk, migrations.RunPython.noop),
    ]
