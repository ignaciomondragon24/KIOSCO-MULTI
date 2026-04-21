# Migration to safely handle external_pos_id field removal from PointDevice
# This field was briefly added then moved to MPCredentials in migration 0004

from django.db import migrations, connection


def remove_external_pos_id(apps, schema_editor):
    """Remove external_pos_id column from pointdevice if it exists."""
    cursor = schema_editor.connection.cursor()
    try:
        columns = [
            col.name for col in
            schema_editor.connection.introspection.get_table_description(
                cursor, 'mercadopago_pointdevice'
            )
        ]
    except Exception:
        return  # Table doesn't exist yet — safe to skip

    if 'external_pos_id' not in columns:
        return  # Column already gone — nothing to do

    # Use savepoint so a failure doesn't break the transaction on PostgreSQL
    from django.db import connection as db_connection
    if db_connection.vendor == 'postgresql':
        cursor.execute('SAVEPOINT sp_drop_col')
    try:
        cursor.execute(
            'ALTER TABLE mercadopago_pointdevice DROP COLUMN external_pos_id'
        )
    except Exception:
        if db_connection.vendor == 'postgresql':
            cursor.execute('ROLLBACK TO SAVEPOINT sp_drop_col')
    else:
        if db_connection.vendor == 'postgresql':
            cursor.execute('RELEASE SAVEPOINT sp_drop_col')


class Migration(migrations.Migration):

    dependencies = [
        ('mercadopago', '0002_alter_mpcredentials_id_alter_pointdevice_id_and_more'),
    ]

    operations = [
        migrations.RunPython(remove_external_pos_id, migrations.RunPython.noop),
    ]
