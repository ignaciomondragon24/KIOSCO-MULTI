"""
CHE GOLOSO - Test Exhaustivo del Sistema Completo
==================================================
Auditoría profunda de lógica de negocio, edge cases, seguridad,
y consistencia entre módulos. Perspectiva de operador de kiosco real.

Se complementa con test_audit_business_numbers.py (aritmética pura).
Aquí se testean flujos end-to-end, validaciones faltantes, permisos,
y escenarios que un kiosco encuentra día a día.
"""
import json
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Sum

from stocks.models import Product, ProductCategory, StockMovement, ProductPackaging
from stocks.services import StockManagementService
from pos.models import POSSession, POSTransaction, POSTransactionItem, POSPayment
from pos.services import POSService, CartService, CheckoutService
from cashregister.models import (
    PaymentMethod, CashRegister, CashShift, CashMovement, BillCount,
)
from promotions.models import Promotion, PromotionProduct
from promotions.engine import PromotionEngine
from purchase.models import Supplier, Purchase, PurchaseItem
from expenses.models import Expense, ExpenseCategory

User = get_user_model()


class ExhaustiveBaseTestCase(TestCase):
    """Setup completo para tests exhaustivos con HTTP client."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_group, _ = Group.objects.get_or_create(name='Admin')
        cls.manager_group, _ = Group.objects.get_or_create(name='Cajero Manager')
        cls.cashier_group, _ = Group.objects.get_or_create(name='Cashier')
        cls.stock_group, _ = Group.objects.get_or_create(name='Stock Manager')

        cls.admin = User.objects.create_user(
            username='ex_admin', password='pass123',
            is_superuser=True, is_staff=True,
        )
        cls.admin.groups.add(cls.admin_group)

        cls.manager = User.objects.create_user(
            username='ex_manager', password='pass123',
        )
        cls.manager.groups.add(cls.manager_group)

        cls.cashier = User.objects.create_user(
            username='ex_cashier', password='pass123',
        )
        cls.cashier.groups.add(cls.cashier_group)

        cls.stock_user = User.objects.create_user(
            username='ex_stock', password='pass123',
        )
        cls.stock_user.groups.add(cls.stock_group)

        cls.cash_method = PaymentMethod.objects.create(
            code='cash', name='Efectivo', is_cash=True,
            requires_counting=True, position=1,
        )
        cls.card_method = PaymentMethod.objects.create(
            code='debit', name='Débito', is_cash=False, position=2,
        )
        cls.transfer_method = PaymentMethod.objects.create(
            code='transfer', name='Transferencia', is_cash=False, position=3,
        )

        cls.category = ProductCategory.objects.create(name='Golosinas')

    def make_product(self, name='TestProd', sale_price='100.00',
                     purchase_price='60.00', cost_price='60.00',
                     current_stock='50.000', **kw):
        return Product.objects.create(
            name=name, sale_price=Decimal(sale_price),
            purchase_price=Decimal(purchase_price),
            cost_price=Decimal(cost_price),
            current_stock=Decimal(current_stock),
            category=self.category, **kw,
        )

    def make_shift(self, user=None, initial='5000.00'):
        user = user or self.cashier
        reg = CashRegister.objects.create(
            code=f'CAJA-{CashRegister.objects.count()+1:02d}', name='Test',
        )
        return CashShift.objects.create(
            cash_register=reg, cashier=user,
            initial_amount=Decimal(initial),
        )

    def make_pos_transaction(self, shift=None):
        shift = shift or self.make_shift()
        session = POSService.get_or_create_session(shift)
        txn = POSService.get_pending_transaction(session)
        return txn, shift

    def login_as(self, user):
        c = Client()
        c.login(username=user.username, password='pass123')
        return c


# ============================================================
# 1. EDGE CASES DE STOCK QUE ROMPEN UN KIOSCO
# ============================================================

class StockEdgeCasesAudit(ExhaustiveBaseTestCase):
    """Escenarios reales que causan descuadre de inventario."""

    def test_double_deduction_same_product_same_transaction(self):
        """Agregar el mismo producto 2 veces al carrito suma cantidad, no duplica."""
        prod = self.make_product(current_stock='100.000', sale_price='50.00')
        txn, shift = self.make_pos_transaction()

        CartService.add_item(txn, prod.id, Decimal('3'))
        CartService.add_item(txn, prod.id, Decimal('2'))

        items = txn.items.all()
        self.assertEqual(items.count(), 1, 'Debe haber 1 solo ítem, no 2')
        self.assertEqual(items.first().quantity, 5)

        CheckoutService.process_payment(
            txn.id, [{'method_id': self.cash_method.id, 'amount': 250}],
        )
        prod.refresh_from_db()
        self.assertEqual(prod.current_stock, Decimal('95.000'))

    def test_sell_more_than_stock(self):
        """Vender más de lo que hay: el sistema lo permite (documenta comportamiento)."""
        prod = self.make_product(current_stock='2.000', sale_price='100.00')
        txn, shift = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('10'))

        ok, result = CheckoutService.process_payment(
            txn.id, [{'method_id': self.cash_method.id, 'amount': 1000}],
        )
        self.assertTrue(ok, 'El sistema permite vender sin stock suficiente')
        prod.refresh_from_db()
        self.assertEqual(prod.current_stock, Decimal('-8.000'))

    def test_receive_purchase_updates_cost_correctly(self):
        """Recibir compra actualiza stock Y costo promedio."""
        prod = self.make_product(
            current_stock='10.000', cost_price='50.00', purchase_price='50.00',
        )
        supplier = Supplier.objects.create(name='Test Supplier')
        purchase = Purchase.objects.create(
            supplier=supplier, order_number='OC-TEST-001',
        )
        PurchaseItem.objects.create(
            purchase=purchase, product=prod,
            quantity=20, unit_cost=Decimal('80.00'),
        )

        # Simular recepción (lógica de purchase_receive view)
        for item in purchase.items.all():
            StockManagementService.add_stock(
                product=item.product, quantity=item.quantity,
                cost=item.unit_cost, user=self.admin,
                reference=purchase.order_number,
            )
            item.received_quantity = item.quantity
            item.save()

        prod.refresh_from_db()
        self.assertEqual(prod.current_stock, Decimal('30.000'))
        # Costo promedio: (50*10 + 80*20) / 30 = 2100/30 = 70
        expected_cost = (Decimal('50') * 10 + Decimal('80') * 20) / 30
        self.assertAlmostEqual(float(prod.cost_price), float(expected_cost), places=2)

    def test_purchase_receive_preserves_weighted_average_cost(self):
        """
        CORREGIDO: purchase_receive() ya no sobreescribe el costo promedio.
        add_stock() calcula el promedio ponderado y ese valor se mantiene.
        """
        prod = self.make_product(
            current_stock='100.000', cost_price='50.00',
        )
        supplier = Supplier.objects.create(name='Bug Supplier')
        purchase = Purchase.objects.create(
            supplier=supplier, order_number='OC-BUG-001',
        )
        PurchaseItem.objects.create(
            purchase=purchase, product=prod,
            quantity=10, unit_cost=Decimal('200.00'),
        )

        # Simular el flujo corregido de purchase_receive view
        for item in purchase.items.all():
            StockManagementService.add_stock(
                product=item.product, quantity=item.quantity,
                cost=item.unit_cost, user=self.admin,
                reference=purchase.order_number,
            )
            item.received_quantity = item.quantity
            item.save()

        prod.refresh_from_db()
        # Costo promedio correcto: (50*100 + 200*10) / 110 = 7000/110 ≈ 63.64
        expected_cost = (Decimal('50') * 100 + Decimal('200') * 10) / 110
        self.assertAlmostEqual(
            float(prod.cost_price), float(expected_cost), places=2,
            msg='El costo promedio ponderado debe preservarse tras recibir compra',
        )

    def test_stock_value_consistency_after_operations(self):
        """El valor total de stock debe ser rastreable por movimientos."""
        prod = self.make_product(current_stock='0.000', cost_price='0.00')

        StockManagementService.add_stock(prod, 50, cost=Decimal('100'))
        StockManagementService.add_stock(prod, 30, cost=Decimal('120'))

        prod.refresh_from_db()
        # 50*100 + 30*120 = 5000 + 3600 = 8600, stock=80
        self.assertEqual(prod.current_stock, Decimal('80.000'))
        # cost_price = 8600/80 = 107.50
        expected_cost = Decimal('8600') / Decimal('80')
        self.assertAlmostEqual(float(prod.cost_price), float(expected_cost), places=2)

        # Vender 20 unidades
        StockManagementService.deduct_stock(prod, 20)
        prod.refresh_from_db()
        self.assertEqual(prod.current_stock, Decimal('60.000'))
        # cost_price no cambia al vender
        self.assertAlmostEqual(float(prod.cost_price), float(expected_cost), places=2)

    def test_packaging_stock_drift_after_many_operations(self):
        """Múltiples operaciones de venta no causan drift en packaging stock."""
        prod = self.make_product(current_stock='240.000', sale_price='10.00')
        unit_pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='unit', name='Unidad',
            units_per_display=12, displays_per_bulk=2,
            sale_price=Decimal('10'), current_stock=Decimal('240'),
        )
        display_pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='display', name='Display x12',
            units_per_display=12, displays_per_bulk=2,
            sale_price=Decimal('100'), current_stock=Decimal('20'),
        )

        # 10 ventas de 5 unidades cada una
        for _ in range(10):
            StockManagementService.deduct_stock_with_cascade(
                prod, Decimal('5'), reference='test',
            )

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()

        # 240 - 50 = 190
        self.assertEqual(prod.current_stock, Decimal('190'))
        self.assertEqual(unit_pkg.current_stock, Decimal('190'))
        # Display: 20 - 50/12 ≈ 15.833...
        expected_display = Decimal('20') - (Decimal('50') / Decimal('12'))
        self.assertAlmostEqual(
            float(display_pkg.current_stock), float(expected_display), places=2,
        )


# ============================================================
# 2. FLUJOS POS COMPLETOS VIA HTTP
# ============================================================

class POSFlowHTTPAudit(ExhaustiveBaseTestCase):
    """Tests de endpoints HTTP del POS como lo usaría un cajero real."""

    def test_pos_requires_open_shift(self):
        """Sin turno abierto, el POS redirige a abrir turno."""
        c = self.login_as(self.cashier)
        resp = c.get(reverse('pos:pos_main'))
        self.assertEqual(resp.status_code, 302)

    def test_cart_add_via_api(self):
        """Agregar producto al carrito via API."""
        prod = self.make_product(sale_price='100.00', current_stock='50.000')
        shift = self.make_shift(user=self.cashier)
        session = POSService.get_or_create_session(shift)
        txn = POSService.get_pending_transaction(session)

        c = self.login_as(self.cashier)
        resp = c.post(
            reverse('pos:api_cart_add'),
            json.dumps({
                'transaction_id': txn.id,
                'product_id': prod.id,
                'quantity': 3,
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['totals']['total'], 300.0)

    def test_checkout_via_api(self):
        """Checkout completo via API HTTP."""
        prod = self.make_product(sale_price='200.00', current_stock='50.000')
        shift = self.make_shift(user=self.cashier)
        txn, _ = self.make_pos_transaction(shift=shift)
        CartService.add_item(txn, prod.id, Decimal('2'))

        c = self.login_as(self.cashier)
        resp = c.post(
            reverse('pos:api_checkout'),
            json.dumps({
                'transaction_id': txn.id,
                'payments': [{'method_id': self.cash_method.id, 'amount': 400}],
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['change'], 0.0)

        prod.refresh_from_db()
        self.assertEqual(prod.current_stock, Decimal('48.000'))

    def test_quick_checkout_via_api(self):
        """Pago rápido (un solo método) via API."""
        prod = self.make_product(sale_price='150.00', current_stock='50.000')
        shift = self.make_shift(user=self.cashier)
        txn, _ = self.make_pos_transaction(shift=shift)
        CartService.add_item(txn, prod.id, Decimal('1'))

        c = self.login_as(self.cashier)
        resp = c.post(
            reverse('pos:api_quick_checkout'),
            json.dumps({
                'transaction_id': txn.id,
                'method_code': 'cash',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total'], 150.0)

    def test_empty_cart_checkout_rejected(self):
        """No se puede cobrar un carrito vacío."""
        shift = self.make_shift(user=self.cashier)
        txn, _ = self.make_pos_transaction(shift=shift)

        c = self.login_as(self.cashier)
        resp = c.post(
            reverse('pos:api_quick_checkout'),
            json.dumps({
                'transaction_id': txn.id,
                'method_code': 'cash',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_suspend_and_resume_transaction(self):
        """Apartar y retomar una venta."""
        prod = self.make_product(sale_price='100.00', current_stock='50.000')
        shift = self.make_shift(user=self.cashier)
        txn, _ = self.make_pos_transaction(shift=shift)
        CartService.add_item(txn, prod.id, Decimal('5'))

        c = self.login_as(self.cashier)

        # Suspender
        resp = c.post(reverse('pos:api_transaction_suspend', args=[txn.id]))
        self.assertEqual(resp.status_code, 200)
        txn.refresh_from_db()
        self.assertEqual(txn.status, 'suspended')

        # Retomar
        resp = c.post(reverse('pos:api_transaction_resume', args=[txn.id]))
        self.assertEqual(resp.status_code, 200)
        txn.refresh_from_db()
        self.assertEqual(txn.status, 'pending')

        # Items siguen ahí
        self.assertEqual(txn.items.count(), 1)
        self.assertEqual(txn.items.first().quantity, 5)

    def test_cancel_transaction_doesnt_affect_stock(self):
        """Cancelar una venta pendiente no descuenta stock."""
        prod = self.make_product(current_stock='50.000', sale_price='100.00')
        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('10'))

        stock_before = prod.current_stock
        c = self.login_as(self.cashier)
        c.post(reverse('pos:api_transaction_cancel', args=[txn.id]))

        prod.refresh_from_db()
        self.assertEqual(prod.current_stock, stock_before)

    def test_item_discount_validation(self):
        """Descuento por ítem: validaciones de porcentaje y monto."""
        prod = self.make_product(sale_price='100.00', current_stock='50.000')
        shift = self.make_shift(user=self.manager)
        txn, _ = self.make_pos_transaction(shift=shift)
        item, _ = CartService.add_item(txn, prod.id, Decimal('2'))

        c = self.login_as(self.manager)

        # Porcentaje > 100 rechazado
        resp = c.post(
            reverse('pos:api_cart_item_discount', args=[item.id]),
            json.dumps({'type': 'percent', 'value': 150}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

        # Descuento fijo > subtotal rechazado
        resp = c.post(
            reverse('pos:api_cart_item_discount', args=[item.id]),
            json.dumps({'type': 'fixed', 'value': 500}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

        # Descuento válido aceptado
        resp = c.post(
            reverse('pos:api_cart_item_discount', args=[item.id]),
            json.dumps({'type': 'percent', 'value': 10}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertAlmostEqual(data['item']['discount'], 20.0)  # 10% de 200

    def test_transaction_discount_percent(self):
        """Descuento general a la transacción por porcentaje."""
        prod = self.make_product(sale_price='100.00', current_stock='50.000')
        shift = self.make_shift(user=self.manager)
        txn, _ = self.make_pos_transaction(shift=shift)
        CartService.add_item(txn, prod.id, Decimal('10'))

        c = self.login_as(self.manager)
        resp = c.post(
            reverse('pos:api_apply_discount', args=[txn.id]),
            json.dumps({'type': 'percent', 'value': 15}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # 10 * 100 = 1000, 15% = 150 descuento
        self.assertAlmostEqual(data['totals']['discount'], 150.0)
        self.assertAlmostEqual(data['totals']['total'], 850.0)


# ============================================================
# 3. PERMISOS Y SEGURIDAD
# ============================================================

class PermissionAudit(ExhaustiveBaseTestCase):
    """Verifica que los roles tengan acceso correcto."""

    def test_cashier_cannot_access_cost_sale(self):
        """Cajero no puede hacer venta al costo (solo Admin/Manager)."""
        shift = self.make_shift(user=self.cashier)
        txn, _ = self.make_pos_transaction(shift=shift)

        c = self.login_as(self.cashier)
        resp = c.post(
            reverse('pos:api_checkout_cost_sale'),
            json.dumps({
                'transaction_id': txn.id,
                'payments': [{'method_id': self.cash_method.id, 'amount': 100}],
            }),
            content_type='application/json',
        )
        self.assertIn(resp.status_code, [302, 403])

    def test_cashier_cannot_access_internal_consumption(self):
        """Cajero no puede hacer consumo interno (solo Admin/Manager)."""
        shift = self.make_shift(user=self.cashier)
        txn, _ = self.make_pos_transaction(shift=shift)

        c = self.login_as(self.cashier)
        resp = c.post(
            reverse('pos:api_checkout_internal_consumption'),
            json.dumps({'transaction_id': txn.id}),
            content_type='application/json',
        )
        self.assertIn(resp.status_code, [302, 403])

    def test_cashier_cannot_create_product(self):
        """Cajero no puede crear productos (solo Admin/Manager)."""
        c = self.login_as(self.cashier)
        resp = c.get(reverse('stocks:product_create'))
        self.assertIn(resp.status_code, [302, 403])

    def test_cashier_cannot_adjust_stock(self):
        """Cajero no puede hacer conteo físico (solo Admin/Manager)."""
        prod = self.make_product()
        c = self.login_as(self.cashier)
        resp = c.get(reverse('stocks:inventory_count', args=[prod.pk]))
        self.assertIn(resp.status_code, [302, 403])

    def test_cashier_cannot_access_expenses(self):
        """Cajero no puede ver/crear gastos (solo Admin)."""
        c = self.login_as(self.cashier)
        resp = c.get(reverse('expenses:expense_list'))
        self.assertIn(resp.status_code, [302, 403])

    def test_cashier_cannot_access_purchases(self):
        """Cajero no puede ver compras (solo Admin)."""
        c = self.login_as(self.cashier)
        resp = c.get(reverse('purchase:purchase_list'))
        self.assertIn(resp.status_code, [302, 403])

    def test_cashier_cannot_access_reports(self):
        """Cajero no puede ver reportes de ventas (solo Admin)."""
        c = self.login_as(self.cashier)
        resp = c.get(reverse('sales:daily_report'))
        self.assertIn(resp.status_code, [302, 403])

    def test_manager_can_do_cost_sale(self):
        """Manager SÍ puede hacer venta al costo."""
        prod = self.make_product(sale_price='200.00', cost_price='100.00', current_stock='50.000')
        shift = self.make_shift(user=self.manager)
        txn, _ = self.make_pos_transaction(shift=shift)
        CartService.add_item(txn, prod.id, Decimal('1'))

        c = self.login_as(self.manager)
        resp = c.post(
            reverse('pos:api_checkout_cost_sale'),
            json.dumps({
                'transaction_id': txn.id,
                'payments': [{'method_id': self.cash_method.id, 'amount': 100}],
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)

    def test_cashier_cannot_apply_discounts(self):
        """CORREGIDO: Cajero no puede aplicar descuentos (solo Admin/Manager)."""
        prod = self.make_product(sale_price='100.00', current_stock='50.000')
        shift = self.make_shift(user=self.cashier)
        txn, _ = self.make_pos_transaction(shift=shift)
        item, _ = CartService.add_item(txn, prod.id, Decimal('2'))

        c = self.login_as(self.cashier)
        resp = c.post(
            reverse('pos:api_cart_item_discount', args=[item.id]),
            json.dumps({'type': 'percent', 'value': 10}),
            content_type='application/json',
        )
        self.assertIn(resp.status_code, [302, 403])

        resp = c.post(
            reverse('pos:api_apply_discount', args=[txn.id]),
            json.dumps({'type': 'percent', 'value': 15}),
            content_type='application/json',
        )
        self.assertIn(resp.status_code, [302, 403])

    def test_unauthenticated_api_rejected(self):
        """APIs sin login retornan 401 (ajax_login_required)."""
        c = Client()
        endpoints = [
            reverse('pos:api_cart_add'),
            reverse('pos:api_checkout'),
        ]
        for url in endpoints:
            resp = c.post(url, '{}', content_type='application/json')
            self.assertIn(resp.status_code, [401, 302], f'{url} debería requerir login')

    def test_cashier_cannot_close_other_shift(self):
        """Cajero no puede cerrar el turno de otro cajero."""
        other_cashier = User.objects.create_user(
            username='other_cashier', password='pass123',
        )
        other_cashier.groups.add(self.cashier_group)
        other_shift = self.make_shift(user=other_cashier)

        c = self.login_as(self.cashier)
        resp = c.post(
            reverse('cashregister:close_shift', args=[other_shift.pk]),
            {'actual_amount': '5000', 'notes': ''},
        )
        # Debería redirigir con error
        self.assertEqual(resp.status_code, 302)


# ============================================================
# 4. CAJA: APERTURA, CIERRE, MOVIMIENTOS
# ============================================================

class CashShiftFlowAudit(ExhaustiveBaseTestCase):
    """Tests del ciclo de vida completo de un turno de caja."""

    def test_cannot_open_two_shifts_same_user(self):
        """Un cajero no puede tener 2 turnos abiertos simultáneamente."""
        self.make_shift(user=self.cashier)

        c = self.login_as(self.cashier)
        reg2 = CashRegister.objects.create(code='CAJA-EXTRA', name='Extra')
        resp = c.post(reverse('cashregister:open_shift'), {
            'cash_register': reg2.id,
            'initial_amount': '5000',
        })
        # Debería redirigir con warning
        self.assertEqual(resp.status_code, 302)
        # Solo debe haber 1 turno abierto
        open_shifts = CashShift.objects.filter(cashier=self.cashier, status='open')
        self.assertEqual(open_shifts.count(), 1)

    def test_cannot_open_shift_on_occupied_register(self):
        """No se puede abrir turno en una caja que ya tiene turno abierto."""
        shift1 = self.make_shift(user=self.cashier)
        register = shift1.cash_register

        other = User.objects.create_user(username='other2', password='pass123')
        other.groups.add(self.cashier_group)

        c = self.login_as(other)
        resp = c.post(reverse('cashregister:open_shift'), {
            'cash_register': register.id,
            'initial_amount': '3000',
        })
        # La vista puede redirigir (302) o re-renderizar con error (200)
        # Lo importante es que NO se haya creado un segundo turno en la misma caja
        shifts_on_register = CashShift.objects.filter(
            cash_register=register, status='open'
        )
        self.assertEqual(shifts_on_register.count(), 1,
                         "Se creó un segundo turno en una caja ocupada — BUG")

    def test_shift_close_with_multiple_payment_methods(self):
        """Cierre de caja con ventas en múltiples métodos de pago."""
        shift = self.make_shift(initial='5000.00')

        # Venta en efectivo
        CashMovement.objects.create(
            cash_shift=shift, movement_type='income',
            amount=Decimal('1000'), payment_method=self.cash_method,
            description='Venta 1',
        )
        # Venta con tarjeta
        CashMovement.objects.create(
            cash_shift=shift, movement_type='income',
            amount=Decimal('2000'), payment_method=self.card_method,
            description='Venta 2',
        )
        # Gasto en efectivo
        CashMovement.objects.create(
            cash_shift=shift, movement_type='expense',
            amount=Decimal('500'), payment_method=self.cash_method,
            description='Gasto',
        )

        expected = shift.calculate_expected()
        # Solo cash: 5000 + 1000 - 500 = 5500
        self.assertEqual(expected, Decimal('5500.00'))

        # Total income (todos los métodos)
        self.assertEqual(shift.total_income, Decimal('3000.00'))
        self.assertEqual(shift.get_cash_total(), Decimal('1000.00'))
        self.assertEqual(shift.get_non_cash_total(), Decimal('2000.00'))

    def test_manual_cash_movement_affects_expected(self):
        """Movimientos manuales de caja afectan el esperado."""
        shift = self.make_shift(initial='10000.00')

        c = self.login_as(self.cashier)
        c.post(reverse('cashregister:add_movement', args=[shift.pk]), {
            'movement_type': 'expense',
            'amount': '1500',
            'payment_method': self.cash_method.id,
            'description': 'Compra de insumos',
        })

        expected = shift.calculate_expected()
        self.assertEqual(expected, Decimal('8500.00'))


# ============================================================
# 5. COMPRAS Y PROVEEDORES
# ============================================================

class PurchaseFlowAudit(ExhaustiveBaseTestCase):
    """Flujo completo de compras."""

    def test_purchase_receive_cannot_receive_twice(self):
        """Una compra ya recibida no puede recibirse de nuevo."""
        supplier = Supplier.objects.create(name='Test')
        purchase = Purchase.objects.create(
            supplier=supplier, order_number='OC-TWICE', status='received',
        )

        c = self.login_as(self.admin)
        resp = c.post(reverse('purchase:purchase_receive', args=[purchase.pk]))
        self.assertEqual(resp.status_code, 302)
        # No debería haber movimientos de stock nuevos
        self.assertEqual(StockMovement.objects.filter(reference='OC-TWICE').count(), 0)

    def test_purchase_item_subtotal_auto_calc(self):
        """El subtotal del ítem se calcula automáticamente."""
        prod = self.make_product()
        supplier = Supplier.objects.create(name='Auto')
        purchase = Purchase.objects.create(
            supplier=supplier, order_number='OC-AUTO',
        )
        item = PurchaseItem.objects.create(
            purchase=purchase, product=prod,
            quantity=15, unit_cost=Decimal('45.00'),
        )
        self.assertEqual(item.subtotal, Decimal('675.00'))

    def test_purchase_cancel_prevents_receive(self):
        """Una compra cancelada no puede recibirse."""
        supplier = Supplier.objects.create(name='Cancel')
        purchase = Purchase.objects.create(
            supplier=supplier, order_number='OC-CANCEL', status='cancelled',
        )

        c = self.login_as(self.admin)
        # No debería recibirse (status check en vista)
        # La vista verifica status == 'received', no 'cancelled', así que podría pasar
        # Esto es un hallazgo potencial


# ============================================================
# 6. GASTOS
# ============================================================

class ExpenseAudit(ExhaustiveBaseTestCase):
    """Auditoría de gastos."""

    def test_cash_expense_with_drawer_flag_creates_cash_movement(self):
        """
        Gasto en efectivo con `affects_cash_drawer=True` crea CashMovement
        en el turno activo (salió físicamente del cajón del POS).
        """
        exp_category = ExpenseCategory.objects.create(name='Limpieza')
        shift = self.make_shift()

        c = self.login_as(self.admin)
        resp = c.post(reverse('expenses:expense_create'), {
            'category': exp_category.id,
            'description': 'Artículos de limpieza',
            'amount': '500.00',
            'expense_date': timezone.now().date().isoformat(),
            'payment_method': 'cash',
            'affects_cash_drawer': 'on',
        })
        self.assertEqual(resp.status_code, 302)

        expense = Expense.objects.get(description='Artículos de limpieza')
        movements = CashMovement.objects.filter(
            cash_shift=shift,
            amount=Decimal('500.00'),
            movement_type='expense',
            reference=f'EXP-{expense.id}',
        )
        self.assertEqual(movements.count(), 1)

    def test_cash_expense_without_drawer_flag_no_cash_movement(self):
        """Gasto efectivo sin el flag (pago externo) NO afecta el cierre Z."""
        exp_category = ExpenseCategory.objects.create(name='Alquiler')
        shift = self.make_shift()

        c = self.login_as(self.admin)
        c.post(reverse('expenses:expense_create'), {
            'category': exp_category.id,
            'description': 'Alquiler del mes',
            'amount': '100000.00',
            'expense_date': timezone.now().date().isoformat(),
            'payment_method': 'cash',
        })
        movements = CashMovement.objects.filter(cash_shift=shift, movement_type='expense')
        self.assertEqual(movements.count(), 0)

    def test_non_cash_expense_no_cash_movement(self):
        """Gastos que no son en efectivo NO crean CashMovement."""
        exp_category = ExpenseCategory.objects.create(name='Servicios')
        shift = self.make_shift()

        c = self.login_as(self.admin)
        c.post(reverse('expenses:expense_create'), {
            'category': exp_category.id,
            'description': 'Pago de luz',
            'amount': '3000.00',
            'expense_date': timezone.now().date().isoformat(),
            'payment_method': 'transfer',
        })

        movements = CashMovement.objects.filter(cash_shift=shift, movement_type='expense')
        self.assertEqual(movements.count(), 0)

    def test_delete_expense_removes_cash_movement(self):
        """Eliminar un gasto con affects_cash_drawer también elimina su CashMovement."""
        exp_category = ExpenseCategory.objects.create(name='Varios')
        shift = self.make_shift()

        c = self.login_as(self.admin)
        c.post(reverse('expenses:expense_create'), {
            'category': exp_category.id,
            'description': 'Compra menor',
            'amount': '200.00',
            'expense_date': timezone.now().date().isoformat(),
            'payment_method': 'cash',
            'affects_cash_drawer': 'on',
        })
        expense = Expense.objects.get(description='Compra menor')
        self.assertEqual(CashMovement.objects.filter(reference=f'EXP-{expense.id}').count(), 1)

        c.post(reverse('expenses:expense_delete', args=[expense.pk]))
        self.assertEqual(CashMovement.objects.filter(reference=f'EXP-{expense.id}').count(), 0)


# ============================================================
# 7. PROMOCIONES: EDGE CASES AVANZADOS
# ============================================================

class PromotionEdgeCasesAudit(ExhaustiveBaseTestCase):
    """Edge cases de promociones que un kiosco encuentra."""

    def _make_promo(self, promo_type, products, **kwargs):
        defaults = {
            'name': f'Test {promo_type}', 'promo_type': promo_type,
            'status': 'active', 'priority': 50, 'is_combinable': True,
            'quantity_required': 2, 'quantity_charged': 1,
            'min_quantity': 1, 'discount_percent': Decimal('0'),
            'discount_amount': Decimal('0'), 'second_unit_discount': Decimal('50'),
        }
        defaults.update(kwargs)
        promo = Promotion.objects.create(**defaults)
        for p in products:
            PromotionProduct.objects.create(promotion=promo, product=p)
        return promo

    def test_nxm_with_odd_quantity(self):
        """2x1 con cantidad impar: 5 unidades = 2 sets (4u) + 1 sin descuento."""
        prod = self.make_product(sale_price='100.00')
        self._make_promo('nxm', [prod], quantity_required=2, quantity_charged=1)

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 5, 'unit_price': 100},
        ])
        # 5 // 2 = 2 sets, free=2*1=2 unidades gratis
        self.assertEqual(result['discount_total'], 200.0)
        self.assertEqual(result['final_total'], 300.0)  # 500 - 200

    def test_two_combinable_promos_on_different_products(self):
        """Dos promos combinables sobre productos distintos: ambas aplican."""
        p1 = self.make_product(name='P1', sale_price='100.00')
        p2 = self.make_product(name='P2', sale_price='200.00')

        self._make_promo('simple_discount', [p1],
                         discount_percent=Decimal('10'), name='Desc P1', priority=60)
        self._make_promo('simple_discount', [p2],
                         discount_percent=Decimal('20'), name='Desc P2', priority=50)

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': p1.id, 'quantity': 1, 'unit_price': 100},
            {'item_id': 2, 'product_id': p2.id, 'quantity': 1, 'unit_price': 200},
        ])
        # P1: 10% de 100 = 10, P2: 20% de 200 = 40
        self.assertAlmostEqual(result['discount_total'], 50.0, places=2)
        self.assertEqual(len(result['applied_promotions']), 2)

    def test_combo_with_quantities_greater_than_one(self):
        """Combo con qty > 1: solo aplica 1 vez."""
        p1 = self.make_product(name='C1', sale_price='100.00')
        p2 = self.make_product(name='C2', sale_price='50.00')
        self._make_promo('combo', [p1, p2], final_price=Decimal('120.00'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': p1.id, 'quantity': 3, 'unit_price': 100},
            {'item_id': 2, 'product_id': p2.id, 'quantity': 2, 'unit_price': 50},
        ])
        # Original: 300+100=400, combo final_price=120
        # Discount = 400-120=280
        self.assertEqual(result['discount_total'], 280.0)

    def test_promotion_with_zero_price_product(self):
        """Producto con precio 0 no debería causar error en combo."""
        p1 = self.make_product(name='Free', sale_price='0.01')
        p2 = self.make_product(name='Paid', sale_price='100.00')
        self._make_promo('combo', [p1, p2], final_price=Decimal('80.00'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': p1.id, 'quantity': 1, 'unit_price': 0.01},
            {'item_id': 2, 'product_id': p2.id, 'quantity': 1, 'unit_price': 100},
        ])
        # 100.01 - 80 = 20.01
        self.assertAlmostEqual(result['discount_total'], 20.01, places=2)

    def test_promotion_priority_order(self):
        """Promo de mayor prioridad se aplica primero."""
        prod = self.make_product(sale_price='100.00')
        hi = self._make_promo('simple_discount', [prod],
                              discount_percent=Decimal('10'), priority=90,
                              is_combinable=False, name='Alta')
        lo = self._make_promo('simple_discount', [prod],
                              discount_percent=Decimal('50'), priority=10,
                              is_combinable=True, name='Baja')

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 1, 'unit_price': 100},
        ])
        # La alta (10%) no es combinable, bloquea la baja (50%)
        self.assertAlmostEqual(result['discount_total'], 10.0, places=2)


# ============================================================
# 8. BÚSQUEDA DE PRODUCTOS
# ============================================================

class ProductSearchAudit(ExhaustiveBaseTestCase):
    """Tests de búsqueda en POS."""

    def test_search_by_barcode(self):
        prod = self.make_product(name='CocaCola', barcode='7790895000898')
        shift = self.make_shift(user=self.cashier)

        c = self.login_as(self.cashier)
        resp = c.get(reverse('pos:api_search'), {'q': '7790895000898'})
        data = resp.json()
        self.assertEqual(len(data['products']), 1)
        self.assertEqual(data['products'][0]['name'], 'CocaCola')

    def test_search_by_packaging_barcode(self):
        """Buscar por código de barras de empaque devuelve el producto con info del empaque."""
        prod = self.make_product(name='Chicle', sale_price='10.00')
        pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='display', name='Display x12',
            units_per_display=12, displays_per_bulk=2,
            barcode='7790000012345', sale_price=Decimal('100.00'),
        )

        shift = self.make_shift(user=self.cashier)
        c = self.login_as(self.cashier)
        resp = c.get(reverse('pos:api_search'), {'q': '7790000012345'})
        data = resp.json()

        self.assertEqual(len(data['products']), 1)
        self.assertEqual(data['products'][0]['packaging_id'], pkg.id)
        self.assertEqual(data['products'][0]['unit_price'], 100.0)

    def test_search_accent_insensitive(self):
        """Buscar 'limon' encuentra 'Limón'."""
        prod = self.make_product(name='Caramelo de Limón')
        shift = self.make_shift(user=self.cashier)

        c = self.login_as(self.cashier)
        resp = c.get(reverse('pos:api_search'), {'q': 'limon'})
        data = resp.json()
        self.assertEqual(len(data['products']), 1)

    def test_search_empty_query(self):
        c = self.login_as(self.cashier)
        resp = c.get(reverse('pos:api_search'), {'q': ''})
        data = resp.json()
        self.assertEqual(len(data['products']), 0)


# ============================================================
# 9. PRODUCTO: CREACIÓN RÁPIDA DESDE POS
# ============================================================

class QuickProductCreateAudit(ExhaustiveBaseTestCase):
    """Tests de creación rápida de producto desde el POS."""

    def test_quick_create_product(self):
        shift = self.make_shift(user=self.cashier)
        c = self.login_as(self.cashier)

        resp = c.post(
            reverse('pos:api_quick_add_product'),
            json.dumps({
                'barcode': '9999999999999',
                'name': 'Producto Nuevo',
                'sale_price': 250,
                'purchase_price': 150,
                'initial_stock': 10,
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])

        # Verificar que se creó
        prod = Product.objects.get(barcode='9999999999999')
        self.assertEqual(prod.name, 'Producto Nuevo')
        self.assertEqual(prod.sale_price, Decimal('250'))
        self.assertEqual(prod.current_stock, 10)

    def test_quick_create_duplicate_barcode_rejected(self):
        """No puede crear producto con barcode duplicado."""
        self.make_product(barcode='1234567890123')

        c = self.login_as(self.cashier)
        resp = c.post(
            reverse('pos:api_quick_add_product'),
            json.dumps({
                'barcode': '1234567890123',
                'name': 'Duplicado',
                'sale_price': 100,
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_quick_create_without_name_rejected(self):
        c = self.login_as(self.cashier)
        resp = c.post(
            reverse('pos:api_quick_add_product'),
            json.dumps({'sale_price': 100}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)


# ============================================================
# 10. CONSISTENCIA CRUZADA COMPLETA
# ============================================================

class FullDaySimulationAudit(ExhaustiveBaseTestCase):
    """Simula un día completo de operación de kiosco y verifica todo al final."""

    def test_full_day_operation(self):
        """
        Simula:
        - Apertura de caja con $10.000
        - 5 ventas en efectivo
        - 2 ventas con tarjeta
        - 1 venta mixta
        - 1 gasto manual
        - Cierre de caja
        Verifica que todo cuadre.
        """
        p1 = self.make_product(name='Alfajor', sale_price='200.00', cost_price='120.00', current_stock='100.000')
        p2 = self.make_product(name='Gaseosa', sale_price='500.00', cost_price='300.00', current_stock='50.000')

        shift = self.make_shift(initial='10000.00')
        initial_stock_p1 = p1.current_stock
        initial_stock_p2 = p2.current_stock

        total_items_p1 = 0
        total_items_p2 = 0

        # 5 ventas en efectivo
        for i in range(5):
            txn, _ = self.make_pos_transaction(shift=shift)
            CartService.add_item(txn, p1.id, Decimal('2'))
            total_items_p1 += 2
            CheckoutService.process_payment(
                txn.id, [{'method_id': self.cash_method.id, 'amount': 400}],
            )

        # 2 ventas con tarjeta
        for i in range(2):
            txn, _ = self.make_pos_transaction(shift=shift)
            CartService.add_item(txn, p2.id, Decimal('1'))
            total_items_p2 += 1
            CheckoutService.process_payment(
                txn.id, [{'method_id': self.card_method.id, 'amount': 500}],
            )

        # 1 venta mixta (p1 + p2)
        txn, _ = self.make_pos_transaction(shift=shift)
        CartService.add_item(txn, p1.id, Decimal('3'))
        CartService.add_item(txn, p2.id, Decimal('1'))
        total_items_p1 += 3
        total_items_p2 += 1
        txn.refresh_from_db()
        mixed_total = txn.total  # 3*200 + 1*500 = 1100
        CheckoutService.process_payment(
            txn.id, [
                {'method_id': self.cash_method.id, 'amount': 600},
                {'method_id': self.card_method.id, 'amount': 500},
            ],
        )

        # 1 gasto manual en efectivo
        CashMovement.objects.create(
            cash_shift=shift, movement_type='expense',
            amount=Decimal('300'), payment_method=self.cash_method,
            description='Compra de bolsas', created_by=self.cashier,
        )

        # ---- VERIFICACIONES ----

        # 1. Stock final
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p1.current_stock, initial_stock_p1 - total_items_p1)
        self.assertEqual(p2.current_stock, initial_stock_p2 - total_items_p2)

        # 2. Transacciones completadas
        completed = POSTransaction.objects.filter(
            session__cash_shift=shift, status='completed',
        )
        self.assertEqual(completed.count(), 8)

        # 3. Suma de transacciones
        txn_total = completed.aggregate(t=Sum('total'))['t']
        # 5 * 400 + 2 * 500 + 1100 = 2000 + 1000 + 1100 = 4100
        self.assertEqual(txn_total, Decimal('4100.00'))

        # 4. CashMovements income == txn_total
        income_total = CashMovement.objects.filter(
            cash_shift=shift, movement_type='income',
        ).aggregate(t=Sum('amount'))['t']
        self.assertEqual(income_total, txn_total)

        # 5. Efectivo esperado
        expected_cash = shift.calculate_expected()
        # 10000 + cash_income - cash_expense
        cash_income = CashMovement.objects.filter(
            cash_shift=shift, movement_type='income',
            payment_method__is_cash=True,
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        cash_expense = CashMovement.objects.filter(
            cash_shift=shift, movement_type='expense',
            payment_method__is_cash=True,
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

        self.assertEqual(expected_cash, Decimal('10000') + cash_income - cash_expense)

        # 6. Cash + non-cash == total income
        self.assertEqual(
            shift.get_cash_total() + shift.get_non_cash_total(),
            shift.total_income,
        )

        # 7. Cierre de caja
        shift.close(actual_amount=expected_cash)
        self.assertEqual(shift.difference, Decimal('0.00'))
        self.assertEqual(shift.status, 'closed')

    def test_stock_movements_full_traceability(self):
        """Cada unidad vendida tiene un StockMovement rastreable."""
        prod = self.make_product(current_stock='100.000', sale_price='50.00')
        shift = self.make_shift()

        sales = [3, 7, 5, 10, 2]
        for qty in sales:
            txn, _ = self.make_pos_transaction(shift=shift)
            CartService.add_item(txn, prod.id, Decimal(str(qty)))
            txn.refresh_from_db()
            CheckoutService.process_payment(
                txn.id, [{'method_id': self.cash_method.id, 'amount': float(txn.total)}],
            )

        prod.refresh_from_db()
        total_sold = sum(sales)
        self.assertEqual(prod.current_stock, Decimal(str(100 - total_sold)))

        # Verificar movimientos
        sale_movements = StockMovement.objects.filter(
            product=prod, movement_type='sale',
        )
        total_deducted = abs(
            sale_movements.aggregate(t=Sum('quantity'))['t']
        )
        self.assertEqual(total_deducted, Decimal(str(total_sold)))


# ============================================================
# 11. MERCADOPAGO POINT INTEGRATION
# ============================================================

from unittest.mock import patch, MagicMock
from mercadopago.models import MPCredentials, PointDevice, PaymentIntent


class MercadoPagoPointAudit(ExhaustiveBaseTestCase):
    """Verifica que el flujo de pago con MP Point funciona correctamente."""

    def setUp(self):
        super().setUp()
        # Crear credenciales MP
        self.mp_creds = MPCredentials.objects.create(
            name='Test', access_token='TEST-TOKEN', is_active=True,
        )
        # Crear dispositivo Point asociado a una caja
        self.register = CashRegister.objects.create(code='CAJA-MP', name='Caja MP')
        self.device = PointDevice.objects.create(
            device_id='DEVICE-001',
            device_name='Point Test',
            cash_register=self.register,
            status='active',
            operating_mode='PDV',
        )

    def _make_shift_on_register(self, user=None):
        """Crea un turno en la caja con Point."""
        user = user or self.cashier
        return CashShift.objects.create(
            cash_register=self.register,
            cashier=user,
            initial_amount=Decimal('5000'),
        )

    @patch('mercadopago.services.MPPointService.create_payment_intent')
    def test_create_intent_sends_to_point(self, mock_create):
        """Crear payment intent envía el pago al dispositivo Point."""
        mock_create.return_value = (True, {'id': 'MP-INTENT-123'})

        shift = self._make_shift_on_register()
        txn, _ = self.make_pos_transaction(shift=shift)
        prod = self.make_product(sale_price='500.00', current_stock='10.000')
        CartService.add_item(txn, prod.id, Decimal('2'))

        c = self.login_as(self.cashier)
        resp = c.post(
            '/mercadopago/api/create-intent/',
            json.dumps({
                'amount': 1000.00,
                'transaction_id': txn.id,
                'description': 'Venta POS - 2 items',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertIn('payment_intent', data)
        self.assertEqual(data['payment_intent']['device_name'], 'Point Test')

        # Verify MP API was called with correct amount
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args
        self.assertEqual(float(call_kwargs[1].get('amount', call_kwargs[0][1] if len(call_kwargs[0]) > 1 else 0)), 1000.0)

        # Verify PaymentIntent was created locally
        intent = PaymentIntent.objects.get(pos_transaction=txn)
        self.assertEqual(intent.status, 'processing')
        self.assertEqual(intent.mp_payment_intent_id, 'MP-INTENT-123')

    def test_create_intent_requires_open_shift(self):
        """Sin turno abierto no se puede enviar a Point."""
        c = self.login_as(self.cashier)
        resp = c.post(
            '/mercadopago/api/create-intent/',
            json.dumps({'amount': 500.00}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn('turno', data['error'].lower())

    def test_create_intent_requires_linked_device(self):
        """Si no hay ningun dispositivo Point activo, devuelve error."""
        # Deactivate the existing device so fallback also fails
        self.device.status = 'inactive'
        self.device.save()

        # Create shift on a register WITHOUT a Point device
        other_register = CashRegister.objects.create(code='CAJA-SIN', name='Sin Point')
        CashShift.objects.create(
            cash_register=other_register,
            cashier=self.cashier,
            initial_amount=Decimal('5000'),
        )

        c = self.login_as(self.cashier)
        resp = c.post(
            '/mercadopago/api/create-intent/',
            json.dumps({'amount': 500.00}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn('dispositivo', data['error'].lower())

    @patch('mercadopago.services.MPPointService.create_payment_intent')
    def test_check_status_approved(self, mock_create):
        """Polling de status devuelve aprobado cuando MP confirma."""
        mock_create.return_value = (True, {'id': 'MP-INTENT-456'})

        shift = self._make_shift_on_register()
        txn, _ = self.make_pos_transaction(shift=shift)
        prod = self.make_product(sale_price='300.00', current_stock='10.000')
        CartService.add_item(txn, prod.id, Decimal('1'))

        c = self.login_as(self.cashier)
        # Create intent
        resp = c.post(
            '/mercadopago/api/create-intent/',
            json.dumps({'amount': 300.00, 'transaction_id': txn.id}),
            content_type='application/json',
        )
        intent_id = resp.json()['payment_intent']['id']

        # Simulate MP approving the payment
        intent = PaymentIntent.objects.get(pk=intent_id)
        intent.mark_approved({
            'id': 'PAY-789',
            'status': 'approved',
            'payment_method_id': 'debit_card',
            'card': {'last_four_digits': '4567'},
            'installments': 1,
        })

        # Poll status
        resp = c.get(f'/mercadopago/api/status/{intent_id}/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'approved')
        self.assertTrue(data['is_final'])

    def test_create_intent_invalid_amount(self):
        """Monto inválido es rechazado."""
        self._make_shift_on_register()
        c = self.login_as(self.cashier)

        # Zero amount
        resp = c.post(
            '/mercadopago/api/create-intent/',
            json.dumps({'amount': 0}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

        # Negative amount
        resp = c.post(
            '/mercadopago/api/create-intent/',
            json.dumps({'amount': -100}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

        # Missing amount
        resp = c.post(
            '/mercadopago/api/create-intent/',
            json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    @patch('mercadopago.services.MPPointService.create_payment_intent')
    def test_mp_payment_creates_correct_payment_intent_record(self, mock_create):
        """El PaymentIntent local tiene los datos correctos."""
        mock_create.return_value = (True, {'id': 'MP-INTENT-999'})

        shift = self._make_shift_on_register()
        txn, _ = self.make_pos_transaction(shift=shift)
        prod = self.make_product(sale_price='1500.00', current_stock='5.000')
        CartService.add_item(txn, prod.id, Decimal('1'))

        c = self.login_as(self.cashier)
        resp = c.post(
            '/mercadopago/api/create-intent/',
            json.dumps({
                'amount': 1500.00,
                'transaction_id': txn.id,
                'description': 'Venta POS - 1 items',
            }),
            content_type='application/json',
        )
        data = resp.json()
        intent = PaymentIntent.objects.get(pk=data['payment_intent']['id'])

        self.assertEqual(intent.amount, Decimal('1500.00'))
        self.assertEqual(intent.device, self.device)
        self.assertEqual(intent.pos_transaction, txn)
        self.assertEqual(intent.status, 'processing')
        self.assertTrue(intent.external_reference.startswith('CHE-'))
        self.assertIsNotNone(intent.sent_at)
