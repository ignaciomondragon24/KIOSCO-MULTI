import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
django.setup()

from django.db import connection

# Drop signage tables
with connection.cursor() as cursor:
    tables = ['signage_signitem', 'signage_signbatch', 'signage_signgeneration', 'signage_signtemplate']
    for t in tables:
        try:
            cursor.execute(f'DROP TABLE IF EXISTS {t}')
            print(f'Dropped: {t}')
        except Exception as e:
            print(f'Error dropping {t}: {e}')
    
    # Also clean up django_migrations for signage
    cursor.execute("DELETE FROM django_migrations WHERE app = 'signage'")
    print(f'Cleaned django_migrations for signage')

# Verify the system loads
from django.test import Client
from django.contrib.auth import get_user_model
User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()
c = Client()
c.force_login(admin)

pages = [
    ('/', 'Root redirect'),
    ('/dashboard/', 'Dashboard'),
    ('/pos/', 'POS'),
    ('/stocks/', 'Stocks'),
    ('/purchase/', 'Purchase'),
    ('/expenses/', 'Expenses'),
    ('/sales/', 'Sales'),
    ('/promotions/', 'Promotions'),
]
print()
all_ok = True
for url, name in pages:
    r = c.get(url, follow=True)
    status = 'OK' if r.status_code == 200 else f'FAIL({r.status_code})'
    if r.status_code != 200:
        all_ok = False
    print(f'{name}: {status}')

# Check that /signage/ returns 404
r = c.get('/signage/')
print(f'Signage (should be 404): {r.status_code}')
if r.status_code == 404:
    print('CORRECT - signage is removed')
else:
    all_ok = False
    print('ERROR - signage still accessible!')

print()
if all_ok:
    print('ALL CHECKS PASSED - Signage fully removed')
else:
    print('SOME CHECKS FAILED')
