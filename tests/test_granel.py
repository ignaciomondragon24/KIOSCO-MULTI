"""
Tests for the Granel (Caramelera) system:
- Weighted average cost calculation
- Apertura de bultos (abrir_paquete)
- FIFO batch management (BatchService)
- Auditoría de caramelera
- VentaGranel registration
- POS integration with decimal quantities
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from stocks.models import Product, ProductCategory, StockMovement
from stocks.services import StockManagementService
from pos.models import POSSession, POSTransaction, POSTransactionItem
from pos.services import CartService, CheckoutService, POSService
from cashregister.models import PaymentMethod, CashRegister, CashShift
from granel.models import (
    StockBatch, ProductoDeposito, Caramelera, AperturaBulto,
    VentaGranel, AuditoriaCaramelera,
)
from granel.services import GranelService, BatchService

User = get_user_model()


class GranelBaseTestCase(TestCase):
    """Base test case with common setup for granel tests."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_group, _ = Group.objects.get_or_create(name='Admin')
        cls.user = User.objects.create_user(
            username='testgranel', password='testpass123',
            first_name='Test', last_name='User'
        )
        cls.user.groups.add(cls.admin_group)

        cls.category = ProductCategory.objects.create(name='Gomitas Test')

        cls.cash_method = PaymentMethod.objects.create(
            name='Efectivo Test', code='cash_test', is_active=True
        )
        cls.register = CashRegister.objects.create(
            name='Caja Granel Test', code='GRN01', is_active=True
        )
        cls.shift = CashShift.objects.create(
            cash_register=cls.register,
            cashier=cls.user,
            initial_amount=Decimal('10000'),
            status='open'
        )

    def _create_deposito(self, nombre='Ositos 2kg', costo=Decimal('10000'),
                          gramos=Decimal('2000'), stock=5):
        """Create a Product configured as deposito caramelera (replaces old ProductoDeposito)."""
        return Product.objects.create(
            name=nombre,
            sku=f'DEP-{Product.objects.count()+1:04d}',
            cost_price=costo,
            sale_price=costo,
            weight_per_unit_grams=gramos,
            current_stock=Decimal(str(stock)),
            es_deposito_caramelera=True,
            marca='Testbrand',
            category=self.category,
        )

    def _create_caramelera(self, nombre='Gomitas Surtidas',
                            precio_100g=Decimal('2500'),
                            precio_cuarto=Decimal('5500')):
        return Caramelera.objects.create(
            nombre=nombre,
            precio_100g=precio_100g,
            precio_cuarto=precio_cuarto,
        )

    def _create_pos_granel_product(self, caramelera, sale_price=Decimal('2500'),
                                   stock=Decimal('5000')):
        """Create a stocks.Product linked to a Caramelera for POS tests."""
        p = Product.objects.create(
            name=caramelera.nombre,
            sku=f'GRN-{Product.objects.count()+1:04d}',
            sale_price=sale_price,
            is_bulk=True,
            bulk_unit='g',
            is_granel=True,
            granel_price_weight_grams=100,
            current_stock=stock,
            weighted_avg_cost_per_gram=Decimal('5.0000'),
            cost_price=Decimal('500.00'),
            category=self.category,
            granel_caramelera=caramelera,
        )
        return p


class WeightedAverageCostTest(GranelBaseTestCase):
    """Test weighted average cost calculation on abrir_paquete."""

    def test_single_apertura_empty_caramelera(self):
        """First apertura to empty caramelera: cost = costo/g del bulto."""
        caramelera = self._create_caramelera()
        producto = self._create_deposito('Ositos 2kg', Decimal('10000'), Decimal('2000'))
        caramelera.productos_autorizados.add(producto)

        # $10000 / 2000g = $5.0000/g
        apertura = GranelService.abrir_paquete(
            caramelera.pk, producto.pk, self.user
        )

        caramelera.refresh_from_db()
        self.assertEqual(caramelera.stock_gramos_actual, Decimal('2000'))
        self.assertEqual(caramelera.costo_ponderado_gramo, Decimal('5.000000'))
        self.assertEqual(apertura.gramos_agregados, Decimal('2000'))

    def test_two_aperturas_weighted_average(self):
        """Two aperturas with different costs: proper weighted average."""
        caramelera = self._create_caramelera()

        p1 = self._create_deposito('Mogul 1kg', Decimal('5000'), Decimal('1000'))
        p2 = self._create_deposito('Haribo 500g', Decimal('4000'), Decimal('500'))
        caramelera.productos_autorizados.add(p1, p2)

        # Apertura 1: 1000g at $5/g → avg = $5.000000
        GranelService.abrir_paquete(caramelera.pk, p1.pk, self.user)
        caramelera.refresh_from_db()
        self.assertEqual(caramelera.costo_ponderado_gramo, Decimal('5.000000'))

        # Apertura 2: 500g at $8/g → avg = (1000*5 + 500*8) / 1500 = 9000/1500 = 6.0
        GranelService.abrir_paquete(caramelera.pk, p2.pk, self.user)
        caramelera.refresh_from_db()
        self.assertEqual(caramelera.stock_gramos_actual, Decimal('1500'))
        self.assertEqual(caramelera.costo_ponderado_gramo, Decimal('6.000000'))

    def test_margen_100g_property(self):
        """margen_100g should correctly calculate margin percentage."""
        caramelera = self._create_caramelera(precio_100g=Decimal('2500'))
        caramelera.costo_ponderado_gramo = Decimal('5.000000')
        caramelera.save()
        # costo 100g = 500, precio 100g = 2500
        # margen = (2500 - 500) / 2500 * 100 = 80%
        self.assertEqual(caramelera.margen_100g, Decimal('80.00'))


class TransferValidationTest(GranelBaseTestCase):
    """Test apertura validations."""

    def test_apertura_deducts_deposito_stock(self):
        """abrir_paquete should deduct 1 unit from deposito."""
        caramelera = self._create_caramelera()
        producto = self._create_deposito(stock=3)
        caramelera.productos_autorizados.add(producto)

        GranelService.abrir_paquete(caramelera.pk, producto.pk, self.user)
        producto.refresh_from_db()
        self.assertEqual(producto.current_stock, Decimal('2'))

    def test_apertura_no_stock_raises(self):
        """abrir_paquete with no deposito stock should raise ValueError."""
        caramelera = self._create_caramelera()
        producto = self._create_deposito(stock=0)
        caramelera.productos_autorizados.add(producto)

        with self.assertRaises(ValueError):
            GranelService.abrir_paquete(caramelera.pk, producto.pk, self.user)

    def test_apertura_unauthorized_product_raises(self):
        """abrir_paquete with non-authorized product should raise ValueError."""
        caramelera = self._create_caramelera()
        producto = self._create_deposito()
        # NOT added to productos_autorizados

        with self.assertRaises(ValueError):
            GranelService.abrir_paquete(caramelera.pk, producto.pk, self.user)

    def test_apertura_creates_log(self):
        """abrir_paquete should create an AperturaBulto record."""
        caramelera = self._create_caramelera()
        producto = self._create_deposito()
        caramelera.productos_autorizados.add(producto)

        apertura = GranelService.abrir_paquete(caramelera.pk, producto.pk, self.user)

        self.assertIsInstance(apertura, AperturaBulto)
        self.assertEqual(apertura.caramelera, caramelera)
        self.assertEqual(apertura.producto, producto)
        self.assertEqual(apertura.abierto_por, self.user)


class AuditoriaTest(GranelBaseTestCase):
    """Test auditoría de caramelera."""

    def test_auditoria_merma(self):
        """Auditoría con peso real menor que sistema: merma positiva."""
        caramelera = self._create_caramelera()
        caramelera.stock_gramos_actual = Decimal('1000')
        caramelera.save()

        auditoria = GranelService.realizar_auditoria(
            caramelera.pk, Decimal('980'), self.user, motivo='picoteo'
        )

        self.assertEqual(auditoria.stock_sistema_gramos, Decimal('1000'))
        self.assertEqual(auditoria.peso_real_balanza_gramos, Decimal('980'))
        self.assertEqual(auditoria.diferencia_gramos, Decimal('20'))
        self.assertEqual(auditoria.porcentaje_merma, Decimal('2.00'))
        self.assertTrue(auditoria.ajuste_aplicado)

        caramelera.refresh_from_db()
        self.assertEqual(caramelera.stock_gramos_actual, Decimal('980'))

    def test_auditoria_sobrante(self):
        """Auditoría con peso real mayor que sistema: diferencia negativa."""
        caramelera = self._create_caramelera()
        caramelera.stock_gramos_actual = Decimal('500')
        caramelera.save()

        auditoria = GranelService.realizar_auditoria(
            caramelera.pk, Decimal('520'), self.user
        )

        self.assertEqual(auditoria.diferencia_gramos, Decimal('-20'))
        caramelera.refresh_from_db()
        self.assertEqual(caramelera.stock_gramos_actual, Decimal('520'))


class VentaGranelTest(GranelBaseTestCase):
    """Test registrar_venta."""

    def test_registrar_venta_descuenta_stock(self):
        """registrar_venta debería descontar gramos de la caramelera."""
        caramelera = self._create_caramelera()
        caramelera.stock_gramos_actual = Decimal('1000')
        caramelera.costo_ponderado_gramo = Decimal('5.000000')
        caramelera.save()

        venta = GranelService.registrar_venta(
            caramelera.pk, Decimal('200'), Decimal('5000')
        )

        caramelera.refresh_from_db()
        self.assertEqual(caramelera.stock_gramos_actual, Decimal('800'))
        self.assertEqual(venta.gramos_vendidos, Decimal('200'))
        self.assertEqual(venta.precio_cobrado, Decimal('5000'))
        self.assertEqual(venta.costo_total, Decimal('1000.00'))
        self.assertEqual(venta.ganancia, Decimal('4000.00'))

    def test_registrar_venta_sin_stock_raises(self):
        """registrar_venta con stock insuficiente debe lanzar ValueError."""
        caramelera = self._create_caramelera()
        caramelera.stock_gramos_actual = Decimal('100')
        caramelera.save()

        with self.assertRaises(ValueError):
            GranelService.registrar_venta(caramelera.pk, Decimal('500'), Decimal('5000'))

    def test_calcular_precio_libre(self):
        """calcular_precio para < 250g es proporcional a precio/100g."""
        caramelera = self._create_caramelera(precio_100g=Decimal('2500'))
        # 150g → (150/100) * 2500 = 3750
        self.assertEqual(caramelera.calcular_precio(150), Decimal('3750.0'))
        # 200g → (200/100) * 2500 = 5000
        self.assertEqual(caramelera.calcular_precio(200), Decimal('5000.0'))

    def test_calcular_precio_kilo_oferta(self):
        """calcular_precio para >= 250g usa precio por kilo (regla de tres)."""
        # precio_cuarto ahora almacena el precio por kilo oferta
        caramelera = self._create_caramelera(precio_100g=Decimal('2500'),
                                              precio_cuarto=Decimal('20000'))
        # 250g → (250/1000) * 20000 = 5000
        self.assertEqual(caramelera.calcular_precio(250), Decimal('5000.0'))
        # 300g → (300/1000) * 20000 = 6000
        self.assertEqual(caramelera.calcular_precio(300), Decimal('6000.0'))
        # 500g → (500/1000) * 20000 = 10000
        self.assertEqual(caramelera.calcular_precio(500), Decimal('10000.0'))
        # 1000g → (1000/1000) * 20000 = 20000
        self.assertEqual(caramelera.calcular_precio(1000), Decimal('20000.0'))

    def test_calcular_precio_bajo_250_ignora_kilo(self):
        """calcular_precio para < 250g siempre usa precio/100g, incluso con kilo oferta."""
        caramelera = self._create_caramelera(precio_100g=Decimal('2500'),
                                              precio_cuarto=Decimal('20000'))
        # 100g → (100/100) * 2500 = 2500 (NO usa kilo)
        self.assertEqual(caramelera.calcular_precio(100), Decimal('2500.0'))
        # 200g → (200/100) * 2500 = 5000 (NO usa kilo)
        self.assertEqual(caramelera.calcular_precio(200), Decimal('5000.0'))


class FIFOBatchTest(GranelBaseTestCase):
    """Test FIFO batch management (BatchService)."""

    def test_fifo_deduction_order(self):
        """Oldest batch should be deducted first."""
        product = Product.objects.create(
            name='Batch Test',
            sku='BTEST001',
            sale_price=Decimal('100'),
            current_stock=Decimal('10'),
            category=self.category,
        )

        b1 = BatchService.create_batch(product.pk, 5, Decimal('100'),
                                        purchased_at=timezone.now() - timezone.timedelta(days=30))
        b2 = BatchService.create_batch(product.pk, 3, Decimal('120'),
                                        purchased_at=timezone.now() - timezone.timedelta(days=15))
        b3 = BatchService.create_batch(product.pk, 2, Decimal('150'),
                                        purchased_at=timezone.now())

        deductions = BatchService.deduct_fifo(product.pk, 6)

        self.assertEqual(len(deductions), 2)
        self.assertEqual(deductions[0][0].pk, b1.pk)
        self.assertEqual(deductions[0][1], Decimal('5'))
        self.assertEqual(deductions[1][0].pk, b2.pk)
        self.assertEqual(deductions[1][1], Decimal('1'))

        b1.refresh_from_db()
        b2.refresh_from_db()
        b3.refresh_from_db()
        self.assertEqual(b1.quantity_remaining, Decimal('0'))
        self.assertEqual(b2.quantity_remaining, Decimal('2'))
        self.assertEqual(b3.quantity_remaining, Decimal('2'))

    def test_fifo_cost_calculation(self):
        """FIFO cost should use batch-specific costs."""
        product = Product.objects.create(
            name='Batch Cost Test',
            sku='BCTEST001',
            sale_price=Decimal('100'),
            current_stock=Decimal('10'),
            category=self.category,
        )

        BatchService.create_batch(product.pk, 5, Decimal('100'),
                                   purchased_at=timezone.now() - timezone.timedelta(days=10))
        BatchService.create_batch(product.pk, 5, Decimal('200'),
                                   purchased_at=timezone.now())

        cost = BatchService.get_fifo_cost(product.pk, 6)
        self.assertEqual(cost, Decimal('700.00'))


class POSDecimalQuantityTest(GranelBaseTestCase):
    """Test that POS handles decimal quantities and granel integration correctly."""

    def test_add_decimal_quantity_to_cart(self):
        """Granel product with decimal quantity in cart."""
        caramelera = self._create_caramelera()
        granel = self._create_pos_granel_product(caramelera)

        session = POSService.get_or_create_session(self.shift)
        txn = POSService.create_transaction(session)

        item, msg = CartService.add_item(txn, granel.pk, quantity=Decimal('150.5'))
        self.assertIsNotNone(item)
        self.assertEqual(item.quantity, Decimal('150.500'))

    def test_checkout_deducts_granel_stock(self):
        """Checkout should deduct grams from granel stock product."""
        caramelera = self._create_caramelera()
        caramelera.stock_gramos_actual = Decimal('5000')
        caramelera.costo_ponderado_gramo = Decimal('5.000000')
        caramelera.save()
        granel = self._create_pos_granel_product(caramelera, stock=Decimal('5000'))

        session = POSService.get_or_create_session(self.shift)
        txn = POSService.create_transaction(session)
        CartService.add_item(txn, granel.pk, quantity=Decimal('200'))
        txn.refresh_from_db()

        success, result = CheckoutService.process_payment(
            txn.pk, [{'method_code': 'cash_test', 'amount': str(txn.total)}]
        )
        self.assertTrue(success)

        granel.refresh_from_db()
        caramelera.refresh_from_db()
        self.assertEqual(granel.current_stock, Decimal('4800'))
        self.assertEqual(caramelera.stock_gramos_actual, Decimal('4800'))

    def test_checkout_registers_venta_granel(self):
        """Checkout should register VentaGranel when product has granel_caramelera."""
        caramelera = self._create_caramelera()
        caramelera.stock_gramos_actual = Decimal('5000')
        caramelera.costo_ponderado_gramo = Decimal('5.000000')
        caramelera.save()
        granel = self._create_pos_granel_product(caramelera, stock=Decimal('5000'))

        session = POSService.get_or_create_session(self.shift)
        txn = POSService.create_transaction(session)
        CartService.add_item(txn, granel.pk, quantity=Decimal('200'))
        txn.refresh_from_db()

        success, result = CheckoutService.process_payment(
            txn.pk, [{'method_code': 'cash_test', 'amount': str(txn.total)}]
        )
        self.assertTrue(success)

        ventas = VentaGranel.objects.filter(caramelera=caramelera)
        self.assertEqual(ventas.count(), 1)
        venta = ventas.first()
        self.assertEqual(venta.gramos_vendidos, Decimal('200'))
        self.assertEqual(venta.pos_transaction_id, txn.pk)
