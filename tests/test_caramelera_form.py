"""
Tests for caramelera create/edit views and deposito CRUD.
Covers:
- GET caramelera_list, caramelera_create, deposito_list
- POST caramelera_create creates a Caramelera with productos_autorizados
- POST caramelera_edit updates existing
- Validation errors
- caramelera_detail returns 200 with autorizados
- api_abrir_paquete opens a package and updates stock/cost
- api_auditoria registers an audit and adjusts stock
- Unauthenticated redirects
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
import json

from stocks.models import Product, ProductCategory
from granel.models import (
    Caramelera, AperturaBulto, AuditoriaCaramelera,
)

User = get_user_model()


class CarameleraFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sm_group, _ = Group.objects.get_or_create(name='Admin')
        cls.user = User.objects.create_user(
            username='stockmgr2', password='pass123',
            first_name='Stock', last_name='Mgr'
        )
        cls.user.groups.add(cls.sm_group)

        cls.category = ProductCategory.objects.create(name='Gomitas Test')

        # Create Product instances marked as deposito caramelera
        cls.deposito1 = Product.objects.create(
            name='Gomitas Ositos 1kg',
            sku='DEP-0001',
            marca='Mogul',
            cost_price=Decimal('3000'),
            sale_price=Decimal('3000'),
            weight_per_unit_grams=Decimal('1000'),
            current_stock=Decimal('5'),
            es_deposito_caramelera=True,
            category=cls.category,
        )
        cls.deposito2 = Product.objects.create(
            name='Caramelos Acidos 500g',
            sku='DEP-0002',
            marca='Arcor',
            cost_price=Decimal('1000'),
            sale_price=Decimal('1000'),
            weight_per_unit_grams=Decimal('500'),
            current_stock=Decimal('10'),
            es_deposito_caramelera=True,
            category=cls.category,
        )

    def setUp(self):
        self.client = Client()
        self.client.login(username='stockmgr2', password='pass123')

    # ------ GET views ------

    def test_caramelera_list_returns_200(self):
        resp = self.client.get(reverse('granel:caramelera_list'))
        self.assertEqual(resp.status_code, 200)

    def test_caramelera_create_returns_200(self):
        resp = self.client.get(reverse('granel:caramelera_create'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Nueva Caramelera')

    def test_deposito_list_returns_200(self):
        resp = self.client.get(reverse('granel:deposito_list'))
        self.assertEqual(resp.status_code, 200)

    # ------ POST caramelera_create ------

    def _valid_caramelera_post(self):
        return {
            'nombre': 'Gomitas Surtidas',
            'precio_100g': '2500',
            'precio_cuarto': '5500',
            'productos_autorizados': [
                str(self.deposito1.pk),
                str(self.deposito2.pk),
            ],
        }

    def test_create_caramelera_success(self):
        resp = self.client.post(
            reverse('granel:caramelera_create'),
            data=self._valid_caramelera_post(),
        )
        # Should redirect to caramelera_detail
        self.assertEqual(resp.status_code, 302)

        caramelera = Caramelera.objects.get(nombre='Gomitas Surtidas')
        self.assertEqual(caramelera.precio_100g, Decimal('2500'))
        self.assertEqual(caramelera.precio_cuarto, Decimal('5500'))
        self.assertIn(self.deposito1, caramelera.productos_autorizados.all())
        self.assertIn(self.deposito2, caramelera.productos_autorizados.all())

    def test_create_caramelera_missing_nombre(self):
        data = self._valid_caramelera_post()
        data['nombre'] = ''
        resp = self.client.post(reverse('granel:caramelera_create'), data=data)
        # Re-renders form with errors, not a redirect
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'obligatorio')

    def test_create_caramelera_zero_price(self):
        data = self._valid_caramelera_post()
        data['precio_100g'] = '0'
        resp = self.client.post(reverse('granel:caramelera_create'), data=data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'mayor a 0')

    # ------ POST caramelera_edit ------

    def test_edit_caramelera_updates_existing(self):
        # First create
        self.client.post(reverse('granel:caramelera_create'), data=self._valid_caramelera_post())
        caramelera = Caramelera.objects.get(nombre='Gomitas Surtidas')

        # Now edit
        edit_data = self._valid_caramelera_post()
        edit_data['nombre'] = 'Gomitas Editadas'
        edit_data['precio_100g'] = '3000'
        resp = self.client.post(
            reverse('granel:caramelera_edit', args=[caramelera.pk]),
            data=edit_data,
        )
        self.assertEqual(resp.status_code, 302)
        caramelera.refresh_from_db()
        self.assertEqual(caramelera.nombre, 'Gomitas Editadas')
        self.assertEqual(caramelera.precio_100g, Decimal('3000'))

    def test_caramelera_edit_get_returns_200(self):
        self.client.post(reverse('granel:caramelera_create'), data=self._valid_caramelera_post())
        caramelera = Caramelera.objects.get(nombre='Gomitas Surtidas')
        resp = self.client.get(reverse('granel:caramelera_edit', args=[caramelera.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_caramelera_edit_rendera_precios_con_punto_decimal(self):
        """El value de los inputs type=number debe venir sin localizar
        (punto decimal, sin separador de miles) — si no, el browser los
        descarta y el form queda en blanco."""
        caramelera = Caramelera.objects.create(
            nombre='Gomitas Precio Alto',
            precio_100g=Decimal('2500.50'),
            precio_cuarto=Decimal('22500.75'),
        )
        resp = self.client.get(reverse('granel:caramelera_edit', args=[caramelera.pk]))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # Debe aparecer con punto y sin separador de miles
        self.assertIn('value="2500.50"', content)
        self.assertIn('value="22500.75"', content)
        # No debe haber formato localizado con coma / puntos de miles
        self.assertNotIn('value="2.500,50"', content)
        self.assertNotIn('value="22.500,75"', content)

    # ------ Caramelera detail ------

    def test_caramelera_detail_returns_200(self):
        self.client.post(reverse('granel:caramelera_create'), data=self._valid_caramelera_post())
        caramelera = Caramelera.objects.get(nombre='Gomitas Surtidas')
        resp = self.client.get(reverse('granel:caramelera_detail', args=[caramelera.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Gomitas Surtidas')

    # ------ API abrir_paquete ------

    def test_api_abrir_paquete_success(self):
        self.client.post(reverse('granel:caramelera_create'), data=self._valid_caramelera_post())
        caramelera = Caramelera.objects.get(nombre='Gomitas Surtidas')

        resp = self.client.post(
            reverse('granel:api_abrir_paquete', args=[caramelera.pk]),
            data=json.dumps({'producto_id': self.deposito1.pk}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data['gramos_agregados'], float(self.deposito1.weight_per_unit_grams))

        caramelera.refresh_from_db()
        self.assertEqual(caramelera.stock_gramos_actual, self.deposito1.weight_per_unit_grams)

        self.deposito1.refresh_from_db()
        self.assertEqual(self.deposito1.current_stock, Decimal('4'))

    def test_api_abrir_paquete_no_stock_returns_400(self):
        self.client.post(reverse('granel:caramelera_create'), data=self._valid_caramelera_post())
        caramelera = Caramelera.objects.get(nombre='Gomitas Surtidas')

        deposito_vacio = Product.objects.create(
            name='Vacio Test',
            sku='DEP-VACIO',
            cost_price=Decimal('1000'),
            sale_price=Decimal('1000'),
            weight_per_unit_grams=Decimal('500'),
            current_stock=Decimal('0'),
            es_deposito_caramelera=True,
            category=self.category,
        )
        caramelera.productos_autorizados.add(deposito_vacio)

        resp = self.client.post(
            reverse('granel:api_abrir_paquete', args=[caramelera.pk]),
            data=json.dumps({'producto_id': deposito_vacio.pk}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.json())

    # ------ API auditoria ------

    def test_api_auditoria_success(self):
        self.client.post(reverse('granel:caramelera_create'), data=self._valid_caramelera_post())
        caramelera = Caramelera.objects.get(nombre='Gomitas Surtidas')
        caramelera.stock_gramos_actual = Decimal('1000')
        caramelera.save()

        resp = self.client.post(
            reverse('granel:api_auditoria', args=[caramelera.pk]),
            data=json.dumps({'peso_real': 980, 'motivo': 'picoteo'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertAlmostEqual(data['diferencia'], 20.0)

        caramelera.refresh_from_db()
        self.assertEqual(caramelera.stock_gramos_actual, Decimal('980'))

    # ------ Unauthenticated ------

    def test_unauthenticated_redirects(self):
        self.client.logout()
        resp = self.client.get(reverse('granel:caramelera_list'))
        self.assertEqual(resp.status_code, 302)
