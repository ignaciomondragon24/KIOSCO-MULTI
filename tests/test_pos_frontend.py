"""
Test POS Frontend - Comprehensive Testing
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

from stocks.models import Product, ProductCategory, UnitOfMeasure
from cashregister.models import CashRegister, CashShift, PaymentMethod
from pos.models import POSSession, POSTransaction
from decimal import Decimal
import uuid

User = get_user_model()


def setup_test_environment():
    """Create all necessary test data"""
    print("📦 Configurando entorno de prueba...")
    
    # Create test user with superuser privileges for full access
    user, created = User.objects.get_or_create(
        username='pos_test_user',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"   ✅ Usuario creado: {user.username}")
    else:
        # Ensure superuser flag is set
        user.is_superuser = True
        user.set_password('testpass123')
        user.save()
        print(f"   ✅ Usuario existente: {user.username}")
    
    # Create cash register
    cash_register, _ = CashRegister.objects.get_or_create(
        name='TEST_CAJA_01',
        defaults={'is_active': True}
    )
    print(f"   ✅ Caja registradora: {cash_register.name}")
    
    # Create or get open shift
    shift = CashShift.objects.filter(
        cashier=user,
        status='open'
    ).first()
    
    if not shift:
        shift = CashShift.objects.create(
            cash_register=cash_register,
            cashier=user,
            status='open',
            initial_amount=Decimal('1000.00')
        )
        print(f"   ✅ Turno creado: {shift.id}")
    else:
        print(f"   ✅ Turno existente: {shift.id}")
    
    # Create category and unit
    category, _ = ProductCategory.objects.get_or_create(
        name='TEST_CATEGORY',
        defaults={'description': 'Test category'}
    )
    unit, _ = UnitOfMeasure.objects.get_or_create(
        name='Unidad',
        defaults={'abbreviation': 'U'}
    )
    
    # Create test product
    sku = f'TEST-{uuid.uuid4().hex[:6].upper()}'
    product, created = Product.objects.get_or_create(
        barcode='7790001000016',
        defaults={
            'sku': sku,
            'name': 'PRODUCTO TEST POS',
            'category': category,
            'unit_of_measure': unit,
            'purchase_price': Decimal('100.00'),
            'sale_price': Decimal('150.00'),
            'current_stock': 100,
            'is_active': True
        }
    )
    if created:
        print(f"   ✅ Producto creado: {product.name}")
    else:
        print(f"   ✅ Producto existente: {product.name}")
    
    return user, shift, product


def run_pos_api_tests(user, shift, product):
    """Test all POS API endpoints"""
    print("\n" + "=" * 60)
    print("🧪 PROBANDO API DEL POS")
    print("=" * 60)
    
    client = Client()
    
    # Login
    login_success = client.login(username='pos_test_user', password='testpass123')
    print(f"\n✅ Login: {'OK' if login_success else 'FAILED'}")
    
    if not login_success:
        print("❌ No se pudo hacer login, abortando pruebas")
        return
    
    # Test 1: Main POS View
    print("\n" + "-" * 40)
    print("📍 Test 1: Vista principal del POS")
    response = client.get(reverse('pos:main'))
    
    if response.status_code == 200:
        print(f"   ✅ GET /pos/ - Status: {response.status_code}")
        # Try to get transaction from context
        if response.context:
            transaction = response.context.get('transaction')
            if transaction:
                print(f"   ✅ Transaction ID: {transaction.id}")
            else:
                print("   ⚠️ No transaction in context")
        else:
            print("   ⚠️ No context available")
            # Try to get a pending transaction from the database
            transaction = POSTransaction.objects.filter(status='pending').last()
    elif response.status_code == 302:
        print(f"   ⚠️ Redirect to: {response.url}")
        # Need to follow redirect, might need to open shift
        return
    else:
        print(f"   ❌ GET /pos/ - Status: {response.status_code}")
        return
    
    # Test 2: API Search
    print("\n" + "-" * 40)
    print("📍 Test 2: API de Búsqueda")
    
    # Search by name
    response = client.get(reverse('pos:api_search'), {'q': 'TEST'})
    if response.status_code == 200:
        data = response.json()
        products_found = len(data.get('products', []))
        print(f"   ✅ Búsqueda por nombre 'TEST' - {products_found} resultados")
    else:
        print(f"   ❌ Búsqueda por nombre - Status: {response.status_code}")
    
    # Search by barcode
    response = client.get(reverse('pos:api_search'), {'q': '7790001000016'})
    if response.status_code == 200:
        data = response.json()
        products_found = len(data.get('products', []))
        print(f"   ✅ Búsqueda por código '7790001000016' - {products_found} resultados")
    else:
        print(f"   ❌ Búsqueda por código - Status: {response.status_code}")
    
    if not transaction:
        print("   ⚠️ No hay transaction activa, no se pueden probar más APIs")
        return
    
    # Test 3: Add to Cart
    print("\n" + "-" * 40)
    print("📍 Test 3: Agregar al Carrito")
    
    response = client.post(
        reverse('pos:api_cart_add'),
        data=json.dumps({
            'transaction_id': transaction.id,
            'product_id': product.id,
            'quantity': 2
        }),
        content_type='application/json'
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success: {data.get('success', False)}")
        if 'cart' in data:
            items_count = len(data.get('cart', {}).get('items', []))
            print(f"   ✅ Items en carrito: {items_count}")
    else:
        print(f"   ❌ Agregar al carrito - Status: {response.status_code}")
        try:
            print(f"   ❌ Response: {response.content.decode()[:200]}")
        except:
            pass
    
    # Test 4: Get Transaction Detail
    print("\n" + "-" * 40)
    print("📍 Test 4: Detalle de Transacción")
    
    response = client.get(reverse('pos:api_transaction_detail', args=[transaction.id]))
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Transaction ID: {data.get('id')}")
        print(f"   ✅ Items: {len(data.get('items', []))}")
        print(f"   ✅ Total: ${data.get('total', 0)}")
    else:
        print(f"   ❌ Get transaction - Status: {response.status_code}")
    
    # Test 5: Calculate Cost Total (for cost sale)
    print("\n" + "-" * 40)
    print("📍 Test 5: Calcular Costo Total")
    
    response = client.get(reverse('pos:api_calculate_cost_total', args=[transaction.id]))
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Costo total: ${data.get('cost_total', 0)}")
    else:
        print(f"   ❌ Calculate cost - Status: {response.status_code}")
    
    # Test 6: Update Cart Item
    print("\n" + "-" * 40)
    print("📍 Test 6: Actualizar Cantidad")
    
    transaction.refresh_from_db()
    items = transaction.items.all()
    
    if items.exists():
        item = items.first()
        response = client.post(
            reverse('pos:api_cart_update', args=[item.id]),
            data=json.dumps({'quantity': 3}),
            content_type='application/json'
        )
        if response.status_code == 200:
            data = response.json()
            new_qty = data.get('item', {}).get('quantity', 'N/A')
            print(f"   ✅ Nueva cantidad: {new_qty}")
        else:
            print(f"   ❌ Update item - Status: {response.status_code}")
    else:
        print("   ⚠️ No hay items para actualizar")
    
    # Test 7: Last Transaction
    print("\n" + "-" * 40)
    print("📍 Test 7: Última Transacción")
    
    response = client.get(reverse('pos:api_last_transaction'))
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Has last: {data.get('has_last', False)}")
    else:
        print(f"   ❌ Last transaction - Status: {response.status_code}")
    
    # Test 8: Checkout
    print("\n" + "-" * 40)
    print("📍 Test 8: Checkout (Finalizar Venta)")
    
    # Get or create payment method
    payment_method, _ = PaymentMethod.objects.get_or_create(
        code='cash',
        defaults={
            'name': 'Efectivo',
            'is_active': True,
            'requires_change': True
        }
    )
    
    transaction.refresh_from_db()
    response = client.post(
        reverse('pos:api_checkout'),
        data=json.dumps({
            'transaction_id': transaction.id,
            'payments': [
                {
                    'method_code': 'cash',
                    'amount': 500.00
                }
            ]
        }),
        content_type='application/json'
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success: {data.get('success', False)}")
        if data.get('success'):
            print(f"   ✅ Ticket: {data.get('ticket_number')}")
            print(f"   ✅ Total: ${data.get('total')}")
            print(f"   ✅ Vuelto: ${data.get('change', 0)}")
    else:
        print(f"   ❌ Checkout - Status: {response.status_code}")
        try:
            print(f"   ❌ Error: {response.content.decode()[:200]}")
        except:
            pass
    
    # Test 9: Print Ticket
    print("\n" + "-" * 40)
    print("📍 Test 9: Imprimir Ticket")
    
    completed = POSTransaction.objects.filter(status='completed').last()
    if completed:
        response = client.get(reverse('pos:print_ticket', args=[completed.id]))
        if response.status_code == 200:
            content_type = response.get('Content-Type', 'unknown')
            print(f"   ✅ Ticket generado - Type: {content_type[:30]}")
        else:
            print(f"   ❌ Print ticket - Status: {response.status_code}")
    else:
        print("   ⚠️ No hay transacciones completadas")
    
    # Test 10: Suspended Transactions
    print("\n" + "-" * 40)
    print("📍 Test 10: Transacciones Suspendidas")
    
    response = client.get(reverse('pos:suspended'))
    if response.status_code == 200:
        print(f"   ✅ Vista suspendidas - OK")
    else:
        print(f"   ❌ Suspendidas - Status: {response.status_code}")


def test_other_modules():
    """Test other module frontends"""
    print("\n" + "=" * 60)
    print("🧪 PROBANDO OTROS MÓDULOS")
    print("=" * 60)
    
    client = Client()
    
    # Create superuser for full access
    user, created = User.objects.get_or_create(
        username='admin_test',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    user.set_password('admin123')
    user.save()
    client.login(username='admin_test', password='admin123')
    
    # Test URLs grouped by module
    modules = {
        'Accounts': [
            ('accounts:dashboard', 'Dashboard'),
            ('accounts:user_list', 'Usuarios'),
        ],
        'Stocks': [
            ('stocks:product_list', 'Productos'),
            ('stocks:category_list', 'Categorías'),
            ('stocks:low_stock', 'Low Stock'),
            ('stocks:price_list', 'Lista de Precios'),
        ],
        'Cash Register': [
            ('cashregister:dashboard', 'Dashboard Caja'),
            ('cashregister:register_list', 'Registros'),
            ('cashregister:shift_list', 'Turnos'),
            ('cashregister:movement_list', 'Movimientos'),
        ],
        'Sales': [
            ('sales:dashboard', 'Dashboard Ventas'),
            ('sales:sale_list', 'Ventas'),
        ],
        'Expenses': [
            ('expenses:expense_list', 'Gastos'),
            ('expenses:category_list', 'Categorías Gastos'),
            ('expenses:recurring_list', 'Gastos Recurrentes'),
        ],
        'Purchase': [
            ('purchase:supplier_list', 'Proveedores'),
            ('purchase:purchase_list', 'Compras'),
        ],
        'Promotions': [
            ('promotions:promotion_list', 'Promociones'),
        ],
        'Company': [
            ('company:settings', 'Config. Empresa'),
            ('company:branch_list', 'Sucursales'),
        ],
    }
    
    total_passed = 0
    total_failed = 0
    
    for module_name, urls in modules.items():
        print(f"\n📦 {module_name}:")
        for url_name, description in urls:
            try:
                url = reverse(url_name)
                response = client.get(url)
                
                if response.status_code == 200:
                    print(f"   ✅ {description} - OK")
                    total_passed += 1
                elif response.status_code == 302:
                    print(f"   ✅ {description} - Redirect")
                    total_passed += 1
                else:
                    print(f"   ❌ {description} - {response.status_code}")
                    total_failed += 1
            except Exception as e:
                print(f"   ❌ {description} - Error: {str(e)[:50]}")
                total_failed += 1
    
    print(f"\n📊 Total: {total_passed} OK, {total_failed} fallidos")


def test_forms():
    """Test form submissions"""
    print("\n" + "=" * 60)
    print("🧪 PROBANDO FORMULARIOS")
    print("=" * 60)
    
    client = Client()
    
    user, _ = User.objects.get_or_create(
        username='form_test',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    user.set_password('test123')
    user.save()
    client.login(username='form_test', password='test123')
    
    # Test Category Creation
    print("\n📍 Crear Categoría:")
    response = client.post(reverse('stocks:category_create'), {
        'name': f'TEST_CAT_{uuid.uuid4().hex[:4]}',
        'description': 'Test'
    })
    if response.status_code in [200, 302]:
        print(f"   ✅ Status: {response.status_code}")
    else:
        print(f"   ❌ Status: {response.status_code}")
    
    # Test Expense Category Creation
    print("\n📍 Crear Categoría de Gastos:")
    response = client.post(reverse('expenses:category_create'), {
        'name': f'TEST_EXP_{uuid.uuid4().hex[:4]}',
        'description': 'Test expense category'
    })
    if response.status_code in [200, 302]:
        print(f"   ✅ Status: {response.status_code}")
    else:
        print(f"   ❌ Status: {response.status_code}")


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 PRUEBAS COMPLETAS DEL FRONTEND - CHE GOLOSO")
    print("=" * 60)
    
    user, shift, product = setup_test_environment()
    run_pos_api_tests(user, shift, product)
    test_other_modules()
    test_forms()
    
    print("\n" + "=" * 60)
    print("✅ PRUEBAS COMPLETADAS")
    print("=" * 60)
