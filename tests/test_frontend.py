"""
Script de prueba del frontend - CHE GOLOSO
Verifica todas las URLs y busca errores JavaScript/CSS
"""
import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

print('=' * 70)
print('PRUEBA COMPLETA DEL FRONTEND - CHE GOLOSO')
print('=' * 70)

User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()

client = Client()
client.force_login(admin)

# Lista de URLs principales del sistema
urls_to_test = [
    # Accounts
    ('/', 'Home/Redirect'),
    ('/login/', 'Login'),
    ('/dashboard/', 'Dashboard'),
    
    # Stocks
    ('/stocks/', 'Lista de Productos'),
    ('/stocks/create/', 'Crear Producto'),
    ('/stocks/categories/', 'Categorias'),
    ('/stocks/categories/create/', 'Crear Categoria'),
    ('/stocks/units/', 'Unidades de Medida'),
    ('/stocks/movements/', 'Movimientos de Stock'),
    
    # CashRegister
    ('/cashregister/', 'Lista de Cajas'),
    ('/cashregister/shifts/', 'Turnos'),
    ('/cashregister/open/', 'Abrir Turno'),
    
    # POS
    ('/pos/', 'Punto de Venta'),
    
    # Promotions
    ('/promotions/', 'Lista de Promociones'),
    ('/promotions/create/', 'Crear Promocion'),
    
    # Expenses
    ('/expenses/', 'Lista de Gastos'),
    ('/expenses/create/', 'Crear Gasto'),
    ('/expenses/categories/', 'Categorias de Gastos'),
    
    # Purchase
    ('/purchase/suppliers/', 'Proveedores'),
    ('/purchase/suppliers/create/', 'Crear Proveedor'),
    ('/purchase/', 'Lista de Compras'),
    ('/purchase/create/', 'Crear Compra'),
    
    # Sales/Reports
    ('/sales/', 'Reportes'),
    
    # Assistant
    ('/assistant/', 'Asistente AI'),
    ('/assistant/settings/', 'Config Asistente'),
    
    # Company
    ('/company/settings/', 'Config Empresa'),
]

errors_found = []
warnings_found = []

print('\n--- VERIFICACION DE URLs ---\n')

for url, name in urls_to_test:
    try:
        response = client.get(url, follow=True)
        content = response.content.decode('utf-8', errors='ignore')
        
        # Verificar status
        if response.status_code == 200:
            status = '[OK]'
            
            # Buscar errores comunes en el HTML
            error_patterns = [
                (r'TemplateSyntaxError', 'Error de sintaxis de template'),
                (r'TemplateDoesNotExist', 'Template no existe'),
                (r'NoReverseMatch', 'URL reverse no encontrado'),
                (r'AttributeError', 'Error de atributo'),
                (r'KeyError', 'Error de clave'),
                (r'TypeError', 'Error de tipo'),
                (r'ValueError', 'Error de valor'),
                (r'DoesNotExist', 'Objeto no existe'),
                (r'undefined is not', 'Error JavaScript'),
                (r'Uncaught', 'Error JavaScript no capturado'),
                (r'SyntaxError', 'Error de sintaxis'),
            ]
            
            for pattern, desc in error_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    errors_found.append(f'{url}: {desc}')
                    status = '[WARN]'
            
            # Verificar referencias a archivos estáticos rotos
            static_refs = re.findall(r'src=["\']([^"\']+)["\']|href=["\']([^"\']+\.(?:js|css))["\']', content)
            
        elif response.status_code == 302:
            status = '[REDIR]'
        elif response.status_code == 404:
            status = '[404]'
            errors_found.append(f'{url}: Pagina no encontrada')
        elif response.status_code == 500:
            status = '[500]'
            errors_found.append(f'{url}: Error del servidor')
        else:
            status = f'[{response.status_code}]'
            
        print(f'{status:8} {name:25} {url}')
        
    except Exception as e:
        print(f'[ERROR]  {name:25} {url}')
        errors_found.append(f'{url}: {str(e)[:50]}')

# Verificar templates existentes
print('\n--- VERIFICACION DE TEMPLATES ---\n')

import os
from pathlib import Path

template_dir = Path('templates')
required_templates = [
    'base.html',
    'accounts/login.html',
    'accounts/dashboard.html',
    'stocks/product_list.html',
    'stocks/product_form.html',
    'stocks/category_list.html',
    'cashregister/register_list.html',
    'cashregister/shift_list.html',
    'pos/pos.html',
    'promotions/promotion_list.html',
    'promotions/promotion_form.html',
    'expenses/expense_list.html',
    'expenses/expense_form.html',
    'purchase/supplier_list.html',
    'purchase/purchase_list.html',
    'sales/reports_dashboard.html',
    'assistant/chat.html',
    'assistant/settings.html',
    'company/settings.html',
]

for template in required_templates:
    path = template_dir / template
    if path.exists():
        print(f'[OK]     {template}')
    else:
        print(f'[MISS]   {template}')
        warnings_found.append(f'Template faltante: {template}')

# Verificar archivos estáticos
print('\n--- VERIFICACION DE ARCHIVOS ESTATICOS ---\n')

static_dir = Path('static')
required_statics = [
    'css/styles.css',
    'js/pos.js',
]

for static_file in required_statics:
    path = static_dir / static_file
    if path.exists():
        print(f'[OK]     {static_file}')
    else:
        print(f'[MISS]   {static_file}')
        warnings_found.append(f'Archivo estatico faltante: {static_file}')

# Listar archivos JS que existen
js_dir = static_dir / 'js'
if js_dir.exists():
    print('\nArchivos JS encontrados:')
    for f in js_dir.iterdir():
        print(f'  - {f.name}')

css_dir = static_dir / 'css'
if css_dir.exists():
    print('\nArchivos CSS encontrados:')
    for f in css_dir.iterdir():
        print(f'  - {f.name}')

# Resumen
print('\n' + '=' * 70)
print('RESUMEN')
print('=' * 70)

if errors_found:
    print(f'\n[!] ERRORES ENCONTRADOS ({len(errors_found)}):')
    for err in errors_found:
        print(f'    - {err}')
else:
    print('\n[OK] No se encontraron errores criticos')

if warnings_found:
    print(f'\n[!] ADVERTENCIAS ({len(warnings_found)}):')
    for warn in warnings_found:
        print(f'    - {warn}')

print('\n' + '=' * 70)
