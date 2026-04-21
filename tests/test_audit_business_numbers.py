"""
CHE GOLOSO - Auditoría Integral de Números del Negocio
======================================================
Estos tests verifican la consistencia aritmética de TODOS los flujos
que manipulan stock, precios, pagos, caja y promociones.

Rol: Auditor experto independiente.
Objetivo: detectar inconsistencias numéricas, edge cases peligrosos y
discrepancias entre distintos caminos de cálculo.
"""
import json
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Sum, F, DecimalField

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

User = get_user_model()


# ============================================================
# Helpers de setup reutilizables
# ============================================================

class AuditBaseTestCase(TestCase):
    """Base con entidades mínimas para todas las pruebas de auditoría."""

    @classmethod
    def setUpTestData(cls):
        # Roles
        cls.admin_group, _ = Group.objects.get_or_create(name='Admin')
        cls.cashier_group, _ = Group.objects.get_or_create(name='Cashier')

        # Usuarios
        cls.admin = User.objects.create_user(
            username='audit_admin', password='pass123',
            is_superuser=True, is_staff=True,
        )
        cls.admin.groups.add(cls.admin_group)

        cls.cashier = User.objects.create_user(
            username='audit_cashier', password='pass123',
        )
        cls.cashier.groups.add(cls.cashier_group)

        # Métodos de pago
        cls.cash_method = PaymentMethod.objects.create(
            code='cash', name='Efectivo', is_cash=True,
            requires_counting=True, position=1,
        )
        cls.card_method = PaymentMethod.objects.create(
            code='debit', name='Débito', is_cash=False,
            requires_counting=False, position=2,
        )
        cls.transfer_method = PaymentMethod.objects.create(
            code='transfer', name='Transferencia', is_cash=False,
            requires_counting=False, position=3,
        )

        # Categoría
        cls.category = ProductCategory.objects.create(name='Golosinas')

    # ---- helpers de instancia ----

    def make_product(self, name='TestProd', sale_price='100.00',
                     purchase_price='60.00', cost_price='60.00',
                     current_stock='50.000', **kw):
        return Product.objects.create(
            name=name,
            sale_price=Decimal(sale_price),
            purchase_price=Decimal(purchase_price),
            cost_price=Decimal(cost_price),
            current_stock=Decimal(current_stock),
            category=self.category,
            **kw,
        )

    def make_shift(self, initial_amount='5000.00'):
        register = CashRegister.objects.create(
            code=f'CAJA-{CashRegister.objects.count()+1:02d}', name='Caja Test',
        )
        return CashShift.objects.create(
            cash_register=register, cashier=self.cashier,
            initial_amount=Decimal(initial_amount),
        )

    def make_pos_transaction(self, shift=None):
        """Crea session + transacción pendiente lista para usar."""
        shift = shift or self.make_shift()
        session = POSService.get_or_create_session(shift)
        txn = POSService.get_pending_transaction(session)
        return txn, shift


# ============================================================
# 1. AUDITORÍA DE STOCK
# ============================================================

class StockDeductionAudit(AuditBaseTestCase):
    """Verifica que cada deducción de stock sea aritméticamente correcta
    y que los movimientos reflejen exactamente lo ocurrido."""

    def test_deduct_stock_basic_arithmetic(self):
        """stock_before - qty == stock_after, y el movimiento lo registra."""
        prod = self.make_product(current_stock='100.000')
        ok, msg, mov = StockManagementService.deduct_stock(prod, 7)
        prod.refresh_from_db()

        self.assertTrue(ok)
        self.assertEqual(prod.current_stock, Decimal('93.000'))
        self.assertEqual(mov.stock_before, Decimal('100.000'))
        self.assertEqual(mov.stock_after, Decimal('93.000'))
        self.assertEqual(mov.quantity, Decimal('-7'))

    def test_deduct_stock_allows_negative_stock(self):
        """El sistema permite stock negativo (documentar comportamiento)."""
        prod = self.make_product(current_stock='3.000')
        ok, msg, mov = StockManagementService.deduct_stock(prod, 10)
        prod.refresh_from_db()

        self.assertTrue(ok)
        self.assertEqual(prod.current_stock, Decimal('-7.000'))
        self.assertIn('ALERTA', mov.notes)

    def test_deduct_stock_movement_chain_consistency(self):
        """Múltiples deducciones: la cadena stock_after[n] == stock_before[n+1]."""
        prod = self.make_product(current_stock='100.000')

        quantities = [Decimal('10'), Decimal('25'), Decimal('5'), Decimal('30')]
        for qty in quantities:
            StockManagementService.deduct_stock(prod, qty)
            prod.refresh_from_db()

        movements = StockMovement.objects.filter(product=prod).order_by('created_at')
        prev_after = None
        for mov in movements:
            if prev_after is not None:
                self.assertEqual(
                    mov.stock_before, prev_after,
                    f'Cadena rota: mov {mov.id} stock_before={mov.stock_before} '
                    f'pero anterior stock_after={prev_after}',
                )
            prev_after = mov.stock_after

        # Verificar total
        prod.refresh_from_db()
        expected = Decimal('100') - sum(quantities)
        self.assertEqual(prod.current_stock, expected)


class StockAdditionAudit(AuditBaseTestCase):
    """Verifica adiciones de stock y cálculo de costo promedio ponderado."""

    def test_add_stock_basic(self):
        prod = self.make_product(current_stock='10.000', cost_price='50.00')
        mov = StockManagementService.add_stock(prod, 20, cost=Decimal('80.00'))
        prod.refresh_from_db()

        self.assertEqual(prod.current_stock, Decimal('30.000'))
        # Costo promedio = (50*10 + 80*20) / 30 = 2100/30 = 70.00
        expected_cost = (Decimal('50') * 10 + Decimal('80') * 20) / 30
        self.assertAlmostEqual(float(prod.cost_price), float(expected_cost), places=2)

    def test_add_stock_zero_initial_stock(self):
        """Cuando stock=0, el costo promedio debe ser el costo de la nueva compra."""
        prod = self.make_product(current_stock='0.000', cost_price='0.00')
        StockManagementService.add_stock(prod, 10, cost=Decimal('100.00'))
        prod.refresh_from_db()

        self.assertEqual(prod.current_stock, Decimal('10.000'))
        self.assertEqual(prod.cost_price, Decimal('100.00'))

    def test_weighted_average_cost_multiple_additions(self):
        """Verifica el cálculo incremental del costo promedio."""
        prod = self.make_product(current_stock='0.000', cost_price='0.00')

        # Compra 1: 10 u a $100
        StockManagementService.add_stock(prod, 10, cost=Decimal('100.00'))
        prod.refresh_from_db()
        self.assertEqual(prod.cost_price, Decimal('100.00'))

        # Compra 2: 20 u a $130
        StockManagementService.add_stock(prod, 20, cost=Decimal('130.00'))
        prod.refresh_from_db()
        # (100*10 + 130*20) / 30 = 3600/30 = 120
        expected = (Decimal('100') * 10 + Decimal('130') * 20) / 30
        self.assertAlmostEqual(float(prod.cost_price), float(expected), places=2)


class StockAdjustmentAudit(AuditBaseTestCase):
    """Audita ajustes de inventario."""

    def test_adjust_stock_up(self):
        prod = self.make_product(current_stock='10.000')
        mov = StockManagementService.adjust_stock(prod, Decimal('25'), 'Reconteo')
        prod.refresh_from_db()

        self.assertEqual(prod.current_stock, Decimal('25.000'))
        self.assertEqual(mov.movement_type, 'adjustment_in')
        self.assertEqual(mov.quantity, Decimal('15'))

    def test_adjust_stock_down(self):
        prod = self.make_product(current_stock='30.000')
        mov = StockManagementService.adjust_stock(prod, Decimal('12'), 'Merma')
        prod.refresh_from_db()

        self.assertEqual(prod.current_stock, Decimal('12.000'))
        self.assertEqual(mov.movement_type, 'adjustment_out')
        self.assertEqual(mov.quantity, Decimal('-18'))

    def test_adjust_stock_no_change(self):
        prod = self.make_product(current_stock='10.000')
        mov = StockManagementService.adjust_stock(prod, Decimal('10'), 'Verificación')
        self.assertEqual(mov.quantity, Decimal('0'))
        self.assertEqual(mov.movement_type, 'adjustment_in')  # >= 0


class StockPackagingCascadeAudit(AuditBaseTestCase):
    """Verifica la cascada de stock a través de los niveles de packaging."""

    def _setup_product_with_packaging(self, stock=Decimal('288')):
        """Producto con 3 niveles: unidad, display (12u), bulto (24u=2disp*12u)."""
        prod = self.make_product(name='Chicle', current_stock=str(stock))
        unit_pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='unit', name='Unidad',
            units_per_display=12, displays_per_bulk=2,
            purchase_price=Decimal('10'), sale_price=Decimal('15'),
            current_stock=stock,
        )
        display_pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='display', name='Display x12',
            units_per_display=12, displays_per_bulk=2,
            purchase_price=Decimal('100'), sale_price=Decimal('150'),
            current_stock=stock / 12,
        )
        bulk_pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='bulk', name='Bulto x24',
            units_per_display=12, displays_per_bulk=2,
            purchase_price=Decimal('200'), sale_price=Decimal('280'),
            current_stock=stock / 24,
        )
        return prod, unit_pkg, display_pkg, bulk_pkg

    def test_cascade_deduct_proportional(self):
        """Deducir N unidades descuenta proporcionalmente en todos los niveles."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup_product_with_packaging(
            stock=Decimal('288'),
        )
        deduct_qty = Decimal('24')
        StockManagementService.deduct_stock_with_cascade(
            prod, deduct_qty, reference='test',
        )

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()

        # Producto: 288 - 24 = 264
        self.assertEqual(prod.current_stock, Decimal('264'))
        # Unidad: 288 - 24 = 264
        self.assertEqual(unit_pkg.current_stock, Decimal('264'))
        # Display: 24 - 24/12 = 22
        self.assertEqual(display_pkg.current_stock, Decimal('22'))
        # Bulto: 12 - 24/24 = 11
        self.assertEqual(bulk_pkg.current_stock, Decimal('11'))

    def test_cascade_consistency_unit_equals_product(self):
        """El stock del packaging 'unit' debe coincidir con product.current_stock."""
        prod, unit_pkg, _, _ = self._setup_product_with_packaging(Decimal('288'))
        StockManagementService.deduct_stock_with_cascade(prod, Decimal('50'), reference='test')

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()

        self.assertEqual(
            prod.current_stock, unit_pkg.current_stock,
            'El stock del producto base y el packaging "unit" deben ser iguales.',
        )

    def test_receive_packaging_updates_all_levels(self):
        """Recibir bultos actualiza producto, unidades, displays y bultos."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup_product_with_packaging(
            stock=Decimal('0'),
        )
        # Asignar stock 0 a todos
        unit_pkg.current_stock = Decimal('0')
        unit_pkg.save()
        display_pkg.current_stock = Decimal('0')
        display_pkg.save()
        bulk_pkg.current_stock = Decimal('0')
        bulk_pkg.save()
        prod.current_stock = Decimal('0')
        prod.save()

        # Recibir 5 bultos (cada bulto = 24 unidades)
        StockManagementService.receive_packaging(bulk_pkg, quantity=5)

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()

        # Bulto: 0 + 5 = 5
        self.assertEqual(bulk_pkg.current_stock, Decimal('5'))
        # Producto base: 0 + 5*24 = 120 unidades
        self.assertEqual(prod.current_stock, Decimal('120'))
        # Unidad: 0 + 120
        self.assertEqual(unit_pkg.current_stock, Decimal('120'))
        # Display: 0 + 120/12 = 10
        self.assertEqual(display_pkg.current_stock, Decimal('10'))

    def test_open_packaging_bulk_to_display(self):
        """Abrir un bulto convierte a displays sin cambiar product.current_stock."""
        prod, _, display_pkg, bulk_pkg = self._setup_product_with_packaging(Decimal('288'))

        stock_before = prod.current_stock
        StockManagementService.open_packaging(bulk_pkg, quantity=1)

        prod.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()

        # Product.current_stock NO cambia
        self.assertEqual(prod.current_stock, stock_before)
        # Bulto: 12 - 1 = 11
        self.assertEqual(bulk_pkg.current_stock, Decimal('11'))
        # Display: 24 + 2 (displays_per_bulk=2) = 26
        self.assertEqual(display_pkg.current_stock, Decimal('26'))

    def test_open_packaging_display_to_unit(self):
        """Abrir un display convierte a unidades sin cambiar product.current_stock."""
        prod, unit_pkg, display_pkg, _ = self._setup_product_with_packaging(Decimal('288'))

        stock_before = prod.current_stock
        StockManagementService.open_packaging(display_pkg, quantity=2)

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()

        self.assertEqual(prod.current_stock, stock_before)
        # Display: 24 - 2 = 22
        self.assertEqual(display_pkg.current_stock, Decimal('22'))
        # Unidad: 288 + 2*12 = 312
        self.assertEqual(unit_pkg.current_stock, Decimal('312'))

    def test_adjust_stock_cascades_up(self):
        """Conteo físico POR ARRIBA: resync absoluto de todos los niveles."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup_product_with_packaging(
            stock=Decimal('288'),
        )
        StockManagementService.adjust_stock(prod, Decimal('312'), 'Conteo físico')

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()

        self.assertEqual(prod.current_stock, Decimal('312'))
        self.assertEqual(unit_pkg.current_stock, Decimal('312'))
        # Display: 312/12 = 26
        self.assertEqual(display_pkg.current_stock, Decimal('26'))
        # Bulto: 312/24 = 13
        self.assertEqual(bulk_pkg.current_stock, Decimal('13'))

    def test_adjust_stock_cascades_down(self):
        """Conteo físico POR DEBAJO: resync absoluto de todos los niveles."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup_product_with_packaging(
            stock=Decimal('288'),
        )
        StockManagementService.adjust_stock(prod, Decimal('240'), 'Merma')

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()

        self.assertEqual(prod.current_stock, Decimal('240'))
        self.assertEqual(unit_pkg.current_stock, Decimal('240'))
        # Display: 240/12 = 20
        self.assertEqual(display_pkg.current_stock, Decimal('20'))
        # Bulto: 240/24 = 10
        self.assertEqual(bulk_pkg.current_stock, Decimal('10'))

    def test_adjust_stock_repairs_desync(self):
        """Si los packagings venían desincronizados, el ajuste los repara."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup_product_with_packaging(
            stock=Decimal('288'),
        )
        # Simular estado corrupto (el bug histórico): display y bulto
        # quedaron viejos mientras el producto ya se actualizó por el lado.
        display_pkg.current_stock = Decimal('999')
        display_pkg.save()
        bulk_pkg.current_stock = Decimal('999')
        bulk_pkg.save()

        # El cajero cuenta 240 físicamente → los 3 niveles deben quedar consistentes
        StockManagementService.adjust_stock(prod, Decimal('240'), 'Conteo físico')

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()

        self.assertEqual(prod.current_stock, Decimal('240'))
        self.assertEqual(unit_pkg.current_stock, Decimal('240'))
        self.assertEqual(display_pkg.current_stock, Decimal('20'))
        self.assertEqual(bulk_pkg.current_stock, Decimal('10'))

    def test_adjust_stock_unit_always_matches_product(self):
        """Tras adjust_stock, unit_pkg.current_stock == product.current_stock."""
        prod, unit_pkg, _, _ = self._setup_product_with_packaging(Decimal('288'))
        StockManagementService.adjust_stock(prod, Decimal('17'), 'Reconteo')

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        self.assertEqual(prod.current_stock, unit_pkg.current_stock)


class EndToEndSaleAndPurchaseCascade(AuditBaseTestCase):
    """Tests de producción: venta real por packaging y recepción de compra real."""

    def _setup_product_with_packaging(self, stock=Decimal('288')):
        """Producto Chicle: 1u, 1 display = 12u, 1 bulto = 24u (2 displays)."""
        prod = self.make_product(
            name='Chicle',
            sale_price='15.00',
            purchase_price='10.00',
            cost_price='10.00',
            current_stock=str(stock),
        )
        unit_pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='unit', name='Unidad',
            barcode='1000000000001',
            units_per_display=12, displays_per_bulk=2,
            purchase_price=Decimal('10'), sale_price=Decimal('15'),
            current_stock=stock,
        )
        display_pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='display', name='Display x12',
            barcode='1000000000002',
            units_per_display=12, displays_per_bulk=2,
            purchase_price=Decimal('100'), sale_price=Decimal('150'),
            current_stock=stock / 12,
        )
        bulk_pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='bulk', name='Bulto x24',
            barcode='1000000000003',
            units_per_display=12, displays_per_bulk=2,
            purchase_price=Decimal('200'), sale_price=Decimal('280'),
            current_stock=stock / 24,
        )
        return prod, unit_pkg, display_pkg, bulk_pkg

    # ----- VENTAS -----

    def test_sell_one_display_cascades_all_levels(self):
        """Vender 1 display via POS: descuenta 12 unidades y cascade a los 3 niveles."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup_product_with_packaging(
            stock=Decimal('288'),
        )
        txn, shift = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('1'), packaging_id=display_pkg.id)
        txn.refresh_from_db()
        # 1 display a $150
        self.assertEqual(txn.total, Decimal('150.00'))

        ok, result = CheckoutService.process_payment(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 150}],
        )
        self.assertTrue(ok)

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()

        # Producto base: 288 - 12 = 276
        self.assertEqual(prod.current_stock, Decimal('276'))
        # Unidad: mirror de producto
        self.assertEqual(unit_pkg.current_stock, Decimal('276'))
        # Display: 24 - 1 = 23
        self.assertEqual(display_pkg.current_stock, Decimal('23'))
        # Bulto: 12 - 12/24 = 11.5
        self.assertEqual(bulk_pkg.current_stock, Decimal('11.5'))

    def test_sell_two_bulks_cascades_all_levels(self):
        """Vender 2 bultos: descuenta 48 unidades y cascade correcta."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup_product_with_packaging(
            stock=Decimal('288'),
        )
        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('2'), packaging_id=bulk_pkg.id)
        txn.refresh_from_db()
        # 2 bultos x $280
        self.assertEqual(txn.total, Decimal('560.00'))

        ok, _ = CheckoutService.process_payment(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 560}],
        )
        self.assertTrue(ok)

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()

        # Producto: 288 - 48 = 240
        self.assertEqual(prod.current_stock, Decimal('240'))
        # Unidad: 240
        self.assertEqual(unit_pkg.current_stock, Decimal('240'))
        # Display: 24 - 48/12 = 20
        self.assertEqual(display_pkg.current_stock, Decimal('20'))
        # Bulto: 12 - 2 = 10
        self.assertEqual(bulk_pkg.current_stock, Decimal('10'))

    def test_sell_five_units_cascades(self):
        """Vender 5 unidades sueltas: cascade a display y bulto en fracciones."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup_product_with_packaging(
            stock=Decimal('288'),
        )
        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('5'), packaging_id=unit_pkg.id)
        txn.refresh_from_db()
        self.assertEqual(txn.total, Decimal('75.00'))

        ok, _ = CheckoutService.process_payment(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 75}],
        )
        self.assertTrue(ok)

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()

        self.assertEqual(prod.current_stock, Decimal('283'))
        self.assertEqual(unit_pkg.current_stock, Decimal('283'))
        # Display: 24 - 5/12 = 23.583 (DB redondea a 3 decimales)
        q = Decimal('0.001')
        expected_display = (Decimal('24') - Decimal('5') / Decimal('12')).quantize(q)
        self.assertEqual(display_pkg.current_stock.quantize(q), expected_display)
        # Bulto: 12 - 5/24
        expected_bulk = (Decimal('12') - Decimal('5') / Decimal('24')).quantize(q)
        self.assertEqual(bulk_pkg.current_stock.quantize(q), expected_bulk)

    def test_sale_keeps_invariant_unit_equals_product(self):
        """Invariante post-venta: unit_pkg.current_stock == product.current_stock."""
        prod, unit_pkg, display_pkg, _ = self._setup_product_with_packaging(
            stock=Decimal('288'),
        )
        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('3'), packaging_id=display_pkg.id)
        CheckoutService.process_payment(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 450}],
        )
        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        self.assertEqual(prod.current_stock, unit_pkg.current_stock)

    # ----- RECEPCIÓN DE COMPRA -----

    def _make_purchase(self, product, packaging, quantity, unit_cost):
        """Crea una orden de compra pendiente de recepción."""
        supplier, _ = Supplier.objects.get_or_create(name='Proveedor Test')
        purchase = Purchase.objects.create(
            supplier=supplier,
            order_number=f'OC-{Purchase.objects.count()+1:04d}',
            status='ordered',
            subtotal=Decimal(unit_cost) * Decimal(quantity),
            total=Decimal(unit_cost) * Decimal(quantity),
            created_by=self.admin,
        )
        PurchaseItem.objects.create(
            purchase=purchase,
            product=product,
            packaging=packaging,
            quantity=quantity,
            unit_cost=Decimal(unit_cost),
        )
        return purchase

    def _receive_purchase(self, purchase):
        """Replica la lógica de purchase_receive (add_stock en cascada + batch)."""
        from stocks.models import StockBatch
        from datetime import datetime
        for item in purchase.items.all():
            if item.packaging and item.packaging.units_quantity > 0:
                units_per_pkg = Decimal(str(item.packaging.units_quantity))
                base_qty = Decimal(str(item.quantity)) * units_per_pkg
                unit_cost_base = (
                    item.unit_cost / units_per_pkg
                ).quantize(Decimal('0.0001'))
            else:
                base_qty = Decimal(str(item.quantity))
                unit_cost_base = item.unit_cost
            StockManagementService.add_stock(
                product=item.product,
                quantity=base_qty,
                cost=unit_cost_base,
                reference=purchase.order_number,
                user=self.admin,
            )
            StockBatch.objects.create(
                product=item.product,
                purchase=purchase,
                supplier_name=purchase.supplier.name,
                quantity_purchased=base_qty,
                quantity_remaining=base_qty,
                purchase_price=unit_cost_base,
                purchased_at=timezone.now(),
                created_by=self.admin,
            )
        purchase.status = 'received'
        purchase.received_date = timezone.now().date()
        purchase.save()

    def test_receive_bulks_cascades_all_levels(self):
        """Recibir 3 bultos (72u) via add_stock: cascade a producto + 3 packagings."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup_product_with_packaging(
            stock=Decimal('0'),
        )
        # Reset stocks a 0 (el helper pone fracciones)
        for p in (unit_pkg, display_pkg, bulk_pkg):
            p.current_stock = Decimal('0')
            p.save()

        purchase = self._make_purchase(prod, bulk_pkg, quantity=3, unit_cost='200')
        self._receive_purchase(purchase)

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()

        # Producto: 0 + 3*24 = 72
        self.assertEqual(prod.current_stock, Decimal('72'))
        # Unidad: mirror
        self.assertEqual(unit_pkg.current_stock, Decimal('72'))
        # Display: 0 + 72/12 = 6
        self.assertEqual(display_pkg.current_stock, Decimal('6'))
        # Bulto: 0 + 72/24 = 3
        self.assertEqual(bulk_pkg.current_stock, Decimal('3'))

    def test_receive_displays_cascades_all_levels(self):
        """Recibir 5 displays (60u) via add_stock."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup_product_with_packaging(
            stock=Decimal('0'),
        )
        for p in (unit_pkg, display_pkg, bulk_pkg):
            p.current_stock = Decimal('0')
            p.save()

        purchase = self._make_purchase(prod, display_pkg, quantity=5, unit_cost='100')
        self._receive_purchase(purchase)

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()

        # 5 displays x 12u = 60u
        self.assertEqual(prod.current_stock, Decimal('60'))
        self.assertEqual(unit_pkg.current_stock, Decimal('60'))
        self.assertEqual(display_pkg.current_stock, Decimal('5'))
        # Bulto: 0 + 60/24 = 2.5
        self.assertEqual(bulk_pkg.current_stock, Decimal('2.5'))

    def test_receive_units_cascades_all_levels(self):
        """Recibir 100 unidades sueltas via add_stock."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup_product_with_packaging(
            stock=Decimal('0'),
        )
        for p in (unit_pkg, display_pkg, bulk_pkg):
            p.current_stock = Decimal('0')
            p.save()

        purchase = self._make_purchase(prod, unit_pkg, quantity=100, unit_cost='10')
        self._receive_purchase(purchase)

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()

        self.assertEqual(prod.current_stock, Decimal('100'))
        self.assertEqual(unit_pkg.current_stock, Decimal('100'))
        q = Decimal('0.001')
        self.assertEqual(
            display_pkg.current_stock.quantize(q),
            (Decimal('100') / Decimal('12')).quantize(q),
        )
        self.assertEqual(
            bulk_pkg.current_stock.quantize(q),
            (Decimal('100') / Decimal('24')).quantize(q),
        )

    # ----- CICLOS COMPLETOS COMPRA → VENTA -----

    def test_full_cycle_buy_then_sell(self):
        """Compra de 2 bultos + venta de 1 display: stocks finales consistentes."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup_product_with_packaging(
            stock=Decimal('0'),
        )
        for p in (unit_pkg, display_pkg, bulk_pkg):
            p.current_stock = Decimal('0')
            p.save()

        # Comprar 2 bultos = 48 unidades
        purchase = self._make_purchase(prod, bulk_pkg, quantity=2, unit_cost='200')
        self._receive_purchase(purchase)

        prod.refresh_from_db()
        self.assertEqual(prod.current_stock, Decimal('48'))

        # Vender 1 display = 12 unidades
        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('1'), packaging_id=display_pkg.id)
        CheckoutService.process_payment(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 150}],
        )

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()

        # 48 - 12 = 36
        self.assertEqual(prod.current_stock, Decimal('36'))
        self.assertEqual(unit_pkg.current_stock, Decimal('36'))
        # Display: 0 + 48/12 - 1 = 3
        self.assertEqual(display_pkg.current_stock, Decimal('3'))
        # Bulto: 0 + 2 - 12/24 = 1.5
        self.assertEqual(bulk_pkg.current_stock, Decimal('1.5'))


# ============================================================
# 2. AUDITORÍA DE PRECIOS Y MÁRGENES
# ============================================================

class PriceAndMarginAudit(AuditBaseTestCase):
    """Verifica cálculos de margen, ganancia y valores de stock."""

    def test_margin_percent_formula(self):
        """margin = (venta - costo) / costo * 100"""
        prod = self.make_product(sale_price='130.00', purchase_price='100.00', cost_price='100.00')
        self.assertEqual(prod.margin_percent, Decimal('30.00'))

    def test_margin_percent_zero_purchase(self):
        """Si cost_price=0, margen debe ser 0 (no dividir por cero)."""
        prod = self.make_product(sale_price='100.00', purchase_price='0.00', cost_price='0.00')
        self.assertEqual(prod.margin_percent, 0)

    def test_margin_percent_negative_margin(self):
        """Si se vende por debajo del costo, margen debe ser negativo."""
        prod = self.make_product(sale_price='80.00', purchase_price='100.00', cost_price='100.00')
        self.assertEqual(prod.margin_percent, Decimal('-20.00'))

    def test_profit_per_unit(self):
        prod = self.make_product(sale_price='150.00', purchase_price='100.00', cost_price='100.00')
        self.assertEqual(prod.profit, Decimal('50.00'))

    def test_stock_value_at_cost(self):
        prod = self.make_product(current_stock='25.000', cost_price='80.00')
        self.assertEqual(prod.stock_value, Decimal('25') * Decimal('80'))

    def test_stock_value_at_sale(self):
        prod = self.make_product(current_stock='25.000', sale_price='120.00')
        self.assertEqual(prod.stock_value_sale, Decimal('25') * Decimal('120'))

    def test_calculate_quantity_for_amount_bulk(self):
        """$500 de un producto a $200/kg → 2.500 kg."""
        prod = self.make_product(sale_price='200.00', is_bulk=True, bulk_unit='kg')
        qty, total = prod.calculate_quantity_for_amount(Decimal('500'))
        self.assertEqual(qty, Decimal('2.500'))
        self.assertEqual(total, Decimal('500.000'))

    def test_calculate_quantity_for_amount_zero_price(self):
        """Precio cero no debe dar error de división."""
        prod = self.make_product(sale_price='0.01')  # Min allowed by validator
        prod.sale_price = Decimal('0')
        qty, total = prod.calculate_quantity_for_amount(Decimal('500'))
        self.assertEqual(qty, Decimal('0'))
        self.assertEqual(total, Decimal('0'))


class PackagingPriceAudit(AuditBaseTestCase):
    """Verifica cálculos de precios en packaging."""

    def _make_bulk_packaging(self, purchase_price='2400.00', margin='30.00'):
        prod = self.make_product(name='Test Packaging')
        pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='bulk', name='Bulto x24',
            units_per_display=12, displays_per_bulk=2,
            purchase_price=Decimal(purchase_price),
            sale_price=Decimal('3120.00'),
            margin_percent=Decimal(margin),
        )
        return pkg

    def test_unit_purchase_price(self):
        """unit_purchase_price = purchase_price / units_quantity"""
        pkg = self._make_bulk_packaging(purchase_price='2400.00')
        # units_quantity = 12 * 2 = 24
        expected = Decimal('2400') / 24
        self.assertEqual(pkg.unit_purchase_price, expected)

    def test_unit_sale_price(self):
        pkg = self._make_bulk_packaging()
        expected = Decimal('3120') / 24
        self.assertEqual(pkg.unit_sale_price, expected)

    def test_display_purchase_price_from_bulk(self):
        pkg = self._make_bulk_packaging(purchase_price='2400.00')
        # display_purchase_price = purchase_price / displays_per_bulk = 2400/2
        self.assertEqual(pkg.display_purchase_price, Decimal('1200'))

    def test_calculate_prices_from_margin(self):
        """Verifica que todos los precios derivados del margen sean coherentes."""
        pkg = self._make_bulk_packaging(purchase_price='2400.00', margin='30.00')
        result = pkg.calculate_prices_from_margin()

        self.assertIsNotNone(result)
        # bulk_sale = 2400 * 1.30 = 3120
        self.assertEqual(result['bulk_sale'], Decimal('3120.00'))
        # unit_sale = 3120 / 24 = 130.00
        self.assertEqual(result['unit_sale'], Decimal('130.00'))
        # display_sale = 3120 / 2 = 1560.00
        self.assertEqual(result['display_sale'], Decimal('1560.00'))
        # Profit per bulk = 3120 - 2400 = 720
        self.assertEqual(result['profit_per_bulk'], Decimal('720.00'))

    def test_calculate_prices_from_margin_zero_purchase(self):
        """Con purchase_price=0, debe retornar None."""
        prod = self.make_product()
        pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='bulk', name='Bulto',
            units_per_display=12, displays_per_bulk=2,
            purchase_price=Decimal('0.00'),
        )
        self.assertIsNone(pkg.calculate_prices_from_margin())

    def test_packaging_save_auto_calculates_units_quantity(self):
        """Verifica que save() calcule units_quantity correctamente."""
        prod = self.make_product()

        unit = ProductPackaging.objects.create(
            product=prod, packaging_type='unit', name='U',
            units_per_display=12, displays_per_bulk=2,
        )
        self.assertEqual(unit.units_quantity, 1)

        display = ProductPackaging.objects.create(
            product=prod, packaging_type='display', name='D',
            units_per_display=12, displays_per_bulk=2,
        )
        self.assertEqual(display.units_quantity, 12)

        bulk = ProductPackaging.objects.create(
            product=prod, packaging_type='bulk', name='B',
            units_per_display=12, displays_per_bulk=2,
        )
        self.assertEqual(bulk.units_quantity, 24)


# ============================================================
# 3. AUDITORÍA DE PAGOS Y CHECKOUT
# ============================================================

class PaymentCheckoutAudit(AuditBaseTestCase):
    """Verifica que el flujo de checkout sea aritméticamente consistente."""

    def test_simple_cash_payment(self):
        """Pago exacto en efectivo: total == paid, change == 0."""
        prod = self.make_product(sale_price='500.00', current_stock='50.000')
        txn, shift = self.make_pos_transaction()

        CartService.add_item(txn, prod.id, Decimal('2'))
        txn.refresh_from_db()
        self.assertEqual(txn.total, Decimal('1000.00'))

        ok, result = CheckoutService.process_payment(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 1000}],
        )
        self.assertTrue(ok)
        self.assertEqual(Decimal(str(result['change'])), Decimal('0'))
        self.assertEqual(Decimal(str(result['paid'])), Decimal('1000'))

    def test_overpayment_change(self):
        """Pago con exceso: change = paid - total."""
        prod = self.make_product(sale_price='300.00', current_stock='50.000')
        txn, shift = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('1'))
        txn.refresh_from_db()

        ok, result = CheckoutService.process_payment(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 500}],
        )
        self.assertTrue(ok)
        self.assertEqual(Decimal(str(result['change'])), Decimal('200'))

    def test_insufficient_payment_rolls_back(self):
        """Pago insuficiente debe revertir toda la operación atómica."""
        prod = self.make_product(sale_price='1000.00', current_stock='50.000')
        txn, shift = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('1'))

        ok, result = CheckoutService.process_payment(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 500}],
        )
        self.assertFalse(ok)

        # Verificar rollback: no debe haber pagos ni movimientos de caja
        self.assertEqual(POSPayment.objects.filter(transaction=txn).count(), 0)
        self.assertEqual(CashMovement.objects.filter(cash_shift=txn.session.cash_shift).count(), 0)

        # Stock no debe haber cambiado
        prod.refresh_from_db()
        self.assertEqual(prod.current_stock, Decimal('50.000'))

    def test_mixed_payment(self):
        """Pago mixto: sum(payments) >= total."""
        prod = self.make_product(sale_price='1000.00', current_stock='50.000')
        txn, shift = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('1'))

        ok, result = CheckoutService.process_payment(
            txn.id,
            [
                {'method_id': self.cash_method.id, 'amount': 600},
                {'method_id': self.card_method.id, 'amount': 400},
            ],
        )
        self.assertTrue(ok)
        self.assertEqual(Decimal(str(result['change'])), Decimal('0'))

        # Verificar que se crearon 2 POSPayments
        payments = POSPayment.objects.filter(transaction=txn)
        self.assertEqual(payments.count(), 2)
        self.assertEqual(
            payments.aggregate(total=Sum('amount'))['total'],
            Decimal('1000.00'),
        )

    def test_cash_movement_matches_transaction_total(self):
        """La suma de CashMovements de una venta debe igualar el total de la transacción."""
        prod = self.make_product(sale_price='750.00', current_stock='50.000')
        txn, shift = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('2'))
        txn.refresh_from_db()
        expected_total = txn.total  # 1500

        ok, result = CheckoutService.process_payment(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 2000}],
        )
        self.assertTrue(ok)

        # CashMovement debe registrar el total de la venta, no el pago completo
        total_movements = CashMovement.objects.filter(
            cash_shift=shift,
            reference=txn.ticket_number,
        ).aggregate(total=Sum('amount'))['total']

        self.assertEqual(
            total_movements, expected_total,
            f'CashMovement total ({total_movements}) != transaction total ({expected_total})',
        )

    def test_mixed_payment_cash_movements_total(self):
        """En pago mixto, la suma de todos los CashMovements == total de la transacción."""
        prod = self.make_product(sale_price='500.00', current_stock='50.000')
        txn, shift = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('2'))
        txn.refresh_from_db()
        expected_total = txn.total  # 1000

        ok, result = CheckoutService.process_payment(
            txn.id,
            [
                {'method_id': self.cash_method.id, 'amount': 600},
                {'method_id': self.card_method.id, 'amount': 500},
            ],
        )
        self.assertTrue(ok)

        total_movements = CashMovement.objects.filter(
            cash_shift=shift,
            reference=txn.ticket_number,
        ).aggregate(total=Sum('amount'))['total']

        self.assertEqual(
            total_movements, expected_total,
            f'Suma de CashMovements ({total_movements}) != total transacción ({expected_total})',
        )

    def test_stock_deducted_on_checkout(self):
        """Checkout debe descontar el stock exacto del producto."""
        prod = self.make_product(sale_price='100.00', current_stock='50.000')
        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('7'))

        CheckoutService.process_payment(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 700}],
        )

        prod.refresh_from_db()
        self.assertEqual(prod.current_stock, Decimal('43.000'))

    def test_stock_deducted_with_packaging(self):
        """Vender 3 displays descuenta 3*12=36 unidades base."""
        prod = self.make_product(sale_price='15.00', current_stock='288.000')
        pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='display', name='Display x12',
            units_per_display=12, displays_per_bulk=2,
            sale_price=Decimal('150.00'), current_stock=Decimal('24'),
        )
        # Necesitamos unit packaging para cascade
        ProductPackaging.objects.create(
            product=prod, packaging_type='unit', name='Unidad',
            units_per_display=12, displays_per_bulk=2,
            sale_price=Decimal('15.00'), current_stock=Decimal('288'),
        )

        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('3'), packaging_id=pkg.id)
        txn.refresh_from_db()

        # Precio debe ser el del packaging: 3 * 150 = 450
        self.assertEqual(txn.total, Decimal('450.00'))

        CheckoutService.process_payment(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 450}],
        )

        prod.refresh_from_db()
        # 3 displays * 12 unidades = 36 unidades deducidas
        self.assertEqual(prod.current_stock, Decimal('252.000'))

    def test_transaction_item_subtotal_calculation(self):
        """item.subtotal = max((price * qty) - discount, 0)"""
        prod = self.make_product(sale_price='100.00', current_stock='50.000')
        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('5'))

        item = txn.items.first()
        self.assertEqual(item.subtotal, Decimal('500.00'))
        self.assertEqual(item.unit_price, Decimal('100.00'))
        self.assertEqual(item.quantity, 5)

    def test_calculate_totals_consistency(self):
        """txn.total == sum(items subtotals) - discount + tax."""
        p1 = self.make_product(name='P1', sale_price='100.00', current_stock='50.000')
        p2 = self.make_product(name='P2', sale_price='250.00', current_stock='50.000')
        txn, _ = self.make_pos_transaction()

        CartService.add_item(txn, p1.id, Decimal('3'))  # 300
        CartService.add_item(txn, p2.id, Decimal('2'))  # 500
        txn.refresh_from_db()

        expected_subtotal = Decimal('300') + Decimal('500')
        self.assertEqual(txn.subtotal, expected_subtotal)
        self.assertEqual(txn.total, expected_subtotal - txn.discount_total + txn.tax_total)


class CostSaleAudit(AuditBaseTestCase):
    """Audita ventas al costo."""

    def test_cost_sale_uses_cost_price(self):
        """Venta al costo: items repriced at cost_price, stock deducted."""
        prod = self.make_product(
            sale_price='200.00', cost_price='120.00',
            purchase_price='100.00', current_stock='50.000',
        )
        txn, shift = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('3'))

        ok, result = CheckoutService.process_cost_sale(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 360}],
        )
        self.assertTrue(ok)
        txn.refresh_from_db()

        # Total debe ser 3 * 120 (cost_price)
        self.assertEqual(txn.total, Decimal('360.00'))
        self.assertEqual(txn.transaction_type, 'cost_sale')

        # Item prices updated
        item = txn.items.first()
        self.assertEqual(item.unit_price, Decimal('120.00'))

        # Stock deducted
        prod.refresh_from_db()
        self.assertEqual(prod.current_stock, Decimal('47.000'))

    def test_cost_sale_fallback_to_purchase_price(self):
        """Si cost_price=0, usa purchase_price."""
        prod = self.make_product(
            sale_price='200.00', cost_price='0.00',
            purchase_price='80.00', current_stock='50.000',
        )
        txn, shift = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('2'))

        ok, result = CheckoutService.process_cost_sale(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 160}],
        )
        self.assertTrue(ok)

        item = txn.items.first()
        self.assertEqual(item.unit_price, Decimal('80.00'))


class InternalConsumptionAudit(AuditBaseTestCase):
    """Audita consumo interno."""

    def test_internal_consumption_deducts_stock_no_payment(self):
        prod = self.make_product(
            sale_price='200.00', cost_price='120.00', current_stock='50.000',
        )
        txn, shift = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('5'))

        ok, result = CheckoutService.process_internal_consumption(txn.id, 'Test')
        self.assertTrue(ok)

        txn.refresh_from_db()
        self.assertEqual(txn.total, Decimal('0.00'))
        self.assertEqual(txn.amount_paid, Decimal('0.00'))
        self.assertEqual(txn.transaction_type, 'internal_consumption')

        # Stock sí se deduce
        prod.refresh_from_db()
        self.assertEqual(prod.current_stock, Decimal('45.000'))

        # No debe haber CashMovements
        movements = CashMovement.objects.filter(cash_shift=shift)
        self.assertEqual(movements.count(), 0)


# ============================================================
# 4. AUDITORÍA DE PROMOCIONES
# ============================================================

class PromotionEngineAudit(AuditBaseTestCase):
    """Audita cada tipo de promoción del motor."""

    def _make_promo(self, promo_type, products, **kwargs):
        defaults = {
            'name': f'Test {promo_type}',
            'promo_type': promo_type,
            'status': 'active',
            'priority': 50,
            'is_combinable': True,
            'quantity_required': 2,
            'quantity_charged': 1,
            'min_quantity': 1,
            'discount_percent': Decimal('0'),
            'discount_amount': Decimal('0'),
            'second_unit_discount': Decimal('50'),
        }
        defaults.update(kwargs)
        promo = Promotion.objects.create(**defaults)
        for p in products:
            PromotionProduct.objects.create(promotion=promo, product=p)
        return promo

    # ---- NxM (2x1, 3x2) ----

    def test_nxm_2x1_basic(self):
        """2x1: compras 2, pagás 1 (descuento = precio del más barato)."""
        prod = self.make_product(sale_price='100.00')
        self._make_promo('nxm', [prod], quantity_required=2, quantity_charged=1)

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 2, 'unit_price': 100},
        ])
        self.assertEqual(result['discount_total'], 100.0)
        self.assertEqual(result['final_total'], 100.0)

    def test_nxm_3x2_basic(self):
        """3x2: compras 3, pagás 2."""
        prod = self.make_product(sale_price='150.00')
        self._make_promo('nxm', [prod], quantity_required=3, quantity_charged=2)

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 3, 'unit_price': 150},
        ])
        # 3 unidades, 1 gratis = descuento de $150
        self.assertEqual(result['discount_total'], 150.0)
        self.assertEqual(result['final_total'], 300.0)

    def test_nxm_insufficient_quantity(self):
        """Si qty < required, no se aplica descuento."""
        prod = self.make_product(sale_price='100.00')
        self._make_promo('nxm', [prod], quantity_required=2, quantity_charged=1)

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 1, 'unit_price': 100},
        ])
        self.assertEqual(result['discount_total'], 0)

    def test_nxm_multiple_sets(self):
        """4 unidades con 2x1 = 2 sets completos, descuento = 2 * precio."""
        prod = self.make_product(sale_price='100.00')
        self._make_promo('nxm', [prod], quantity_required=2, quantity_charged=1)

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 4, 'unit_price': 100},
        ])
        self.assertEqual(result['discount_total'], 200.0)
        self.assertEqual(result['final_total'], 200.0)

    def test_nxm_discounts_cheapest(self):
        """En 2x1 con productos de distinto precio, descuenta el más barato."""
        p1 = self.make_product(name='Caro', sale_price='200.00')
        p2 = self.make_product(name='Barato', sale_price='80.00')
        self._make_promo('nxm', [p1, p2], quantity_required=2, quantity_charged=1)

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': p1.id, 'quantity': 1, 'unit_price': 200},
            {'item_id': 2, 'product_id': p2.id, 'quantity': 1, 'unit_price': 80},
        ])
        # Descuenta el barato: $80
        self.assertEqual(result['discount_total'], 80.0)

    # ---- Descuento porcentual simple ----

    def test_simple_discount_percent(self):
        prod = self.make_product(sale_price='200.00')
        self._make_promo('simple_discount', [prod], discount_percent=Decimal('10'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 3, 'unit_price': 200},
        ])
        # 3*200 = 600, 10% = 60
        self.assertAlmostEqual(result['discount_total'], 60.0, places=2)

    def test_simple_discount_fixed_amount(self):
        prod = self.make_product(sale_price='200.00')
        self._make_promo('simple_discount', [prod], discount_amount=Decimal('50'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 1, 'unit_price': 200},
        ])
        self.assertEqual(result['discount_total'], 50.0)

    def test_simple_discount_fixed_capped_at_subtotal(self):
        """Descuento fijo no puede superar el subtotal del ítem."""
        prod = self.make_product(sale_price='30.00')
        self._make_promo('simple_discount', [prod], discount_amount=Decimal('50'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 1, 'unit_price': 30},
        ])
        # min(50, 30) = 30
        self.assertEqual(result['discount_total'], 30.0)

    # ---- Descuento por cantidad ----

    def test_quantity_discount_meets_threshold(self):
        prod = self.make_product(sale_price='100.00')
        self._make_promo('quantity_discount', [prod],
                         min_quantity=5, discount_percent=Decimal('15'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 6, 'unit_price': 100},
        ])
        # 6*100 = 600, 15% = 90
        self.assertAlmostEqual(result['discount_total'], 90.0, places=2)

    def test_quantity_discount_below_threshold(self):
        prod = self.make_product(sale_price='100.00')
        self._make_promo('quantity_discount', [prod],
                         min_quantity=5, discount_percent=Decimal('15'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 3, 'unit_price': 100},
        ])
        self.assertEqual(result['discount_total'], 0)

    # ---- Segunda unidad ----

    def test_second_unit_50_percent(self):
        """2 unidades, 2da al 50%: descuento = 1 * price * 50%."""
        prod = self.make_product(sale_price='100.00')
        self._make_promo('second_unit', [prod], second_unit_discount=Decimal('50'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 2, 'unit_price': 100},
        ])
        # 1 unidad descontada al 50% = $50
        self.assertEqual(result['discount_total'], 50.0)

    def test_second_unit_three_items(self):
        """3 unidades: solo 1 tiene descuento (int(3)//2 = 1)."""
        prod = self.make_product(sale_price='100.00')
        self._make_promo('second_unit', [prod], second_unit_discount=Decimal('50'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 3, 'unit_price': 100},
        ])
        self.assertEqual(result['discount_total'], 50.0)

    def test_second_unit_four_items(self):
        """4 unidades: 2 tienen descuento (int(4)//2 = 2)."""
        prod = self.make_product(sale_price='100.00')
        self._make_promo('second_unit', [prod], second_unit_discount=Decimal('50'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 4, 'unit_price': 100},
        ])
        self.assertEqual(result['discount_total'], 100.0)

    def test_second_unit_single_item_no_discount(self):
        prod = self.make_product(sale_price='100.00')
        self._make_promo('second_unit', [prod], second_unit_discount=Decimal('50'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 1, 'unit_price': 100},
        ])
        self.assertEqual(result['discount_total'], 0)

    # ---- Combo ----

    def test_combo_all_products_present(self):
        """Combo con todos los productos presentes: descuento = original - final_price."""
        p1 = self.make_product(name='Combo1', sale_price='300.00')
        p2 = self.make_product(name='Combo2', sale_price='200.00')
        self._make_promo('combo', [p1, p2], final_price=Decimal('400.00'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': p1.id, 'quantity': 1, 'unit_price': 300},
            {'item_id': 2, 'product_id': p2.id, 'quantity': 1, 'unit_price': 200},
        ])
        # 300+200=500 - 400 = 100 descuento
        self.assertEqual(result['discount_total'], 100.0)
        self.assertEqual(result['final_total'], 400.0)

    def test_combo_missing_product(self):
        """Si falta un producto del combo, no aplica."""
        p1 = self.make_product(name='Combo1', sale_price='300.00')
        p2 = self.make_product(name='Combo2', sale_price='200.00')
        self._make_promo('combo', [p1, p2], final_price=Decimal('400.00'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': p1.id, 'quantity': 1, 'unit_price': 300},
        ])
        self.assertEqual(result['discount_total'], 0)

    def test_combo_proportional_discount_distribution(self):
        """El descuento del combo se distribuye proporcionalmente."""
        p1 = self.make_product(name='Combo1', sale_price='300.00')
        p2 = self.make_product(name='Combo2', sale_price='200.00')
        self._make_promo('combo', [p1, p2], final_price=Decimal('400.00'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': p1.id, 'quantity': 1, 'unit_price': 300},
            {'item_id': 2, 'product_id': p2.id, 'quantity': 1, 'unit_price': 200},
        ])

        discounts = {
            d['item_id']: d['discount']
            for ap in result['applied_promotions']
            for d in ap['item_discounts']
        }
        # p1: 300/500 * 100 = 60
        self.assertAlmostEqual(discounts[1], 60.0, places=2)
        # p2: 200/500 * 100 = 40
        self.assertAlmostEqual(discounts[2], 40.0, places=2)
        # Sum = 100
        self.assertAlmostEqual(sum(discounts.values()), 100.0, places=2)

    # ---- Non-combinable ----

    def test_non_combinable_blocks_second_promo(self):
        """Una promo no combinable impide que otra se aplique al mismo ítem."""
        prod = self.make_product(sale_price='100.00')
        self._make_promo('simple_discount', [prod],
                         discount_percent=Decimal('10'), is_combinable=False,
                         priority=80, name='Promo alta')
        self._make_promo('simple_discount', [prod],
                         discount_percent=Decimal('20'), is_combinable=True,
                         priority=50, name='Promo baja')

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 1, 'unit_price': 100},
        ])
        # Solo aplica la de mayor prioridad (10%), la de 20% queda bloqueada
        self.assertAlmostEqual(result['discount_total'], 10.0, places=2)
        self.assertEqual(len(result['applied_promotions']), 1)

    def test_final_total_never_negative(self):
        """final_total siempre >= 0 incluso con descuento excesivo."""
        prod = self.make_product(sale_price='10.00')
        self._make_promo('simple_discount', [prod], discount_amount=Decimal('1000'))

        result = PromotionEngine.calculate_cart([
            {'item_id': 1, 'product_id': prod.id, 'quantity': 1, 'unit_price': 10},
        ])
        self.assertGreaterEqual(result['final_total'], 0)

    def test_empty_cart(self):
        result = PromotionEngine.calculate_cart([])
        self.assertEqual(result['original_total'], 0)
        self.assertEqual(result['discount_total'], 0)
        self.assertEqual(result['final_total'], 0)


class PromoWithPackagingEndToEnd(AuditBaseTestCase):
    """Promos aplicadas sobre displays/bultos: verifica precio con descuento
    y cascada de stock a todos los niveles tras el checkout real."""

    def _setup(self, stock=Decimal('288')):
        prod = self.make_product(
            name='Chicle',
            sale_price='15.00',
            purchase_price='10.00',
            cost_price='10.00',
            current_stock=str(stock),
        )
        unit_pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='unit', name='Unidad',
            barcode='2000000000001',
            units_per_display=12, displays_per_bulk=2,
            purchase_price=Decimal('10'), sale_price=Decimal('15'),
            current_stock=stock,
        )
        display_pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='display', name='Display x12',
            barcode='2000000000002',
            units_per_display=12, displays_per_bulk=2,
            purchase_price=Decimal('100'), sale_price=Decimal('150'),
            current_stock=stock / 12,
        )
        bulk_pkg = ProductPackaging.objects.create(
            product=prod, packaging_type='bulk', name='Bulto x24',
            barcode='2000000000003',
            units_per_display=12, displays_per_bulk=2,
            purchase_price=Decimal('200'), sale_price=Decimal('280'),
            current_stock=stock / 24,
        )
        return prod, unit_pkg, display_pkg, bulk_pkg

    def _make_promo(self, promo_type, products, scope='unit', **kwargs):
        defaults = {
            'name': f'Test {promo_type} {scope}',
            'promo_type': promo_type,
            'status': 'active',
            'priority': 50,
            'is_combinable': True,
            'quantity_required': 2,
            'quantity_charged': 1,
            'min_quantity': 1,
            'discount_percent': Decimal('0'),
            'discount_amount': Decimal('0'),
            'second_unit_discount': Decimal('50'),
            'applies_to_packaging_type': scope,
        }
        defaults.update(kwargs)
        promo = Promotion.objects.create(**defaults)
        for p in products:
            PromotionProduct.objects.create(promotion=promo, product=p)
        return promo

    # ----- Promo 2x1 sobre display -----

    def test_promo_2x1_on_displays_applies_and_cascades(self):
        """Promo 2x1 sobre displays: 2 displays = pagás 1 + descuento cascade."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup(stock=Decimal('288'))
        self._make_promo('nxm', [prod], scope='display',
                         quantity_required=2, quantity_charged=1)

        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('2'), packaging_id=display_pkg.id)
        # apply_promotions se re-ejecuta al add_item
        txn.refresh_from_db()

        # 2 displays x $150 = $300 original; 2x1 descuenta $150 → total $150
        item = txn.items.first()
        self.assertEqual(item.promotion_discount, Decimal('150.00'))
        self.assertEqual(txn.total, Decimal('150.00'))

        ok, _ = CheckoutService.process_payment(
            txn.id, [{'method_id': self.cash_method.id, 'amount': 150}],
        )
        self.assertTrue(ok)

        # Stock: aunque el cliente pagó por 1, se ENTREGAN 2 displays = 24u
        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()
        self.assertEqual(prod.current_stock, Decimal('264'))
        self.assertEqual(unit_pkg.current_stock, Decimal('264'))
        self.assertEqual(display_pkg.current_stock, Decimal('22'))
        self.assertEqual(bulk_pkg.current_stock, Decimal('11'))

    def test_promo_scope_display_does_not_match_units(self):
        """Promo con scope=display NO se dispara al vender solo unidades."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup(stock=Decimal('288'))
        self._make_promo('nxm', [prod], scope='display',
                         quantity_required=2, quantity_charged=1)

        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('2'), packaging_id=unit_pkg.id)
        txn.refresh_from_db()

        item = txn.items.first()
        self.assertEqual(item.promotion_discount, Decimal('0.00'))
        # 2 unidades a $15 = $30 (sin promo)
        self.assertEqual(txn.total, Decimal('30.00'))

    def test_promo_scope_unit_does_not_match_displays(self):
        """Promo con scope=unit NO se dispara al vender displays."""
        prod, unit_pkg, display_pkg, _ = self._setup(stock=Decimal('288'))
        self._make_promo('nxm', [prod], scope='unit',
                         quantity_required=2, quantity_charged=1)

        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('2'), packaging_id=display_pkg.id)
        txn.refresh_from_db()

        item = txn.items.first()
        self.assertEqual(item.promotion_discount, Decimal('0.00'))
        self.assertEqual(txn.total, Decimal('300.00'))

    # ----- Promo Nx$ fijo sobre display -----

    def test_promo_nx_fixed_price_on_displays(self):
        """Promo 2x$250 sobre displays: 2 displays se cobran a $250 en total."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup(stock=Decimal('288'))
        self._make_promo('nx_fixed_price', [prod], scope='display',
                         quantity_required=2,
                         final_price=Decimal('250'))  # precio fijo total

        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('2'), packaging_id=display_pkg.id)
        txn.refresh_from_db()

        # Original: 2 x $150 = $300. Fijo: $250. Descuento: $50.
        self.assertEqual(txn.total, Decimal('250.00'))

        ok, _ = CheckoutService.process_payment(
            txn.id, [{'method_id': self.cash_method.id, 'amount': 250}],
        )
        self.assertTrue(ok)

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()
        self.assertEqual(prod.current_stock, Decimal('264'))
        self.assertEqual(unit_pkg.current_stock, Decimal('264'))
        self.assertEqual(display_pkg.current_stock, Decimal('22'))
        self.assertEqual(bulk_pkg.current_stock, Decimal('11'))

    # ----- Descuento % sobre bulto -----

    def test_promo_simple_discount_on_bulk(self):
        """15% OFF sobre bulto: 1 bulto $280 → $238 + cascade 24u."""
        prod, unit_pkg, display_pkg, bulk_pkg = self._setup(stock=Decimal('288'))
        self._make_promo('simple_discount', [prod], scope='bulk',
                         discount_percent=Decimal('15'))

        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('1'), packaging_id=bulk_pkg.id)
        txn.refresh_from_db()

        # $280 * 15% = $42 descuento → total $238
        item = txn.items.first()
        self.assertEqual(item.promotion_discount, Decimal('42.00'))
        self.assertEqual(txn.total, Decimal('238.00'))

        ok, _ = CheckoutService.process_payment(
            txn.id, [{'method_id': self.cash_method.id, 'amount': 238}],
        )
        self.assertTrue(ok)

        prod.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()
        bulk_pkg.refresh_from_db()
        # 1 bulto = 24 unidades
        self.assertEqual(prod.current_stock, Decimal('264'))
        self.assertEqual(unit_pkg.current_stock, Decimal('264'))
        self.assertEqual(display_pkg.current_stock, Decimal('22'))
        self.assertEqual(bulk_pkg.current_stock, Decimal('11'))

    # ----- Scope=any funciona para cualquier empaque -----

    def test_promo_scope_any_matches_all_packagings(self):
        """Promo scope=any: aplica sobre display Y unit por igual."""
        prod, unit_pkg, display_pkg, _ = self._setup(stock=Decimal('288'))
        self._make_promo('simple_discount', [prod], scope='any',
                         discount_percent=Decimal('10'))

        # Caso 1: vender display
        txn1, _ = self.make_pos_transaction()
        CartService.add_item(txn1, prod.id, Decimal('1'), packaging_id=display_pkg.id)
        txn1.refresh_from_db()
        self.assertEqual(txn1.total, Decimal('135.00'))  # 150 - 10%

        # Caso 2: nuevo shift+txn para vender unidades
        txn2, _ = self.make_pos_transaction(shift=self.make_shift())
        CartService.add_item(txn2, prod.id, Decimal('5'), packaging_id=unit_pkg.id)
        txn2.refresh_from_db()
        # 5 * 15 = 75. 10% = 7.5 → 67.5
        self.assertEqual(txn2.total, Decimal('67.50'))


# ============================================================
# 5. AUDITORÍA DE CAJA REGISTRADORA
# ============================================================

class CashRegisterAudit(AuditBaseTestCase):
    """Verifica la aritmética de apertura, cierre y diferencias de caja."""

    def test_calculate_expected_basic(self):
        """expected = initial + cash_income - cash_expense."""
        shift = self.make_shift(initial_amount='5000.00')

        # Simulamos ventas en efectivo
        CashMovement.objects.create(
            cash_shift=shift, movement_type='income', amount=Decimal('1500.00'),
            payment_method=self.cash_method, description='Venta 1',
        )
        CashMovement.objects.create(
            cash_shift=shift, movement_type='income', amount=Decimal('800.00'),
            payment_method=self.cash_method, description='Venta 2',
        )
        # Gasto
        CashMovement.objects.create(
            cash_shift=shift, movement_type='expense', amount=Decimal('200.00'),
            payment_method=self.cash_method, description='Gasto test',
        )

        expected = shift.calculate_expected()
        # 5000 + 1500 + 800 - 200 = 7100
        self.assertEqual(expected, Decimal('7100.00'))

    def test_calculate_expected_ignores_non_cash(self):
        """Non-cash income no se suma al esperado de efectivo."""
        shift = self.make_shift(initial_amount='5000.00')

        CashMovement.objects.create(
            cash_shift=shift, movement_type='income', amount=Decimal('1000.00'),
            payment_method=self.cash_method, description='Venta efectivo',
        )
        CashMovement.objects.create(
            cash_shift=shift, movement_type='income', amount=Decimal('3000.00'),
            payment_method=self.card_method, description='Venta tarjeta',
        )

        expected = shift.calculate_expected()
        # Solo cuenta efectivo: 5000 + 1000 = 6000
        self.assertEqual(expected, Decimal('6000.00'))

    def test_shift_close_difference_positive(self):
        """Sobrante: actual > expected → difference > 0."""
        shift = self.make_shift(initial_amount='5000.00')
        CashMovement.objects.create(
            cash_shift=shift, movement_type='income', amount=Decimal('2000.00'),
            payment_method=self.cash_method, description='Venta',
        )

        shift.close(actual_amount=Decimal('7100.00'))
        # Expected: 5000+2000=7000. Actual: 7100. Diff: +100
        self.assertEqual(shift.difference, Decimal('100.00'))
        self.assertEqual(shift.expected_amount, Decimal('7000.00'))
        self.assertEqual(shift.status, 'closed')

    def test_shift_close_difference_negative(self):
        """Faltante: actual < expected → difference < 0."""
        shift = self.make_shift(initial_amount='5000.00')
        CashMovement.objects.create(
            cash_shift=shift, movement_type='income', amount=Decimal('2000.00'),
            payment_method=self.cash_method, description='Venta',
        )

        shift.close(actual_amount=Decimal('6500.00'))
        # Expected: 7000. Actual: 6500. Diff: -500
        self.assertEqual(shift.difference, Decimal('-500.00'))

    def test_shift_close_exact(self):
        """Cierre exacto: difference == 0."""
        shift = self.make_shift(initial_amount='5000.00')
        CashMovement.objects.create(
            cash_shift=shift, movement_type='income', amount=Decimal('2000.00'),
            payment_method=self.cash_method, description='Venta',
        )

        shift.close(actual_amount=Decimal('7000.00'))
        self.assertEqual(shift.difference, Decimal('0.00'))

    def test_cash_plus_noncash_equals_total_income(self):
        """get_cash_total() + get_non_cash_total() == total_income."""
        shift = self.make_shift()
        CashMovement.objects.create(
            cash_shift=shift, movement_type='income', amount=Decimal('1000.00'),
            payment_method=self.cash_method, description='Venta 1',
        )
        CashMovement.objects.create(
            cash_shift=shift, movement_type='income', amount=Decimal('500.00'),
            payment_method=self.card_method, description='Venta 2',
        )
        CashMovement.objects.create(
            cash_shift=shift, movement_type='income', amount=Decimal('300.00'),
            payment_method=self.transfer_method, description='Venta 3',
        )

        self.assertEqual(
            shift.get_cash_total() + shift.get_non_cash_total(),
            shift.total_income,
        )

    def test_bill_count_total(self):
        """Conteo de billetes: sum(denom * qty)."""
        shift = self.make_shift()
        BillCount.objects.create(cash_shift=shift, denomination=1000, quantity=5, count_type='closing')
        BillCount.objects.create(cash_shift=shift, denomination=500, quantity=3, count_type='closing')
        BillCount.objects.create(cash_shift=shift, denomination=100, quantity=10, count_type='closing')

        total = shift.get_bill_count_total('closing')
        # 5000 + 1500 + 1000 = 7500
        self.assertEqual(total, Decimal('7500'))

    def test_bill_count_subtotal_type(self):
        """BillCount.subtotal devuelve int; verificamos valor correcto."""
        shift = self.make_shift()
        bc = BillCount.objects.create(
            cash_shift=shift, denomination=2000, quantity=7, count_type='closing',
        )
        self.assertEqual(bc.subtotal, 14000)

    def test_shift_no_movements(self):
        """Turno sin movimientos: expected == initial."""
        shift = self.make_shift(initial_amount='3000.00')
        expected = shift.calculate_expected()
        self.assertEqual(expected, Decimal('3000.00'))


# ============================================================
# 6. AUDITORÍA DE REPORTES DE VENTAS
# ============================================================

class SalesReportConsistencyAudit(AuditBaseTestCase):
    """Verifica que los reportes agreguen datos consistentes con las transacciones."""

    def _complete_sale(self, products_qty_price, shift=None):
        """Helper: crea y completa una venta. Returns (txn, shift)."""
        txn, shift = self.make_pos_transaction(shift=shift)

        for prod, qty in products_qty_price:
            CartService.add_item(txn, prod.id, Decimal(str(qty)))

        txn.refresh_from_db()
        CheckoutService.process_payment(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': float(txn.total) + 100}],
        )
        txn.refresh_from_db()
        return txn, shift

    def test_sum_payments_equals_sum_transactions(self):
        """Sum(POSPayment.amount) para una venta == transaction.amount_paid."""
        prod = self.make_product(sale_price='100.00', current_stock='100.000')
        txn, _ = self._complete_sale([(prod, 5)])

        payments_total = POSPayment.objects.filter(
            transaction=txn,
        ).aggregate(total=Sum('amount'))['total']

        self.assertEqual(payments_total, txn.amount_paid)

    def test_multiple_transactions_totals(self):
        """La suma de todas las transacciones completadas == sum(total)."""
        p1 = self.make_product(name='R1', sale_price='100.00', current_stock='100.000')
        p2 = self.make_product(name='R2', sale_price='250.00', current_stock='100.000')

        shift = self.make_shift()
        txn1, _ = self._complete_sale([(p1, 3)], shift=shift)   # 300
        txn2, _ = self._complete_sale([(p2, 2)], shift=shift)   # 500

        db_total = POSTransaction.objects.filter(
            session__cash_shift=shift, status='completed',
        ).aggregate(total=Sum('total'))['total']

        self.assertEqual(db_total, Decimal('800.00'))

    def test_cash_movements_match_completed_transactions(self):
        """Sum(CashMovement income) de ventas == Sum(POSTransaction.total) del turno."""
        p1 = self.make_product(name='CM1', sale_price='200.00', current_stock='100.000')

        shift = self.make_shift()
        self._complete_sale([(p1, 3)], shift=shift)  # 600
        self._complete_sale([(p1, 2)], shift=shift)  # 400

        # Movimientos de caja tipo ingreso
        total_movements = CashMovement.objects.filter(
            cash_shift=shift, movement_type='income',
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Transacciones completadas
        total_txns = POSTransaction.objects.filter(
            session__cash_shift=shift, status='completed',
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')

        self.assertEqual(
            total_movements, total_txns,
            f'CashMovements ({total_movements}) != Transactions ({total_txns})',
        )

    def test_item_subtotals_sum_to_transaction_subtotal(self):
        """Sum(item.subtotal) == transaction.subtotal."""
        p1 = self.make_product(name='IS1', sale_price='100.00', current_stock='100.000')
        p2 = self.make_product(name='IS2', sale_price='250.00', current_stock='100.000')

        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, p1.id, Decimal('3'))
        CartService.add_item(txn, p2.id, Decimal('2'))
        txn.refresh_from_db()

        items_sum = txn.items.aggregate(
            total=Sum('subtotal'),
        )['total']

        self.assertEqual(items_sum, txn.subtotal)

    def test_stock_movements_match_items_sold(self):
        """Las unidades deducidas de stock deben coincidir con las vendidas."""
        prod = self.make_product(name='SM1', sale_price='50.00', current_stock='100.000')

        txn, shift = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('7'))

        stock_before = prod.current_stock

        CheckoutService.process_payment(
            txn.id,
            [{'method_id': self.cash_method.id, 'amount': 350}],
        )

        prod.refresh_from_db()
        deducted = stock_before - prod.current_stock
        self.assertEqual(deducted, Decimal('7'))

        # Verificar con StockMovement
        sale_movements = StockMovement.objects.filter(
            product=prod, reference_id=txn.id, movement_type='sale',
        )
        total_moved = abs(sale_movements.aggregate(total=Sum('quantity'))['total'])
        self.assertEqual(total_moved, Decimal('7'))


# ============================================================
# 7. AUDITORÍA DE COMPRAS
# ============================================================

class PurchaseAudit(AuditBaseTestCase):
    """Verifica la aritmética de compras y sus ítems."""

    def test_purchase_item_subtotal(self):
        """item.subtotal = quantity * unit_cost."""
        prod = self.make_product()
        supplier = Supplier.objects.create(name='Proveedor Test')
        purchase = Purchase.objects.create(
            supplier=supplier, order_number='OC-001',
        )
        item = PurchaseItem.objects.create(
            purchase=purchase, product=prod,
            quantity=10, unit_cost=Decimal('50.00'),
        )
        self.assertEqual(item.subtotal, Decimal('500.00'))

    def test_purchase_item_subtotal_recalculated_on_save(self):
        """Cambiar qty o cost y re-save recalcula subtotal."""
        prod = self.make_product()
        supplier = Supplier.objects.create(name='Proveedor Test 2')
        purchase = Purchase.objects.create(
            supplier=supplier, order_number='OC-002',
        )
        item = PurchaseItem.objects.create(
            purchase=purchase, product=prod,
            quantity=5, unit_cost=Decimal('100.00'),
        )
        self.assertEqual(item.subtotal, Decimal('500.00'))

        item.quantity = 8
        item.save()
        self.assertEqual(item.subtotal, Decimal('800.00'))


# ============================================================
# 8. AUDITORÍA CRUZADA (Cross-Module Consistency)
# ============================================================

class CrossModuleConsistencyAudit(AuditBaseTestCase):
    """Tests que verifican consistencia entre módulos."""

    def test_full_sale_cycle_stock_to_cash(self):
        """
        Ciclo completo: agregar al carrito → checkout → verificar stock,
        movimientos, pagos, caja — todo debe cuadrar.
        """
        prod = self.make_product(
            name='Alfajor', sale_price='500.00',
            cost_price='300.00', current_stock='100.000',
        )
        shift = self.make_shift(initial_amount='10000.00')
        txn, _ = self.make_pos_transaction(shift=shift)

        CartService.add_item(txn, prod.id, Decimal('4'))
        txn.refresh_from_db()
        sale_total = txn.total  # 2000

        ok, result = CheckoutService.process_payment(
            txn.id,
            [
                {'method_id': self.cash_method.id, 'amount': 1500},
                {'method_id': self.card_method.id, 'amount': 500},
            ],
        )
        self.assertTrue(ok)
        txn.refresh_from_db()

        # 1. Transaction state
        self.assertEqual(txn.status, 'completed')
        self.assertEqual(txn.total, Decimal('2000.00'))
        self.assertEqual(txn.amount_paid, Decimal('2000.00'))
        self.assertEqual(txn.change_given, Decimal('0.00'))

        # 2. Stock deducted
        prod.refresh_from_db()
        self.assertEqual(prod.current_stock, Decimal('96.000'))

        # 3. POSPayments sum
        payments_sum = POSPayment.objects.filter(
            transaction=txn,
        ).aggregate(total=Sum('amount'))['total']
        self.assertEqual(payments_sum, Decimal('2000.00'))

        # 4. CashMovements sum == sale total
        cash_sum = CashMovement.objects.filter(
            cash_shift=shift, reference=txn.ticket_number,
        ).aggregate(total=Sum('amount'))['total']
        self.assertEqual(cash_sum, sale_total)

        # 5. Expected cash
        expected_cash = shift.calculate_expected()
        # initial(10000) + cash income(1500) = 11500
        self.assertEqual(expected_cash, Decimal('11500.00'))

        # 6. StockMovement audit trail
        stock_mov = StockMovement.objects.filter(
            product=prod, reference_id=txn.id,
        )
        self.assertTrue(stock_mov.exists())
        total_deducted = abs(stock_mov.aggregate(total=Sum('quantity'))['total'])
        self.assertEqual(total_deducted, Decimal('4'))

    def test_multiple_sales_cash_totals_consistent(self):
        """
        Varias ventas en un turno: la suma de CashMovements de ingreso
        debe igualar la suma de transacciones completadas.
        """
        p1 = self.make_product(name='Multi1', sale_price='100.00', current_stock='100.000')
        p2 = self.make_product(name='Multi2', sale_price='200.00', current_stock='100.000')

        shift = self.make_shift()

        # Venta 1: 3 x p1 = 300
        txn1, _ = self.make_pos_transaction(shift=shift)
        CartService.add_item(txn1, p1.id, Decimal('3'))
        CheckoutService.process_payment(txn1.id, [{'method_id': self.cash_method.id, 'amount': 300}])

        # Venta 2: 2 x p2 = 400
        txn2, _ = self.make_pos_transaction(shift=shift)
        CartService.add_item(txn2, p2.id, Decimal('2'))
        CheckoutService.process_payment(txn2.id, [{'method_id': self.card_method.id, 'amount': 400}])

        # Venta 3: 1 x p1 + 1 x p2 = 300
        txn3, _ = self.make_pos_transaction(shift=shift)
        CartService.add_item(txn3, p1.id, Decimal('1'))
        CartService.add_item(txn3, p2.id, Decimal('1'))
        CheckoutService.process_payment(txn3.id, [{'method_id': self.cash_method.id, 'amount': 300}])

        # Totales
        txn_total = POSTransaction.objects.filter(
            session__cash_shift=shift, status='completed',
        ).aggregate(total=Sum('total'))['total']

        movement_total = CashMovement.objects.filter(
            cash_shift=shift, movement_type='income',
        ).aggregate(total=Sum('amount'))['total']

        self.assertEqual(txn_total, Decimal('1000.00'))
        self.assertEqual(movement_total, txn_total)

    def test_inventory_value_after_sales(self):
        """Valor de inventario a costo debe reflejar las ventas."""
        prod = self.make_product(
            sale_price='100.00', cost_price='60.00', current_stock='50.000',
        )
        initial_value = prod.stock_value  # 50 * 60 = 3000

        txn, _ = self.make_pos_transaction()
        CartService.add_item(txn, prod.id, Decimal('10'))
        CheckoutService.process_payment(
            txn.id, [{'method_id': self.cash_method.id, 'amount': 1000}],
        )

        prod.refresh_from_db()
        final_value = prod.stock_value  # 40 * 60 = 2400

        self.assertEqual(initial_value - final_value, Decimal('600.000'))
        self.assertEqual(prod.current_stock, Decimal('40.000'))
