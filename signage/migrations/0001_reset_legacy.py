"""
Reset legacy signage tables from previous module version.
Drops old tables and clears stale migration records so the new schema
can be created cleanly by 0002_initial.
"""
from django.db import migrations


def drop_legacy_tables(apps, schema_editor):
    """Drop old signage tables. Uses CASCADE on PostgreSQL, plain DROP on SQLite."""
    conn = schema_editor.connection
    is_pg = conn.vendor == 'postgresql'
    tables = ['signage_signitem', 'signage_signbatch', 'signage_signtemplate']
    with conn.cursor() as cursor:
        for table in tables:
            suffix = ' CASCADE' if is_pg else ''
            cursor.execute(f'DROP TABLE IF EXISTS {table}{suffix};')


def clear_old_migration_records(apps, schema_editor):
    """Remove old signage migration records that no longer exist."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM django_migrations WHERE app = 'signage' AND name != '0001_reset_legacy'"
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('stocks', '0007_alter_stockmovement_quantity'),
    ]

    operations = [
        migrations.RunPython(drop_legacy_tables, migrations.RunPython.noop),
        migrations.RunPython(clear_old_migration_records, migrations.RunPython.noop),
    ]

    
