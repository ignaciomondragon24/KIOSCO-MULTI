"""
Promotions Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import json

from .models import Promotion, PromotionProduct, PromotionGroup
from .forms import PromotionForm
from .engine import PromotionEngine
from decorators.decorators import group_required


def _resolve_promo_group(group_name):
    """
    Devuelve un PromotionGroup existente o lo crea. None si group_name vacío.
    """
    if not group_name:
        return None
    name = group_name.strip()
    if not name:
        return None
    obj, _ = PromotionGroup.objects.get_or_create(name=name)
    return obj


@login_required
@group_required(['Admin', 'Cajero Manager'])
def promotion_list(request):
    """List all promotions."""
    promotions = Promotion.objects.all()
    
    # Counts for stats cards
    active_count = Promotion.objects.filter(status='active').count()
    paused_count = Promotion.objects.filter(status='paused').count()
    draft_count = Promotion.objects.filter(status='draft').count()
    total_count = Promotion.objects.count()
    
    # Filters
    status = request.GET.get('status', '')
    promo_type = request.GET.get('type', '')
    search = request.GET.get('search', '')
    
    if status:
        promotions = promotions.filter(status=status)
    if promo_type:
        promotions = promotions.filter(promo_type=promo_type)
    if search:
        promotions = promotions.filter(name__icontains=search)
    
    context = {
        'promotions': promotions,
        'selected_status': status,
        'selected_type': promo_type,
        'search': search,
        'status': status,
        'type': promo_type,
        'active_count': active_count,
        'paused_count': paused_count,
        'draft_count': draft_count,
        'total_count': total_count,
    }
    
    return render(request, 'promotions/promotion_list.html', context)


@login_required
@group_required(['Admin', 'Cajero Manager'])
def promotion_create(request):
    """Create new promotion."""
    if request.method == 'POST':
        # Build mutable copy of POST data to fix field names
        post_data = request.POST.copy()
        
        # Map HTML form field names to model field names based on promo_type
        promo_type = post_data.get('promo_type', 'nxm')

        if promo_type == 'nxm':
            post_data['quantity_required'] = post_data.get('buy_quantity') or '2'
            post_data['quantity_charged'] = post_data.get('pay_quantity') or '1'
        elif promo_type == 'nx_fixed_price':
            post_data['quantity_required'] = post_data.get('nx_quantity') or '2'
            post_data['final_price'] = post_data.get('nx_fixed_price') or '0'
        elif promo_type == 'combo':
            post_data['final_price'] = post_data.get('combo_price') or '0'
        elif promo_type == 'simple_discount':
            post_data['discount_percent'] = post_data.get('discount_percent_simple') or '0'
            
        # Set default status to active if not provided
        if not post_data.get('status'):
            post_data['status'] = 'active'
            
        # Handle products - convert comma-separated string to list
        products_str = post_data.get('products', '')
        product_ids = []
        if products_str:
            product_ids = [int(pid.strip()) for pid in products_str.split(',') if pid.strip().isdigit()]
            
        # Create promotion directly without the form for products
        try:
            from stocks.models import Product
            from decimal import Decimal

            # Safe conversions
            def safe_int(val, default=0):
                try:
                    return int(val) if val else default
                except (ValueError, TypeError):
                    return default

            def safe_decimal(val, default='0'):
                try:
                    return Decimal(str(val)) if val else Decimal(default)
                except:
                    return Decimal(default)

            # Validate required price/discount based on promo_type
            validation_errors = []
            if promo_type in ('nx_fixed_price', 'combo'):
                if safe_decimal(post_data.get('final_price'), '0') <= 0:
                    validation_errors.append('Debe ingresar el precio para esta promoción.')
            elif promo_type == 'second_unit':
                if safe_decimal(post_data.get('second_unit_discount'), '0') <= 0:
                    validation_errors.append('Debe ingresar el descuento de 2da unidad.')
            elif promo_type in ('quantity_discount', 'simple_discount'):
                if safe_decimal(post_data.get('discount_percent'), '0') <= 0:
                    validation_errors.append('Debe ingresar el porcentaje de descuento.')

            if not product_ids:
                validation_errors.append('Debe seleccionar al menos un producto.')

            if validation_errors:
                for error in validation_errors:
                    messages.error(request, error)
                form = PromotionForm(post_data)
                # Pass selected products so they survive re-render
                selected_products = Product.objects.filter(id__in=product_ids) if product_ids else []
                return render(request, 'promotions/promotion_form.html', {
                    'form': form,
                    'title': 'Nueva Promoción',
                    'selected_products': selected_products,
                    'existing_groups': PromotionGroup.objects.all(),
                    'current_group_name': post_data.get('group_name', ''),
                })

            # Days: if no day checkbox is present in POST, default all to True
            day_fields = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            any_day_in_post = any(d in post_data for d in day_fields)
            if any_day_in_post:
                day_values = {d: post_data.get(d) == 'on' for d in day_fields}
            else:
                day_values = {d: True for d in day_fields}

            promotion = Promotion(
                name=post_data.get('name', ''),
                description=post_data.get('description', ''),
                promo_type=promo_type,
                status=post_data.get('status', 'active'),
                priority=safe_int(post_data.get('priority'), 50),
                is_combinable=post_data.get('is_combinable') == 'on',
                applies_to_packaging_type=(
                    post_data.get('applies_to_packaging_type') or 'unit'
                ),
                # Days
                **day_values,
                # NxM / nx_fixed_price config
                quantity_required=safe_int(post_data.get('quantity_required'), 2),
                quantity_charged=safe_int(post_data.get('quantity_charged'), 1),
                # Discounts
                discount_percent=safe_decimal(post_data.get('discount_percent'), '0'),
                second_unit_discount=safe_decimal(post_data.get('second_unit_discount'), '0'),
                final_price=safe_decimal(post_data.get('final_price'), '0'),
                min_quantity=safe_int(post_data.get('min_quantity'), 1),
                # Grupo enlazado (opcional)
                group=_resolve_promo_group(post_data.get('group_name', '')),
                created_by=request.user
            )
            
            # Handle dates
            start_date = post_data.get('start_date')
            end_date = post_data.get('end_date')
            if start_date:
                promotion.start_date = start_date
            if end_date:
                promotion.end_date = end_date
                
            promotion.save()
            
            # Add products
            if product_ids:
                products = Product.objects.filter(id__in=product_ids)
                for product in products:
                    PromotionProduct.objects.create(promotion=promotion, product=product)
            
            messages.success(request, f'Promoción "{promotion.name}" creada correctamente.')
            return redirect('promotions:promotion_list')
            
        except Exception as e:
            messages.error(request, f'Error al crear la promoción: {str(e)}')
            form = PromotionForm(post_data)
    else:
        form = PromotionForm()

    return render(request, 'promotions/promotion_form.html', {
        'form': form,
        'title': 'Nueva Promoción',
        'existing_groups': PromotionGroup.objects.all(),
    })


@login_required
@group_required(['Admin', 'Cajero Manager'])
def promotion_edit(request, pk):
    """Edit promotion."""
    promotion = get_object_or_404(Promotion, pk=pk)
    
    if request.method == 'POST':
        post_data = request.POST.copy()

        # Handle products - convert comma-separated string to list
        products_str = post_data.get('products', '')
        product_ids = []
        if products_str:
            product_ids = [int(pid.strip()) for pid in products_str.split(',') if pid.strip().isdigit()]

        # Map HTML form field names based on promo_type
        promo_type = post_data.get('promo_type', promotion.promo_type)

        if promo_type == 'nxm':
            post_data['quantity_required'] = post_data.get('buy_quantity') or '2'
            post_data['quantity_charged'] = post_data.get('pay_quantity') or '1'
        elif promo_type == 'nx_fixed_price':
            post_data['quantity_required'] = post_data.get('nx_quantity') or '2'
            post_data['final_price'] = post_data.get('nx_fixed_price') or '0'
        elif promo_type == 'combo':
            post_data['final_price'] = post_data.get('combo_price') or '0'
        elif promo_type == 'simple_discount':
            post_data['discount_percent'] = post_data.get('discount_percent_simple') or '0'

        try:
            from stocks.models import Product
            from decimal import Decimal

            def safe_int(val, default=0):
                try:
                    return int(val) if val else default
                except (ValueError, TypeError):
                    return default

            def safe_decimal(val, default='0'):
                try:
                    return Decimal(str(val)) if val else Decimal(default)
                except:
                    return Decimal(default)

            # Validate required price/discount based on promo_type
            validation_errors = []
            if promo_type in ('nx_fixed_price', 'combo'):
                if safe_decimal(post_data.get('final_price'), '0') <= 0:
                    validation_errors.append('Debe ingresar el precio para esta promoción.')
            elif promo_type == 'second_unit':
                if safe_decimal(post_data.get('second_unit_discount'), '0') <= 0:
                    validation_errors.append('Debe ingresar el descuento de 2da unidad.')
            elif promo_type in ('quantity_discount', 'simple_discount'):
                if safe_decimal(post_data.get('discount_percent'), '0') <= 0:
                    validation_errors.append('Debe ingresar el porcentaje de descuento.')

            if not product_ids:
                validation_errors.append('Debe seleccionar al menos un producto.')

            if validation_errors:
                for error in validation_errors:
                    messages.error(request, error)
                form = PromotionForm(post_data, instance=promotion)
                selected_products = Product.objects.filter(id__in=product_ids) if product_ids else list(promotion.products.all())
                return render(request, 'promotions/promotion_form.html', {
                    'form': form,
                    'title': 'Editar Promoción',
                    'promotion': promotion,
                    'selected_products': selected_products,
                    'existing_groups': PromotionGroup.objects.all(),
                    'current_group_name': post_data.get('group_name', promotion.group.name if promotion.group else ''),
                })

            promotion.name = post_data.get('name', promotion.name)
            promotion.description = post_data.get('description', '')
            promotion.promo_type = promo_type
            promotion.status = post_data.get('status', promotion.status) or 'active'
            promotion.priority = safe_int(post_data.get('priority'), 50)
            promotion.is_combinable = post_data.get('is_combinable') == 'on'
            promotion.applies_to_packaging_type = (
                post_data.get('applies_to_packaging_type') or 'unit'
            )
            # Days: if no day checkbox present in POST, keep existing values
            day_fields = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            any_day_in_post = any(d in post_data for d in day_fields)
            if any_day_in_post:
                for d in day_fields:
                    setattr(promotion, d, post_data.get(d) == 'on')
            # else: keep existing day values unchanged
            # NxM / N por Precio Fijo config
            promotion.quantity_required = safe_int(post_data.get('quantity_required'), 2)
            promotion.quantity_charged = safe_int(post_data.get('quantity_charged'), 1)
            # Discounts
            promotion.discount_percent = safe_decimal(post_data.get('discount_percent'), '0')
            promotion.second_unit_discount = safe_decimal(post_data.get('second_unit_discount'), '0')
            promotion.final_price = safe_decimal(post_data.get('final_price'), '0')
            promotion.min_quantity = safe_int(post_data.get('min_quantity'), 1)
            # Grupo enlazado: vacío → desvincular; con valor → get-or-create
            promotion.group = _resolve_promo_group(post_data.get('group_name', ''))
            
            # Handle dates
            start_date = post_data.get('start_date')
            end_date = post_data.get('end_date')
            promotion.start_date = start_date if start_date else None
            promotion.end_date = end_date if end_date else None
                
            promotion.save()
            
            # Update products
            PromotionProduct.objects.filter(promotion=promotion).delete()
            if product_ids:
                products = Product.objects.filter(id__in=product_ids)
                for product in products:
                    PromotionProduct.objects.create(promotion=promotion, product=product)
            
            messages.success(request, f'Promoción "{promotion.name}" actualizada correctamente.')
            return redirect('promotions:promotion_list')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar la promoción: {str(e)}')
            form = PromotionForm(instance=promotion)
    else:
        initial_products = promotion.products.all()
        form = PromotionForm(instance=promotion, initial={'products': initial_products})
    
    return render(request, 'promotions/promotion_form.html', {
        'form': form,
        'title': 'Editar Promoción',
        'promotion': promotion,
        'existing_groups': PromotionGroup.objects.all(),
        'current_group_name': promotion.group.name if promotion.group else '',
    })


@login_required
@group_required(['Admin', 'Cajero Manager'])
def promotion_detail(request, pk):
    """Promotion detail."""
    promotion = get_object_or_404(Promotion, pk=pk)
    products = promotion.products.all()
    
    return render(request, 'promotions/promotion_detail.html', {
        'promotion': promotion,
        'products': products
    })


@login_required
@group_required(['Admin'])
def promotion_delete(request, pk):
    """Delete promotion — solo Admin, requiere confirmación escribiendo el nombre."""
    promotion = get_object_or_404(Promotion, pk=pk)

    if request.method == 'POST':
        confirm_name = request.POST.get('confirm_name', '').strip()
        if confirm_name != promotion.name:
            messages.error(
                request,
                f'El nombre no coincide. Escribí "{promotion.name}" exacto para confirmar.'
            )
            return render(request, 'promotions/promotion_confirm_delete.html', {
                'promotion': promotion
            })
        name = promotion.name
        promotion.delete()
        messages.success(request, f'Promoción "{name}" eliminada correctamente.')
        return redirect('promotions:promotion_list')

    return render(request, 'promotions/promotion_confirm_delete.html', {
        'promotion': promotion
    })


@login_required
@group_required(['Admin', 'Cajero Manager'])
@require_POST
def promotion_activate(request, pk):
    """Activate promotion."""
    promotion = get_object_or_404(Promotion, pk=pk)
    promotion.status = 'active'
    promotion.save()
    messages.success(request, f'Promoción "{promotion.name}" activada.')
    return redirect('promotions:promotion_list')


@login_required
@group_required(['Admin', 'Cajero Manager'])
@require_POST
def promotion_pause(request, pk):
    """Pause promotion."""
    promotion = get_object_or_404(Promotion, pk=pk)
    promotion.status = 'paused'
    promotion.save()
    messages.success(request, f'Promoción "{promotion.name}" pausada.')
    return redirect('promotions:promotion_list')


@login_required
def api_calculate(request):
    """API: Calculate promotions for cart items."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    cart_items = data.get('cart_items', [])
    
    result = PromotionEngine.calculate_cart(cart_items)
    
    return JsonResponse(result)
