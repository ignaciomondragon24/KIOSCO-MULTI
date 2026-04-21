import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST

from decorators.decorators import group_required
from .models import SignTemplate, SignBatch, SignItem, ensure_default_templates
from .services import auto_fill_product_data


@login_required
@group_required('Admin', 'Cajero Manager')
def template_list(request):
    """Catálogo de plantillas pre-armadas."""
    ensure_default_templates()
    templates = SignTemplate.objects.filter(is_active=True).order_by('sign_type', 'width_mm')
    # Solo mostrar plantillas con layout completo
    templates = [t for t in templates if t.layout.get('elements')]

    # Agrupar por tipo
    type_meta = {
        'simple': {'icon': 'fa-tag', 'color': '#2D1E5F'},
        'promo': {'icon': 'fa-fire', 'color': '#E91E8C'},
        'bulk': {'icon': 'fa-box', 'color': '#F5D000'},
        'weight': {'icon': 'fa-balance-scale', 'color': '#28a745'},
    }

    grouped = []
    seen_types = set()
    for t in templates:
        if t.sign_type not in seen_types:
            meta = type_meta.get(t.sign_type, {'icon': 'fa-tag', 'color': '#666'})
            grouped.append({
                'type_key': t.sign_type,
                'label': t.get_sign_type_display(),
                'icon': meta['icon'],
                'color': meta['color'],
                'templates': [],
            })
            seen_types.add(t.sign_type)
        # Append to last group
        for g in grouped:
            if g['type_key'] == t.sign_type:
                g['templates'].append(t)
                break

    return render(request, 'signage/template_list.html', {
        'grouped': grouped,
    })


@login_required
@group_required('Admin', 'Cajero Manager')
def template_delete(request, pk):
    """Eliminar (desactivar) una plantilla."""
    template = get_object_or_404(SignTemplate, pk=pk)
    if request.method == 'POST':
        template.is_active = False
        template.save()
        messages.success(request, f'Plantilla "{template.name}" eliminada.')
        return redirect('signage:template_list')
    return render(request, 'signage/template_confirm_delete.html', {
        'template': template,
    })


@login_required
@group_required('Admin', 'Cajero Manager')
def generate(request, pk):
    """Generar carteles a partir de una plantilla."""
    template = get_object_or_404(SignTemplate, pk=pk)
    variables = SignTemplate.get_type_variables(template.sign_type)

    return render(request, 'signage/generate.html', {
        'template': template,
        'layout_json': json.dumps(template.layout),
        'variables': variables,
        'variables_json': json.dumps(variables),
    })


@login_required
def api_product_data(request):
    """API: Auto-completar datos de producto para un tipo de cartel."""
    from stocks.models import Product

    product_id = request.GET.get('product_id')
    sign_type = request.GET.get('sign_type', 'simple')

    if not product_id:
        return JsonResponse({'error': 'product_id requerido'}, status=400)

    try:
        product = Product.objects.get(pk=product_id)
        data = auto_fill_product_data(product, sign_type)
        return JsonResponse({
            'success': True,
            'product_id': product.pk,
            'product_name': product.name,
            'data': data,
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)


@login_required
@group_required('Admin', 'Cajero Manager')
def print_view(request):
    """Vista de impresión optimizada con nesting."""
    return render(request, 'signage/print_preview.html')


@login_required
@group_required('Admin', 'Cajero Manager')
def batch_list(request):
    """Historial de lotes generados."""
    batches = SignBatch.objects.select_related('template', 'created_by')
    return render(request, 'signage/batch_list.html', {
        'batches': batches,
    })


@login_required
@require_POST
def save_batch(request):
    """API: Guardar un lote de carteles."""
    try:
        data = json.loads(request.body)
        template_id = data.get('template_id')
        if not template_id:
            return JsonResponse({'error': 'template_id requerido'}, status=400)

        template = get_object_or_404(SignTemplate, pk=template_id)

        batch = SignBatch.objects.create(
            template=template,
            name=data.get('name', f'Lote {template.name}')[:200],
            paper_size=data.get('paper_size', 'A4'),
            created_by=request.user,
        )

        for i, item_data in enumerate(data.get('items', [])):
            product_id = item_data.get('product_id')
            SignItem.objects.create(
                batch=batch,
                product_id=product_id if product_id else None,
                data_json=json.dumps(item_data.get('data', {})),
                copies=max(1, int(item_data.get('copies', 1))),
                order=i,
            )

        return JsonResponse({'success': True, 'batch_id': batch.pk})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)


@login_required
@group_required('Admin', 'Cajero Manager')
def generate_all(request):
    """Generar TODOS los carteles: precios de inventario + promociones activas."""
    ensure_default_templates()
    templates = SignTemplate.objects.filter(is_active=True, is_default=True)
    # Build quick lookup: sign_type → smallest template (use smaller for nesting efficiency)
    type_templates = {}
    for t in templates.order_by('width_mm'):
        if t.sign_type not in type_templates:
            type_templates[t.sign_type] = t

    # Also offer bigger sizes
    type_templates_big = {}
    for t in templates.order_by('-width_mm'):
        if t.sign_type not in type_templates_big:
            type_templates_big[t.sign_type] = t

    template_choices = {}
    for st in ('simple', 'promo', 'bulk', 'weight'):
        choices = list(templates.filter(sign_type=st).order_by('width_mm'))
        if choices:
            template_choices[st] = choices

    return render(request, 'signage/generate_all.html', {
        'template_choices': template_choices,
        'type_templates': {k: v.pk for k, v in type_templates.items()},
        'type_templates_json': json.dumps({k: v.pk for k, v in type_templates.items()}),
    })


@login_required
def api_generate_all_data(request):
    """API: Genera todos los datos de carteles según inventario y promos activas."""
    from stocks.models import Product
    from promotions.models import Promotion

    template_simple_id = request.GET.get('tpl_simple')
    template_promo_id = request.GET.get('tpl_promo')
    template_bulk_id = request.GET.get('tpl_bulk')
    template_weight_id = request.GET.get('tpl_weight')

    products = Product.objects.filter(is_active=True, sale_price__gt=0).select_related(
        'category', 'unit_of_measure'
    ).order_by('name')

    # Pre-fetch all promo data in 1 query to avoid N+1
    promo_product_map = {}  # product_id -> promo
    active_promos = Promotion.objects.filter(
        status='active',
        promo_type__in=['nxm', 'quantity_discount']
    ).prefetch_related('products')
    for promo in active_promos:
        for p in promo.products.all():
            promo_product_map[p.pk] = promo
    promo_product_ids = set(promo_product_map.keys())

    # Build all items flat, grouped by category
    categories_map = {}  # cat_id -> { id, name, color, items: [] }
    layouts = {}  # sign_type -> layout info

    for product in products:
        has_promo = product.pk in promo_product_ids

        if has_promo:
            sign_type = 'promo'
        elif product.is_bulk and product.bulk_unit in ('kg', 'g'):
            sign_type = 'weight'
        elif product.units_per_package and product.units_per_package > 1:
            sign_type = 'bulk'
        else:
            sign_type = 'simple'

        cat_id = product.category_id or 0
        cat_name = product.category.name if product.category else 'Sin categoría'
        cat_color = product.category.color if product.category else '#999999'

        if cat_id not in categories_map:
            categories_map[cat_id] = {
                'id': cat_id,
                'name': cat_name,
                'color': cat_color,
                'items': [],
            }

        promo = promo_product_map.get(product.pk)
        data = auto_fill_product_data(product, sign_type, promo=promo)
        categories_map[cat_id]['items'].append({
            'product_id': product.pk,
            'product_name': product.name,
            'sign_type': sign_type,
            'data': data,
        })

    # Load template layouts for each requested type
    tpl_ids = {
        'simple': template_simple_id,
        'promo': template_promo_id,
        'bulk': template_bulk_id,
        'weight': template_weight_id,
    }
    for st, tid in tpl_ids.items():
        if tid:
            try:
                tpl = SignTemplate.objects.get(pk=tid)
                layouts[st] = {
                    'layout': tpl.layout,
                    'width_mm': tpl.width_mm,
                    'height_mm': tpl.height_mm,
                    'template_name': tpl.name,
                }
            except SignTemplate.DoesNotExist:
                pass

    # Sort categories by name, convert to list
    categories_list = sorted(categories_map.values(), key=lambda c: c['name'] or '')
    total = sum(len(c['items']) for c in categories_list)

    return JsonResponse({
        'success': True,
        'categories': categories_list,
        'layouts': layouts,
        'total_products': total,
    })
