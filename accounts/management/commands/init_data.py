"""
Management Command to initialize default data for CHE GOLOSO
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from accounts.models import Role
from cashregister.models import PaymentMethod, CashRegister
from stocks.models import UnitOfMeasure, ProductCategory
from expenses.models import ExpenseCategory


class Command(BaseCommand):
    help = 'Initialize default data for Kiosco Pro system'

    def handle(self, *args, **options):
        self.stdout.write('Initializing Kiosco Pro data...\n')
        
        # Create roles
        self.create_roles()
        
        # Create payment methods
        self.create_payment_methods()
        
        # Create cash registers
        self.create_cash_registers()
        
        # Create units of measure
        self.create_units()
        
        # Create categories
        self.create_categories()

        # Create expense categories
        self.create_expense_categories()

        self.stdout.write(self.style.SUCCESS('\n[OK] Data initialization complete!'))

    def create_roles(self):
        """Create default roles with permissions."""
        self.stdout.write('Creating roles...')
        
        roles = [
            ('Admin', 'Administrador - Acceso total'),
            ('Cajero Manager', 'Cajero Manager - POS, Caja, Inventario, Promociones, Cartelería'),
            ('Cashier', 'Cajero - POS y caja'),
        ]
        
        for name, description in roles:
            role, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(f'  ✓ Created role: {name}')
            else:
                self.stdout.write(f'  - Role exists: {name}')

    def create_payment_methods(self):
        """Create default payment methods."""
        self.stdout.write('Creating payment methods...')
        
        methods = [
            {'code': 'cash', 'name': 'Efectivo', 'is_cash': True, 'icon': 'fas fa-money-bill-wave', 'position': 1},
            {'code': 'debit', 'name': 'Débito', 'is_cash': False, 'icon': 'fas fa-credit-card', 'position': 2},
            {'code': 'credit', 'name': 'Crédito', 'is_cash': False, 'icon': 'fas fa-credit-card', 'position': 3},
            {'code': 'transfer', 'name': 'Transferencia', 'is_cash': False, 'icon': 'fas fa-building-columns', 'position': 4},
            {'code': 'mercadopago', 'name': 'MercadoPago QR', 'is_cash': False, 'icon': 'fas fa-qrcode', 'position': 5},
            {'code': 'tarjeta_mp', 'name': 'Tarjeta (Point)', 'is_cash': False, 'icon': 'fas fa-credit-card', 'position': 6},
        ]
        
        for method_data in methods:
            method, created = PaymentMethod.objects.get_or_create(
                code=method_data['code'],
                defaults=method_data
            )
            if created:
                self.stdout.write(f'  ✓ Created payment method: {method.name}')
            else:
                # Update name, icon, and position on existing methods
                updated_fields = []
                if method.icon != method_data['icon']:
                    method.icon = method_data['icon']
                    updated_fields.append('icon')
                if method.name != method_data['name']:
                    method.name = method_data['name']
                    updated_fields.append('name')
                if method.position != method_data['position']:
                    method.position = method_data['position']
                    updated_fields.append('position')
                if updated_fields:
                    method.save(update_fields=updated_fields)
                    self.stdout.write(f'  ↻ Updated {", ".join(updated_fields)} for: {method.name}')
                else:
                    self.stdout.write(f'  - Payment method exists: {method.name}')

    def create_cash_registers(self):
        """Create default cash registers."""
        self.stdout.write('Creating cash registers...')
        
        registers = [
            {'code': 'CAJA-01', 'name': 'Caja Principal', 'location': 'Entrada'},
            {'code': 'CAJA-02', 'name': 'Caja Secundaria', 'location': 'Pasillo Central'},
        ]
        
        for register_data in registers:
            register, created = CashRegister.objects.get_or_create(
                code=register_data['code'],
                defaults=register_data
            )
            if created:
                self.stdout.write(f'  ✓ Created cash register: {register.code}')
            else:
                self.stdout.write(f'  - Cash register exists: {register.code}')

    def create_units(self):
        """Create default units of measure."""
        self.stdout.write('Creating units of measure...')
        
        units = [
            {'name': 'Unidad', 'abbreviation': 'u', 'symbol': 'u', 'unit_type': 'unit'},
            {'name': 'Kilogramo', 'abbreviation': 'kg', 'symbol': 'kg', 'unit_type': 'weight'},
            {'name': 'Gramo', 'abbreviation': 'g', 'symbol': 'g', 'unit_type': 'weight'},
            {'name': 'Litro', 'abbreviation': 'L', 'symbol': 'L', 'unit_type': 'volume'},
            {'name': 'Mililitro', 'abbreviation': 'ml', 'symbol': 'ml', 'unit_type': 'volume'},
            {'name': 'Metro', 'abbreviation': 'm', 'symbol': 'm', 'unit_type': 'length'},
            {'name': 'Centímetro', 'abbreviation': 'cm', 'symbol': 'cm', 'unit_type': 'length'},
            {'name': 'Docena', 'abbreviation': 'doc', 'symbol': 'doc', 'unit_type': 'unit'},
            {'name': 'Paquete', 'abbreviation': 'paq', 'symbol': 'paq', 'unit_type': 'unit'},
            {'name': 'Caja', 'abbreviation': 'caja', 'symbol': 'caja', 'unit_type': 'unit'},
        ]
        
        for unit_data in units:
            unit, created = UnitOfMeasure.objects.get_or_create(
                name=unit_data['name'],
                defaults=unit_data
            )
            if created:
                self.stdout.write(f'  ✓ Created unit: {unit.name}')
            else:
                self.stdout.write(f'  - Unit exists: {unit.name}')

    def create_categories(self):
        """Create default product categories."""
        self.stdout.write('  - Categorías: se crean desde el sistema, no por defecto.')

    def create_expense_categories(self):
        """Create default expense categories."""
        self.stdout.write('Creating expense categories...')
        categories = [
            {'name': 'Proveedores', 'description': 'Pagos a proveedores por compras de mercadería', 'color': '#2D1E5F'},
            {'name': 'Servicios', 'description': 'Electricidad, agua, internet, etc.', 'color': '#17a2b8'},
            {'name': 'Personal', 'description': 'Sueldos y gastos de personal', 'color': '#28a745'},
            {'name': 'Varios', 'description': 'Otros gastos', 'color': '#6c757d'},
        ]
        for cat_data in categories:
            cat, created = ExpenseCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data,
            )
            if created:
                self.stdout.write(f'  ✓ Created expense category: {cat.name}')
            else:
                self.stdout.write(f'  - Expense category exists: {cat.name}')
