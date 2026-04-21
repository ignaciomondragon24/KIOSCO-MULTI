"""
Fix M2M con cursor directo (no schema_editor.execute, no DO block).
Incluye logging detallado visible en Railway deploy logs.
"""
from django.db import migrations


def fix_m2m_direct(apps, schema_editor):
    conn = schema_editor.connection
    if conn.vendor != 'postgresql':
        print("[M2M-FIX] SQLite detectado, sin cambios necesarios.")
        return

    with conn.cursor() as cursor:
        # Verificar estado actual de la tabla
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'granel_caramelera_productos_autorizados'
            ORDER BY ordinal_position
        """)
        existing_cols = [row[0] for row in cursor.fetchall()]
        print(f"[M2M-FIX] Columnas actuales en M2M: {existing_cols}")

        if 'product_id' in existing_cols:
            print("[M2M-FIX] product_id YA EXISTE. No se necesita fix.")
            return

        print("[M2M-FIX] product_id NO existe. Ejecutando DROP + CREATE...")

        # Paso 1: Drop
        cursor.execute(
            "DROP TABLE IF EXISTS granel_caramelera_productos_autorizados CASCADE"
        )
        print("[M2M-FIX] DROP TABLE ejecutado.")

        # Paso 2: Create con columna correcta
        cursor.execute("""
            CREATE TABLE granel_caramelera_productos_autorizados (
                id BIGSERIAL NOT NULL PRIMARY KEY,
                caramelera_id BIGINT NOT NULL,
                product_id BIGINT NOT NULL
            )
        """)
        print("[M2M-FIX] CREATE TABLE ejecutado.")

        # Paso 3: FK constraints
        cursor.execute("""
            ALTER TABLE granel_caramelera_productos_autorizados
            ADD CONSTRAINT granel_car_pa_car_fk
            FOREIGN KEY (caramelera_id)
            REFERENCES granel_caramelera(id)
            DEFERRABLE INITIALLY DEFERRED
        """)
        cursor.execute("""
            ALTER TABLE granel_caramelera_productos_autorizados
            ADD CONSTRAINT granel_car_pa_prod_fk
            FOREIGN KEY (product_id)
            REFERENCES stocks_product(id)
            DEFERRABLE INITIALLY DEFERRED
        """)

        # Paso 4: Unique + índices
        cursor.execute("""
            ALTER TABLE granel_caramelera_productos_autorizados
            ADD CONSTRAINT granel_car_pa_unique
            UNIQUE (caramelera_id, product_id)
        """)
        cursor.execute("""
            CREATE INDEX granel_car_pa_car_idx
            ON granel_caramelera_productos_autorizados(caramelera_id)
        """)
        cursor.execute("""
            CREATE INDEX granel_car_pa_prod_idx
            ON granel_caramelera_productos_autorizados(product_id)
        """)

        print("[M2M-FIX] COMPLETADO. Tabla M2M recreada correctamente.")


class Migration(migrations.Migration):

    dependencies = [
        ('granel', '0010_force_recreate_m2m_table'),
        ('stocks', '0014_add_caramelera_fields'),
    ]

    operations = [
        migrations.RunPython(fix_m2m_direct, migrations.RunPython.noop),
    ]
