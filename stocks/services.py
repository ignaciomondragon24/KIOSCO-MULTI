"""
Stock Management Services
"""
from decimal import Decimal
from django.db import transaction
from .models import Product, StockMovement, ProductPackaging


class StockManagementService:
    """Service for managing product stock."""
    
    @staticmethod
    @transaction.atomic
    def add_stock(product, quantity, cost=None, reference='', reference_id=None, notes='', user=None):
        """
        Add stock to a product.

        Args:
            product: Product instance
            quantity: Quantity to add (positive)
            cost: Unit cost (optional)
            reference: Reference string
            reference_id: Reference ID
            notes: Additional notes
            user: User performing the action

        Returns:
            StockMovement instance
        """
        # Lock the product row to prevent concurrent modifications
        product = Product.objects.select_for_update().get(pk=product.pk)

        quantity = Decimal(str(quantity))
        cost = Decimal(str(cost)) if cost else product.cost_price

        stock_before = product.current_stock
        stock_after = stock_before + quantity

        # Update product stock
        product.current_stock = stock_after

        # Update average cost if cost provided
        if cost and cost > 0:
            total_value = (product.cost_price * stock_before) + (cost * quantity)
            if stock_after > 0:
                product.cost_price = total_value / stock_after

        product.save()

        # Cascade into active packagings (mirror of deduct_stock_with_cascade)
        packagings = {
            p.packaging_type: p
            for p in product.packagings.filter(is_active=True).select_for_update()
        }
        unit_pkg = packagings.get('unit')
        if unit_pkg:
            unit_pkg.current_stock = unit_pkg.current_stock + quantity
            unit_pkg.save(update_fields=['current_stock'])
        display_pkg = packagings.get('display')
        if display_pkg and display_pkg.units_per_display > 0:
            display_pkg.current_stock = display_pkg.current_stock + (
                quantity / Decimal(str(display_pkg.units_per_display))
            )
            display_pkg.save(update_fields=['current_stock'])
        bulk_pkg = packagings.get('bulk')
        if bulk_pkg and bulk_pkg.units_quantity > 0:
            bulk_pkg.current_stock = bulk_pkg.current_stock + (
                quantity / Decimal(str(bulk_pkg.units_quantity))
            )
            bulk_pkg.save(update_fields=['current_stock'])

        # Create movement record
        movement = StockMovement.objects.create(
            product=product,
            movement_type='purchase',
            quantity=quantity,
            unit_cost=cost,
            stock_before=stock_before,
            stock_after=stock_after,
            reference=reference,
            reference_id=reference_id,
            notes=notes,
            created_by=user
        )

        return movement
    
    @staticmethod
    @transaction.atomic
    def deduct_stock(product, quantity, reference='', reference_id=None, notes='', user=None):
        """
        Deduct stock from a product (for sales).

        Args:
            product: Product instance
            quantity: Quantity to deduct (positive)
            reference: Reference string
            reference_id: Reference ID
            notes: Additional notes
            user: User performing the action

        Returns:
            tuple (success: bool, message: str, movement: StockMovement or None)
        """
        # Lock the product row to prevent concurrent modifications
        product = Product.objects.select_for_update().get(pk=product.pk)

        quantity = Decimal(str(quantity))
        stock_before = product.current_stock
        stock_after = stock_before - quantity
        
        # Allow negative stock with warning
        if stock_after < 0:
            notes += ' [ALERTA: Stock negativo]'
        
        # Update product stock
        product.current_stock = stock_after
        product.save()
        
        # Create movement record
        movement = StockMovement.objects.create(
            product=product,
            movement_type='sale',
            quantity=-quantity,  # Negative for deductions
            unit_cost=product.cost_price,
            stock_before=stock_before,
            stock_after=stock_after,
            reference=reference,
            reference_id=reference_id,
            notes=notes,
            created_by=user
        )
        
        # Auto-deduct from parent product (e.g., 20 cigarettes sold = 1 pack deducted)
        if product.parent_product and product.parent_product.units_per_package > 0:
            parent = Product.objects.select_for_update().get(pk=product.parent_product_id)
            parent_qty = quantity / Decimal(str(parent.units_per_package))
            parent_stock_before = parent.current_stock
            parent_stock_after = parent_stock_before - parent_qty
            
            parent_notes = f'Auto: venta de {quantity} {product.name}'
            if parent_stock_after < 0:
                parent_notes += ' [ALERTA: Stock negativo]'
            
            parent.current_stock = parent_stock_after
            parent.save()
            
            StockMovement.objects.create(
                product=parent,
                movement_type='sale',
                quantity=-parent_qty,
                unit_cost=parent.cost_price,
                stock_before=parent_stock_before,
                stock_after=parent_stock_after,
                reference=reference,
                reference_id=reference_id,
                notes=parent_notes,
                created_by=user
            )
        
        return True, 'Stock deducido correctamente', movement
    
    @staticmethod
    @transaction.atomic
    def adjust_stock(product, new_quantity, reason, user=None, notes=''):
        """
        Adjust stock to a specific quantity.

        Args:
            product: Product instance
            new_quantity: New stock quantity
            reason: Motivo del ajuste, e.g. "Robo / Pérdida", "Mercadería Dañada".
                    Se guarda en el campo `reference` del movimiento.
            user: User performing the action
            notes: Detalle libre del ajuste (descripción del incidente,
                   nro de cajas robadas, etc.). Se guarda en `notes`.

        Returns:
            StockMovement instance
        """
        # Lock the product row to prevent concurrent modifications
        product = Product.objects.select_for_update().get(pk=product.pk)

        new_quantity = Decimal(str(new_quantity))
        stock_before = product.current_stock
        difference = new_quantity - stock_before

        movement_type = 'adjustment_in' if difference >= 0 else 'adjustment_out'

        # Update product stock
        product.current_stock = new_quantity
        product.save()

        # Resync active packagings to the new total. Un ajuste manual es
        # una CORRECCIÓN: cada nivel se recalcula absoluto sobre el nuevo
        # stock, no con += diff. Si el packaging ya venía desincronizado
        # de un bug previo, esto lo repara en vez de arrastrar el error.
        packagings = {
            p.packaging_type: p
            for p in product.packagings.filter(is_active=True).select_for_update()
        }
        unit_pkg = packagings.get('unit')
        if unit_pkg:
            unit_pkg.current_stock = new_quantity
            unit_pkg.save(update_fields=['current_stock'])
        display_pkg = packagings.get('display')
        if display_pkg and display_pkg.units_per_display > 0:
            display_pkg.current_stock = new_quantity / Decimal(str(display_pkg.units_per_display))
            display_pkg.save(update_fields=['current_stock'])
        bulk_pkg = packagings.get('bulk')
        if bulk_pkg and bulk_pkg.units_quantity > 0:
            bulk_pkg.current_stock = new_quantity / Decimal(str(bulk_pkg.units_quantity))
            bulk_pkg.save(update_fields=['current_stock'])

        # Create movement record:
        # - reference = motivo legible (Robo, Rotura, Conteo físico, etc.)
        # - notes     = detalle libre del usuario
        movement = StockMovement.objects.create(
            product=product,
            movement_type=movement_type,
            quantity=difference,
            unit_cost=product.cost_price,
            stock_before=stock_before,
            stock_after=new_quantity,
            reference=reason or 'Ajuste de inventario',
            notes=notes or '',
            created_by=user
        )

        return movement
    
    @staticmethod
    def get_stock_value(cost_price=True):
        """
        Calculate total inventory value.
        
        Args:
            cost_price: If True, use cost price; otherwise use sale price
        
        Returns:
            Decimal total value
        """
        from django.db.models import Sum, F
        
        price_field = 'cost_price' if cost_price else 'sale_price'
        
        result = Product.objects.filter(
            is_active=True,
            current_stock__gt=0
        ).aggregate(
            total=Sum(F('current_stock') * F(price_field))
        )
        
        return result['total'] or Decimal('0.00')
    
    @staticmethod
    def get_low_stock_products(min_threshold=None):
        """
        Get products with low stock.
        
        Args:
            min_threshold: Override product's min_stock
        
        Returns:
            QuerySet of products
        """
        from django.db.models import F
        
        queryset = Product.objects.filter(is_active=True)
        
        if min_threshold is not None:
            queryset = queryset.filter(current_stock__lte=min_threshold)
        else:
            queryset = queryset.filter(current_stock__lte=F('min_stock'))
        
        return queryset.select_related('category', 'unit_of_measure')
    
    @staticmethod
    def get_kardex(product, start_date=None, end_date=None):
        """
        Get stock movement history for a product.
        
        Args:
            product: Product instance
            start_date: Start date filter
            end_date: End date filter
        
        Returns:
            QuerySet of movements
        """
        queryset = StockMovement.objects.filter(product=product)
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset.order_by('created_at')

    # ==================== PACKAGING CASCADE ====================

    @staticmethod
    @transaction.atomic
    def deduct_stock_with_cascade(product, quantity, reference='', reference_id=None, notes='', user=None):
        """
        Descuenta stock del producto y actualiza proporcionalmente cada nivel de packaging.
        Si el producto no tiene packagings activos, delega a deduct_stock().
        """
        quantity = Decimal(str(quantity))

        # Lock the product row to prevent concurrent modifications
        product = Product.objects.select_for_update().get(pk=product.pk)

        packagings = {
            p.packaging_type: p
            for p in product.packagings.filter(is_active=True).select_for_update()
        }

        if not packagings:
            return StockManagementService.deduct_stock(
                product, quantity, reference=reference,
                reference_id=reference_id, notes=notes, user=user,
            )

        # --- Producto base ---
        stock_before = product.current_stock
        product.current_stock = stock_before - quantity
        if product.current_stock < 0:
            notes += ' [ALERTA: Stock negativo]'
        product.save()

        base_movement = StockMovement.objects.create(
            product=product,
            movement_type='sale',
            quantity=-quantity,
            unit_cost=product.cost_price,
            stock_before=stock_before,
            stock_after=product.current_stock,
            reference=reference,
            reference_id=reference_id,
            notes=notes,
            created_by=user,
        )

        # --- Unidad ---
        unit_pkg = packagings.get('unit')
        if unit_pkg:
            pkg_before = unit_pkg.current_stock
            unit_pkg.current_stock = pkg_before - quantity
            unit_pkg.save()

        # --- Display ---
        display_pkg = packagings.get('display')
        if display_pkg and display_pkg.units_per_display > 0:
            pkg_before = display_pkg.current_stock
            display_pkg.current_stock = pkg_before - (quantity / Decimal(str(display_pkg.units_per_display)))
            display_pkg.save()

        # --- Bulto ---
        bulk_pkg = packagings.get('bulk')
        if bulk_pkg and bulk_pkg.units_quantity > 0:
            pkg_before = bulk_pkg.current_stock
            bulk_pkg.current_stock = pkg_before - (quantity / Decimal(str(bulk_pkg.units_quantity)))
            bulk_pkg.save()

        return True, 'Stock descontado en cascada', base_movement

    @staticmethod
    @transaction.atomic
    def receive_packaging(packaging_record, quantity, cost=None, user=None):
        """
        Recibe mercadería a nivel de empaque y actualiza TODO en cascada:
        - El empaque recibido (ej: bulk += 5)
        - Las unidades base del producto (Product.current_stock += 5 * 288)
        - Los otros niveles de packaging proporcionalmente
          (ej: display += 5*12, unit += 5*288)

        La idea es que TODOS los niveles reflejen el stock real.
        Cuando recibís 5 bultos, tenés 5 bultos, 60 displays y 1440 unidades.
        """
        quantity = Decimal(str(quantity))
        # Lock product row to prevent concurrent stock modifications
        product = Product.objects.select_for_update().get(pk=packaging_record.product_id)
        packaging_record = ProductPackaging.objects.select_for_update().get(pk=packaging_record.pk)

        # 1) Sumar al packaging recibido
        pkg_before = packaging_record.current_stock
        packaging_record.current_stock = pkg_before + quantity
        if cost is not None and Decimal(str(cost)) > 0:
            packaging_record.purchase_price = Decimal(str(cost))
        packaging_record.save()

        # 2) Calcular unidades base que corresponden
        if packaging_record.packaging_type == 'bulk':
            units_added = quantity * Decimal(str(packaging_record.units_quantity))
        elif packaging_record.packaging_type == 'display':
            units_added = quantity * Decimal(str(packaging_record.units_per_display))
        else:
            units_added = quantity

        # 3) Sumar al producto (unidades base)
        stock_before = product.current_stock
        product.current_stock = stock_before + units_added

        # 4) Actualizar costo promedio
        cost_each = Decimal(str(cost)) if cost else packaging_record.purchase_price
        if cost_each and cost_each > 0 and packaging_record.units_quantity > 0:
            unit_cost = cost_each / Decimal(str(packaging_record.units_quantity))
            total_value = (product.cost_price * stock_before) + (unit_cost * units_added)
            if product.current_stock > 0:
                product.cost_price = total_value / product.current_stock
        product.save()

        # 5) Actualizar OTROS niveles de packaging proporcionalmente
        other_pkgs = product.packagings.select_for_update().filter(
            is_active=True
        ).exclude(pk=packaging_record.pk)

        for other in other_pkgs:
            if other.packaging_type == 'unit':
                # Sumar las unidades base equivalentes
                other.current_stock += units_added
            elif other.packaging_type == 'display':
                if other.units_per_display > 0:
                    other.current_stock += units_added / Decimal(str(other.units_per_display))
            elif other.packaging_type == 'bulk':
                if other.units_quantity > 0:
                    other.current_stock += units_added / Decimal(str(other.units_quantity))
            other.save()

        movement = StockMovement.objects.create(
            product=product,
            movement_type='purchase',
            quantity=units_added,
            unit_cost=cost_each / Decimal(str(packaging_record.units_quantity)) if cost_each and packaging_record.units_quantity > 0 else Decimal('0'),
            stock_before=stock_before,
            stock_after=product.current_stock,
            reference=f'Recepción {packaging_record.get_packaging_type_display()} x{quantity}',
            notes=f'{packaging_record.name}',
            created_by=user,
        )
        return movement

    @staticmethod
    @transaction.atomic
    def open_packaging(packaging_record, quantity=1, user=None):
        """
        Abre un empaque superior y lo convierte al nivel inferior.
        Bulto → Displays | Display → Unidades.
        Product.current_stock NO cambia (las unidades ya estaban contadas).
        """
        quantity = Decimal(str(quantity))
        # Lock product and packaging rows to prevent concurrent modifications
        product = Product.objects.select_for_update().get(pk=packaging_record.product_id)
        packaging_record = ProductPackaging.objects.select_for_update().get(pk=packaging_record.pk)
        pkg_type = packaging_record.packaging_type

        if pkg_type == 'bulk':
            # Bulto → Displays (preferred) or Bulto → Unidades (fallback)
            target = product.packagings.select_for_update().filter(packaging_type='display', is_active=True).first()
            if target:
                convert_qty = quantity * Decimal(str(packaging_record.displays_per_bulk))
                packaging_record.current_stock -= quantity
                packaging_record.save()
                target.current_stock += convert_qty
                target.save()
                ref = f'Apertura Bulto x{quantity} → {convert_qty} displays'
            else:
                # No display — convert directly to units
                target = product.packagings.select_for_update().filter(packaging_type='unit', is_active=True).first()
                if not target:
                    raise ValueError('No existe empaque Display ni Unidad para abrir el bulto')
                convert_qty = quantity * Decimal(str(packaging_record.units_quantity))
                packaging_record.current_stock -= quantity
                packaging_record.save()
                target.current_stock += convert_qty
                target.save()
                ref = f'Apertura Bulto x{quantity} → {convert_qty} unidades'

        elif pkg_type == 'display':
            # Display → Unidades
            target = product.packagings.select_for_update().filter(packaging_type='unit', is_active=True).first()
            if not target:
                raise ValueError('No existe empaque Unidad para abrir el display')
            convert_qty = quantity * Decimal(str(packaging_record.units_per_display))

            packaging_record.current_stock -= quantity
            packaging_record.save()
            target.current_stock += convert_qty
            target.save()

            ref = f'Apertura Display x{quantity} → {convert_qty} unidades'
        else:
            raise ValueError('Solo se pueden abrir Bultos o Displays')

        # Movimientos informativos (no cambia product.current_stock)
        StockMovement.objects.create(
            product=product,
            movement_type='adjustment_out',
            quantity=-quantity,
            stock_before=product.current_stock,
            stock_after=product.current_stock,
            reference=ref,
            notes=f'Empaque origen: {packaging_record.name}',
            created_by=user,
        )
        StockMovement.objects.create(
            product=product,
            movement_type='adjustment_in',
            quantity=convert_qty,
            stock_before=product.current_stock,
            stock_after=product.current_stock,
            reference=ref,
            notes=f'Empaque destino: {target.name}',
            created_by=user,
        )


class BarcodeService:
    """Service for barcode operations."""
    
    @staticmethod
    def generate_ean13():
        """
        Generate a valid EAN-13 barcode.
        
        Returns:
            str: 13-digit EAN barcode
        """
        import random
        
        # Generate 12 random digits
        digits = [random.randint(0, 9) for _ in range(12)]
        
        # Calculate checksum (13th digit)
        odd_sum = sum(digits[::2])
        even_sum = sum(digits[1::2])
        checksum = (10 - ((odd_sum + even_sum * 3) % 10)) % 10
        
        digits.append(checksum)
        return ''.join(map(str, digits))
    
    @staticmethod
    def validate_barcode(code):
        """
        Validate a barcode checksum.
        
        Args:
            code: Barcode string
        
        Returns:
            bool: True if valid
        """
        if not code or not code.isdigit():
            return False
        
        if len(code) == 13:  # EAN-13
            digits = [int(d) for d in code]
            odd_sum = sum(digits[::2][:-1])
            even_sum = sum(digits[1::2])
            checksum = (10 - ((odd_sum + even_sum * 3) % 10)) % 10
            return checksum == digits[-1]
        elif len(code) == 12:  # UPC-A
            digits = [int(d) for d in code]
            odd_sum = sum(digits[::2][:-1])
            even_sum = sum(digits[1::2])
            checksum = (10 - ((odd_sum * 3 + even_sum) % 10)) % 10
            return checksum == digits[-1]
        elif len(code) == 8:  # EAN-8
            digits = [int(d) for d in code]
            weighted_sum = sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits[:-1]))
            checksum = (10 - (weighted_sum % 10)) % 10
            return checksum == digits[-1]
        
        # For other lengths, just check it's numeric
        return True
    
    @staticmethod
    def search_by_barcode(code):
        """
        Search product by barcode.
        
        Args:
            code: Barcode string
        
        Returns:
            Product instance or None
        """
        from .models import Product, ProductPresentation
        
        # First try product barcode
        product = Product.objects.filter(barcode=code, is_active=True).first()
        if product:
            return product
        
        # Then try presentation barcode
        presentation = ProductPresentation.objects.filter(
            barcode=code,
            is_active=True
        ).select_related('product').first()
        
        if presentation:
            return presentation.product
        
        return None
