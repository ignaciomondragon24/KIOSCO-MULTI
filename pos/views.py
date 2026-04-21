"""
POS Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q
from decimal import Decimal
import json
import unicodedata

from .models import POSSession, POSTransaction, POSTransactionItem, POSPayment, QuickAccessButton, POSKeyboardShortcut


def normalize_text(text):
    """Remove accents and convert to lowercase for search."""
    if not text:
        return ''
    # Normalize to NFD form (separates characters and diacritics)
    nfkd_form = unicodedata.normalize('NFKD', text)
    # Remove diacritical marks
    return ''.join(c for c in nfkd_form if not unicodedata.combining(c)).lower()
from .services import POSService, CartService, CheckoutService
from cashregister.models import CashShift, PaymentMethod
from stocks.models import Product, ProductCategory, ProductPackaging
from company.models import Company
from decorators.decorators import group_required


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
def pos_main(request):
    """Main POS view."""
    # Check if user has an open shift
    shift = CashShift.objects.filter(
        cashier=request.user,
        status='open'
    ).first()
    
    if not shift:
        messages.warning(request, 'Debes abrir un turno de caja para usar el POS.')
        return redirect('cashregister:open_shift')
    
    # Get or create POS session
    session = POSService.get_or_create_session(shift)
    
    # Check if resuming a specific transaction
    transaction_id = request.GET.get('transaction')
    if transaction_id:
        try:
            transaction = POSTransaction.objects.get(
                id=transaction_id,
                session__cash_shift=shift,
                status='pending'
            )
        except POSTransaction.DoesNotExist:
            transaction = POSService.get_pending_transaction(session)
    else:
        # Get or create pending transaction
        transaction = POSService.get_pending_transaction(session)
    
    # If transaction is completed, create a new one
    if transaction.status == 'completed':
        transaction = POSService.create_transaction(session)
    
    # Get cart items
    items = transaction.items.select_related('product', 'promotion').all()
    
    # Get quick access buttons
    quick_buttons = QuickAccessButton.objects.filter(
        is_active=True,
        product__is_active=True
    ).select_related('product').order_by('position')
    
    # Get products marked for quick access
    quick_access_products = Product.objects.filter(
        is_active=True,
        is_quick_access=True
    ).order_by('quick_access_position')
    
    # Get payment methods
    payment_methods = PaymentMethod.objects.filter(is_active=True).order_by('position')
    
    # Count suspended transactions for this shift
    suspended_count = POSTransaction.objects.filter(
        session__cash_shift=shift,
        status='suspended'
    ).count()
    
    # Get categories for quick product add
    categories = ProductCategory.objects.filter(is_active=True).order_by('name')
    
    # Ensure shortcuts exist and pass them to template
    POSKeyboardShortcut.ensure_defaults()
    keyboard_shortcuts = POSKeyboardShortcut.objects.filter(is_enabled=True).order_by('order')
    key_choices = POSKeyboardShortcut.KEY_CHOICES

    context = {
        'shift': shift,
        'cash_register': shift.cash_register,
        'session': session,
        'transaction': transaction,
        'items': items,
        'quick_buttons': quick_buttons,
        'quick_access_products': quick_access_products,
        'payment_methods': payment_methods,
        'suspended_count': suspended_count,
        'categories': categories,
        'keyboard_shortcuts': keyboard_shortcuts,
        'key_choices': key_choices,
    }
    return render(request, 'pos/pos_main.html', context)


# API Endpoints

@login_required
@require_GET
def api_search(request):
    """Search products with accent-insensitive matching. Also searches ProductPackaging barcodes."""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'products': []})
    
    # Normalize query (remove accents)
    query_normalized = normalize_text(query)
    
    # For barcode searches, check ProductPackaging barcodes FIRST.
    # Si un Product legacy y un ProductPackaging activo comparten el mismo EAN-13
    # (caso tipico: un viejo producto "X 20u" creado como Product independiente y
    # el nuevo ProductPackaging display del producto base), el packaging gana —
    # es la fuente de verdad para precio y stock.
    packaging_match = None
    if query.isdigit() and 8 <= len(query) <= 13:
        packaging_match = ProductPackaging.objects.filter(
            barcode=query, is_active=True, product__is_active=True
        ).select_related('product', 'product__unit_of_measure', 'product__category').first()
        if packaging_match:
            products = Product.objects.filter(id=packaging_match.product_id)
        else:
            # Fallback: Product.barcode directo
            products = Product.objects.filter(is_active=True, barcode=query)
    elif len(query) >= 1:
        # Get all active products and filter in Python for accent-insensitive search
        all_products = Product.objects.filter(is_active=True).select_related('unit_of_measure', 'category')
        
        # Filter products where normalized name/sku/barcode contains normalized query
        matching_ids = []
        for p in all_products:
            name_normalized = normalize_text(p.name)
            sku_normalized = normalize_text(p.sku) if p.sku else ''
            barcode = p.barcode or ''
            
            if (query_normalized in name_normalized or 
                query_normalized in sku_normalized or
                query in barcode):
                matching_ids.append(p.id)
        
        products = Product.objects.filter(id__in=matching_ids).select_related('unit_of_measure', 'category').order_by('name')[:15]
    else:
        products = Product.objects.none()
    
    products_data = []
    for p in products:
        product_data = {
            'id': p.id,
            'name': p.name,
            'barcode': p.barcode or '',
            'sku': p.sku,
            'unit_price': float(p.sale_price),
            'stock': float(p.current_stock),
            'unit': p.get_unit_display(),
            'is_bulk': p.is_bulk,
            'bulk_unit': p.bulk_unit if p.is_bulk else None,
            'allow_sell_by_amount': p.allow_sell_by_amount,
            'is_granel': p.is_granel,
            'granel_price_weight_grams': p.granel_price_weight_grams if p.is_granel else None,
            'sale_price_250g': float(p.sale_price_250g) if p.is_granel else None,
            'has_parent': p.parent_product is not None,
            'parent_name': p.parent_product.name if p.parent_product else None,
            'packaging_id': None,
            'packaging_type': None,
            'packaging_name': None,
            'packaging_units': 1,
        }
        
        # If this was matched through a packaging barcode, include packaging info
        if packaging_match and packaging_match.product_id == p.id:
            product_data['unit_price'] = float(packaging_match.sale_price)
            product_data['packaging_id'] = packaging_match.id
            product_data['packaging_type'] = packaging_match.packaging_type
            product_data['packaging_name'] = packaging_match.name
            product_data['packaging_units'] = packaging_match.units_quantity
            product_data['barcode'] = packaging_match.barcode
            # Show stock in terms of this packaging level
            if packaging_match.units_quantity > 1:
                stock_in_pkg = float(p.current_stock) / packaging_match.units_quantity
                product_data['stock_in_packaging'] = round(stock_in_pkg, 1)
        else:
            # Si no fue match por barcode pero el producto tiene empaques activos,
            # devolver todos los niveles para que el POS pueda mostrar un selector
            # al hacer click (unidad / display / bulto).
            pkgs = list(p.packagings.filter(is_active=True).order_by('packaging_type'))
            if pkgs:
                options = []
                for pkg in pkgs:
                    units = pkg.units_quantity or 1
                    stock_in_pkg = (float(p.current_stock) / units) if units > 0 else 0
                    options.append({
                        'id': pkg.id,
                        'packaging_type': pkg.packaging_type,
                        'type_display': pkg.get_packaging_type_display(),
                        'name': pkg.name,
                        'barcode': pkg.barcode or '',
                        'sale_price': float(pkg.sale_price),
                        'units_quantity': units,
                        'stock_in_packaging': round(stock_in_pkg, 2),
                    })
                # Solo exponer el selector si hay mas de un nivel real
                # (un solo packaging unit no agrega valor — el user ya ve el precio base).
                if len(options) > 1:
                    product_data['packagings'] = options

        products_data.append(product_data)
    
    data = {'products': products_data}
    
    return JsonResponse(data)


@login_required
@require_GET
def api_all_products(request):
    """Return all active products for the sidebar products panel."""
    products = Product.objects.filter(is_active=True).select_related(
        'unit_of_measure', 'category'
    ).order_by('category__name', 'name')
    quick_ids = set(QuickAccessButton.objects.filter(is_active=True).values_list('product_id', flat=True))
    return JsonResponse({
        'products': [
            {
                'id': p.id,
                'name': p.name,
                'barcode': p.barcode or '',
                'sku': p.sku or '',
                'unit_price': float(p.sale_price),
                'cost_price': float(p.cost_price or p.purchase_price or 0),
                'stock': float(p.current_stock),
                'unit': p.get_unit_display(),
                'is_bulk': p.is_bulk,
                'bulk_unit': p.bulk_unit if p.is_bulk else None,
                'allow_sell_by_amount': p.allow_sell_by_amount,
                'is_granel': p.is_granel,
                'granel_price_weight_grams': p.granel_price_weight_grams if p.is_granel else None,
                'sale_price_250g': float(p.sale_price_250g) if p.is_granel else None,
                'category': p.category.name if p.category else 'Sin categoría',
                'category_id': p.category_id or 0,
                'is_quick': p.id in quick_ids,
            }
            for p in products
        ]
    })


@login_required
@require_POST
def api_toggle_quick_access(request):
    """Toggle quick access button for a product from the POS sidebar."""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        if not product_id:
            return JsonResponse({'success': False, 'error': 'product_id requerido'}, status=400)

        product = Product.objects.get(id=product_id, is_active=True)
        btn = QuickAccessButton.objects.filter(product=product).first()

        if btn:
            btn.delete()
            is_quick = False
        else:
            max_pos = QuickAccessButton.objects.order_by('-position').values_list('position', flat=True).first() or 0
            QuickAccessButton.objects.create(
                product=product,
                position=max_pos + 1,
                is_active=True
            )
            is_quick = True

        # Return updated quick buttons for grid refresh
        buttons = QuickAccessButton.objects.filter(
            is_active=True, product__is_active=True
        ).select_related('product').order_by('position')
        buttons_data = [
            {
                'product_id': b.product.id,
                'name': b.product.name[:15],
                'price': float(b.product.sale_price),
                'color': b.color,
                'is_granel': b.product.is_granel,
                'is_bulk': b.product.is_bulk,
                'sale_price_250g': float(b.product.sale_price_250g),
                'stock': float(b.product.current_stock),
            }
            for b in buttons
        ]

        return JsonResponse({
            'success': True,
            'is_quick': is_quick,
            'product_id': product_id,
            'buttons': buttons_data
        })
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_GET
def api_calculate_cost_total(request, transaction_id):
    """Calculate total at cost price for a transaction."""
    from decimal import Decimal
    
    try:
        transaction = POSTransaction.objects.get(id=transaction_id, status='pending')
    except POSTransaction.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Transacción no encontrada'}, status=404)
    
    total_cost = Decimal('0.00')
    items_cost = []
    
    for item in transaction.items.select_related('product').all():
        cost_price = item.product.cost_price or item.product.purchase_price or Decimal('0.00')
        item_cost = cost_price * item.quantity
        total_cost += item_cost
        items_cost.append({
            'product_name': item.product.name,
            'quantity': float(item.quantity),
            'cost_price': float(cost_price),
            'total': float(item_cost)
        })
    
    return JsonResponse({
        'success': True,
        'total_cost': float(total_cost),
        'items': items_cost
    })


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
@require_POST
def api_cart_add(request):
    """Add item to cart."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    
    transaction_id = data.get('transaction_id')
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    packaging_id = data.get('packaging_id')
    # Optional: override unit_price (used for granel items where price is calculated on frontend)
    override_unit_price = data.get('unit_price')

    if not transaction_id or not product_id:
        return JsonResponse({'success': False, 'error': 'Datos incompletos'}, status=400)

    try:
        transaction = POSTransaction.objects.get(id=transaction_id, status='pending')
    except POSTransaction.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Transacción no encontrada'}, status=404)

    override_price_decimal = Decimal(str(override_unit_price)) if override_unit_price is not None else None
    item, message = CartService.add_item(
        transaction, product_id, Decimal(str(quantity)),
        packaging_id=packaging_id, override_unit_price=override_price_decimal
    )
    
    if item:
        # Check stock and add warning if needed
        warning = None
        try:
            from stocks.models import Product
            prod = Product.objects.get(id=product_id)
            if prod.current_stock <= 0:
                warning = f'\u26a0 {prod.name} sin stock disponible'
        except Product.DoesNotExist:
            pass
        
        resp = {
            'success': True,
            'item_id': item.id,
            'message': message,
            'totals': {
                'subtotal': float(transaction.subtotal),
                'discount': float(transaction.discount_total),
                'total': float(transaction.total),
                'items_count': transaction.items_count
            }
        }
        if warning:
            resp['warning'] = warning
        return JsonResponse(resp)
    
    return JsonResponse({'success': False, 'error': message}, status=400)


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
@require_POST
def api_cart_update(request, item_id):
    """Update cart item quantity."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    
    quantity = data.get('quantity')
    
    if quantity is None:
        return JsonResponse({'success': False, 'error': 'Cantidad no especificada'}, status=400)
    
    success, message = CartService.update_quantity(item_id, quantity)
    
    if success:
        item = POSTransactionItem.objects.get(id=item_id)
        transaction = item.transaction
        return JsonResponse({
            'success': True,
            'message': message,
            'totals': {
                'subtotal': float(transaction.subtotal),
                'discount': float(transaction.discount_total),
                'total': float(transaction.total),
                'items_count': transaction.items_count
            }
        })
    
    return JsonResponse({'success': False, 'error': message}, status=400)


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
@require_POST
def api_cart_remove(request, item_id):
    """Remove item from cart."""
    success, message = CartService.remove_item(item_id)
    
    if success:
        return JsonResponse({'success': True, 'message': message})
    
    return JsonResponse({'success': False, 'error': message}, status=400)


@login_required
@require_POST
def api_calculate_by_amount(request):
    """
    Calculate quantity based on amount for bulk products.
    e.g.: "$500 de gomitas" returns the quantity in kg/gr
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    
    product_id = data.get('product_id')
    amount = data.get('amount')
    
    if not product_id or amount is None:
        return JsonResponse({'success': False, 'error': 'Datos incompletos'}, status=400)
    
    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'}, status=404)
    
    if not product.allow_sell_by_amount:
        return JsonResponse({
            'success': False, 
            'error': 'Este producto no permite venta por monto'
        }, status=400)
    
    quantity, actual_total = product.calculate_quantity_for_amount(Decimal(str(amount)))
    
    return JsonResponse({
        'success': True,
        'product_id': product.id,
        'product_name': product.name,
        'requested_amount': float(amount),
        'quantity': float(quantity),
        'unit': product.get_unit_display(),
        'unit_price': float(product.sale_price),
        'actual_total': float(actual_total),
        'is_bulk': product.is_bulk,
    })


@login_required
@require_POST
def api_cart_add_by_amount(request):
    """
    Add item to cart by specifying the amount instead of quantity.
    Calculates the quantity based on the price.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    
    transaction_id = data.get('transaction_id')
    product_id = data.get('product_id')
    amount = data.get('amount')
    
    if not transaction_id or not product_id or amount is None:
        return JsonResponse({'success': False, 'error': 'Datos incompletos'}, status=400)
    
    try:
        transaction = POSTransaction.objects.get(id=transaction_id, status='pending')
        product = Product.objects.get(id=product_id, is_active=True)
    except POSTransaction.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Transacción no encontrada'}, status=404)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'}, status=404)
    
    if not product.allow_sell_by_amount:
        return JsonResponse({
            'success': False, 
            'error': 'Este producto no permite venta por monto'
        }, status=400)
    
    # Calculate quantity from amount
    quantity, actual_total = product.calculate_quantity_for_amount(Decimal(str(amount)))
    
    if quantity <= 0:
        return JsonResponse({'success': False, 'error': 'Cantidad inválida'}, status=400)
    
    # Add to cart
    item, message = CartService.add_item(transaction, product_id, quantity)
    
    if item:
        return JsonResponse({
            'success': True,
            'item_id': item.id,
            'message': f'{quantity} {product.get_unit_display()} de {product.name}',
            'quantity': float(quantity),
            'unit': product.get_unit_display(),
            'actual_total': float(actual_total),
            'totals': {
                'subtotal': float(transaction.subtotal),
                'discount': float(transaction.discount_total),
                'total': float(transaction.total),
                'items_count': transaction.items_count
            }
        })
    
    return JsonResponse({'success': False, 'error': message}, status=400)


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
@require_POST
def api_cart_clear(request, transaction_id):
    """Clear cart."""
    try:
        transaction = POSTransaction.objects.get(id=transaction_id, status='pending')
    except POSTransaction.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Transacción no encontrada'}, status=404)
    
    success, message = CartService.clear_cart(transaction)
    
    return JsonResponse({'success': success, 'message': message})


@login_required
@require_GET
def api_transaction_detail(request, transaction_id):
    """Get transaction details."""
    try:
        transaction = POSTransaction.objects.get(id=transaction_id)
    except POSTransaction.DoesNotExist:
        return JsonResponse({'error': 'Transacción no encontrada'}, status=404)
    
    items = transaction.items.select_related('product', 'promotion', 'packaging').all()
    
    data = {
        'id': transaction.id,
        'ticket_number': transaction.ticket_number,
        'status': transaction.status,
        'items': [
            {
                'id': item.id,
                'product_id': item.product.id,
                'product_name': item.product.name,
                'quantity': float(item.quantity),
                'unit_price': float(item.unit_price),
                'discount': float(item.discount),
                'promotion_discount': float(item.promotion_discount),
                'subtotal': float(item.subtotal),
                'promotion_name': item.promotion_name,
                'promotion_group_name': item.promotion_group_name,
                'promotion_type': item.promotion.promo_type if item.promotion else None,
                'promotion_qty_required': item.promotion.quantity_required if item.promotion else None,
                'promotion_qty_charged': item.promotion.quantity_charged if item.promotion else None,
                'promotion_final_price': float(item.promotion.final_price) if item.promotion and item.promotion.final_price else None,
                'promotion_discount_percent': float(item.promotion.discount_percent) if item.promotion else None,
                'promotion_second_unit_discount': float(item.promotion.second_unit_discount) if item.promotion else None,
                'packaging_id': item.packaging_id,
                'packaging_name': item.packaging.name if item.packaging else None,
                'packaging_type': item.packaging.packaging_type if item.packaging else None,
                'packaging_units': item.packaging_units,
                'is_granel': item.product.is_granel,
                'granel_price_weight_grams': item.product.granel_price_weight_grams if item.product.is_granel else None,
            }
            for item in items
        ],
        'totals': {
            'subtotal': float(transaction.subtotal),
            'discount': float(transaction.discount_total),
            'total': float(transaction.total),
            'items_count': transaction.items_count
        }
    }
    
    return JsonResponse(data)


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
@require_POST
def api_checkout(request):
    """Process checkout."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    
    transaction_id = data.get('transaction_id')
    payments = data.get('payments', [])
    
    if not transaction_id or not payments:
        return JsonResponse({'success': False, 'error': 'Datos incompletos'}, status=400)
    
    success, result = CheckoutService.process_payment(transaction_id, payments)
    
    if success:
        return JsonResponse(result)
    
    return JsonResponse({'success': False, **result}, status=400)


@login_required
@group_required(['Admin', 'Cajero Manager'])
@require_POST
def api_checkout_cost_sale(request):
    """Process checkout at cost price for employees/owners."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    
    transaction_id = data.get('transaction_id')
    payments = data.get('payments', [])
    employee_note = data.get('note', '')
    
    if not transaction_id or not payments:
        return JsonResponse({'success': False, 'error': 'Datos incompletos'}, status=400)
    
    success, result = CheckoutService.process_cost_sale(transaction_id, payments, employee_note)
    
    if success:
        return JsonResponse(result)
    
    return JsonResponse({'success': False, **result}, status=400)


@login_required
@group_required(['Admin', 'Cajero Manager'])
@require_POST
def api_checkout_internal_consumption(request):
    """Process internal consumption (stock deduction without payment)."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    
    transaction_id = data.get('transaction_id')
    consumer_note = data.get('note', request.user.get_full_name() or request.user.username)
    
    if not transaction_id:
        return JsonResponse({'success': False, 'error': 'Datos incompletos'}, status=400)
    
    success, result = CheckoutService.process_internal_consumption(transaction_id, consumer_note)
    
    if success:
        return JsonResponse(result)
    
    return JsonResponse({'success': False, **result}, status=400)


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
@require_POST
def api_transaction_suspend(request, transaction_id):
    """Suspend transaction."""
    success, message = CheckoutService.suspend_transaction(transaction_id)
    
    return JsonResponse({'success': success, 'message': message})


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
@require_POST
def api_transaction_resume(request, transaction_id):
    """Resume suspended transaction."""
    success, message = CheckoutService.resume_transaction(transaction_id)
    
    return JsonResponse({'success': success, 'message': message})


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
@require_POST
def api_transaction_cancel(request, transaction_id):
    """Cancel transaction."""
    try:
        data = json.loads(request.body)
        reason = data.get('reason', '')
    except json.JSONDecodeError:
        reason = ''
    
    success, message = CheckoutService.cancel_transaction(transaction_id, reason)
    
    return JsonResponse({'success': success, 'message': message})


@login_required
@group_required(['Admin', 'Cajero Manager'])
@require_POST
def api_cart_item_discount(request, item_id):
    """Apply or remove a discount on a specific cart item."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)

    try:
        item = POSTransactionItem.objects.select_related('transaction').get(
            id=item_id, transaction__status='pending'
        )
    except POSTransactionItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Ítem no encontrado'}, status=404)

    discount_type  = data.get('type', 'percent')   # 'percent' | 'fixed' | 'remove'
    discount_value = Decimal(str(data.get('value', 0)))

    item_total_before_discount = item.unit_price * item.quantity
    # El descuento manual no puede pasarse del neto ya descontado por promo.
    promo_discount = item.promotion_discount or Decimal('0.00')
    max_manual = item_total_before_discount - promo_discount

    if discount_type == 'remove':
        item.discount = Decimal('0.00')
    elif discount_type == 'percent':
        if discount_value <= 0 or discount_value > 100:
            return JsonResponse({'success': False, 'error': 'Porcentaje inválido (1-100)'}, status=400)
        item.discount = (item_total_before_discount * discount_value / Decimal('100')).quantize(Decimal('0.01'))
        if item.discount > max_manual:
            item.discount = max(max_manual, Decimal('0.00')).quantize(Decimal('0.01'))
    elif discount_type == 'fixed':
        if discount_value <= 0:
            return JsonResponse({'success': False, 'error': 'Monto inválido'}, status=400)
        if discount_value > max_manual:
            return JsonResponse({
                'success': False,
                'error': 'El descuento manual supera el monto disponible del ítem (ya hay una promo aplicada)'
            }, status=400)
        item.discount = discount_value.quantize(Decimal('0.01'))
    else:
        return JsonResponse({'success': False, 'error': 'Tipo inválido'}, status=400)

    item.save()  # triggers subtotal recalc
    transaction = item.transaction
    transaction.calculate_totals()
    transaction.save()

    return JsonResponse({
        'success': True,
        'message': 'Descuento aplicado' if discount_type != 'remove' else 'Descuento eliminado',
        'item': {
            'id': item.id,
            'discount': float(item.discount),
            'promotion_discount': float(item.promotion_discount),
            'subtotal': float(item.subtotal),
        },
        'totals': {
            'subtotal': float(transaction.subtotal),
            'discount': float(transaction.discount_total),
            'total': float(transaction.total),
            'items_count': transaction.items_count,
        },
    })


@login_required
@group_required(['Admin', 'Cajero Manager'])
@require_POST
def api_apply_discount(request, transaction_id):
    """Apply discount to transaction."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    
    discount_type = data.get('type', 'percent')  # 'percent' or 'fixed'
    discount_value = Decimal(str(data.get('value', 0)))
    reason = data.get('reason', '')
    
    if discount_value <= 0:
        return JsonResponse({'success': False, 'error': 'Valor de descuento inválido'}, status=400)
    
    try:
        transaction = POSTransaction.objects.get(id=transaction_id, status='pending')
    except POSTransaction.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Transacción no encontrada'}, status=404)
    
    # Calculate promotion discounts already applied to items (usando el campo
    # específico de promo, no el discount manual).
    promo_discount = sum(
        (item.promotion_discount or Decimal('0.00')) for item in transaction.items.all()
    )

    # Calculate manual discount amount (applied on top of promotion discounts)
    effective_subtotal = transaction.subtotal - promo_discount
    if discount_type == 'percent':
        if discount_value > 100:
            return JsonResponse({'success': False, 'error': 'El porcentaje no puede ser mayor a 100%'}, status=400)
        manual_discount = (effective_subtotal * discount_value) / Decimal('100')
    else:  # fixed
        if discount_value > effective_subtotal:
            return JsonResponse({'success': False, 'error': 'El descuento no puede ser mayor al subtotal'}, status=400)
        manual_discount = discount_value

    # Apply discount: promotion discounts + manual discount
    transaction.discount_total = promo_discount + manual_discount
    transaction.notes = f"Descuento: {reason}" if reason else f"Descuento: {discount_value}{'%' if discount_type == 'percent' else '$'}"
    transaction.total = transaction.subtotal - transaction.discount_total + transaction.tax_total
    transaction.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Descuento aplicado',
        'totals': {
            'subtotal': float(transaction.subtotal),
            'discount': float(transaction.discount_total),
            'total': float(transaction.total),
            'items_count': transaction.items_count
        }
    })


@login_required
def suspended_transactions(request):
    """View suspended transactions."""
    transactions = POSTransaction.objects.filter(
        status='suspended',
        session__cash_shift__cashier=request.user
    ).select_related('session__cash_shift__cash_register')
    
    return render(request, 'pos/suspended_transactions.html', {
        'transactions': transactions
    })


@login_required
def print_ticket(request, transaction_id):
    """Generate printable ticket for a transaction."""
    transaction = get_object_or_404(
        POSTransaction.objects.select_related(
            'session__cash_shift__cashier',
            'session__cash_shift__cash_register'
        ),
        pk=transaction_id
    )
    
    # Get items with products
    items = transaction.items.select_related('product', 'product__unit_of_measure', 'promotion').all()
    
    # Get payments
    payments = []
    payment_method_name = None
    for payment in transaction.payments.select_related('payment_method').all():
        payments.append({
            'method_name': payment.payment_method.name,
            'amount': payment.amount
        })
        if not payment_method_name:
            payment_method_name = payment.payment_method.name
    
    # Get company info
    company = Company.get_company()
    
    context = {
        'transaction': transaction,
        'items': items,
        'payments': payments,
        'payment_method_name': payment_method_name,
        'company': company,
    }
    
    return render(request, 'pos/ticket.html', context)


@login_required
@require_GET
def api_last_transaction(request):
    """Get the last completed transaction for the current user's shift."""
    shift = CashShift.objects.filter(
        cashier=request.user,
        status='open'
    ).first()
    
    if not shift:
        return JsonResponse({'success': False, 'error': 'No hay turno abierto'}, status=400)
    
    transaction = POSTransaction.objects.filter(
        session__cash_shift=shift,
        status='completed'
    ).order_by('-completed_at').first()
    
    if not transaction:
        return JsonResponse({'success': False, 'error': 'No hay transacciones completadas'}, status=404)
    
    return JsonResponse({
        'success': True,
        'transaction_id': transaction.id,
        'ticket_number': transaction.ticket_number,
        'total': float(transaction.total)
    })


@login_required
@require_GET
def api_suspended_transactions(request):
    """Get all suspended transactions for the current user's shift."""
    shift = CashShift.objects.filter(
        cashier=request.user,
        status='open'
    ).first()
    
    if not shift:
        return JsonResponse({'success': False, 'error': 'No hay turno abierto'}, status=400)
    
    transactions = POSTransaction.objects.filter(
        session__cash_shift=shift,
        status='suspended'
    ).order_by('-created_at')
    
    transactions_data = []
    for tx in transactions:
        items_count = tx.items.count()
        transactions_data.append({
            'id': tx.id,
            'ticket_number': tx.ticket_number,
            'created_at': tx.created_at.isoformat(),
            'total': float(tx.total),
            'items_count': items_count
        })
    
    return JsonResponse({
        'success': True,
        'transactions': transactions_data
    })


@login_required
@require_POST
def api_quick_add_product(request):
    """Quickly add a new product from the POS when barcode is not found."""
    try:
        data = json.loads(request.body)
        
        barcode = data.get('barcode', '').strip()
        name = data.get('name', '').strip()
        sale_price = data.get('sale_price')
        purchase_price = data.get('purchase_price', 0)
        category_id = data.get('category_id')
        initial_stock = data.get('initial_stock', 0)
        
        if not name:
            return JsonResponse({'success': False, 'error': 'El nombre es requerido'}, status=400)
        
        if not sale_price or float(sale_price) <= 0:
            return JsonResponse({'success': False, 'error': 'El precio de venta es requerido'}, status=400)
        
        # Check if barcode already exists
        if barcode and Product.objects.filter(barcode=barcode).exists():
            return JsonResponse({'success': False, 'error': 'Ya existe un producto con este código de barras'}, status=400)
        
        # Generate SKU
        import random
        import string
        sku = 'POS-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        while Product.objects.filter(sku=sku).exists():
            sku = 'POS-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # Get category
        category = None
        if category_id:
            category = ProductCategory.objects.filter(id=category_id).first()
        
        # Create product
        product = Product.objects.create(
            sku=sku,
            barcode=barcode if barcode else None,
            name=name,
            sale_price=Decimal(str(sale_price)),
            purchase_price=Decimal(str(purchase_price)) if purchase_price else Decimal('0'),
            cost_price=Decimal(str(purchase_price)) if purchase_price else Decimal('0'),
            category=category,
            current_stock=int(initial_stock) if initial_stock else 0,
            is_active=True
        )
        
        # If initial stock, create stock movement
        if initial_stock and int(initial_stock) > 0:
            from stocks.models import StockMovement
            StockMovement.objects.create(
                product=product,
                movement_type='adjustment_in',
                quantity=int(initial_stock),
                unit_cost=Decimal(str(purchase_price)) if purchase_price else Decimal('0'),
                stock_before=0,
                stock_after=int(initial_stock),
                notes='Stock inicial desde POS',
                created_by=request.user
            )
        
        return JsonResponse({
            'success': True,
            'product': {
                'id': product.id,
                'sku': product.sku,
                'barcode': product.barcode,
                'name': product.name,
                'sale_price': float(product.sale_price),
                'current_stock': product.current_stock
            },
            'message': f'Producto "{product.name}" creado exitosamente'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos inválidos'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────
#  API: Atajos de teclado configurables
# ─────────────────────────────────────────────────────────────

@login_required
@require_GET
def api_keyboard_shortcuts(request):
    """Return the current keyboard shortcut configuration."""
    POSKeyboardShortcut.ensure_defaults()
    shortcuts = POSKeyboardShortcut.objects.filter(is_enabled=True)
    return JsonResponse({
        'shortcuts': [s.to_dict() for s in shortcuts],
    })


@login_required
@require_POST
def api_update_keyboard_shortcut(request):
    """Update the key assigned to a shortcut action."""
    try:
        data = json.loads(request.body)
        action = data.get('action', '').strip()
        new_key = data.get('key', '').strip()

        valid_actions = dict(POSKeyboardShortcut.ACTION_CHOICES)
        if action not in valid_actions:
            return JsonResponse({'success': False, 'error': 'Acción inválida'}, status=400)

        valid_keys = dict(POSKeyboardShortcut.KEY_CHOICES)
        if new_key not in valid_keys:
            return JsonResponse({'success': False, 'error': 'Tecla inválida'}, status=400)

        shortcut = POSKeyboardShortcut.objects.filter(action=action).first()
        if not shortcut:
            return JsonResponse({'success': False, 'error': 'Atajo no encontrado'}, status=404)

        # Check for duplicates (another action already uses this key)
        if new_key != 'none':
            conflict = POSKeyboardShortcut.objects.filter(key=new_key).exclude(action=action).first()
            if conflict:
                conflict_label = dict(POSKeyboardShortcut.ACTION_CHOICES).get(conflict.action, conflict.action)
                return JsonResponse({
                    'success': False,
                    'error': f'La tecla {new_key} ya está asignada a "{conflict_label}"'
                }, status=409)

        shortcut.key = new_key
        shortcut.save()

        # Return updated full list
        all_shortcuts = POSKeyboardShortcut.objects.filter(is_enabled=True)
        return JsonResponse({
            'success': True,
            'shortcuts': [s.to_dict() for s in all_shortcuts],
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)


# ─────────────────────────────────────────────────────────────
#  API: Historial de ventas del turno actual
# ─────────────────────────────────────────────────────────────

@login_required
@require_GET
def api_sales_history(request):
    """Return completed transactions for the current shift (last 50)."""
    shift = CashShift.objects.filter(cashier=request.user, status='open').first()
    if not shift:
        return JsonResponse({'success': False, 'error': 'Sin turno activo'}, status=400)

    transactions = (
        POSTransaction.objects
        .filter(session__cash_shift=shift, status='completed')
        .prefetch_related('payments__payment_method', 'items__product')
        .order_by('-completed_at')[:50]
    )

    data = []
    for tx in transactions:
        payment_labels = [
            f'{p.payment_method.name} ${p.amount:.2f}'.replace('.', ',')
            for p in tx.payments.all()
        ]
        items_preview = ', '.join(
            f'{it.product.name} x{it.quantity:g}'
            for it in tx.items.all()[:4]
        )
        if tx.items.count() > 4:
            items_preview += f' y {tx.items.count() - 4} más…'
        data.append({
            'id': tx.id,
            'ticket_number': tx.ticket_number,
            'total': float(tx.total),
            'completed_at': tx.completed_at.strftime('%H:%M:%S') if tx.completed_at else '',
            'items_count': tx.items_count,
            'items_preview': items_preview,
            'payments': payment_labels,
            'transaction_type': tx.get_transaction_type_display(),
        })

    return JsonResponse({'success': True, 'transactions': data})


# ─────────────────────────────────────────────────────────────
#  API: Pago rápido directo (sin abrir modal de cobro)
# ─────────────────────────────────────────────────────────────

@login_required
@require_POST
def api_quick_checkout(request):
    """Process a checkout directly with a single payment method (no modal)."""
    try:
        data = json.loads(request.body)
        transaction_id = data.get('transaction_id')
        method_code = data.get('method_code')  # 'cash', 'mercadopago', etc.

        if not transaction_id or not method_code:
            return JsonResponse({'success': False, 'error': 'Faltan datos'}, status=400)

        transaction = get_object_or_404(POSTransaction, id=transaction_id, status='pending')
        method = PaymentMethod.objects.filter(code=method_code, is_active=True).first()
        if not method:
            return JsonResponse({'success': False, 'error': f'Método "{method_code}" no disponible'}, status=400)

        if transaction.total <= 0:
            return JsonResponse({'success': False, 'error': 'El carrito está vacío'}, status=400)

        # Delegate to the existing checkout service
        success, result = CheckoutService.process_payment(
            transaction_id=transaction.id,
            payments=[{'method_id': method.id, 'amount': float(transaction.total)}],
        )

        if success:
            return JsonResponse({
                'success': True,
                'ticket_number': result['ticket_number'],
                'total': float(result['total']),
                'change': float(result.get('change', 0)),
                'transaction_id': result['transaction_id'],
                'method_name': method.name,
            })
        return JsonResponse({'success': False, 'error': result.get('error', 'Error al cobrar')}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos inválidos'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

