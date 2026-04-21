"""
Audit script: checks all URL references in templates and views for issues.
"""
import os, re, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')

import django
django.setup()

from django.urls import reverse, NoReverseMatch

# ─── 1. Check all named URLs resolve ────────────────────────────────────────
print("\n" + "="*60)
print("1. NAMED URL RESOLUTION")
print("="*60)

from django.urls import get_resolver
resolver = get_resolver()
all_names = [k for k in resolver.reverse_dict.keys() if isinstance(k, str)]
print(f"Total named URLs: {len(all_names)}")

# ─── 2. Scan templates for URL references ───────────────────────────────────
print("\n" + "="*60)
print("2. URL REFERENCES IN TEMPLATES")
print("="*60)

templates_dir = 'templates'
broken = []
ok_count = 0

for root, dirs, files in os.walk(templates_dir):
    for fname in files:
        if not fname.endswith('.html'):
            continue
        path = os.path.join(root, fname)
        with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
            content = fp.read()
        for m in re.finditer(r"\{%\s*url\s+'([^']+)'", content):
            url_name = m.group(1)
            if ':' not in url_name:
                continue
            # Try no args, then with pk=1
            resolved = False
            for args in [[], [1]]:
                try:
                    reverse(url_name, args=args)
                    resolved = True
                    break
                except NoReverseMatch:
                    pass
            if resolved:
                ok_count += 1
            else:
                broken.append((path.replace('templates\\', ''), url_name))

print(f"OK:     {ok_count}")
print(f"BROKEN: {len(broken)}")
for tmpl, name in broken:
    print(f"  BROKEN  {tmpl}: '{name}'")

# ─── 3. Check views for common issues ────────────────────────────────────────
print("\n" + "="*60)
print("3. VIEWS — MISSING TEMPLATE CHECKS")
print("="*60)

view_issues = []
apps = ['accounts','pos','cashregister','stocks','promotions','signage',
        'purchase','expenses','sales','company','mercadopago','assistant']

for app in apps:
    views_path = os.path.join(app, 'views.py')
    if not os.path.exists(views_path):
        continue
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    for m in re.finditer(r"render\(request,\s*['\"]([^'\"]+)['\"]", content):
        tmpl_path = os.path.join('templates', m.group(1))
        if not os.path.exists(tmpl_path):
            view_issues.append(f"{views_path}: template '{m.group(1)}' NOT FOUND")

if view_issues:
    for i in view_issues:
        print(f"  MISSING  {i}")
else:
    print("  All render() template references found OK")

# ─── 4. Check models for missing migrations ──────────────────────────────────
print("\n" + "="*60)
print("4. PENDING MIGRATIONS CHECK")
print("="*60)

from django.db.migrations.executor import MigrationExecutor
from django.db import connection

executor = MigrationExecutor(connection)
plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
if plan:
    print(f"  PENDING MIGRATIONS: {len(plan)}")
    for migration, _ in plan:
        print(f"    - {migration}")
else:
    print("  No pending migrations")

# ─── 5. Check key model field issues ─────────────────────────────────────────
print("\n" + "="*60)
print("5. KEY MODEL SANITY CHECKS")
print("="*60)

from stocks.models import Product
from purchase.models import Purchase, PurchaseItem, Supplier
from expenses.models import Expense
from pos.models import Transaction
from cashregister.models import CashRegister, Shift

print(f"  Products (active):    {Product.objects.filter(is_active=True).count()}")
print(f"  Products (total):     {Product.objects.count()}")
print(f"  Products with no SKU: {Product.objects.filter(sku='').count()}")
print(f"  Products with no sale_price: {Product.objects.filter(sale_price=0).count()}")
print(f"  Purchases total:      {Purchase.objects.count()}")
print(f"  PurchaseItems total:  {PurchaseItem.objects.count()}")
print(f"  Expenses total:       {Expense.objects.count()}")
print(f"  Transactions(POS):    {Transaction.objects.count()}")
print(f"  CashRegisters:        {CashRegister.objects.count()}")
print(f"  Shifts (open):        {Shift.objects.filter(status='open').count()}")
print(f"  Suppliers:            {Supplier.objects.count()}")

# ─── 6. Check base.html for nav links ─────────────────────────────────────────
print("\n" + "="*60)
print("6. BASE.HTML NAV LINK CHECK")
print("="*60)

with open('templates/base.html', 'r', encoding='utf-8') as f:
    base_content = f.read()

base_broken = []
for m in re.finditer(r"\{%\s*url\s+'([^']+)'", base_content):
    url_name = m.group(1)
    if ':' not in url_name:
        continue
    resolved = False
    for args in [[], [1]]:
        try:
            reverse(url_name, args=args)
            resolved = True
            break
        except NoReverseMatch:
            pass
    if not resolved:
        base_broken.append(url_name)

if base_broken:
    print(f"  BROKEN nav links in base.html: {len(base_broken)}")
    for b in base_broken:
        print(f"    - '{b}'")
else:
    print("  All base.html nav links OK")

# ─── 7. Check accounts dashboard links ────────────────────────────────────────
print("\n" + "="*60)
print("7. DASHBOARD TEMPLATE CHECK")
print("="*60)

dash_path = 'templates/accounts/dashboard.html'
if os.path.exists(dash_path):
    with open(dash_path, 'r', encoding='utf-8') as f:
        dash_content = f.read()
    dash_broken = []
    for m in re.finditer(r"\{%\s*url\s+'([^']+)'", dash_content):
        url_name = m.group(1)
        if ':' not in url_name:
            continue
        resolved = False
        for args in [[], [1]]:
            try:
                reverse(url_name, args=args)
                resolved = True
                break
            except NoReverseMatch:
                pass
        if not resolved:
            dash_broken.append(url_name)
    if dash_broken:
        print(f"  BROKEN links in dashboard.html: {len(dash_broken)}")
        for b in dash_broken:
            print(f"    - '{b}'")
    else:
        print("  All dashboard.html links OK")

# ─── 8. Check JS files for broken API endpoints ────────────────────────────────
print("\n" + "="*60)
print("8. STATIC JS API CALLS CHECK")
print("="*60)

js_dir = 'static/js'
js_api_issues = []
api_pattern = re.compile(r"fetch\s*\(\s*['\"]([^'\"]+)['\"]")
for fname in os.listdir(js_dir):
    if not fname.endswith('.js'):
        continue
    with open(os.path.join(js_dir, fname), 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    for m in api_pattern.finditer(content):
        url = m.group(1)
        # Check if it's a hardcoded URL (not a template variable)
        if url.startswith('/') and '{{' not in url:
            js_api_issues.append(f"{fname}: fetch('{url}')")

if js_api_issues:
    print(f"  Hardcoded API URLs in JS (may be fine):")
    for i in js_api_issues:
        print(f"    {i}")
else:
    print("  No hardcoded API URLs found")

print("\n" + "="*60)
print("AUDIT COMPLETE")
print("="*60 + "\n")
