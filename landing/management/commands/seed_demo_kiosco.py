"""
Carga datos demo de un kiosco argentino tipico para que las capturas de la
landing y las demos comerciales se vean cargadas con productos reales.

Crea categorias, productos, marca acceso rapido los principales, arma 2-3
promociones tipicas (2x1, combo) y genera transacciones de los ultimos dias
para que el dashboard tenga ventas para mostrar.

Uso: python manage.py seed_demo_kiosco
     python manage.py seed_demo_kiosco --reset   # borra datos demo previos
"""
from datetime import date, timedelta
from decimal import Decimal
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from stocks.models import Product, ProductCategory
from promotions.models import Promotion, PromotionProduct


# Productos tipicos de kiosco argentino con precios estimados 2026.
# (categoria, nombre, precio_compra, precio_venta, stock, quick_access, color, icono)
PRODUCTS = [
    # Bebidas
    ('Bebidas', 'Coca Cola 2.25L',           1900, 2800,  18, True,  '#E60000', 'fa-bottle-droplet'),
    ('Bebidas', 'Coca Cola 500ml',            550,  900,  42, True,  '#E60000', 'fa-bottle-water'),
    ('Bebidas', 'Sprite 2.25L',              1750, 2600,  12, False, '#5BBF21', 'fa-bottle-droplet'),
    ('Bebidas', 'Manaos Naranja 2.25L',       950, 1500,  20, True,  '#F59100', 'fa-bottle-droplet'),
    ('Bebidas', 'Agua Villavicencio 500ml',   400,  700,  35, False, '#3498DB', 'fa-bottle-water'),
    ('Bebidas', 'Cerveza Quilmes 1L',        1400, 2200,  24, True,  '#FFD000', 'fa-beer-mug-empty'),
    ('Bebidas', 'Speed Energizante 250ml',    900, 1500,  28, False, '#FF6600', 'fa-bolt'),
    ('Bebidas', 'Powerade Mora 500ml',        700, 1200,  18, False, '#0066CC', 'fa-bottle-water'),

    # Golosinas
    ('Golosinas', 'Alfajor Jorgito Triple',   400,  700,  60, True,  '#A52A2A', 'fa-cookie-bite'),
    ('Golosinas', 'Alfajor Bon o Bon',        450,  800,  48, True,  '#8B4513', 'fa-cookie-bite'),
    ('Golosinas', 'Alfajor Aguila Doble',     500,  900,  35, False, '#5C2C0E', 'fa-cookie-bite'),
    ('Golosinas', 'Chupetin Pico Dulce',       80,  150, 200, False, '#FF1493', 'fa-candy-cane'),
    ('Golosinas', 'Sugus Tira',               300,  550,  80, False, '#FFC107', 'fa-candy-cane'),
    ('Golosinas', 'Mogul Tira',               350,  600,  72, False, '#9C27B0', 'fa-candy-cane'),
    ('Golosinas', 'Beldent Menta',            450,  750,  55, True,  '#00BFA5', 'fa-cookie'),
    ('Golosinas', 'Topline Frutilla',         420,  700,  60, False, '#E91E63', 'fa-cookie'),

    # Chocolates
    ('Chocolates', 'Cofler Block',            900, 1500,  30, True,  '#5D2606', 'fa-cookie-bite'),
    ('Chocolates', 'Aguila Tableta',          850, 1400,  28, False, '#3E1A02', 'fa-cookie-bite'),
    ('Chocolates', 'Bon o Bon x6',           1200, 2000,  22, True,  '#8B4513', 'fa-cookie-bite'),
    ('Chocolates', 'Marroc',                  280,  500, 100, False, '#A0522D', 'fa-cookie-bite'),

    # Snacks
    ('Snacks', 'Papas Lays Clasicas',         900, 1500,  35, True,  '#FFD000', 'fa-bag-shopping'),
    ('Snacks', 'Papas Pringles Original',    2400, 3800,  18, False, '#E60000', 'fa-bag-shopping'),
    ('Snacks', 'Doritos Queso',              1200, 1900,  28, True,  '#FF6600', 'fa-bag-shopping'),
    ('Snacks', 'Mani Salado 100g',            550,  900,  40, False, '#D2691E', 'fa-bag-shopping'),

    # Cigarrillos
    ('Cigarrillos', 'Marlboro Box',          2200, 3500,  45, True,  '#E60000', 'fa-smoking'),
    ('Cigarrillos', 'Philip Morris Box',     1900, 3200,  38, True,  '#003D80', 'fa-smoking'),
    ('Cigarrillos', 'Camel Box',             2100, 3400,  20, False, '#F59100', 'fa-smoking'),
    ('Cigarrillos', 'Lucky Strike',          2000, 3300,  15, False, '#A52A2A', 'fa-smoking'),

    # Lacteos / Helados
    ('Lacteos', 'Yogur Ser 200g',             450,  750,  18, False, '#FFC1CC', 'fa-mug-saucer'),
    ('Lacteos', 'Helado Cucurucho Frigor',    700, 1200,  30, True,  '#FF69B4', 'fa-ice-cream'),

    # Cafeteria / panificados
    ('Cafeteria', 'Cafe Nescafe Sobre',       300,  500,  60, False, '#6F4E37', 'fa-mug-hot'),
    ('Cafeteria', 'Medialuna Manteca',        300,  550,  40, True,  '#D4A373', 'fa-bread-slice'),
    ('Cafeteria', 'Tostado Jamon y Queso',    900, 1600,  15, False, '#E2A766', 'fa-bread-slice'),
]


CATEGORY_COLORS = {
    'Bebidas':    '#0066CC',
    'Golosinas':  '#E91E63',
    'Chocolates': '#5D2606',
    'Snacks':     '#FF9800',
    'Cigarrillos':'#616161',
    'Lacteos':    '#80DEEA',
    'Cafeteria':  '#6F4E37',
}


class Command(BaseCommand):
    help = 'Carga productos tipicos de kiosco argentino y genera ventas demo.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Borra los productos demo (TestProd, Quick Test, etc.) antes de cargar.',
        )
        parser.add_argument(
            '--no-sales',
            action='store_true',
            help='No genera transacciones simuladas (solo carga productos).',
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts['reset']:
            self._reset_test_data()

        self._load_categories()
        self._load_products()
        self._load_promotions()

        if not opts['no_sales']:
            self._simulate_sales()

        self.stdout.write(self.style.SUCCESS('Datos demo cargados correctamente.'))

    def _reset_test_data(self):
        """
        Desactiva (no borra) productos test para que no aparezcan en POS ni
        listados. Borrar directamente falla por FKs protegidas (PurchaseItem,
        POSTransactionItem).
        """
        updated = Product.objects.filter(
            name__regex=r'(?i)(test|qa|prueba|quick|mix test)'
        ).update(is_active=False, is_quick_access=False)
        self.stdout.write(f'  Desactivados {updated} productos de test.')

        ProductCategory.objects.filter(
            name__regex=r'(?i)^(test|qa|testcat|test category)',
        ).update(is_active=False)

    def _load_categories(self):
        for name, color in CATEGORY_COLORS.items():
            cat, created = ProductCategory.objects.get_or_create(
                name=name,
                defaults={'color': color, 'default_margin_percent': Decimal('40.00')},
            )
            if created:
                self.stdout.write(f'  Categoria "{name}" creada.')

    def _load_products(self):
        for i, row in enumerate(PRODUCTS, start=1):
            cat_name, name, p_buy, p_sell, stock, quick, color, icon = row
            cat = ProductCategory.objects.get(name=cat_name)
            sku = f'KIO-{i:04d}'
            barcode = f'779{1000000000 + i:010d}'[:13]

            product, created = Product.objects.update_or_create(
                name=name,
                defaults={
                    'sku': sku,
                    'barcode': barcode,
                    'category': cat,
                    'purchase_price': Decimal(str(p_buy)),
                    'sale_price': Decimal(str(p_sell)),
                    'cost_price': Decimal(str(p_buy)),
                    'current_stock': Decimal(str(stock)),
                    'min_stock': 5,
                    'is_active': True,
                    'is_quick_access': quick,
                    'quick_access_color': color,
                    'quick_access_icon': icon,
                    'quick_access_position': i if quick else 0,
                },
            )
            if created:
                self.stdout.write(f'  + {name}')

    def _load_promotions(self):
        Promotion.objects.filter(name__startswith='[Demo]').delete()

        # 2x1 en alfajores
        alfajores = Product.objects.filter(name__icontains='Alfajor')
        if alfajores.exists():
            promo = Promotion.objects.create(
                name='[Demo] 2x1 en Alfajores Jorgito',
                description='Llevando 2 alfajores Jorgito Triple, pagas solo 1.',
                promo_type='nxm',
                status='active',
                priority=80,
                quantity_required=2,
                quantity_charged=1,
                applies_to_packaging_type='unit',
                start_date=date.today() - timedelta(days=2),
                end_date=date.today() + timedelta(days=30),
            )
            for p in alfajores.filter(name__icontains='Jorgito'):
                PromotionProduct.objects.create(promotion=promo, product=p)
            self.stdout.write('  + Promo 2x1 alfajores creada.')

        # 3x2 en gaseosas chicas
        gaseosa_chica = Product.objects.filter(name__icontains='Coca Cola 500ml').first()
        if gaseosa_chica:
            promo = Promotion.objects.create(
                name='[Demo] 3x2 en Coca Cola 500ml',
                description='Llevando 3 Coca Cola 500ml pagas solo 2.',
                promo_type='nxm',
                status='active',
                priority=70,
                quantity_required=3,
                quantity_charged=2,
                applies_to_packaging_type='unit',
                start_date=date.today() - timedelta(days=5),
                end_date=date.today() + timedelta(days=30),
            )
            PromotionProduct.objects.create(promotion=promo, product=gaseosa_chica)
            self.stdout.write('  + Promo 3x2 Coca 500ml creada.')

        # Combo medialuna + cafe
        medialuna = Product.objects.filter(name__icontains='Medialuna').first()
        cafe = Product.objects.filter(name__icontains='Cafe').first()
        if medialuna and cafe:
            promo = Promotion.objects.create(
                name='[Demo] Combo Cafe + Medialuna',
                description='Cafe Nescafe + Medialuna manteca a precio especial.',
                promo_type='combo',
                status='active',
                priority=60,
                applies_to_packaging_type='unit',
                final_price=Decimal('900.00'),
                start_date=date.today() - timedelta(days=1),
                end_date=date.today() + timedelta(days=30),
            )
            PromotionProduct.objects.create(promotion=promo, product=medialuna)
            PromotionProduct.objects.create(promotion=promo, product=cafe)
            self.stdout.write('  + Promo combo cafe + medialuna creada.')

        # Descuento porcentual en cigarrillos premium
        marlboro = Product.objects.filter(name__icontains='Marlboro').first()
        if marlboro:
            promo = Promotion.objects.create(
                name='[Demo] 10% off Marlboro',
                description='10 por ciento de descuento en Marlboro Box.',
                promo_type='simple_discount',
                status='active',
                priority=40,
                applies_to_packaging_type='unit',
                discount_percent=Decimal('10.00'),
                start_date=date.today() - timedelta(days=3),
                end_date=date.today() + timedelta(days=30),
            )
            PromotionProduct.objects.create(promotion=promo, product=marlboro)
            self.stdout.write('  + Promo 10% Marlboro creada.')

    def _simulate_sales(self):
        """
        Crea transacciones simuladas de los ultimos 7 dias para que el dashboard
        tenga datos reales para mostrar. Las transacciones son livianas: usan
        modelos directos sin pasar por la maquina de checkout (suficiente para
        capturas, no para metricas exactas).
        """
        try:
            from cashregister.models import CashShift, CashRegister
            from pos.models import POSSession, POSTransaction, POSTransactionItem
            from accounts.models import User
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  No se pudo simular ventas: {e}'))
            return

        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            self.stdout.write(self.style.WARNING('  Sin superuser, no se simulan ventas.'))
            return

        # Limpiar transacciones demo previas
        POSTransaction.objects.filter(notes__startswith='[demo-seed]').delete()

        register = CashRegister.objects.first()
        if not register:
            self.stdout.write(self.style.WARNING('  Sin caja registradora configurada, salto simulacion.'))
            return

        products = list(Product.objects.filter(is_active=True, current_stock__gt=0))
        if not products:
            return

        now = timezone.now()
        ticket_seq = 0

        for days_ago in range(7, -1, -1):
            day = now - timedelta(days=days_ago)
            num_sales = random.randint(8, 22)

            shift = CashShift.objects.create(
                cash_register=register,
                cashier=admin,
                initial_amount=Decimal('5000.00'),
                opened_at=day.replace(hour=8, minute=0),
                status='closed' if days_ago > 0 else 'active',
                closed_at=day.replace(hour=22, minute=0) if days_ago > 0 else None,
                actual_amount=Decimal('25000.00') if days_ago > 0 else Decimal('0.00'),
            )
            session = POSSession.objects.create(cash_shift=shift, status='closed' if days_ago > 0 else 'active')

            for _ in range(num_sales):
                ticket_seq += 1
                items_in_sale = random.randint(1, 4)
                txn = POSTransaction.objects.create(
                    session=session,
                    ticket_number=f'CAJA-01-{day.strftime("%Y%m%d")}-{ticket_seq:04d}',
                    status='completed',
                    transaction_type='sale',
                    completed_at=day.replace(hour=random.randint(9, 21), minute=random.randint(0, 59)),
                    notes='[demo-seed]',
                )
                subtotal = Decimal('0')
                for _ in range(items_in_sale):
                    p = random.choice(products)
                    qty = Decimal(str(random.randint(1, 3)))
                    item = POSTransactionItem.objects.create(
                        transaction=txn,
                        product=p,
                        quantity=qty,
                        unit_price=p.sale_price,
                        unit_cost=p.purchase_price,
                    )
                    subtotal += item.subtotal

                txn.subtotal = subtotal
                txn.total = subtotal
                txn.amount_paid = subtotal
                txn.items_count = items_in_sale
                txn.save()

        self.stdout.write(f'  Generadas ~{ticket_seq} transacciones de demo en los ultimos 8 dias.')
