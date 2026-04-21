"""
Management Command to create sample products
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
import random

from stocks.models import Product, ProductCategory, UnitOfMeasure


class Command(BaseCommand):
    help = 'Create sample products for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample products...\n')
        
        # Get categories and units
        unit = UnitOfMeasure.objects.filter(abbreviation='u').first()
        kg = UnitOfMeasure.objects.filter(abbreviation='kg').first()
        liter = UnitOfMeasure.objects.filter(abbreviation='L').first()
        
        if not unit:
            self.stdout.write(self.style.ERROR('Run init_data first!'))
            return
        
        products_data = [
            # Almacén
            {'name': 'Arroz Largo Fino 1kg', 'category': 'Almacén', 'cost': 800, 'price': 1200, 'unit': unit, 'barcode': '7790001000001'},
            {'name': 'Fideos Tallarines 500g', 'category': 'Almacén', 'cost': 400, 'price': 650, 'unit': unit, 'barcode': '7790001000002'},
            {'name': 'Aceite Girasol 1.5L', 'category': 'Almacén', 'cost': 1200, 'price': 1850, 'unit': unit, 'barcode': '7790001000003'},
            {'name': 'Azúcar 1kg', 'category': 'Almacén', 'cost': 500, 'price': 750, 'unit': unit, 'barcode': '7790001000004'},
            {'name': 'Harina 000 1kg', 'category': 'Almacén', 'cost': 350, 'price': 550, 'unit': unit, 'barcode': '7790001000005'},
            
            # Bebidas
            {'name': 'Coca Cola 2.25L', 'category': 'Bebidas', 'cost': 1500, 'price': 2200, 'unit': unit, 'barcode': '7790002000001'},
            {'name': 'Agua Mineral 2L', 'category': 'Bebidas', 'cost': 400, 'price': 650, 'unit': unit, 'barcode': '7790002000002'},
            {'name': 'Cerveza Quilmes 1L', 'category': 'Bebidas', 'cost': 800, 'price': 1300, 'unit': unit, 'barcode': '7790002000003'},
            {'name': 'Fanta 2.25L', 'category': 'Bebidas', 'cost': 1400, 'price': 2100, 'unit': unit, 'barcode': '7790002000004'},
            {'name': 'Vino Tinto 750ml', 'category': 'Bebidas', 'cost': 1000, 'price': 1600, 'unit': unit, 'barcode': '7790002000005'},
            
            # Lácteos
            {'name': 'Leche Entera 1L', 'category': 'Lácteos', 'cost': 600, 'price': 950, 'unit': unit, 'barcode': '7790003000001'},
            {'name': 'Yogur Firme 190g', 'category': 'Lácteos', 'cost': 250, 'price': 420, 'unit': unit, 'barcode': '7790003000002'},
            {'name': 'Queso Cremoso 1kg', 'category': 'Lácteos', 'cost': 3500, 'price': 5200, 'unit': kg, 'barcode': '7790003000003'},
            {'name': 'Manteca 200g', 'category': 'Lácteos', 'cost': 800, 'price': 1250, 'unit': unit, 'barcode': '7790003000004'},
            {'name': 'Dulce de Leche 400g', 'category': 'Lácteos', 'cost': 700, 'price': 1100, 'unit': unit, 'barcode': '7790003000005'},
            
            # Golosinas
            {'name': 'Chocolate Milka 150g', 'category': 'Golosinas', 'cost': 600, 'price': 950, 'unit': unit, 'barcode': '7790011000001'},
            {'name': 'Galletitas Oreo 118g', 'category': 'Golosinas', 'cost': 400, 'price': 680, 'unit': unit, 'barcode': '7790011000002'},
            {'name': 'Alfajor Triple 70g', 'category': 'Golosinas', 'cost': 250, 'price': 450, 'unit': unit, 'barcode': '7790011000003'},
            {'name': 'Chicles Beldent x10', 'category': 'Golosinas', 'cost': 150, 'price': 280, 'unit': unit, 'barcode': '7790011000004'},
            {'name': 'Caramelos Surtidos 500g', 'category': 'Golosinas', 'cost': 500, 'price': 850, 'unit': unit, 'barcode': '7790011000005'},
            
            # Limpieza
            {'name': 'Detergente 750ml', 'category': 'Limpieza', 'cost': 400, 'price': 680, 'unit': unit, 'barcode': '7790009000001'},
            {'name': 'Lavandina 2L', 'category': 'Limpieza', 'cost': 350, 'price': 580, 'unit': unit, 'barcode': '7790009000002'},
            {'name': 'Papel Higiénico x4', 'category': 'Limpieza', 'cost': 600, 'price': 950, 'unit': unit, 'barcode': '7790009000003'},
            {'name': 'Jabón en Polvo 800g', 'category': 'Limpieza', 'cost': 900, 'price': 1450, 'unit': unit, 'barcode': '7790009000004'},
            {'name': 'Esponja Multiuso', 'category': 'Limpieza', 'cost': 150, 'price': 280, 'unit': unit, 'barcode': '7790009000005'},
        ]
        
        created_count = 0
        for data in products_data:
            category = ProductCategory.objects.filter(name=data['category']).first()
            
            product, created = Product.objects.get_or_create(
                barcode=data['barcode'],
                defaults={
                    'name': data['name'],
                    'category': category,
                    'unit_of_measure': data['unit'],
                    'cost_price': Decimal(str(data['cost'])),
                    'purchase_price': Decimal(str(data['cost'])),
                    'sale_price': Decimal(str(data['price'])),
                    'current_stock': Decimal(str(random.randint(10, 100))),
                    'min_stock': Decimal('5'),
                    'max_stock': Decimal('100'),
                    'is_active': True,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ Created: {product.name}')
            else:
                self.stdout.write(f'  - Exists: {product.name}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Created {created_count} products!'))
