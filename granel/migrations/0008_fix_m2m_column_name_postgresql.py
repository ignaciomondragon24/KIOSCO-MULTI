"""
Fix para producción (PostgreSQL): la migración 0007 usó AlterField en la M2M
Caramelera.productos_autorizados, que en Django solo actualiza los metadatos
pero NO renombra la columna en PostgreSQL.

La tabla granel_caramelera_productos_autorizados sigue teniendo productodeposito_id
en lugar de product_id. Esta migración lo corrige vía RunSQL, solo en PostgreSQL
(SQLite ya lo tiene correcto).

También corrige AperturaBulto.producto que tenía el mismo problema:
la FK sigue apuntando a granel_productodeposito en vez de stocks_product.
"""
from django.db import migrations


def rename_column_postgresql(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    with schema_editor.connection.cursor() as cursor:
        # --- M2M: productos_autorizados ---
        # Verificar si la columna vieja existe antes de renombrar
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'granel_caramelera_productos_autorizados'
              AND column_name = 'productodeposito_id'
        """)
        if cursor.fetchone():
            cursor.execute("""
                ALTER TABLE granel_caramelera_productos_autorizados
                RENAME COLUMN productodeposito_id TO product_id
            """)

        # --- FK: AperturaBulto.producto ---
        # La FK puede apuntar a la tabla vieja; verificar si existe la constraint
        cursor.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'granel_aperturabulto'
              AND constraint_type = 'FOREIGN KEY'
              AND constraint_name LIKE '%productodeposito%'
        """)
        old_fk = cursor.fetchone()
        if old_fk:
            fk_name = old_fk[0]
            cursor.execute(
                f'ALTER TABLE granel_aperturabulto DROP CONSTRAINT "{fk_name}"'
            )
            cursor.execute("""
                ALTER TABLE granel_aperturabulto
                ADD CONSTRAINT granel_aperturabulto_producto_id_fk
                FOREIGN KEY (producto_id) REFERENCES stocks_product(id)
                DEFERRABLE INITIALLY DEFERRED
            """)


class Migration(migrations.Migration):

    dependencies = [
        ('granel', '0007_use_product_for_caramelera'),
        ('stocks', '0014_add_caramelera_fields'),
    ]

    operations = [
        migrations.RunPython(rename_column_postgresql, migrations.RunPython.noop),
    ]
