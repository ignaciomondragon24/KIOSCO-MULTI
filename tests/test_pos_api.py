"""
Test script for POS API endpoints
"""
import os
import json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superrecord.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from pos.models import POSTransaction, POSSession

User = get_user_model()

def test_pos_api():
    print("=" * 50)
    print("TEST DE APIs DE POS")
    print("=" * 50)
    
    # Crear cliente y autenticar
    client = Client()
    user = User.objects.filter(is_superuser=True).first()
    client.force_login(user)
    print(f"\nUsuario autenticado: {user.username}")
    
    # Test 1: Búsqueda de productos
    print("\n1. BÚSQUEDA DE PRODUCTOS")
    print("-" * 30)
    response = client.get('/pos/api/search/', {'q': 'coca'})
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        print(f"   Productos encontrados: {len(products)}")
        for p in products[:3]:
            print(f"   - {p.get('name')} | ${p.get('sale_price')}")
    else:
        print(f"   Error: {response.content[:200]}")
    
    # Test 2: Búsqueda por código de barras
    print("\n2. BÚSQUEDA POR CÓDIGO DE BARRAS")
    print("-" * 30)
    response = client.get('/pos/api/search/', {'q': '7790001000001'})
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        print(f"   Productos encontrados: {len(products)}")
        if products:
            print(f"   - {products[0].get('name')} | ${products[0].get('sale_price')}")
    
    # Test 3: Verificar/crear sesión POS activa para testing
    print("\n3. CREACIÓN DE SESIÓN POS")
    print("-" * 30)
    from cashregister.models import CashRegister, CashShift
    from decimal import Decimal
    
    register = CashRegister.objects.filter(is_active=True).first()
    
    # Buscar turno del usuario actual o crear uno
    shift = CashShift.objects.filter(cashier=user, status='open').first()
    
    if not shift:
        # Crear turno nuevo (sin pasar initial_amount en el constructor)
        shift = CashShift(
            cash_register=register,
            cashier=user,
            status='open'
        )
        shift.initial_amount = Decimal('10000.00')
        shift.save()
        print(f"   Turno creado: {shift.id}")
    else:
        print(f"   Turno existente: {shift.id}")
    
    # Verificar/crear sesión POS
    session = POSSession.objects.filter(cash_shift=shift, status='active').first()
    if not session:
        session = POSSession.objects.create(
            cash_shift=shift,
            status='active'
        )
        print(f"   Sesión POS creada: {session.id}")
    else:
        print(f"   Sesión POS existente: {session.id}")
    
    # Generar número de ticket único (usando todos los tickets del día, no solo de la sesión)
    from django.utils import timezone
    import random
    import string
    today = timezone.now().strftime('%Y%m%d')
    count = POSTransaction.objects.filter(ticket_number__contains=today).count() + 1
    # Agregar un sufijo aleatorio para evitar duplicados en tests repetidos
    rand_suffix = ''.join(random.choices(string.digits, k=4))
    ticket_number = f"{register.code or 'TEST'}-{today}-{count:04d}-{rand_suffix}"
    
    # Crear nueva transacción
    transaction = POSTransaction.objects.create(
        session=session,
        ticket_number=ticket_number,
        status='pending'
    )
    print(f"   Transacción creada: {transaction.id} | Ticket: {ticket_number}")
    
    # Test 4: Agregar producto al carrito
    print("\n4. AGREGAR PRODUCTO AL CARRITO")
    print("-" * 30)
    response = client.post(
        '/pos/api/cart/add/',
        json.dumps({
            'transaction_id': transaction.id,
            'product_id': 6,  # Coca Cola
            'quantity': 2
        }),
        content_type='application/json'
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Éxito: {data.get('success', False)}")
        if data.get('item'):
            print(f"   Item agregado: {data['item'].get('product_name')}")
            print(f"   Subtotal: ${data['item'].get('subtotal')}")
        if data.get('totals'):
            print(f"   Total carrito: ${data['totals'].get('total')}")
    else:
        print(f"   Error: {response.content[:500]}")
    
    # Test 5: Ver detalle de transacción
    print("\n5. DETALLE DE TRANSACCIÓN")
    print("-" * 30)
    response = client.get(f'/pos/api/transaction/{transaction.id}/')
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Items: {len(data.get('items', []))}")
        totals = data.get('totals', {})
        print(f"   Total: ${totals.get('total')}")
    
    # Test 6: Aplicar descuento (usando 'type' y 'value' como espera el endpoint)
    print("\n6. APLICAR DESCUENTO")
    print("-" * 30)
    response = client.post(
        f'/pos/api/transaction/{transaction.id}/discount/',
        json.dumps({
            'type': 'percent',
            'value': 10
        }),
        content_type='application/json'
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Éxito: {data.get('success', False)}")
        if data.get('totals'):
            print(f"   Descuento: ${data['totals'].get('discount')}")
            print(f"   Total con descuento: ${data['totals'].get('total')}")
    else:
        print(f"   Error: {response.content[:500]}")
    
    # Test 7: Checkout (usando 'payments' como lista, como espera el endpoint)
    print("\n7. CHECKOUT")
    print("-" * 30)
    # Recargar transacción para obtener el total con descuento
    transaction.refresh_from_db()
    response = client.post(
        '/pos/api/checkout/',
        json.dumps({
            'transaction_id': transaction.id,
            'payments': [
                {
                    'method_code': 'cash',
                    'amount': 5000
                }
            ]
        }),
        content_type='application/json'
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Éxito: {data.get('success', False)}")
        print(f"   Vuelto: ${data.get('change', 0)}")
        print(f"   Ticket: {data.get('ticket_number', 'N/A')}")
    else:
        print(f"   Error: {response.content[:500]}")
    
    # Test 8: Última transacción (para reimprimir)
    print("\n8. ÚLTIMA TRANSACCIÓN (REIMPRIMIR)")
    print("-" * 30)
    response = client.get('/pos/api/last-transaction/')
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if data.get('transaction'):
            t = data['transaction']
            print(f"   Ticket: {t.get('ticket_number')}")
            print(f"   Total: ${t.get('total')}")
    else:
        print(f"   Error: {response.content[:500]}")
    
    print("\n" + "=" * 50)
    print("TESTS COMPLETADOS")
    print("=" * 50)

if __name__ == '__main__':
    test_pos_api()
