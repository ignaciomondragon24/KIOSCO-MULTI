#!/bin/bash

echo "=== CHE GOLOSO - Starting ==="
echo "PORT: ${PORT:-8000}"
echo "DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo 'YES' || echo 'NO')"
echo "DEBUG: ${DEBUG:-not set}"
echo "ALLOWED_HOSTS: ${ALLOWED_HOSTS:-not set}"
echo "RAILWAY_PUBLIC_DOMAIN: ${RAILWAY_PUBLIC_DOMAIN:-not set}"

# Fix directo de tabla M2M rota (antes de migrations, idempotente)
echo "Checking granel M2M table..."
python -c "
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
import django
django.setup()
from django.db import connection
if connection.vendor != 'postgresql':
    print('  SQLite: skip')
    sys.exit(0)
with connection.cursor() as c:
    # Verificar si las tablas base existen
    c.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='granel_caramelera')\")
    if not c.fetchone()[0]:
        print('  granel_caramelera no existe aun, skip')
        sys.exit(0)
    c.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='stocks_product')\")
    if not c.fetchone()[0]:
        print('  stocks_product no existe aun, skip')
        sys.exit(0)
    # Ver columnas actuales
    c.execute(\"SELECT column_name FROM information_schema.columns WHERE table_name='granel_caramelera_productos_autorizados' ORDER BY ordinal_position\")
    cols = [r[0] for r in c.fetchall()]
    print(f'  Columnas M2M: {cols}')
    if 'product_id' in cols:
        print('  product_id OK, no se necesita fix')
        sys.exit(0)
    print('  FIXING: drop + recreate M2M table...')
    c.execute('DROP TABLE IF EXISTS granel_caramelera_productos_autorizados CASCADE')
    c.execute(\"\"\"
        CREATE TABLE granel_caramelera_productos_autorizados (
            id BIGSERIAL PRIMARY KEY,
            caramelera_id BIGINT NOT NULL REFERENCES granel_caramelera(id) DEFERRABLE INITIALLY DEFERRED,
            product_id BIGINT NOT NULL REFERENCES stocks_product(id) DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT granel_car_pa_uniq UNIQUE (caramelera_id, product_id)
        )
    \"\"\")
    c.execute('CREATE INDEX ON granel_caramelera_productos_autorizados(caramelera_id)')
    c.execute('CREATE INDEX ON granel_caramelera_productos_autorizados(product_id)')
    print('  M2M table FIXED OK')
" 2>&1 || echo "WARNING: M2M fix skipped"

# Fix AperturaBulto FK: producto_id debe apuntar a stocks_product, no a granel_productodeposito
echo "Checking AperturaBulto FK constraint..."
python -c "
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
import django; django.setup()
from django.db import connection
if connection.vendor != 'postgresql':
    print('  SQLite: skip')
    sys.exit(0)
with connection.cursor() as c:
    c.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='granel_aperturabulto')\")
    if not c.fetchone()[0]:
        print('  granel_aperturabulto no existe aun, skip')
        sys.exit(0)
    # Find FK constraints on producto_id that reference the WRONG table
    c.execute(\"\"\"
        SELECT con.conname, cls.relname AS referenced_table
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = ANY(con.conkey)
        JOIN pg_class cls ON cls.oid = con.confrelid
        WHERE rel.relname = 'granel_aperturabulto'
          AND att.attname = 'producto_id'
          AND con.contype = 'f'
    \"\"\")
    fks = c.fetchall()
    print(f'  FK constraints on producto_id: {fks}')
    needs_fix = False
    for fk_name, ref_table in fks:
        if ref_table != 'stocks_product':
            print(f'  FIXING: dropping wrong FK {fk_name} -> {ref_table}')
            c.execute(f'ALTER TABLE granel_aperturabulto DROP CONSTRAINT \"{fk_name}\"')
            needs_fix = True
        else:
            print(f'  FK {fk_name} -> {ref_table} OK')
    if needs_fix:
        # Check if correct FK already exists
        c.execute(\"\"\"
            SELECT 1 FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = ANY(con.conkey)
            JOIN pg_class cls ON cls.oid = con.confrelid
            WHERE rel.relname = 'granel_aperturabulto'
              AND att.attname = 'producto_id'
              AND con.contype = 'f'
              AND cls.relname = 'stocks_product'
        \"\"\")
        if not c.fetchone():
            c.execute(\"\"\"
                ALTER TABLE granel_aperturabulto
                ADD CONSTRAINT granel_aperturabulto_producto_id_fk_stocks_product
                FOREIGN KEY (producto_id) REFERENCES stocks_product(id)
                DEFERRABLE INITIALLY DEFERRED
            \"\"\")
            print('  New FK -> stocks_product created OK')
    elif not fks:
        print('  No FK found, creating correct one...')
        c.execute(\"\"\"
            ALTER TABLE granel_aperturabulto
            ADD CONSTRAINT granel_aperturabulto_producto_id_fk_stocks_product
            FOREIGN KEY (producto_id) REFERENCES stocks_product(id)
            DEFERRABLE INITIALLY DEFERRED
        \"\"\")
        print('  FK -> stocks_product created OK')
    else:
        print('  AperturaBulto FK OK, no fix needed')
" 2>&1 || echo "WARNING: AperturaBulto FK fix skipped"

# Pre-flight: ensure mercadopago migration state is consistent
echo "Checking mercadopago migration state..."
python -c "
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
import django; django.setup()
from django.db import connection
if connection.vendor != 'postgresql':
    sys.exit(0)
with connection.cursor() as c:
    # Check if migration 0003 is recorded as applied but 0004 is not
    c.execute(\"SELECT name FROM django_migrations WHERE app='mercadopago' ORDER BY id\")
    applied = [r[0] for r in c.fetchall()]
    print(f'  Applied mercadopago migrations: {applied}')
    if '0003_remove_external_pos_id' in applied and '0004_add_qr_flow_and_optional_device' not in applied:
        print('  0003 applied but 0004 missing — will let migrate handle it')
    if '0003_remove_external_pos_id' not in applied:
        print('  0003 not yet applied — will run during migrate')
" 2>&1 || echo "WARNING: migration pre-check skipped"

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput || echo "WARNING: Migration failed, continuing..."

# Defensive: ensure mercadopago_mpcredentials.external_pos_id and
# mercadopago_paymentintent.payment_flow exist even if migration 0004 didn't apply.
# This unblocks production immediately if Django migrations got stuck for any reason.
echo "Verifying mercadopago QR fields..."
python -c "
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
import django; django.setup()
from django.db import connection
if connection.vendor != 'postgresql':
    print('  SQLite: skip')
    sys.exit(0)
with connection.cursor() as c:
    # Skip if base table doesn't exist yet
    c.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='mercadopago_mpcredentials')\")
    if not c.fetchone()[0]:
        print('  mercadopago_mpcredentials no existe aun, skip')
        sys.exit(0)

    # 1) external_pos_id en mpcredentials
    c.execute(\"\"\"
        SELECT 1 FROM information_schema.columns
        WHERE table_name='mercadopago_mpcredentials' AND column_name='external_pos_id'
    \"\"\")
    if not c.fetchone():
        print('  Adding mpcredentials.external_pos_id ...')
        c.execute(\"\"\"
            ALTER TABLE mercadopago_mpcredentials
            ADD COLUMN external_pos_id varchar(100) NOT NULL DEFAULT ''
        \"\"\")
        print('  external_pos_id added OK')
    else:
        print('  external_pos_id OK')

    # 2) payment_flow en paymentintent
    c.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='mercadopago_paymentintent')\")
    if c.fetchone()[0]:
        c.execute(\"\"\"
            SELECT 1 FROM information_schema.columns
            WHERE table_name='mercadopago_paymentintent' AND column_name='payment_flow'
        \"\"\")
        if not c.fetchone():
            print('  Adding paymentintent.payment_flow ...')
            c.execute(\"\"\"
                ALTER TABLE mercadopago_paymentintent
                ADD COLUMN payment_flow varchar(20) NOT NULL DEFAULT 'qr'
            \"\"\")
            print('  payment_flow added OK')
        else:
            print('  payment_flow OK')

        # 3) device puede ser NULL (QR no requiere device)
        c.execute(\"\"\"
            SELECT is_nullable FROM information_schema.columns
            WHERE table_name='mercadopago_paymentintent' AND column_name='device_id'
        \"\"\")
        row = c.fetchone()
        if row and row[0] == 'NO':
            print('  Making paymentintent.device_id nullable ...')
            c.execute(\"ALTER TABLE mercadopago_paymentintent ALTER COLUMN device_id DROP NOT NULL\")
            print('  device_id is now nullable OK')
        else:
            print('  device_id nullable OK')

    # 4) Marcar migración 0004 como aplicada para que Django no intente correrla otra vez
    c.execute(\"SELECT 1 FROM django_migrations WHERE app='mercadopago' AND name='0004_add_qr_flow_and_optional_device'\")
    if not c.fetchone():
        c.execute(\"\"\"
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('mercadopago', '0004_add_qr_flow_and_optional_device', NOW())
        \"\"\")
        print('  Marked migration 0004 as applied')
" 2>&1 || echo "WARNING: mercadopago field repair skipped"

# Defensive: ensure promotions 0004 (PromotionGroup + group FK) is in place.
# Sin esto, el engine hace SELECT ... group_id FROM promotions_promotion y
# revienta el POS entero (apply_promotions corre en cada add_item).
echo "Verifying promotions PromotionGroup schema..."
python -c "
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
import django; django.setup()
from django.db import connection
if connection.vendor != 'postgresql':
    print('  SQLite: skip')
    sys.exit(0)
with connection.cursor() as c:
    # Skip si la tabla base aún no existe
    c.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='promotions_promotion')\")
    if not c.fetchone()[0]:
        print('  promotions_promotion no existe aun, skip')
        sys.exit(0)

    # 1) Crear tabla promotions_promotiongroup si falta
    c.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='promotions_promotiongroup')\")
    if not c.fetchone()[0]:
        print('  Creating promotions_promotiongroup table ...')
        c.execute(\"\"\"
            CREATE TABLE promotions_promotiongroup (
                id BIGSERIAL PRIMARY KEY,
                name varchar(200) NOT NULL UNIQUE,
                description text NOT NULL DEFAULT '',
                created_at timestamptz NOT NULL DEFAULT NOW(),
                updated_at timestamptz NOT NULL DEFAULT NOW()
            )
        \"\"\")
        print('  promotions_promotiongroup created OK')
    else:
        print('  promotions_promotiongroup OK')

    # 2) Agregar columna group_id a promotions_promotion si falta
    c.execute(\"\"\"
        SELECT 1 FROM information_schema.columns
        WHERE table_name='promotions_promotion' AND column_name='group_id'
    \"\"\")
    if not c.fetchone():
        print('  Adding promotions_promotion.group_id ...')
        c.execute(\"\"\"
            ALTER TABLE promotions_promotion
            ADD COLUMN group_id bigint NULL
                REFERENCES promotions_promotiongroup(id)
                ON DELETE SET NULL
                DEFERRABLE INITIALLY DEFERRED
        \"\"\")
        c.execute('CREATE INDEX promotions_promotion_group_id_idx ON promotions_promotion(group_id)')
        print('  group_id column added OK')
    else:
        print('  promotions_promotion.group_id OK')

    # 3) Marcar migración 0004 como aplicada para que Django no intente correrla otra vez
    c.execute(\"SELECT 1 FROM django_migrations WHERE app='promotions' AND name='0004_promotiongroup_promotion_group'\")
    if not c.fetchone():
        c.execute(\"\"\"
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('promotions', '0004_promotiongroup_promotion_group', NOW())
        \"\"\")
        print('  Marked promotions.0004 as applied')
" 2>&1 || echo "WARNING: promotions schema repair skipped"

# Defensive: ensure POSTransactionItem tiene promotion_discount + promotion_group_name.
# Migración 0009 los agrega; este bloque es red de seguridad si la migración
# no corrió todavía (mismo enfoque que usamos con promotions 0004 más arriba).
echo "Verifying pos_postransactionitem promo fields..."
python -c "
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
import django; django.setup()
from django.db import connection
if connection.vendor != 'postgresql':
    print('  SQLite: skip')
    sys.exit(0)
with connection.cursor() as c:
    c.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='pos_postransactionitem')\")
    if not c.fetchone()[0]:
        print('  pos_postransactionitem no existe aun, skip')
        sys.exit(0)

    # 1) promotion_discount
    c.execute(\"\"\"
        SELECT 1 FROM information_schema.columns
        WHERE table_name='pos_postransactionitem' AND column_name='promotion_discount'
    \"\"\")
    if not c.fetchone():
        print('  Adding pos_postransactionitem.promotion_discount ...')
        c.execute(\"\"\"
            ALTER TABLE pos_postransactionitem
            ADD COLUMN promotion_discount numeric(10,2) NOT NULL DEFAULT 0
        \"\"\")
        print('  promotion_discount added OK')
    else:
        print('  promotion_discount OK')

    # 2) promotion_group_name
    c.execute(\"\"\"
        SELECT 1 FROM information_schema.columns
        WHERE table_name='pos_postransactionitem' AND column_name='promotion_group_name'
    \"\"\")
    if not c.fetchone():
        print('  Adding pos_postransactionitem.promotion_group_name ...')
        c.execute(\"\"\"
            ALTER TABLE pos_postransactionitem
            ADD COLUMN promotion_group_name varchar(200) NOT NULL DEFAULT ''
        \"\"\")
        print('  promotion_group_name added OK')
    else:
        print('  promotion_group_name OK')

    # 3) Marcar migración 0009 como aplicada para que Django no la reintente
    c.execute(\"SELECT 1 FROM django_migrations WHERE app='pos' AND name='0009_item_promotion_discount_and_group'\")
    if not c.fetchone():
        c.execute(\"\"\"
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('pos', '0009_item_promotion_discount_and_group', NOW())
        \"\"\")
        print('  Marked pos.0009 as applied')
" 2>&1 || echo "WARNING: pos promo fields repair skipped"

# Defensive: ensure purchase_purchaseitem.packaging_id exists (migration 0005).
# Sin esto, crear una OC con empaque explota con:
#   column "packaging_id" of relation "purchase_purchaseitem" does not exist
echo "Verifying purchase_purchaseitem.packaging_id..."
python -c "
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
import django; django.setup()
from django.db import connection
if connection.vendor != 'postgresql':
    print('  SQLite: skip')
    sys.exit(0)
with connection.cursor() as c:
    c.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='purchase_purchaseitem')\")
    if not c.fetchone()[0]:
        print('  purchase_purchaseitem no existe aun, skip')
        sys.exit(0)
    c.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='stocks_productpackaging')\")
    if not c.fetchone()[0]:
        print('  stocks_productpackaging no existe aun, skip')
        sys.exit(0)

    # 1) Agregar columna packaging_id si falta
    c.execute(\"\"\"
        SELECT 1 FROM information_schema.columns
        WHERE table_name='purchase_purchaseitem' AND column_name='packaging_id'
    \"\"\")
    if not c.fetchone():
        print('  Adding purchase_purchaseitem.packaging_id ...')
        c.execute(\"\"\"
            ALTER TABLE purchase_purchaseitem
            ADD COLUMN packaging_id bigint NULL
                REFERENCES stocks_productpackaging(id)
                DEFERRABLE INITIALLY DEFERRED
        \"\"\")
        c.execute('CREATE INDEX purchase_purchaseitem_packaging_id_idx ON purchase_purchaseitem(packaging_id)')
        print('  packaging_id column added OK')
    else:
        print('  purchase_purchaseitem.packaging_id OK')

    # 2) Marcar migración 0005 como aplicada para que Django no la reintente
    c.execute(\"SELECT 1 FROM django_migrations WHERE app='purchase' AND name='0005_purchaseitem_packaging_alter_purchaseitem_quantity_and_more'\")
    if not c.fetchone():
        c.execute(\"\"\"
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('purchase', '0005_purchaseitem_packaging_alter_purchaseitem_quantity_and_more', NOW())
        \"\"\")
        print('  Marked purchase.0005 as applied')
" 2>&1 || echo "WARNING: purchase packaging field repair skipped"

# Defensive: ensure expenses_expensecategory.is_investment exists (migration 0004).
# Sin esto, cualquier view que cargue ExpenseCategory explota con:
#   column expenses_expensecategory.is_investment does not exist
# Pasa por ejemplo al recibir una OC (purchase_receive crea Expense -> ExpenseCategory).
echo "Verifying expenses_expensecategory.is_investment..."
python -c "
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
import django; django.setup()
from django.db import connection
if connection.vendor != 'postgresql':
    print('  SQLite: skip')
    sys.exit(0)
with connection.cursor() as c:
    c.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='expenses_expensecategory')\")
    if not c.fetchone()[0]:
        print('  expenses_expensecategory no existe aun, skip')
        sys.exit(0)

    # 1) Agregar columna is_investment si falta
    c.execute(\"\"\"
        SELECT 1 FROM information_schema.columns
        WHERE table_name='expenses_expensecategory' AND column_name='is_investment'
    \"\"\")
    if not c.fetchone():
        print('  Adding expenses_expensecategory.is_investment ...')
        c.execute(\"\"\"
            ALTER TABLE expenses_expensecategory
            ADD COLUMN is_investment boolean NOT NULL DEFAULT false
        \"\"\")
        print('  is_investment column added OK')

        # Marcar Compras/mercaderia como inversion (mismo data migration que 0004)
        c.execute(\"UPDATE expenses_expensecategory SET is_investment=true WHERE LOWER(name)='compras'\")
        c.execute(\"UPDATE expenses_expensecategory SET is_investment=true WHERE LOWER(name) LIKE '%mercaderia%' OR LOWER(name) LIKE '%mercaderia%'\")
        print('  Marked Compras/mercaderia as investment OK')
    else:
        print('  expenses_expensecategory.is_investment OK')

    # 2) Marcar migración 0004 como aplicada para que Django no la reintente
    c.execute(\"SELECT 1 FROM django_migrations WHERE app='expenses' AND name='0004_expensecategory_is_investment'\")
    if not c.fetchone():
        c.execute(\"\"\"
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('expenses', '0004_expensecategory_is_investment', NOW())
        \"\"\")
        print('  Marked expenses.0004 as applied')
" 2>&1 || echo "WARNING: expenses is_investment repair skipped"

# Defensive: ensure promotions_promotion.applies_to_packaging_type exists (migration 0005).
# Mismo patron: si la migracion 0005 no corrio pero el codigo la usa, el POS
# rompe en apply_promotions. Se agrega columna con default 'unit' y se marca la
# migracion como aplicada.
echo "Verifying promotions_promotion.applies_to_packaging_type..."
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='promotions_promotion')\")
    if not c.fetchone()[0]:
        print('  promotions_promotion no existe aun, skip')
        raise SystemExit(0)

    c.execute(\"\"\"
        SELECT 1 FROM information_schema.columns
        WHERE table_name='promotions_promotion' AND column_name='applies_to_packaging_type'
    \"\"\")
    if not c.fetchone():
        print('  Adding promotions_promotion.applies_to_packaging_type ...')
        c.execute(\"\"\"
            ALTER TABLE promotions_promotion
            ADD COLUMN applies_to_packaging_type varchar(20) NOT NULL DEFAULT 'unit'
        \"\"\")
        print('  applies_to_packaging_type column added OK')
    else:
        print('  applies_to_packaging_type OK')

    c.execute(\"SELECT 1 FROM django_migrations WHERE app='promotions' AND name='0005_promotion_applies_to_packaging_type'\")
    if not c.fetchone():
        c.execute(\"\"\"
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('promotions', '0005_promotion_applies_to_packaging_type', NOW())
        \"\"\")
        print('  Marked promotions.0005 as applied')
" 2>&1 || echo "WARNING: promotions applies_to_packaging_type repair skipped"

# Defensive: ensure expenses_expense.affects_cash_drawer exists (migration 0005).
# Sin esto, crear/editar gastos explota con:
#   column expenses_expense.affects_cash_drawer does not exist
# Y el cierre Z sigue contando gastos operativos como egresos del cajon.
echo "Verifying expenses_expense.affects_cash_drawer..."
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='expenses_expense')\")
    if not c.fetchone()[0]:
        print('  expenses_expense no existe aun, skip')
        raise SystemExit(0)

    c.execute(\"\"\"
        SELECT 1 FROM information_schema.columns
        WHERE table_name='expenses_expense' AND column_name='affects_cash_drawer'
    \"\"\")
    if not c.fetchone():
        print('  Adding expenses_expense.affects_cash_drawer ...')
        c.execute(\"\"\"
            ALTER TABLE expenses_expense
            ADD COLUMN affects_cash_drawer boolean NOT NULL DEFAULT false
        \"\"\")
        print('  affects_cash_drawer column added OK')
    else:
        print('  affects_cash_drawer OK')

    c.execute(\"SELECT 1 FROM django_migrations WHERE app='expenses' AND name='0005_expense_affects_cash_drawer'\")
    if not c.fetchone():
        c.execute(\"\"\"
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('expenses', '0005_expense_affects_cash_drawer', NOW())
        \"\"\")
        print('  Marked expenses.0005 as applied')
" 2>&1 || echo "WARNING: expenses affects_cash_drawer repair skipped"

# Setup initial data
echo "Setting up initial data..."
python manage.py setup_initial_data || echo "WARNING: setup_initial_data failed, continuing..."

# Flush business data if requested (set FLUSH_ON_DEPLOY=true in Railway env vars, then remove it after deploy)
if [ "$FLUSH_ON_DEPLOY" = "true" ]; then
    echo "*** FLUSH_ON_DEPLOY detected — wiping all business data (keeping users)... ***"
    python manage.py flush_data --yes || echo "WARNING: flush_data failed, continuing..."
    echo "*** Flush complete. REMOVE the FLUSH_ON_DEPLOY env var now to prevent re-flush. ***"
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "WARNING: collectstatic failed, continuing..."

echo "Starting gunicorn on port ${PORT:-8000}..."
exec gunicorn superrecord.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --threads 2 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --timeout 120 \
    --log-file - \
    --access-logfile - \
    --error-logfile - \
    --preload
