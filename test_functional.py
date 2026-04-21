#!/usr/bin/env python
"""
Script de pruebas funcionales para CHE GOLOSO
Verifica que todos los módulos funcionen correctamente
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date

User = get_user_model()


class Colors:
    """Colores para output en consola."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def ok(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def fail(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")


def section(msg):
    print(f"\n{Colors.YELLOW}{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}{Colors.END}")


def test_login(client, username='admin', password='admin123'):
    """Probar login."""
    response = client.post('/login/', {
        'username': username,
        'password': password
    }, follow=True)
    
    if response.status_code == 200 and 'dashboard' in response.request['PATH_INFO'].lower() or 'home' in response.request['PATH_INFO'].lower():
        return True
    return False


def run_tests():
    """Ejecutar todas las pruebas funcionales."""
    results = {'passed': 0, 'failed': 0}
    client = Client()
    
    # =========================================
    section("1. PRUEBAS DE AUTENTICACIÓN")
    # =========================================
    
    # Verificar que existe usuario admin
    try:
        admin = User.objects.get(username='admin')
        ok("Usuario admin existe")
        results['passed'] += 1
    except User.DoesNotExist:
        fail("Usuario admin NO existe")
        results['failed'] += 1
        # Crear admin para continuar pruebas
        admin = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
        info("Creado usuario admin para pruebas")
    
    # Probar login
    if test_login(client):
        ok("Login funciona correctamente")
        results['passed'] += 1
    else:
        fail("Login NO funciona")
        results['failed'] += 1
    
    # =========================================
    section("2. PRUEBAS DE GASTOS (Expenses)")
    # =========================================
    
    from expenses.models import ExpenseCategory, Expense
    
    # Crear categoría de gasto
    try:
        cat, created = ExpenseCategory.objects.get_or_create(
            name='Servicios Test',
            defaults={'description': 'Categoría de prueba', 'color': '#3498db'}
        )
        ok(f"Categoría de gasto {'creada' if created else 'existe'}: {cat.name}")
        results['passed'] += 1
    except Exception as e:
        fail(f"Error creando categoría de gasto: {e}")
        results['failed'] += 1
        cat = None
    
    # Crear gasto
    if cat:
        try:
            expense = Expense.objects.create(
                category=cat,
                description='Gasto de prueba',
                amount=Decimal('1500.00'),
                expense_date=date.today(),
                payment_method='cash',
                created_by=admin
            )
            ok(f"Gasto creado: ${expense.amount}")
            results['passed'] += 1
            expense.delete()  # Limpiar
        except Exception as e:
            fail(f"Error creando gasto: {e}")
            results['failed'] += 1
    
    # Probar formulario de gastos via HTTP
    response = client.get('/expenses/create/')
    if response.status_code == 200:
        ok("Formulario de nuevo gasto carga correctamente")
        results['passed'] += 1
    else:
        fail(f"Formulario de gasto falla: {response.status_code}")
        results['failed'] += 1
    
    # =========================================
    section("3. PRUEBAS DE PROVEEDORES Y COMPRAS (Purchase)")
    # =========================================
    
    from purchase.models import Supplier, Purchase, PurchaseItem
    from stocks.models import Product, ProductCategory
    
    # Crear proveedor
    try:
        supplier, created = Supplier.objects.get_or_create(
            name='Proveedor Test',
            defaults={'phone': '123456789', 'cuit': '20-12345678-9'}
        )
        ok(f"Proveedor {'creado' if created else 'existe'}: {supplier.name}")
        results['passed'] += 1
    except Exception as e:
        fail(f"Error con proveedor: {e}")
        results['failed'] += 1
        supplier = None
    
    # Probar formulario de proveedor
    response = client.get('/purchase/suppliers/create/')
    if response.status_code == 200:
        ok("Formulario de nuevo proveedor carga correctamente")
        results['passed'] += 1
    else:
        fail(f"Formulario de proveedor falla: {response.status_code}")
        results['failed'] += 1
    
    # Crear producto de prueba para compras
    try:
        prod_cat, _ = ProductCategory.objects.get_or_create(name='Test Category')
        product, created = Product.objects.get_or_create(
            sku='TEST-001',
            defaults={
                'name': 'Producto Test',
                'sale_price': Decimal('100.00'),
                'current_stock': 10,
                'category': prod_cat
            }
        )
        ok(f"Producto {'creado' if created else 'existe'}: {product.name}")
        results['passed'] += 1
    except Exception as e:
        fail(f"Error con producto: {e}")
        results['failed'] += 1
        product = None
    
    # Crear orden de compra
    if supplier and product:
        try:
            purchase = Purchase.objects.create(
                supplier=supplier,
                order_number=f'OC-TEST-001',
                status='draft',
                created_by=admin
            )
            
            # Crear item de compra con cantidad ENTERA
            item = PurchaseItem.objects.create(
                purchase=purchase,
                product=product,
                quantity=10,  # Entero, no decimal
                unit_cost=Decimal('50.00')
            )
            
            ok(f"Orden de compra creada: {purchase.order_number}")
            ok(f"Item de compra con cantidad entera: {item.quantity}")
            results['passed'] += 2
            
            # Limpiar
            item.delete()
            purchase.delete()
        except Exception as e:
            fail(f"Error creando orden de compra: {e}")
            results['failed'] += 1
    
    # Probar formulario de compra
    response = client.get('/purchase/create/')
    if response.status_code == 200:
        ok("Formulario de nueva compra carga correctamente")
        results['passed'] += 1
    else:
        fail(f"Formulario de compra falla: {response.status_code}")
        results['failed'] += 1
    
    # =========================================
    section("4. PRUEBAS DE STOCK")
    # =========================================
    
    from stocks.models import StockMovement
    
    if product:
        # Verificar que stock es entero
        if isinstance(product.current_stock, int) or product.current_stock == int(product.current_stock):
            ok(f"Stock es valor entero: {product.current_stock}")
            results['passed'] += 1
        else:
            fail(f"Stock tiene decimales: {product.current_stock}")
            results['failed'] += 1
        
        # Crear movimiento de stock
        try:
            movement = StockMovement.objects.create(
                product=product,
                movement_type='adjustment',
                quantity=5,  # Entero
                stock_before=product.current_stock,
                stock_after=product.current_stock + 5,
                reference='Test adjustment',
                created_by=admin
            )
            ok(f"Movimiento de stock creado: {movement.quantity}")
            results['passed'] += 1
            movement.delete()
        except Exception as e:
            fail(f"Error en movimiento de stock: {e}")
            results['failed'] += 1
    
    # Probar lista de productos
    response = client.get('/stocks/products/')
    if response.status_code == 200:
        ok("Lista de productos carga correctamente")
        results['passed'] += 1
    else:
        fail(f"Lista de productos falla: {response.status_code}")
        results['failed'] += 1
    
    # =========================================
    section("5. PRUEBAS DE CAJA (Cash Register)")
    # =========================================
    
    from cashregister.models import CashRegister, PaymentMethod
    
    # Verificar caja registradora
    try:
        register, created = CashRegister.objects.get_or_create(
            code='CAJA-01',
            defaults={'name': 'Caja Principal', 'is_active': True}
        )
        ok(f"Caja registradora {'creada' if created else 'existe'}: {register.code}")
        results['passed'] += 1
    except Exception as e:
        fail(f"Error con caja: {e}")
        results['failed'] += 1
    
    # Verificar métodos de pago
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    if payment_methods.exists():
        ok(f"Métodos de pago configurados: {payment_methods.count()}")
        results['passed'] += 1
    else:
        fail("No hay métodos de pago configurados")
        results['failed'] += 1
    
    # Probar dashboard de caja
    response = client.get('/cashregister/')
    if response.status_code == 200:
        ok("Dashboard de caja carga correctamente")
        results['passed'] += 1
    else:
        fail(f"Dashboard de caja falla: {response.status_code}")
        results['failed'] += 1
    
    # =========================================
    section("6. PRUEBAS DE POS")
    # =========================================
    
    # Probar POS main
    response = client.get('/pos/')
    if response.status_code in [200, 302]:  # 302 si requiere turno abierto
        ok("POS carga o redirige correctamente")
        results['passed'] += 1
    else:
        fail(f"POS falla: {response.status_code}")
        results['failed'] += 1
    
    # =========================================
    section("7. PRUEBAS DE PROMOCIONES")
    # =========================================
    
    from promotions.models import Promotion
    
    # Probar lista de promociones
    response = client.get('/promotions/')
    if response.status_code == 200:
        ok("Lista de promociones carga correctamente")
        results['passed'] += 1
    else:
        fail(f"Promociones falla: {response.status_code}")
        results['failed'] += 1
    
    # =========================================
    section("8. PRUEBAS DE DASHBOARD")
    # =========================================
    
    response = client.get('/dashboard/')
    if response.status_code == 200:
        ok("Dashboard principal carga correctamente")
        results['passed'] += 1
    else:
        fail(f"Dashboard falla: {response.status_code}")
        results['failed'] += 1
    
    # =========================================
    # RESUMEN FINAL
    # =========================================
    print(f"\n{'='*60}")
    print(f"{Colors.BLUE}  RESUMEN DE PRUEBAS{Colors.END}")
    print(f"{'='*60}")
    
    total = results['passed'] + results['failed']
    print(f"{Colors.GREEN}  Pasaron: {results['passed']}/{total}{Colors.END}")
    print(f"{Colors.RED}  Fallaron: {results['failed']}/{total}{Colors.END}")
    
    if results['failed'] == 0:
        print(f"\n{Colors.GREEN}🎉 ¡TODAS LAS PRUEBAS PASARON!{Colors.END}")
    else:
        print(f"\n{Colors.RED}⚠️  Hay {results['failed']} prueba(s) que fallaron{Colors.END}")
    
    return results['failed'] == 0


if __name__ == '__main__':
    print(f"\n{Colors.YELLOW}{'='*60}")
    print("  CHE GOLOSO - PRUEBAS FUNCIONALES")
    print(f"{'='*60}{Colors.END}")
    
    success = run_tests()
    sys.exit(0 if success else 1)
