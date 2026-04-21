"""
Tests para los nuevos flujos implementados:
1. Deducción FIFO de lotes en ventas POS
2. Conteo físico de inventario (reemplaza ajuste de stock)
3. Búsqueda por código de barras en API de compras
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from stocks.models import Product, ProductCategory, StockMovement
from stocks.services import StockManagementService
from pos.models import POSSession, POSTransaction, POSTransactionItem
from pos.services import CartService, CheckoutService, POSService
from cashregister.models import PaymentMethod, CashRegister, CashShift
from granel.models import StockBatch
from granel.services import BatchService
from purchase.models import Supplier, Purchase, PurchaseItem

User = get_user_model()


class POSFIFODeductionTest(TestCase):
    """Verifica que cada venta POS consume los lotes FIFO correctamente."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_group, _ = Group.objects.get_or_create(name='Admin')
        cls.user = User.objects.create_user(
            username='test_fifo_pos', password='pass123',
            first_name='Test', last_name='FIFO'
        )
        cls.user.groups.add(cls.admin_group)

        cls.category = ProductCategory.objects.create(name='Test FIFO')
        cls.cash_method = PaymentMethod.objects.create(
            name='Efectivo FIFO', code='cash_fifo', is_active=True
        )
        cls.register = CashRegister.objects.create(
            name='Caja FIFO', code='FIFO01', is_active=True
        )
        cls.shift = CashShift.objects.create(
            cash_register=cls.register,
            cashier=cls.user,
            initial_amount=Decimal('10000'),
            status='open'
        )

    def _make_product(self, name='Producto FIFO', cost=Decimal('100'), stock=10):
        return Product.objects.create(
            name=name,
            sku=f'FIFO-{Product.objects.count()+1:04d}',
            sale_price=Decimal('150'),
            cost_price=cost,
            purchase_price=cost,
            current_stock=Decimal(str(stock)),
            category=self.category,
        )

    def _make_batch(self, product, qty, cost, days_ago=0):
        return StockBatch.objects.create(
            product=product,
            quantity_purchased=Decimal(str(qty)),
            quantity_remaining=Decimal(str(qty)),
            purchase_price=Decimal(str(cost)),
            purchased_at=timezone.now() - timezone.timedelta(days=days_ago),
            supplier_name='Proveedor Test',
            created_by=self.user,
        )

    def _checkout(self, product, quantity=1):
        session = POSService.get_or_create_session(self.shift)
        transaction = POSService.get_pending_transaction(session)
        CartService.add_item(transaction, product.id, quantity=Decimal(str(quantity)))
        success, result = CheckoutService.process_payment(
            transaction.id,
            [{'method_code': 'cash_fifo', 'amount': str(product.sale_price * quantity * 2)}]
        )
        return success, result

    def test_sale_deducts_fifo_batch(self):
        """Una venta debe descontar del lote más antiguo primero."""
        product = self._make_product(stock=10)
        old_batch = self._make_batch(product, qty=5, cost=100, days_ago=30)
        new_batch = self._make_batch(product, qty=5, cost=120, days_ago=5)

        # Vender 3 unidades — deben salir del lote más viejo
        success, _ = self._checkout(product, quantity=3)
        self.assertTrue(success)

        old_batch.refresh_from_db()
        new_batch.refresh_from_db()

        self.assertEqual(old_batch.quantity_remaining, Decimal('2'))
        self.assertEqual(new_batch.quantity_remaining, Decimal('5'))  # sin tocar

    def test_sale_spans_multiple_batches(self):
        """Una venta que supera un lote debe consumir el siguiente en FIFO."""
        product = self._make_product(stock=10)
        b1 = self._make_batch(product, qty=2, cost=100, days_ago=20)
        b2 = self._make_batch(product, qty=5, cost=130, days_ago=10)

        # Vender 4: consume b1 completo (2) + 2 de b2
        success, _ = self._checkout(product, quantity=4)
        self.assertTrue(success)

        b1.refresh_from_db()
        b2.refresh_from_db()

        self.assertEqual(b1.quantity_remaining, Decimal('0'))
        self.assertEqual(b2.quantity_remaining, Decimal('3'))

    def test_sale_with_no_batches_doesnt_crash(self):
        """Venta sin lotes creados no debe romper el checkout."""
        product = self._make_product(stock=5)
        # No creamos batches
        success, result = self._checkout(product, quantity=2)
        self.assertTrue(success, f'Checkout falló: {result}')

        product.refresh_from_db()
        self.assertEqual(product.current_stock, Decimal('3'))

    def test_fifo_preserves_stock_on_failure(self):
        """Si el pago es insuficiente, los lotes no deben modificarse."""
        product = self._make_product(stock=5)
        batch = self._make_batch(product, qty=5, cost=100, days_ago=1)

        session = POSService.get_or_create_session(self.shift)
        transaction = POSService.get_pending_transaction(session)
        CartService.add_item(transaction, product.id, quantity=Decimal('2'))

        # Pago insuficiente
        success, _ = CheckoutService.process_payment(
            transaction.id,
            [{'method_code': 'cash_fifo', 'amount': '1'}]  # $1 para una compra de $300
        )
        self.assertFalse(success)

        batch.refresh_from_db()
        self.assertEqual(batch.quantity_remaining, Decimal('5'))  # intacto


class InventoryCountTest(TestCase):
    """Verifica el flujo de Conteo Físico (reemplaza Ajuste de Stock)."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_group, _ = Group.objects.get_or_create(name='Admin')
        cls.manager_group, _ = Group.objects.get_or_create(name='Cajero Manager')
        cls.cashier_group, _ = Group.objects.get_or_create(name='Cashier')

        cls.admin = User.objects.create_user(
            username='admin_count', password='pass123',
            first_name='Admin', last_name='Count'
        )
        cls.admin.groups.add(cls.admin_group)

        cls.cashier = User.objects.create_user(
            username='cashier_count', password='pass123',
            first_name='Cashier', last_name='Count'
        )
        cls.cashier.groups.add(cls.cashier_group)

        cls.category = ProductCategory.objects.create(name='Test Count')

    def _make_product(self, stock=10):
        return Product.objects.create(
            name=f'Prod Count {Product.objects.count()}',
            sku=f'CNT-{Product.objects.count()+1:04d}',
            sale_price=Decimal('100'),
            cost_price=Decimal('60'),
            current_stock=Decimal(str(stock)),
            category=self.category,
        )

    def test_inventory_count_url_exists(self):
        """La URL inventory_count debe existir."""
        product = self._make_product()
        url = reverse('stocks:inventory_count', args=[product.pk])
        self.assertIn('/conteo/', url)

    def test_admin_can_access_inventory_count(self):
        """Admin puede acceder al conteo físico."""
        product = self._make_product()
        c = Client()
        c.login(username='admin_count', password='pass123')
        resp = c.get(reverse('stocks:inventory_count', args=[product.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_cashier_cannot_access_inventory_count(self):
        """Cajero no puede acceder al conteo físico."""
        product = self._make_product()
        c = Client()
        c.login(username='cashier_count', password='pass123')
        resp = c.get(reverse('stocks:inventory_count', args=[product.pk]))
        self.assertIn(resp.status_code, [302, 403])

    def test_inventory_count_decrease_creates_movement(self):
        """Conteo hacia abajo debe crear movimiento de ajuste."""
        product = self._make_product(stock=10)
        c = Client()
        c.login(username='admin_count', password='pass123')

        resp = c.post(
            reverse('stocks:inventory_count', args=[product.pk]),
            {'new_quantity': '7', 'reason': 'conteo_fisico', 'notes': 'Conteo mensual'},
        )
        self.assertRedirects(resp, reverse('stocks:product_detail', args=[product.pk]))

        product.refresh_from_db()
        self.assertEqual(product.current_stock, Decimal('7'))

        movement = StockMovement.objects.filter(
            product=product, movement_type='adjustment_out'
        ).first()
        self.assertIsNotNone(movement)

    def test_inventory_count_increase_creates_movement(self):
        """Conteo hacia arriba debe crear movimiento de ajuste."""
        product = self._make_product(stock=5)
        c = Client()
        c.login(username='admin_count', password='pass123')

        resp = c.post(
            reverse('stocks:inventory_count', args=[product.pk]),
            {'new_quantity': '8', 'reason': 'correccion_error', 'notes': ''},
        )
        self.assertRedirects(resp, reverse('stocks:product_detail', args=[product.pk]))

        product.refresh_from_db()
        self.assertEqual(product.current_stock, Decimal('8'))

        movement = StockMovement.objects.filter(
            product=product, movement_type='adjustment_in'
        ).first()
        self.assertIsNotNone(movement)

    def test_inventory_count_decrease_deducts_fifo_batches(self):
        """Una baja de stock en conteo debe descontar lotes FIFO."""
        product = self._make_product(stock=10)
        batch = StockBatch.objects.create(
            product=product,
            quantity_purchased=Decimal('10'),
            quantity_remaining=Decimal('10'),
            purchase_price=Decimal('100'),
            purchased_at=timezone.now(),
            supplier_name='Prov Test',
            created_by=self.admin,
        )

        c = Client()
        c.login(username='admin_count', password='pass123')
        c.post(
            reverse('stocks:inventory_count', args=[product.pk]),
            {'new_quantity': '6', 'reason': 'robo_perdida', 'notes': 'Robo'},
        )

        batch.refresh_from_db()
        self.assertEqual(batch.quantity_remaining, Decimal('6'))

    def test_stock_adjust_url_removed(self):
        """La vieja URL stock_adjust ya no debe existir."""
        product = self._make_product()
        from django.urls import NoReverseMatch
        with self.assertRaises(NoReverseMatch):
            reverse('stocks:stock_adjust', args=[product.pk])


class PurchaseBarcodeSearchTest(TestCase):
    """Verifica la búsqueda de productos por código de barras en compras."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_group, _ = Group.objects.get_or_create(name='Admin')
        cls.user = User.objects.create_user(
            username='admin_barcode', password='pass123',
            first_name='Admin', last_name='BC'
        )
        cls.user.groups.add(cls.admin_group)

        cls.category = ProductCategory.objects.create(name='Test BC')
        cls.product_with_barcode = Product.objects.create(
            name='Coca Cola 500ml',
            sku='CCL500',
            barcode='7790895000628',
            sale_price=Decimal('500'),
            cost_price=Decimal('350'),
            current_stock=Decimal('20'),
            category=cls.category,
        )
        cls.product_no_barcode = Product.objects.create(
            name='Alfajor Triple',
            sku='AFJ001',
            barcode='',
            sale_price=Decimal('300'),
            cost_price=Decimal('200'),
            current_stock=Decimal('15'),
            category=cls.category,
        )

    def _search(self, query, barcode_scan=False):
        c = Client()
        c.login(username='admin_barcode', password='pass123')
        params = f'?q={query}'
        if barcode_scan:
            params += '&barcode=1'
        return c.get(reverse('purchase:api_search_products') + params)

    def test_search_by_name(self):
        """Búsqueda por nombre encuentra producto."""
        resp = self._search('Coca')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(any(p['name'] == 'Coca Cola 500ml' for p in data['results']))

    def test_exact_barcode_scan(self):
        """Scan exacto de barcode devuelve el producto correcto."""
        resp = self._search('7790895000628', barcode_scan=True)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['barcode'], '7790895000628')

    def test_barcode_scan_no_match_returns_empty(self):
        """Barcode inexistente devuelve lista vacía."""
        resp = self._search('9999999999999', barcode_scan=True)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data['results']), 0)

    def test_short_query_returns_empty(self):
        """Búsqueda con menos de 2 caracteres devuelve vacío."""
        resp = self._search('A')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['results'], [])

    def test_results_include_required_fields(self):
        """Los resultados incluyen los campos que necesita el frontend."""
        resp = self._search('Coca')
        data = resp.json()
        if data['results']:
            result = data['results'][0]
            self.assertIn('id', result)
            self.assertIn('name', result)
            self.assertIn('barcode', result)
            self.assertIn('cost_price', result)
            self.assertIn('sale_price', result)


class PurchaseConfirmationStockTest(TestCase):
    """Verifica que al recibir una compra se crea el lote FIFO y se actualiza el stock."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_group, _ = Group.objects.get_or_create(name='Admin')
        cls.user = User.objects.create_user(
            username='admin_purchase', password='pass123',
            first_name='Admin', last_name='Purchase'
        )
        cls.user.groups.add(cls.admin_group)

        cls.category = ProductCategory.objects.create(name='Test Purchase')
        cls.supplier = Supplier.objects.create(
            name='Proveedor Test SA', is_active=True
        )

    def _make_product(self, name='Prod Purchase', stock=0):
        return Product.objects.create(
            name=name,
            sku=f'PUR-{Product.objects.count()+1:04d}',
            sale_price=Decimal('200'),
            cost_price=Decimal('120'),
            current_stock=Decimal(str(stock)),
            category=self.category,
        )

    def test_receive_purchase_creates_fifo_batch(self):
        """Al recibir una compra se crea un StockBatch con los datos correctos."""
        product = self._make_product(stock=0)
        purchase = Purchase.objects.create(
            supplier=self.supplier,
            order_number='OC-TEST-0001',
            status='draft',
            created_by=self.user,
        )
        PurchaseItem.objects.create(
            purchase=purchase,
            product=product,
            quantity=10,
            unit_cost=Decimal('120'),
        )

        c = Client()
        c.login(username='admin_purchase', password='pass123')
        c.post(reverse('purchase:purchase_receive', args=[purchase.pk]))

        product.refresh_from_db()
        self.assertEqual(product.current_stock, Decimal('10'))

        batch = StockBatch.objects.filter(product=product).first()
        self.assertIsNotNone(batch)
        self.assertEqual(batch.quantity_purchased, Decimal('10'))
        self.assertEqual(batch.quantity_remaining, Decimal('10'))
        self.assertEqual(batch.purchase_price, Decimal('120'))
        self.assertEqual(batch.supplier_name, self.supplier.name)

    def test_receive_purchase_updates_weighted_avg_cost(self):
        """Recibir compra actualiza el costo promedio ponderado."""
        product = self._make_product(stock=5)
        product.cost_price = Decimal('100')
        product.save()

        purchase = Purchase.objects.create(
            supplier=self.supplier,
            order_number='OC-TEST-0002',
            status='draft',
            created_by=self.user,
        )
        PurchaseItem.objects.create(
            purchase=purchase,
            product=product,
            quantity=5,
            unit_cost=Decimal('120'),  # más caro que el stock existente
        )

        c = Client()
        c.login(username='admin_purchase', password='pass123')
        c.post(reverse('purchase:purchase_receive', args=[purchase.pk]))

        product.refresh_from_db()
        # (5*100 + 5*120) / 10 = 1100/10 = 110
        self.assertEqual(product.cost_price, Decimal('110'))
        self.assertEqual(product.current_stock, Decimal('10'))

    def test_receive_purchase_creates_stock_movement(self):
        """Recibir compra debe crear un StockMovement tipo 'purchase'."""
        product = self._make_product(stock=0)
        purchase = Purchase.objects.create(
            supplier=self.supplier,
            order_number='OC-TEST-0003',
            status='draft',
            created_by=self.user,
        )
        PurchaseItem.objects.create(
            purchase=purchase,
            product=product,
            quantity=8,
            unit_cost=Decimal('100'),
        )

        c = Client()
        c.login(username='admin_purchase', password='pass123')
        c.post(reverse('purchase:purchase_receive', args=[purchase.pk]))

        movement = StockMovement.objects.filter(
            product=product, movement_type='purchase'
        ).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity, Decimal('8'))

    def test_create_purchase_via_json_fetch(self):
        """El frontend usa fetch+JSON para crear OC — debe retornar success:True."""
        product = self._make_product(name='Prod JSON')
        c = Client()
        c.login(username='admin_purchase', password='pass123')

        import json
        payload = {
            'supplier_id': self.supplier.pk,
            'order_date': '2026-04-01',
            'tax_percent': 21,
            'notes': 'Test fetch',
            'items': [{'product_id': product.pk, 'quantity': 3, 'unit_cost': 150, 'sale_price': None}]
        }
        resp = c.post(
            reverse('purchase:purchase_create'),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'), f'No success en respuesta: {data}')
        self.assertIn('order_number', data)

        # Verificar que la compra existe en DB
        from purchase.models import Purchase
        oc = Purchase.objects.get(pk=data['pk'])
        self.assertEqual(oc.supplier, self.supplier)
        self.assertEqual(oc.items.count(), 1)

    def test_receive_with_display_packaging_does_not_overwrite_unit_price(self):
        """Al recibir un item cuyo packaging es display (o bulk), el
        sale_price del item es el precio del display, no el de la unidad.
        No debe sobreescribir product.sale_price ni packaging unit."""
        from stocks.models import ProductPackaging
        product = self._make_product(stock=0, name='Prod Con Display')
        product.sale_price = Decimal('100')  # precio unitario original
        product.cost_price = Decimal('40')
        product.save()

        unit_pkg = ProductPackaging.objects.create(
            product=product, packaging_type='unit', name='Unidad',
            units_per_display=1, displays_per_bulk=1,
            purchase_price=Decimal('40'), sale_price=Decimal('100'),
        )
        display_pkg = ProductPackaging.objects.create(
            product=product, packaging_type='display', name='Display x 6',
            units_per_display=6, displays_per_bulk=1,
            purchase_price=Decimal('240'), sale_price=Decimal('500'),
        )

        purchase = Purchase.objects.create(
            supplier=self.supplier,
            order_number='OC-TEST-0010',
            status='draft',
            created_by=self.user,
        )
        PurchaseItem.objects.create(
            purchase=purchase, product=product, packaging=display_pkg,
            quantity=2, unit_cost=Decimal('240'),
            sale_price=Decimal('600'),  # precio del display, no de la unidad
        )

        c = Client()
        c.login(username='admin_purchase', password='pass123')
        c.post(reverse('purchase:purchase_receive', args=[purchase.pk]))

        product.refresh_from_db()
        unit_pkg.refresh_from_db()
        display_pkg.refresh_from_db()

        # El display subió a $600 (lo que cargó el comprador)
        self.assertEqual(display_pkg.sale_price, Decimal('600'))
        # La unidad quedó como estaba (NO se cambió a $600)
        self.assertEqual(product.sale_price, Decimal('100'))
        self.assertEqual(unit_pkg.sale_price, Decimal('100'))

    def test_receive_without_packaging_updates_unit_price(self):
        """Sin packaging, el sale_price del item es el unitario y debe
        propagarse a product.sale_price como siempre."""
        product = self._make_product(stock=0, name='Prod Sin Pkg')
        product.sale_price = Decimal('100')
        product.save()

        purchase = Purchase.objects.create(
            supplier=self.supplier, order_number='OC-TEST-0011',
            status='draft', created_by=self.user,
        )
        PurchaseItem.objects.create(
            purchase=purchase, product=product,
            quantity=10, unit_cost=Decimal('50'),
            sale_price=Decimal('120'),
        )

        c = Client()
        c.login(username='admin_purchase', password='pass123')
        c.post(reverse('purchase:purchase_receive', args=[purchase.pk]))

        product.refresh_from_db()
        self.assertEqual(product.sale_price, Decimal('120'))

    def test_receive_with_unit_packaging_updates_both_product_and_unit(self):
        """Si el item usa el packaging unit, el precio es el de la unidad
        — hay que actualizar product.sale_price Y unit_pkg.sale_price para
        mantener el invariante."""
        from stocks.models import ProductPackaging
        product = self._make_product(stock=0, name='Prod Con Unit Pkg')
        product.sale_price = Decimal('100')
        product.save()
        unit_pkg = ProductPackaging.objects.create(
            product=product, packaging_type='unit', name='Unidad',
            units_per_display=1, displays_per_bulk=1,
            purchase_price=Decimal('40'), sale_price=Decimal('100'),
        )

        purchase = Purchase.objects.create(
            supplier=self.supplier, order_number='OC-TEST-0012',
            status='draft', created_by=self.user,
        )
        PurchaseItem.objects.create(
            purchase=purchase, product=product, packaging=unit_pkg,
            quantity=5, unit_cost=Decimal('50'),
            sale_price=Decimal('150'),
        )

        c = Client()
        c.login(username='admin_purchase', password='pass123')
        c.post(reverse('purchase:purchase_receive', args=[purchase.pk]))

        product.refresh_from_db()
        unit_pkg.refresh_from_db()
        self.assertEqual(product.sale_price, Decimal('150'))
        self.assertEqual(unit_pkg.sale_price, Decimal('150'))

    def test_cannot_receive_same_purchase_twice(self):
        """Una compra ya recibida no se puede recibir de nuevo."""
        product = self._make_product(stock=0)
        purchase = Purchase.objects.create(
            supplier=self.supplier,
            order_number='OC-TEST-0004',
            status='received',
            created_by=self.user,
        )
        PurchaseItem.objects.create(
            purchase=purchase,
            product=product,
            quantity=5,
            unit_cost=Decimal('100'),
        )

        c = Client()
        c.login(username='admin_purchase', password='pass123')
        c.post(reverse('purchase:purchase_receive', args=[purchase.pk]))

        # Stock should NOT have changed (already received)
        product.refresh_from_db()
        self.assertEqual(product.current_stock, Decimal('0'))
