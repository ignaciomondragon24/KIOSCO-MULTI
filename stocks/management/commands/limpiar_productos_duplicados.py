"""
Lista/desactiva Products cuyo barcode coincide con un ProductPackaging.barcode
de OTRO producto. Caso tipico: un viejo Product "Belden menta verde 20u"
independiente y el nuevo ProductPackaging display del Product "Belden menta 10g"
comparten el mismo EAN-13 — el POS encuentra el Product viejo y nunca llega al
empaque, rompiendo precio y stock.

Uso:
    python manage.py limpiar_productos_duplicados           # solo listar
    python manage.py limpiar_productos_duplicados --apply   # desactivar (soft-delete)
"""
from django.core.management.base import BaseCommand
from stocks.models import Product, ProductPackaging


class Command(BaseCommand):
    help = 'Lista o desactiva Products duplicados con barcode de algun ProductPackaging de otro producto.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Desactiva (is_active=False) los Products duplicados. Sin esta flag, solo lista.',
        )

    def handle(self, *args, **opts):
        apply_changes = opts['apply']

        # Mapa barcode -> packaging activo (de producto activo). Si hay colision
        # entre dos packagings (imposible con la validacion nueva, pero por las dudas)
        # nos quedamos con el primero.
        packaging_by_barcode = {}
        for pkg in ProductPackaging.objects.filter(
            is_active=True, product__is_active=True
        ).exclude(barcode='').exclude(barcode__isnull=True).select_related('product'):
            packaging_by_barcode.setdefault(pkg.barcode, pkg)

        duplicates = []
        for prod in Product.objects.exclude(barcode='').exclude(barcode__isnull=True):
            pkg = packaging_by_barcode.get(prod.barcode)
            if pkg and pkg.product_id != prod.pk:
                duplicates.append((prod, pkg))

        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No hay Products duplicados con barcode de empaque.'))
            return

        self.stdout.write(self.style.WARNING(f'Encontrados {len(duplicates)} Products duplicados:'))
        self.stdout.write('')
        for prod, pkg in duplicates:
            self.stdout.write(
                f'  [Product {prod.pk}] "{prod.name}" (SKU {prod.sku}, stock {prod.current_stock}) '
                f'--> choca con empaque "{pkg.name}" ({pkg.get_packaging_type_display()}) '
                f'del producto "{pkg.product.name}" (id {pkg.product_id})'
            )

        if not apply_changes:
            self.stdout.write('')
            self.stdout.write(self.style.NOTICE(
                'Correlo con --apply para desactivarlos (soft-delete, is_active=False).'
            ))
            return

        self.stdout.write('')
        desactivados = 0
        for prod, _ in duplicates:
            prod.is_active = False
            prod.save(update_fields=['is_active'])
            desactivados += 1
        self.stdout.write(self.style.SUCCESS(
            f'Desactivados {desactivados} Products duplicados. '
            f'El stock que tenian NO se migro — revisar manualmente si alguno tenia stock real.'
        ))
