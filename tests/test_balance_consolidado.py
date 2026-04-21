"""Tests del balance consolidado: pérdidas al costo, consumo interno POS."""
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from stocks.models import Product, ProductCategory, StockMovement
from stocks.services import StockManagementService

User = get_user_model()


class BalanceConsolidadoLossesTests(TestCase):
    """El consumo interno cargado desde el POS debe figurar como pérdida
    junto con los ajustes manuales del mismo motivo."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_group, _ = Group.objects.get_or_create(name='Admin')
        cls.admin = User.objects.create_user(
            username='balance_admin', password='pass123',
            is_superuser=True, is_staff=True,
        )
        cls.admin.groups.add(cls.admin_group)
        cls.category = ProductCategory.objects.create(name='Test')

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin)
        self.product_a = Product.objects.create(
            name='Producto A', category=self.category,
            sale_price=Decimal('100'), purchase_price=Decimal('40'),
            cost_price=Decimal('40'), current_stock=Decimal('100.000'),
        )
        self.product_b = Product.objects.create(
            name='Producto B', category=self.category,
            sale_price=Decimal('200'), purchase_price=Decimal('80'),
            cost_price=Decimal('80'), current_stock=Decimal('50.000'),
        )

    def _get_balance(self, **params):
        params.setdefault('period', 'today')
        return self.client.get(reverse('sales:balance_consolidado'), params)

    def test_consumo_interno_pos_entra_al_total_de_perdidas(self):
        """Un StockMovement con movement_type='sale' y reference que empieza
        con 'Consumo interno ' debe sumar al total de pérdidas."""
        StockManagementService.deduct_stock(
            self.product_a, Decimal('3'),
            reference='Consumo interno CAJA-01-20260421-0001 - cafe equipo',
        )

        resp = self._get_balance()
        self.assertEqual(resp.status_code, 200)
        # 3 * 40 = 120
        self.assertEqual(resp.context['total_losses'], Decimal('120.00'))

        reasons = {r['reference']: r for r in resp.context['losses_by_reason']}
        self.assertIn('Consumo Interno', reasons)
        self.assertEqual(reasons['Consumo Interno']['total_cost'], Decimal('120.00'))
        self.assertEqual(reasons['Consumo Interno']['movement_count'], 1)

    def test_consumo_interno_pos_se_agrupa_con_ajustes_manuales(self):
        """El consumo interno POS y el ajuste manual 'Consumo Interno' deben
        colapsar en el mismo bucket."""
        # Ajuste manual
        StockManagementService.adjust_stock(
            self.product_a, Decimal('95.000'), 'Consumo Interno',
        )  # baja 5u * $40 = $200
        # Consumo interno POS (misma producto)
        StockManagementService.deduct_stock(
            self.product_a, Decimal('2'),
            reference='Consumo interno CAJA-01-20260421-0002 - merienda',
        )  # 2u * $40 = $80

        resp = self._get_balance()
        self.assertEqual(resp.context['total_losses'], Decimal('280.00'))

        reasons = {r['reference']: r for r in resp.context['losses_by_reason']}
        self.assertEqual(len(reasons), 1)
        self.assertIn('Consumo Interno', reasons)
        self.assertEqual(reasons['Consumo Interno']['total_cost'], Decimal('280.00'))
        self.assertEqual(reasons['Consumo Interno']['movement_count'], 2)
        # Producto A debe aparecer con los 7u totales bajo Consumo Interno
        products = reasons['Consumo Interno']['products']
        prod_a = next(p for p in products if p['product__id'] == self.product_a.id)
        self.assertEqual(prod_a['total_qty'], Decimal('7'))
        self.assertEqual(prod_a['total_cost'], Decimal('280.00'))

    def test_venta_normal_no_cuenta_como_perdida(self):
        """Un StockMovement con movement_type='sale' y reference que NO empieza
        con 'Consumo interno ' (ej: venta común) no debe sumar pérdidas."""
        StockManagementService.deduct_stock(
            self.product_a, Decimal('5'),
            reference='Venta CAJA-01-20260421-0003',
        )

        resp = self._get_balance()
        self.assertEqual(resp.context['total_losses'], Decimal('0'))
        self.assertEqual(resp.context['losses_by_reason'], [])

    def test_correccion_y_devolucion_no_cuentan(self):
        """Ajustes por 'Corrección de Error' y 'Devolución' no son pérdidas."""
        StockManagementService.adjust_stock(
            self.product_a, Decimal('90.000'), 'Corrección de Error',
        )
        StockManagementService.adjust_stock(
            self.product_b, Decimal('45.000'), 'Devolución',
        )

        resp = self._get_balance()
        self.assertEqual(resp.context['total_losses'], Decimal('0'))
        self.assertEqual(resp.context['losses_by_reason'], [])

    def test_mezcla_motivos_arma_buckets_separados(self):
        """Ajustes con distintos motivos deben aparecer en buckets separados."""
        StockManagementService.adjust_stock(
            self.product_a, Decimal('98.000'), 'Robo / Pérdida',
        )  # 2 * 40 = 80
        StockManagementService.deduct_stock(
            self.product_b, Decimal('1'),
            reference='Consumo interno CAJA-01-20260421-0004 - muestra',
        )  # 1 * 80 = 80

        resp = self._get_balance()
        self.assertEqual(resp.context['total_losses'], Decimal('160.00'))

        reasons = {r['reference']: r for r in resp.context['losses_by_reason']}
        self.assertEqual(set(reasons.keys()), {'Robo / Pérdida', 'Consumo Interno'})
        self.assertEqual(reasons['Robo / Pérdida']['total_cost'], Decimal('80.00'))
        self.assertEqual(reasons['Consumo Interno']['total_cost'], Decimal('80.00'))
