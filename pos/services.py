"""
POS Services - Business Logic
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import datetime

from .models import POSSession, POSTransaction, POSTransactionItem, POSPayment

logger = logging.getLogger(__name__)


class POSService:
    """Service for POS operations."""
    
    @staticmethod
    def get_or_create_session(shift):
        """Get or create a POS session for a cash shift."""
        session = POSSession.objects.filter(
            cash_shift=shift,
            status='active'
        ).first()
        
        if not session:
            session = POSSession.objects.create(
                cash_shift=shift
            )
        
        return session
    
    @staticmethod
    def create_transaction(session):
        """Create a new POS transaction."""
        from django.db import IntegrityError

        for _attempt in range(5):
            ticket_number = POSService.generate_ticket_number(session)
            try:
                return POSTransaction.objects.create(
                    session=session,
                    ticket_number=ticket_number
                )
            except IntegrityError:
                continue
        # Último intento sin catch — si falla, que explote visible
        ticket_number = POSService.generate_ticket_number(session)
        return POSTransaction.objects.create(
            session=session,
            ticket_number=ticket_number
        )
    
    @staticmethod
    def get_pending_transaction(session):
        """Get or create a pending transaction for a session."""
        transaction = POSTransaction.objects.filter(
            session=session,
            status='pending'
        ).first()
        
        if not transaction:
            transaction = POSService.create_transaction(session)
        
        return transaction
    
    @staticmethod
    def generate_ticket_number(session):
        """Generate a unique ticket number."""
        import random
        import string
        from django.db import IntegrityError
        
        register_code = session.cash_shift.cash_register.code or 'CAJA'
        date_str = timezone.now().strftime('%Y%m%d')
        
        # Count today's transactions for this register
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        count = POSTransaction.objects.filter(
            session__cash_shift__cash_register=session.cash_shift.cash_register,
            created_at__gte=today_start
        ).count() + 1
        
        # Generate base ticket number
        ticket_number = f'{register_code}-{date_str}-{count:04d}'
        
        # Check if it already exists and add suffix if needed
        while POSTransaction.objects.filter(ticket_number=ticket_number).exists():
            count += 1
            ticket_number = f'{register_code}-{date_str}-{count:04d}'
        
        return ticket_number


class CartService:
    """Service for cart operations."""
    
    @staticmethod
    @transaction.atomic
    def add_item(pos_transaction, product_id, quantity=Decimal('1'), packaging_id=None,
                 override_unit_price=None):
        """
        Add a product to the cart.

        Args:
            pos_transaction: POSTransaction instance
            product_id: Product ID
            quantity: Quantity to add (grams for granel products)
            packaging_id: ProductPackaging ID (optional).
            override_unit_price: If provided, use this as unit_price (used for granel where
                                  the price per gram varies due to ceiling/cuarto logic).

        Returns:
            tuple (item: POSTransactionItem or None, message: str)
        """
        from stocks.models import Product, ProductPackaging

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return None, 'Producto no encontrado'

        quantity = Decimal(str(quantity))

        # Resolve packaging
        packaging = None
        packaging_units = 1
        unit_price = product.sale_price

        if packaging_id:
            try:
                packaging = ProductPackaging.objects.get(id=packaging_id, product=product, is_active=True)
                packaging_units = packaging.units_quantity
                unit_price = packaging.sale_price
            except ProductPackaging.DoesNotExist:
                pass

        # For granel products: price is per `granel_price_weight_grams` grams (e.g. per 100g).
        # The frontend calculates the correct total and passes it as override_unit_price.
        # If override_unit_price is given, use it directly as unit_price.
        if override_unit_price is not None:
            unit_price = override_unit_price

        # Granel items are always stored as individual entries (one per weight transaction),
        # never merged with existing cart entries.
        if product.is_granel:
            existing_item = None
        else:
            # Check if item already exists in cart (same product AND same packaging)
            existing_item = POSTransactionItem.objects.filter(
                transaction=pos_transaction,
                product=product,
                packaging=packaging
            ).first()

        # Capture cost at time of sale
        # For granel products, cost per gram so that unit_cost * quantity = total cost
        if product.is_granel and product.weighted_avg_cost_per_gram > 0:
            unit_cost = product.weighted_avg_cost_per_gram
        else:
            unit_cost = product.cost_price or product.purchase_price or Decimal('0.00')

        if existing_item:
            existing_item.quantity += quantity
            existing_item.unit_cost = unit_cost  # Refresh cost on quantity update
            existing_item.save()
            item = existing_item
            pkg_label = f' ({packaging.name})' if packaging else ''
            message = f'{product.name}{pkg_label} actualizado ({existing_item.quantity})'
        else:
            item = POSTransactionItem.objects.create(
                transaction=pos_transaction,
                product=product,
                packaging=packaging,
                packaging_units=packaging_units,
                quantity=quantity,
                unit_price=unit_price,
                unit_cost=unit_cost,
            )
            pkg_label = f' ({packaging.name})' if packaging else ''
            if product.is_granel:
                message = f'{int(quantity) if quantity == int(quantity) else quantity}g de {product.name}'
            else:
                message = f'{product.name}{pkg_label} agregado'
        
        # Apply promotions
        CartService.apply_promotions(pos_transaction)
        
        # Recalculate totals
        pos_transaction.calculate_totals()
        
        return item, message
    
    @staticmethod
    @transaction.atomic
    def update_quantity(item_id, quantity):
        """Update item quantity."""
        try:
            item = POSTransactionItem.objects.get(id=item_id)
        except POSTransactionItem.DoesNotExist:
            return False, 'Ítem no encontrado'
        
        quantity = Decimal(str(quantity))
        
        if quantity <= 0:
            return CartService.remove_item(item_id)
        
        item.quantity = quantity
        item.save()
        
        # Apply promotions and recalculate
        CartService.apply_promotions(item.transaction)
        item.transaction.calculate_totals()
        
        return True, 'Cantidad actualizada'
    
    @staticmethod
    @transaction.atomic
    def remove_item(item_id):
        """Remove item from cart."""
        try:
            item = POSTransactionItem.objects.get(id=item_id)
            pos_transaction = item.transaction
            item.delete()
            
            # Apply promotions and recalculate
            CartService.apply_promotions(pos_transaction)
            pos_transaction.calculate_totals()
            
            return True, 'Ítem eliminado'
        except POSTransactionItem.DoesNotExist:
            return False, 'Ítem no encontrado'
    
    @staticmethod
    @transaction.atomic
    def clear_cart(pos_transaction):
        """Clear all items from cart."""
        pos_transaction.items.all().delete()
        pos_transaction.subtotal = Decimal('0.00')
        pos_transaction.discount_total = Decimal('0.00')
        pos_transaction.total = Decimal('0.00')
        pos_transaction.items_count = 0
        pos_transaction.save()
        
        return True, 'Carrito vaciado'
    
    @staticmethod
    def apply_promotions(pos_transaction):
        """Apply promotions to cart items.

        Importante: sólo tocamos el campo ``promotion_discount`` + metadatos
        de la promo. El ``discount`` (manual del cajero) queda intocado para
        que no se pise al re-aplicar promos cuando cambia el carrito.
        """
        from promotions.engine import PromotionEngine

        items = pos_transaction.items.all()
        if not items:
            return

        # Reset SÓLO los campos de promoción — el descuento manual no se toca.
        for item in items:
            item.promotion_discount = Decimal('0.00')
            item.promotion = None
            item.promotion_name = ''
            item.promotion_group_name = ''
            item.save()

        # Get cart items data. Prefetch packaging para evitar N+1 al leer
        # packaging_type dentro del list-comp.
        items = items.select_related('packaging')
        cart_items = [
            {
                'item_id': item.id,
                'product_id': item.product_id,
                'quantity': float(item.quantity),
                'unit_price': float(item.unit_price),
                'packaging_units': int(item.packaging_units or 1),
                'packaging_type': (item.packaging.packaging_type
                                   if item.packaging_id else 'unit'),
            }
            for item in items
        ]

        # Calculate promotions
        result = PromotionEngine.calculate_cart(cart_items)

        # Apply discounts to items
        for applied in result.get('applied_promotions', []):
            for item_discount in applied.get('item_discounts', []):
                item_id = item_discount.get('item_id')
                discount = Decimal(str(item_discount.get('discount', 0)))

                if item_id and discount > 0:
                    try:
                        item = POSTransactionItem.objects.get(id=item_id)
                        # Sumamos (no pisamos) para soportar promos combinables
                        item.promotion_discount += discount
                        item.promotion_id = applied.get('promotion_id')
                        item.promotion_name = applied.get('promotion_name', '')
                        item.promotion_group_name = applied.get('group_name', '')
                        item.save()
                    except POSTransactionItem.DoesNotExist:
                        pass


class CheckoutService:
    """Service for checkout operations."""
    
    @staticmethod
    def process_payment(transaction_id, payments):
        """
        Process payment for a transaction.
        
        Args:
            transaction_id: POSTransaction ID
            payments: List of dicts with 'method_code' and 'amount'
        
        Returns:
            tuple (success: bool, result: dict)
        """
        from cashregister.models import PaymentMethod, CashMovement
        from stocks.services import StockManagementService
        
        try:
            pos_transaction = POSTransaction.objects.get(
                id=transaction_id,
                status='pending'
            )
        except POSTransaction.DoesNotExist:
            return False, {'error': 'Transacción no encontrada o ya procesada'}
        
        try:
          return CheckoutService._process_payment_atomic(pos_transaction, payments)
        except ValueError as e:
            return False, {'error': str(e)}
    
    @staticmethod
    @transaction.atomic
    def _process_payment_atomic(pos_transaction, payments):
        from cashregister.models import PaymentMethod, CashMovement
        from stocks.services import StockManagementService
        
        # Calculate total to pay
        total_to_pay = pos_transaction.total
        total_paid = Decimal('0.00')
        
        # Validate and create payments
        for payment_data in payments:
            method_id = payment_data.get('method_id')
            method_code = payment_data.get('method_code')
            amount = Decimal(str(payment_data.get('amount', 0)))
            
            if amount <= 0:
                continue
            
            try:
                # Support both method_id and method_code
                if method_id:
                    method = PaymentMethod.objects.get(id=method_id, is_active=True)
                elif method_code:
                    method = PaymentMethod.objects.get(code=method_code, is_active=True)
                else:
                    return False, {'error': 'Método de pago no especificado'}
            except PaymentMethod.DoesNotExist:
                return False, {'error': f'Método de pago inválido'}
            
            POSPayment.objects.create(
                transaction=pos_transaction,
                payment_method=method,
                amount=amount,
                reference=payment_data.get('reference', '')
            )
            
            # Calculate remaining amount to pay (before this payment)
            remaining = max(Decimal('0.00'), total_to_pay - total_paid)
            
            # Register cash movement only for the actual sale amount, not change
            movement_amount = min(amount, remaining) if remaining > 0 else Decimal('0.00')
            
            if movement_amount > 0:
                CashMovement.objects.create(
                    cash_shift=pos_transaction.session.cash_shift,
                    movement_type='income',
                    amount=movement_amount,
                    payment_method=method,
                    description=f'Venta {pos_transaction.ticket_number}',
                    reference=pos_transaction.ticket_number
                )
            
            total_paid += amount
        
        # Verify sufficient payment
        if total_paid < total_to_pay:
            # Raise to trigger atomic rollback (reverts POSPayments AND CashMovements)
            raise ValueError(f'Pago insuficiente. Faltan ${total_to_pay - total_paid}')
        
        # Calculate change
        change = total_paid - total_to_pay
        
        # Deduct stock — ruteo por tipo de producto:
        # - Granel (caramelera): registrar_venta maneja descuento de caramelera
        #   Y sincroniza el Product POS. Si falla, la excepción propaga y el
        #   @transaction.atomic revierte todo (antes se tragaba el error y
        #   el stock de la caramelera quedaba desincronizado).
        # - No-granel: descuento estándar de stock + FIFO batches.
        from granel.services import BatchService, GranelService
        for item in pos_transaction.items.all():
            caramelera = getattr(item.product, 'granel_caramelera', None)

            if caramelera is not None:
                GranelService.registrar_venta(
                    caramelera_id=caramelera.pk,
                    gramos_vendidos=item.quantity,
                    precio_cobrado=item.subtotal,
                    pos_transaction_id=pos_transaction.id,
                )
            else:
                units_to_deduct = item.quantity * item.packaging_units
                pkg_note = ''
                if item.packaging and item.packaging_units > 1:
                    pkg_note = f' [{item.packaging.get_packaging_type_display()}: {item.quantity} x {item.packaging_units} unids]'
                if item.product.packagings.filter(is_active=True).exists():
                    StockManagementService.deduct_stock_with_cascade(
                        product=item.product,
                        quantity=units_to_deduct,
                        reference=f'Venta {pos_transaction.ticket_number}{pkg_note}',
                        reference_id=pos_transaction.id
                    )
                else:
                    StockManagementService.deduct_stock(
                        product=item.product,
                        quantity=units_to_deduct,
                        reference=f'Venta {pos_transaction.ticket_number}{pkg_note}',
                        reference_id=pos_transaction.id
                    )
                deductions = BatchService.deduct_fifo(item.product.pk, units_to_deduct)
                # Sobrescribir unit_cost con el costo FIFO real del lote consumido,
                # para que el reporte de ganancia refleje precio de costo real.
                # Si no hay lotes (producto sin compras registradas), conserva
                # el costo promedio que ya tenía el item.
                if deductions and item.quantity > 0:
                    fifo_cost_total = sum(b.purchase_price * qty for b, qty in deductions)
                    item.unit_cost = (fifo_cost_total / item.quantity).quantize(Decimal('0.01'))
                    item.save(update_fields=['unit_cost'])

        # Complete transaction
        pos_transaction.status = 'completed'
        pos_transaction.completed_at = timezone.now()
        pos_transaction.amount_paid = total_paid
        pos_transaction.change_given = change
        pos_transaction.save()

        return True, {
            'success': True,
            'transaction_id': pos_transaction.id,
            'ticket_number': pos_transaction.ticket_number,
            'total': float(total_to_pay),
            'paid': float(total_paid),
            'change': float(change),
            'items_count': pos_transaction.items_count
        }
    
    @staticmethod
    @transaction.atomic
    def cancel_transaction(transaction_id, reason=''):
        """Cancel a transaction."""
        try:
            pos_transaction = POSTransaction.objects.get(
                id=transaction_id,
                status='pending'
            )
        except POSTransaction.DoesNotExist:
            return False, 'Transacción no encontrada'
        
        pos_transaction.status = 'cancelled'
        pos_transaction.cancelled_at = timezone.now()
        pos_transaction.notes = reason
        pos_transaction.save()
        
        return True, 'Transacción cancelada'
    
    @staticmethod
    @transaction.atomic
    def suspend_transaction(transaction_id):
        """Suspend a transaction for later."""
        try:
            pos_transaction = POSTransaction.objects.get(
                id=transaction_id,
                status='pending'
            )
        except POSTransaction.DoesNotExist:
            return False, 'Transacción no encontrada'
        
        pos_transaction.status = 'suspended'
        pos_transaction.suspended_at = timezone.now()
        pos_transaction.save()
        
        return True, 'Transacción suspendida'
    
    @staticmethod
    @transaction.atomic
    def resume_transaction(transaction_id):
        """Resume a suspended transaction."""
        try:
            pos_transaction = POSTransaction.objects.get(
                id=transaction_id,
                status='suspended'
            )
        except POSTransaction.DoesNotExist:
            return False, 'Transacción no encontrada'
        
        pos_transaction.status = 'pending'
        pos_transaction.suspended_at = None
        pos_transaction.save()
        
        return True, 'Transacción reanudada'
    
    @staticmethod
    def process_cost_sale(transaction_id, payments, employee_note=''):
        """
        Process a sale at cost price (for employees/owners).
        
        Args:
            transaction_id: POSTransaction ID
            payments: List of dicts with 'method_code' and 'amount'
            employee_note: Optional note about who consumed
        
        Returns:
            tuple (success: bool, result: dict)
        """
        try:
            pos_transaction = POSTransaction.objects.get(
                id=transaction_id,
                status='pending'
            )
        except POSTransaction.DoesNotExist:
            return False, {'error': 'Transacción no encontrada o ya procesada'}
        
        try:
            return CheckoutService._process_cost_sale_atomic(pos_transaction, payments, employee_note)
        except ValueError as e:
            return False, {'error': str(e)}
    
    @staticmethod
    @transaction.atomic
    def _process_cost_sale_atomic(pos_transaction, payments, employee_note=''):
        from cashregister.models import PaymentMethod, CashMovement
        from stocks.services import StockManagementService
        
        # Update item prices to cost price and recalculate
        for item in pos_transaction.items.all():
            item.unit_price = item.product.cost_price or item.product.purchase_price
            item.discount = Decimal('0.00')            # No discounts on cost sales
            item.promotion_discount = Decimal('0.00')  # Tampoco promos
            item.promotion = None
            item.promotion_name = ''
            item.promotion_group_name = ''
            item.subtotal = item.unit_price * item.quantity
            item.save()
        
        # Recalculate totals
        pos_transaction.calculate_totals()
        pos_transaction.refresh_from_db()
        
        # Calculate total to pay (at cost)
        total_to_pay = pos_transaction.total
        total_paid = Decimal('0.00')
        
        # Validate and create payments
        for payment_data in payments:
            method_id = payment_data.get('method_id')
            method_code = payment_data.get('method_code')
            amount = Decimal(str(payment_data.get('amount', 0)))
            
            if amount <= 0:
                continue
            
            try:
                if method_id:
                    method = PaymentMethod.objects.get(id=method_id, is_active=True)
                elif method_code:
                    method = PaymentMethod.objects.get(code=method_code, is_active=True)
                else:
                    raise ValueError('Método de pago no especificado')
            except PaymentMethod.DoesNotExist:
                raise ValueError('Método de pago inválido')
            
            POSPayment.objects.create(
                transaction=pos_transaction,
                payment_method=method,
                amount=amount,
                reference=f'Venta al costo - {employee_note}'
            )
            
            # Calculate remaining amount to pay (before this payment)
            remaining = max(Decimal('0.00'), total_to_pay - total_paid)
            
            # Register cash movement only for the actual sale amount, not change
            movement_amount = min(amount, remaining) if remaining > 0 else Decimal('0.00')
            
            if movement_amount > 0:
                CashMovement.objects.create(
                    cash_shift=pos_transaction.session.cash_shift,
                    movement_type='income',
                    amount=movement_amount,
                    payment_method=method,
                    description=f'Venta al costo {pos_transaction.ticket_number}',
                    reference=pos_transaction.ticket_number
                )
            
            total_paid += amount
        
        # Verify sufficient payment — raises to trigger full atomic rollback
        if total_paid < total_to_pay:
            raise ValueError(f'Pago insuficiente. Faltan ${total_to_pay - total_paid}')
        
        # Calculate change
        change = total_paid - total_to_pay
        
        # Deduct stock — mismo ruteo que _process_payment_atomic
        from granel.services import BatchService, GranelService
        for item in pos_transaction.items.all():
            caramelera = getattr(item.product, 'granel_caramelera', None)

            if caramelera is not None:
                GranelService.registrar_venta(
                    caramelera_id=caramelera.pk,
                    gramos_vendidos=item.quantity,
                    precio_cobrado=item.subtotal,
                    pos_transaction_id=pos_transaction.id,
                )
            else:
                units_to_deduct = item.quantity * item.packaging_units
                if item.product.packagings.filter(is_active=True).exists():
                    StockManagementService.deduct_stock_with_cascade(
                        product=item.product,
                        quantity=units_to_deduct,
                        reference=f'Venta al costo {pos_transaction.ticket_number}',
                        reference_id=pos_transaction.id
                    )
                else:
                    StockManagementService.deduct_stock(
                        product=item.product,
                        quantity=units_to_deduct,
                        reference=f'Venta al costo {pos_transaction.ticket_number}',
                        reference_id=pos_transaction.id
                    )
                deductions = BatchService.deduct_fifo(item.product.pk, units_to_deduct)
                if deductions and item.quantity > 0:
                    fifo_cost_total = sum(b.purchase_price * qty for b, qty in deductions)
                    item.unit_cost = (fifo_cost_total / item.quantity).quantize(Decimal('0.01'))
                    item.save(update_fields=['unit_cost'])

        # Complete transaction
        pos_transaction.transaction_type = 'cost_sale'
        pos_transaction.status = 'completed'
        pos_transaction.completed_at = timezone.now()
        pos_transaction.amount_paid = total_paid
        pos_transaction.change_given = change
        pos_transaction.notes = f'VENTA AL COSTO - {employee_note}'
        pos_transaction.save()
        
        return True, {
            'success': True,
            'transaction_id': pos_transaction.id,
            'ticket_number': pos_transaction.ticket_number,
            'total': float(total_to_pay),
            'paid': float(total_paid),
            'change': float(change),
            'items_count': pos_transaction.items_count,
            'type': 'cost_sale'
        }
    
    @staticmethod
    @transaction.atomic
    def process_internal_consumption(transaction_id, consumer_note=''):
        """
        Process internal consumption (deduct from stock without payment).
        
        Args:
            transaction_id: POSTransaction ID
            consumer_note: Who/why consumed (for traceability)
        
        Returns:
            tuple (success: bool, result: dict)
        """
        from stocks.services import StockManagementService
        
        try:
            pos_transaction = POSTransaction.objects.get(
                id=transaction_id,
                status='pending'
            )
        except POSTransaction.DoesNotExist:
            return False, {'error': 'Transacción no encontrada o ya procesada'}
        
        if pos_transaction.items.count() == 0:
            return False, {'error': 'El carrito está vacío'}
        
        # Update to cost prices for record keeping
        total_cost = Decimal('0.00')
        for item in pos_transaction.items.all():
            cost = item.product.cost_price or item.product.purchase_price
            item.unit_price = cost
            item.discount = Decimal('0.00')
            item.promotion_discount = Decimal('0.00')
            item.promotion = None
            item.promotion_name = ''
            item.promotion_group_name = ''
            item.subtotal = cost * item.quantity
            item.save()
            total_cost += item.subtotal
        
        # Deduct stock — mismo ruteo que _process_payment_atomic
        from granel.services import BatchService, GranelService
        for item in pos_transaction.items.all():
            caramelera = getattr(item.product, 'granel_caramelera', None)

            if caramelera is not None:
                GranelService.registrar_venta(
                    caramelera_id=caramelera.pk,
                    gramos_vendidos=item.quantity,
                    precio_cobrado=item.subtotal,
                    pos_transaction_id=pos_transaction.id,
                )
            else:
                units_to_deduct = item.quantity * item.packaging_units
                if item.product.packagings.filter(is_active=True).exists():
                    StockManagementService.deduct_stock_with_cascade(
                        product=item.product,
                        quantity=units_to_deduct,
                        reference=f'Consumo interno {pos_transaction.ticket_number} - {consumer_note}',
                        reference_id=pos_transaction.id
                    )
                else:
                    StockManagementService.deduct_stock(
                        product=item.product,
                        quantity=units_to_deduct,
                        reference=f'Consumo interno {pos_transaction.ticket_number} - {consumer_note}',
                        reference_id=pos_transaction.id
                    )
                deductions = BatchService.deduct_fifo(item.product.pk, units_to_deduct)
                if deductions and item.quantity > 0:
                    fifo_cost_total = sum(b.purchase_price * qty for b, qty in deductions)
                    item.unit_cost = (fifo_cost_total / item.quantity).quantize(Decimal('0.01'))
                    item.save(update_fields=['unit_cost'])

        # Complete transaction with zero payment
        pos_transaction.transaction_type = 'internal_consumption'
        pos_transaction.status = 'completed'
        pos_transaction.completed_at = timezone.now()
        pos_transaction.subtotal = total_cost
        pos_transaction.total = Decimal('0.00')  # No payment required
        pos_transaction.amount_paid = Decimal('0.00')
        pos_transaction.change_given = Decimal('0.00')
        pos_transaction.notes = f'CONSUMO INTERNO - {consumer_note}'
        pos_transaction.save()
        
        return True, {
            'success': True,
            'transaction_id': pos_transaction.id,
            'ticket_number': pos_transaction.ticket_number,
            'cost_value': float(total_cost),  # Value at cost for reference
            'items_count': pos_transaction.items_count,
            'type': 'internal_consumption'
        }
