"""
Management command to load sample kiosk products for testing.
Run with: python manage.py load_kiosko_products
"""
from django.core.management.base import BaseCommand
from stocks.models import Product, ProductCategory, UnitOfMeasure
from decimal import Decimal


PRODUCTS = [
    # (name, barcode, sku, category, sale_price, purchase_price, stock, is_quick_access, color, icon)

    # === GASEOSAS ===
    ('Coca Cola 500ml', '7790895000063', 'GAS-001', 'Gaseosas', 1200, 750, 48, True, '#e74c3c', 'fa-bottle-water'),
    ('Coca Cola 1.5L', '7790895000087', 'GAS-002', 'Gaseosas', 2200, 1400, 24, True, '#c0392b', 'fa-bottle-water'),
    ('Pepsi 500ml', '7791813420138', 'GAS-003', 'Gaseosas', 1100, 700, 36, False, '#3498db', 'fa-bottle-water'),
    ('Fanta Naranja 500ml', '7790895003033', 'GAS-004', 'Gaseosas', 1100, 700, 24, False, '#e67e22', 'fa-bottle-water'),
    ('Sprite 500ml', '7790895002050', 'GAS-005', 'Gaseosas', 1100, 700, 24, False, '#2ecc71', 'fa-bottle-water'),
    ('7UP 500ml', '7791813410023', 'GAS-006', 'Gaseosas', 1100, 700, 24, False, '#27ae60', 'fa-bottle-water'),
    ('Manaos Cola 2.25L', '7790040000021', 'GAS-007', 'Gaseosas', 1800, 1100, 36, True, '#8e44ad', 'fa-bottle-water'),
    ('Manaos Naranja 2.25L', '7790040000038', 'GAS-008', 'Gaseosas', 1800, 1100, 24, False, '#e67e22', 'fa-bottle-water'),

    # === AGUAS Y JUGOS ===
    ('Agua Mineral 500ml', '7798062540017', 'AGU-001', 'Aguas y Jugos', 800, 450, 60, True, '#3498db', 'fa-droplet'),
    ('Agua Mineral 1.5L', '7798062540024', 'AGU-002', 'Aguas y Jugos', 1400, 850, 36, False, '#2980b9', 'fa-droplet'),
    ('Jugo Baggio Naranja 200ml', '7790580014012', 'AGU-003', 'Aguas y Jugos', 700, 420, 48, True, '#f39c12', 'fa-wine-glass'),
    ('Jugo Baggio Durazno 200ml', '7790580014029', 'AGU-004', 'Aguas y Jugos', 700, 420, 48, False, '#e67e22', 'fa-wine-glass'),
    ('Vitaminagua 500ml', '7790040000052', 'AGU-005', 'Aguas y Jugos', 1200, 750, 24, False, '#1abc9c', 'fa-droplet'),

    # === SNACKS Y PAPAS ===
    ('Papas Lay\'s 100g', '7790560001084', 'SNK-001', 'Snacks', 1500, 950, 30, True, '#f1c40f', 'fa-bag-shopping'),
    ('Papas Lay\'s 30g', '7790560001015', 'SNK-002', 'Snacks', 600, 380, 60, True, '#f1c40f', 'fa-bag-shopping'),
    ('Papas Pringles Original 40g', '8710398502339', 'SNK-003', 'Snacks', 900, 580, 36, False, '#e74c3c', 'fa-bag-shopping'),
    ('Cheetos 50g', '7792977001135', 'SNK-004', 'Snacks', 700, 440, 36, False, '#e67e22', 'fa-bag-shopping'),
    ('Doritos 100g', '7790580116084', 'SNK-005', 'Snacks', 1400, 880, 24, False, '#c0392b', 'fa-bag-shopping'),
    ('Maní con Chocolate 30g', '7798000531084', 'SNK-006', 'Snacks', 500, 300, 60, False, '#8b4513', 'fa-bag-shopping'),

    # === ALFAJORES Y GOLOSINAS ===
    ('Alfajor Milka Triple', '7622210004093', 'GOL-001', 'Golosinas', 1200, 750, 48, True, '#8e44ad', 'fa-cookie'),
    ('Alfajor Oreo', '7622210005014', 'GOL-002', 'Golosinas', 1100, 680, 48, True, '#2c3e50', 'fa-cookie'),
    ('Alfajor Jorgito', '7790580100670', 'GOL-003', 'Golosinas', 800, 480, 60, True, '#e67e22', 'fa-cookie'),
    ('Alfajor Havanna Blanco', '7798023410016', 'GOL-004', 'Golosinas', 1800, 1100, 24, False, '#ecf0f1', 'fa-cookie'),
    ('Alfajor Havanna Chocolate', '7798023410023', 'GOL-005', 'Golosinas', 1800, 1100, 24, False, '#795548', 'fa-cookie'),
    ('Caja 12 Alfajores Jorgito', '7790580101135', 'GOL-006', 'Golosinas', 8500, 5500, 10, False, '#e67e22', 'fa-box'),
    ('Chocolatín Jack 30g', '7790580001609', 'GOL-007', 'Golosinas', 700, 420, 60, False, '#795548', 'fa-candy-cane'),
    ('Bon o Bon 16g', '7790580024158', 'GOL-008', 'Golosinas', 500, 300, 100, True, '#f39c12', 'fa-candy-cane'),
    ('Chupetín Pico Dulce', '7790580010014', 'GOL-009', 'Golosinas', 300, 170, 100, False, '#e91e63', 'fa-candy-cane'),
    ('Gomitas Fini 100g', '8410525025144', 'GOL-010', 'Golosinas', 1200, 750, 30, False, '#9b59b6', 'fa-candy-cane'),
    ('Caramelos Mentitas', '7790580007014', 'GOL-011', 'Golosinas', 400, 240, 80, False, '#1abc9c', 'fa-candy-cane'),
    ('Chicles Beldent Menta', '7622210004383', 'GOL-012', 'Golosinas', 600, 370, 60, False, '#2ecc71', 'fa-candy-cane'),

    # === CIGARRILLOS ===
    ('Marlboro Rojo x20', '0070272001034', 'CIG-001', 'Cigarrillos', 4500, 3800, 30, True, '#e74c3c', 'fa-smoking'),
    ('Marlboro Gold x20', '0070272001041', 'CIG-002', 'Cigarrillos', 4500, 3800, 30, True, '#f39c12', 'fa-smoking'),
    ('Camel x20', '0050011121134', 'CIG-003', 'Cigarrillos', 4200, 3500, 20, False, '#f1c40f', 'fa-smoking'),
    ('Derby x20', '7790501010019', 'CIG-004', 'Cigarrillos', 3800, 3100, 20, False, '#7f8c8d', 'fa-smoking'),
    ('Philip Morris x20', '0028400005578', 'CIG-005', 'Cigarrillos', 4000, 3300, 20, False, '#e67e22', 'fa-smoking'),

    # === LÁCTEOS Y BEBIDAS FRÍAS ===
    ('Leche La Serenísima Entera 1L', '7790070000059', 'LAC-001', 'Lácteos', 1800, 1350, 24, False, '#ecf0f1', 'fa-bottle-water'),
    ('Yogur Activia Natural 190g', '7790110002122', 'LAC-002', 'Lácteos', 900, 600, 20, False, '#fff9c4', 'fa-jar'),
    ('Queso Rallado Finlandia 70g', '7790110065010', 'LAC-003', 'Lácteos', 1200, 800, 15, False, '#f39c12', 'fa-jar'),
    ('Manteca La Serenísima 200g', '7790070001018', 'LAC-004', 'Lácteos', 2200, 1700, 12, False, '#f1c40f', 'fa-butter'),

    # === PANADERÍA Y GALLETITAS ===
    ('Galletitas Oreo 117g', '7622210900014', 'PAN-001', 'Galletitas', 1200, 780, 30, True, '#2c3e50', 'fa-cookie-bite'),
    ('Galletitas Bagley Surtidas 500g', '7790040005019', 'PAN-002', 'Galletitas', 2800, 1800, 20, False, '#e67e22', 'fa-cookie-bite'),
    ('Facturas (c/u)', '0000000000001', 'PAN-003', 'Panadería', 600, 300, 50, True, '#f39c12', 'fa-bread-slice'),
    ('Medialunas x6', '0000000000002', 'PAN-004', 'Panadería', 2500, 1400, 20, True, '#f39c12', 'fa-bread-slice'),
    ('Pan Bimbo Blanco 400g', '7790580063075', 'PAN-005', 'Panadería', 2200, 1500, 15, False, '#fff9c4', 'fa-bread-slice'),
    ('Pan de Molde Fargo 440g', '7790040031018', 'PAN-006', 'Panadería', 2400, 1600, 15, False, '#fff9c4', 'fa-bread-slice'),

    # === CONFITERÍA / SANDWICH ===
    ('Sándwich Jamón y Queso', '0000000000010', 'CONF-001', 'Confitería', 2500, 1200, 10, True, '#f39c12', 'fa-burger'),
    ('Tostado de Miga', '0000000000011', 'CONF-002', 'Confitería', 3000, 1500, 10, True, '#e67e22', 'fa-burger'),
    ('Empanada (c/u)', '0000000000012', 'CONF-003', 'Confitería', 1200, 600, 20, True, '#c0392b', 'fa-drumstick-bite'),

    # === LIMPIEZA E HIGIENE ===
    ('Jabón Dove 90g', '7791293013012', 'LIM-001', 'Higiene Personal', 1800, 1200, 20, False, '#3498db', 'fa-pump-soap'),
    ('Shampoo Head & Shoulders 90ml', '7500435141383', 'LIM-002', 'Higiene Personal', 2500, 1700, 12, False, '#2980b9', 'fa-pump-soap'),
    ('Desodorante Rexona 90ml', '7791293002047', 'LIM-003', 'Higiene Personal', 3200, 2200, 12, False, '#27ae60', 'fa-spray-can'),
    ('Pañuelos Kleenex x10', '0078800000010', 'LIM-004', 'Higiene Personal', 700, 450, 30, False, '#ecf0f1', 'fa-tissue'),

    # === VARIOS / MISC ===
    ('Preservativos Tulipan x3', '7791204001019', 'VAR-001', 'Varios', 2500, 1600, 20, False, '#e74c3c', 'fa-shield'),
    ('Pilas AA Energizer x2', '0039800042699', 'VAR-002', 'Varios', 2800, 1900, 15, False, '#27ae60', 'fa-battery-full'),
    ('Encendedor BIC', '0070501001502', 'VAR-003', 'Varios', 1500, 900, 30, True, '#e74c3c', 'fa-fire'),
    ('Tarjeta SUBE (recarga)', '0000000000099', 'VAR-004', 'Varios', 1000, 1000, 999, False, '#3498db', 'fa-credit-card'),
]

CATEGORIES = [
    ('Gaseosas', '#e74c3c', 30),
    ('Aguas y Jugos', '#3498db', 35),
    ('Snacks', '#f1c40f', 40),
    ('Golosinas', '#9b59b6', 45),
    ('Cigarrillos', '#7f8c8d', 20),
    ('Lácteos', '#ecf0f1', 30),
    ('Galletitas', '#e67e22', 40),
    ('Panadería', '#f39c12', 50),
    ('Confitería', '#e67e22', 60),
    ('Higiene Personal', '#2ecc71', 35),
    ('Varios', '#95a5a6', 40),
]


class Command(BaseCommand):
    help = 'Carga productos de kiosco de ejemplo para testear el POS. Seguro de ejecutar múltiples veces.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Eliminar todos los productos existentes antes de cargar',
        )

    def handle(self, *args, **options):
        if options['clear']:
            count = Product.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f'  Eliminados {count} registros existentes.'))

        # Get or create unit
        unit, _ = UnitOfMeasure.objects.get_or_create(
            abbreviation='u',
            defaults={'name': 'Unidad', 'symbol': 'u', 'unit_type': 'unit'}
        )

        # Create categories
        self.stdout.write('Creando categorías...')
        categories = {}
        for cat_name, color, margin in CATEGORIES:
            cat, created = ProductCategory.objects.get_or_create(
                name=cat_name,
                defaults={'color': color, 'default_margin_percent': margin}
            )
            categories[cat_name] = cat
            status = '✓ creada' if created else '· existe'
            self.stdout.write(f'  {status}: {cat_name}')

        # Create products
        self.stdout.write('\nCargando productos...')
        created_count = 0
        updated_count = 0

        for i, (name, barcode, sku, cat_name, sale_price, purchase_price, stock, quick_access, color, icon) in enumerate(PRODUCTS):
            cat = categories.get(cat_name)
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name,
                    'barcode': barcode,
                    'category': cat,
                    'unit_of_measure': unit,
                    'sale_price': Decimal(str(sale_price)),
                    'purchase_price': Decimal(str(purchase_price)),
                    'cost_price': Decimal(str(purchase_price)),
                    'current_stock': Decimal(str(stock)),
                    'min_stock': 5,
                    'is_active': True,
                    'is_quick_access': quick_access,
                    'quick_access_color': color,
                    'quick_access_icon': icon,
                    'quick_access_position': i + 1,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ {name} - ${sale_price:,}')
            else:
                # Update price and stock if exists
                product.sale_price = Decimal(str(sale_price))
                product.current_stock = Decimal(str(stock))
                product.is_quick_access = quick_access
                product.save(update_fields=['sale_price', 'current_stock', 'is_quick_access'])
                updated_count += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'✅ Listo! {created_count} productos creados, {updated_count} actualizados.'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'   {Product.objects.filter(is_active=True).count()} productos activos en total.'
        ))
        quick_count = Product.objects.filter(is_quick_access=True).count()
        self.stdout.write(self.style.SUCCESS(
            f'   {quick_count} productos con acceso rápido en el POS.'
        ))
