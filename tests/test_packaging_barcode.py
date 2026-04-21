"""Tests del form de empaques: absorción de Product legacy al crear packaging.

Escenario principal: el dueño tiene un Product viejo creado como producto
standalone (ej: "Display x 6" con stock en "displays"). Ahora quiere
incorporarlo como el display del producto padre. Al ingresar el barcode
del legacy en el form de empaques, el sistema lo absorbe:
  - Convierte el stock del legacy a unidades base (legacy_stock × factor).
  - Suma esas unidades al stock del Product padre.
  - Desactiva el Product legacy (stock 0, barcode NULL, is_active=False).
  - Preserva SKU e historial del legacy.
"""
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from stocks.models import Product, ProductCategory, ProductPackaging, StockMovement

User = get_user_model()


class PackagingBarcodeAbsorptionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin_group, _ = Group.objects.get_or_create(name='Admin')
        cls.admin = User.objects.create_user(
            username='pkg_admin', password='pass123',
            is_superuser=True, is_staff=True,
        )
        cls.admin.groups.add(cls.admin_group)
        cls.category = ProductCategory.objects.create(name='Test Cat')

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin)
        self.product = Product.objects.create(
            name='Producto Padre', sku='PP-001', barcode='7791234000001',
            category=self.category,
            sale_price=Decimal('100'), purchase_price=Decimal('40'),
            cost_price=Decimal('40'), current_stock=Decimal('24'),
        )

    def _post_save_pkg(self, **extra):
        data = {
            'action': 'save_pkg',
            'pkg_units_per_display': '6',
            'pkg_displays_per_bulk': '4',
            'has_unit': '1',
            'unit_barcode': self.product.barcode,
            'unit_name': 'Unidad',
            'unit_purchase_price': '40',
            'unit_sale_price': '100',
        }
        data.update(extra)
        return self.client.post(
            reverse('stocks:product_packaging', args=[self.product.pk]),
            data,
            follow=True,
        )

    def test_absorbe_product_legacy_como_display_con_cascada(self):
        """Legacy con 5 displays y factor=6 → +30 unidades al padre.
        El display creado refleja el stock total via cascada."""
        legacy = Product.objects.create(
            name='Display x 6 Viejo', sku='LEG-001',
            barcode='7791234000077',
            category=self.category,
            sale_price=Decimal('600'), purchase_price=Decimal('240'),
            cost_price=Decimal('240'), current_stock=Decimal('5'),
        )

        resp = self._post_save_pkg(
            has_display='1',
            display_barcode='7791234000077',
            display_name='Display x 6',
            display_purchase_price='240',
            display_sale_price='600',
        )
        self.assertEqual(resp.status_code, 200)

        # Producto padre: 24 (inicial) + 5 × 6 (absorción) = 54 unidades
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('54.000'))

        # El packaging display existe con el barcode
        display = ProductPackaging.objects.get(
            product=self.product, packaging_type='display'
        )
        self.assertEqual(display.barcode, '7791234000077')
        # 54 unidades / 6 por display = 9 displays
        self.assertEqual(display.current_stock, Decimal('9.000'))

        # Legacy desactivado, sin barcode, stock en 0
        legacy.refresh_from_db()
        self.assertIsNone(legacy.barcode)
        self.assertFalse(legacy.is_active)
        self.assertEqual(legacy.current_stock, Decimal('0.000'))
        # SKU preservado
        self.assertEqual(legacy.sku, 'LEG-001')

        # Se registraron los movimientos
        out_mov = StockMovement.objects.filter(
            product=legacy, movement_type='adjustment_out'
        ).first()
        self.assertIsNotNone(out_mov)
        self.assertEqual(out_mov.quantity, Decimal('-5'))

        in_mov = StockMovement.objects.filter(
            product=self.product, movement_type='adjustment_in'
        ).first()
        self.assertIsNotNone(in_mov)
        self.assertEqual(in_mov.quantity, Decimal('30'))
        self.assertEqual(in_mov.stock_before, Decimal('24'))
        self.assertEqual(in_mov.stock_after, Decimal('54'))

    def test_absorbe_bulto_legacy_con_factor_total(self):
        """Legacy absorbido como bulto usa units_per_display × displays_per_bulk."""
        legacy = Product.objects.create(
            name='Bulto x 144 Viejo', sku='LEG-002',
            barcode='7791234000088',
            category=self.category,
            sale_price=Decimal('14400'), purchase_price=Decimal('5760'),
            cost_price=Decimal('5760'), current_stock=Decimal('2'),
        )

        self._post_save_pkg(
            has_bulk='1',
            bulk_barcode='7791234000088',
            bulk_name='Bulto x 144',
            bulk_purchase_price='5760',
            bulk_sale_price='14400',
        )

        # 24 (inicial) + 2 × (6×4) = 24 + 48 = 72
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('72.000'))

        bulk = ProductPackaging.objects.get(
            product=self.product, packaging_type='bulk'
        )
        # 72 / 24 (units_quantity del bulk) = 3
        self.assertEqual(bulk.current_stock, Decimal('3.000'))

        legacy.refresh_from_db()
        self.assertFalse(legacy.is_active)

    def test_absorbe_display_y_bulto_en_un_solo_guardado(self):
        """Dos legacies absorbidos en el mismo submit: ambos stocks se suman
        al padre y los packagings quedan consistentes con la cascada."""
        leg_display = Product.objects.create(
            name='Display Viejo', sku='LD',
            barcode='7791234000111',
            category=self.category,
            sale_price=Decimal('600'), purchase_price=Decimal('240'),
            cost_price=Decimal('240'), current_stock=Decimal('5'),
        )
        leg_bulk = Product.objects.create(
            name='Bulto Viejo', sku='LB',
            barcode='7791234000222',
            category=self.category,
            sale_price=Decimal('14400'), purchase_price=Decimal('5760'),
            cost_price=Decimal('5760'), current_stock=Decimal('1'),
        )

        self._post_save_pkg(
            has_display='1',
            display_barcode='7791234000111',
            display_name='Display x 6',
            display_purchase_price='240',
            display_sale_price='600',
            has_bulk='1',
            bulk_barcode='7791234000222',
            bulk_name='Bulto x 24',
            bulk_purchase_price='5760',
            bulk_sale_price='14400',
        )

        # 24 + 5×6 + 1×24 = 24 + 30 + 24 = 78
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('78.000'))

        display = ProductPackaging.objects.get(
            product=self.product, packaging_type='display'
        )
        bulk = ProductPackaging.objects.get(
            product=self.product, packaging_type='bulk'
        )
        unit = ProductPackaging.objects.get(
            product=self.product, packaging_type='unit'
        )
        # Resync final: todos deben reflejar el stock total
        self.assertEqual(unit.current_stock, Decimal('78.000'))
        self.assertEqual(display.current_stock, Decimal('13.000'))  # 78/6
        self.assertEqual(bulk.current_stock, Decimal('3.250'))       # 78/24

        leg_display.refresh_from_db()
        leg_bulk.refresh_from_db()
        self.assertFalse(leg_display.is_active)
        self.assertFalse(leg_bulk.is_active)

    def test_legacy_sin_stock_no_altera_padre_pero_se_desactiva(self):
        """Legacy con stock 0: no hay nada que sumar, pero igual se
        desactiva y se libera el barcode para que el packaging nuevo lo use."""
        legacy = Product.objects.create(
            name='Display Viejo Vacío', sku='LEG-003',
            barcode='7791234000033',
            category=self.category,
            sale_price=Decimal('600'), purchase_price=Decimal('240'),
            cost_price=Decimal('240'), current_stock=Decimal('0'),
        )

        self._post_save_pkg(
            has_display='1',
            display_barcode='7791234000033',
            display_name='Display x 6',
            display_purchase_price='240',
            display_sale_price='600',
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('24.000'))

        legacy.refresh_from_db()
        self.assertIsNone(legacy.barcode)
        self.assertFalse(legacy.is_active)

    def test_colision_con_otro_packaging_sigue_bloqueando(self):
        """Si el barcode ya lo usa otro packaging activo de otro producto,
        seguimos rechazando (unique constraint de DB)."""
        otro = Product.objects.create(
            name='Otro Padre', sku='OP-001',
            category=self.category,
            sale_price=Decimal('50'), purchase_price=Decimal('20'),
            cost_price=Decimal('20'), current_stock=Decimal('10'),
        )
        ProductPackaging.objects.create(
            product=otro, packaging_type='display',
            barcode='7791234000099', name='Display otro',
            units_per_display=6, displays_per_bulk=1,
            purchase_price=Decimal('120'), sale_price=Decimal('300'),
        )

        resp = self._post_save_pkg(
            has_display='1',
            display_barcode='7791234000099',
            display_name='Display colide',
            display_purchase_price='240',
            display_sale_price='600',
        )
        self.assertFalse(
            ProductPackaging.objects.filter(
                product=self.product, packaging_type='display'
            ).exists()
        )
        msgs = [str(m) for m in list(resp.context['messages'])]
        self.assertTrue(
            any('ya está en uso' in m for m in msgs),
            f'Se esperaba error de barcode en uso, mensajes: {msgs}',
        )

    def test_sin_colision_crea_packaging_normal(self):
        """Flujo feliz sin legacies: no debe cambiar."""
        self._post_save_pkg(
            has_display='1',
            display_barcode='7791234000055',
            display_name='Display libre',
            display_purchase_price='240',
            display_sale_price='600',
        )
        display = ProductPackaging.objects.get(
            product=self.product, packaging_type='display'
        )
        self.assertEqual(display.barcode, '7791234000055')
        # 24 / 6 = 4
        self.assertEqual(display.current_stock, Decimal('4.000'))

        # No cambió el stock del padre (no hubo absorción)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('24.000'))

    def test_barcode_del_propio_producto_no_genera_conflicto(self):
        """Usar el barcode del Product padre para el packaging unit no
        debe disparar absorción (el exclude(pk=product.pk) lo filtra)."""
        original_barcode = self.product.barcode
        self._post_save_pkg()

        self.product.refresh_from_db()
        self.assertEqual(self.product.barcode, original_barcode)
        self.assertEqual(self.product.current_stock, Decimal('24.000'))

        unit = ProductPackaging.objects.get(
            product=self.product, packaging_type='unit'
        )
        self.assertEqual(unit.barcode, original_barcode)
