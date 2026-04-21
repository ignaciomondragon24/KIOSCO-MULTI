"""
Fix definitivo mediante SQL directo: DROP + CREATE de la tabla M2M.
Las migraciones 0008 y 0009 pueden haber fallado silenciosamente.
Este RunSQL fuerza la recreación correcta solo en PostgreSQL.
"""
from django.db import migrations


RECREATE_SQL = """
DO $$
BEGIN
    -- Eliminar tabla anterior con cualquier columna que tenga
    DROP TABLE IF EXISTS granel_caramelera_productos_autorizados CASCADE;

    -- Crear tabla nueva con la columna correcta product_id
    CREATE TABLE granel_caramelera_productos_autorizados (
        id bigserial NOT NULL PRIMARY KEY,
        caramelera_id bigint NOT NULL,
        product_id bigint NOT NULL,
        CONSTRAINT granel_caramelera_pa_caramelera_fk
            FOREIGN KEY (caramelera_id)
            REFERENCES granel_caramelera(id)
            DEFERRABLE INITIALLY DEFERRED,
        CONSTRAINT granel_caramelera_pa_product_fk
            FOREIGN KEY (product_id)
            REFERENCES stocks_product(id)
            DEFERRABLE INITIALLY DEFERRED,
        CONSTRAINT granel_caramelera_pa_unique
            UNIQUE (caramelera_id, product_id)
    );

    CREATE INDEX granel_caramelera_pa_caramelera_idx
        ON granel_caramelera_productos_autorizados (caramelera_id);
    CREATE INDEX granel_caramelera_pa_product_idx
        ON granel_caramelera_productos_autorizados (product_id);
END
$$;
"""

# En SQLite no hacemos nada (ya funciona con el ORM de Django)
SQLITE_NOOP = ""


def run_fix(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(RECREATE_SQL)


class Migration(migrations.Migration):

    dependencies = [
        ('granel', '0009_recreate_m2m_productos_autorizados'),
        ('stocks', '0014_add_caramelera_fields'),
    ]

    operations = [
        migrations.RunPython(run_fix, migrations.RunPython.noop),
    ]
