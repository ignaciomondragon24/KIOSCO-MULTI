"""
Granel Views — CRUD de depósito y carameleras, APIs para aperturas,
auditorías y registro de ventas desde el POS.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Sum, Count
from decimal import Decimal, InvalidOperation
import json

from decorators.decorators import stock_manager_required
from stocks.models import Product
from .models import (
    Caramelera,
    AperturaBulto,
    VentaGranel,
    AuditoriaCaramelera,
)
from .services import GranelService


# ============================================================
# ProductoDeposito — CRUD
# ============================================================

@login_required
@stock_manager_required
def deposito_list(request):
    """Lista de productos del inventario marcados como 'para caramelera'."""
    qs = Product.objects.filter(es_deposito_caramelera=True, is_active=True).order_by('name')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(name__icontains=q) | Product.objects.filter(
            es_deposito_caramelera=True, is_active=True, marca__icontains=q
        )
        qs = qs.distinct()

    return render(request, 'granel/deposito_list.html', {
        'productos': qs,
        'q': q,
    })


@login_required
@stock_manager_required
def deposito_edit(request, pk):
    """Redirige al formulario estándar del inventario para editar el producto."""
    return redirect('stocks:product_edit', pk=pk)


@login_required
@stock_manager_required
@require_POST
def api_deposito_ajustar_stock(request, pk):
    """POST: ajusta el current_stock de un Product (depósito caramelera)."""
    producto = get_object_or_404(Product, pk=pk, es_deposito_caramelera=True)
    try:
        data = json.loads(request.body)
        delta = int(data.get('delta', 0))
        nuevo = int(producto.current_stock) + delta
        if nuevo < 0:
            return JsonResponse({'error': 'El stock no puede quedar negativo.'}, status=400)
        producto.current_stock = nuevo
        producto.save(update_fields=['current_stock', 'updated_at'])
        return JsonResponse({
            'success': True,
            'stock_unidades': int(producto.current_stock),
        })
    except (ValueError, json.JSONDecodeError) as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================================
# Caramelera — CRUD + detalle
# ============================================================

@login_required
@stock_manager_required
def caramelera_list(request):
    """Lista de carameleras activas con stock, precios y margen estimado."""
    carameleras = (
        Caramelera.objects.filter(is_active=True)
        .order_by('nombre')
    )
    return render(request, 'granel/caramelera_list.html', {'carameleras': carameleras})


@login_required
@stock_manager_required
def caramelera_create(request):
    """Formulario para crear una nueva Caramelera."""
    if request.method == 'POST':
        return _caramelera_save(request, None)
    productos = Product.objects.filter(es_deposito_caramelera=True, is_active=True).order_by('name')
    return render(request, 'granel/caramelera_form.html', {
        'title': 'Nueva Caramelera',
        'caramelera': None,
        'productos_deposito': productos,
    })


@login_required
@stock_manager_required
def caramelera_edit(request, pk):
    """Formulario para editar una Caramelera."""
    caramelera = get_object_or_404(Caramelera, pk=pk)
    if request.method == 'POST':
        return _caramelera_save(request, caramelera)
    productos = Product.objects.filter(es_deposito_caramelera=True, is_active=True).order_by('name')
    try:
        autorizados_ids = list(
            caramelera.productos_autorizados.values_list('pk', flat=True)
        )
    except Exception:
        autorizados_ids = []
    return render(request, 'granel/caramelera_form.html', {
        'title': f'Editar {caramelera.nombre}',
        'caramelera': caramelera,
        'productos_deposito': productos,
        'autorizados_ids': autorizados_ids,
    })


def _caramelera_save(request, caramelera):
    """Lógica compartida de creación/edición de Caramelera."""
    nombre = request.POST.get('nombre', '').strip()
    precio_100g_raw = request.POST.get('precio_100g', '').strip()
    precio_cuarto_raw = request.POST.get('precio_cuarto', '0').strip()
    autorizados_ids = request.POST.getlist('productos_autorizados')

    errors = []
    if not nombre:
        errors.append('El nombre es obligatorio.')
    try:
        precio_100g = Decimal(precio_100g_raw)
        if precio_100g <= 0:
            errors.append('El precio por 100g debe ser mayor a 0.')
    except (InvalidOperation, ValueError):
        errors.append('Precio por 100g inválido.')
        precio_100g = Decimal('0')
    try:
        precio_cuarto = Decimal(precio_cuarto_raw) if precio_cuarto_raw else Decimal('0')
    except (InvalidOperation, ValueError):
        precio_cuarto = Decimal('0')

    productos = Product.objects.filter(es_deposito_caramelera=True, is_active=True).order_by('name')
    context = {
        'title': 'Editar' if caramelera else 'Nueva Caramelera',
        'caramelera': caramelera,
        'productos_deposito': productos,
        'autorizados_ids': [int(x) for x in autorizados_ids if x.isdigit()],
        'errors': errors,
    }

    if errors:
        return render(request, 'granel/caramelera_form.html', context)

    if caramelera is None:
        caramelera = Caramelera()

    caramelera.nombre = nombre
    caramelera.precio_100g = precio_100g
    caramelera.precio_cuarto = precio_cuarto
    caramelera.save()

    # Sincronizar productos autorizados
    autorizados = Product.objects.filter(
        pk__in=[int(x) for x in autorizados_ids if x.isdigit()],
        es_deposito_caramelera=True,
        is_active=True,
    )
    caramelera.productos_autorizados.set(autorizados)

    # Crear/actualizar el producto POS vinculado (is_granel=True)
    _sync_caramelera_pos_product(caramelera)

    return redirect('granel:caramelera_detail', pk=caramelera.pk)


def _sync_caramelera_pos_product(caramelera):
    """Crea o actualiza el producto is_granel de stocks vinculado a esta caramelera.

    El producto POS es el que aparece en el buscador del POS y dispara el modal de peso.
    granel_price_weight_grams siempre = 100 (precio por 100g).
    """
    pos_product = caramelera.producto_pos.filter(is_granel=True).first()
    if pos_product is None:
        pos_product = Product(
            is_granel=True,
            granel_caramelera=caramelera,
        )
    pos_product.name = caramelera.nombre
    pos_product.sale_price = caramelera.precio_100g
    pos_product.sale_price_250g = caramelera.precio_cuarto
    pos_product.granel_price_weight_grams = 100  # siempre precio/100g
    pos_product.is_active = caramelera.is_active
    pos_product.current_stock = caramelera.stock_gramos_actual
    pos_product.weighted_avg_cost_per_gram = caramelera.costo_ponderado_gramo
    pos_product.save()


@login_required
@stock_manager_required
def caramelera_detail(request, pk):
    """
    Vista principal de una caramelera:
    - Stock actual, precios, costo ponderado, margen
    - Historial de aperturas recientes
    - Ranking de rotación por producto
    - Ventas recientes con margen real
    - Card de resumen de margen acumulado
    - Modal Abrir Paquete
    - Modal Auditoría
    """
    caramelera = get_object_or_404(Caramelera, pk=pk)

    # Productos autorizados con stock en depósito (stocks.Product)
    autorizados = caramelera.productos_autorizados.filter(is_active=True).order_by('name')

    # Historial de aperturas (últimas 20)
    aperturas = (
        AperturaBulto.objects.filter(caramelera=caramelera)
        .select_related('producto', 'abierto_por')
        .order_by('-abierto_en')[:20]
    )

    # Ranking de rotación — agrupado por producto
    ranking = (
        AperturaBulto.objects.filter(caramelera=caramelera)
        .values('producto__id', 'producto__name', 'producto__marca')
        .annotate(
            bolsas=Count('id'),
            gramos_total=Sum('gramos_agregados'),
        )
        .order_by('-bolsas')[:10]
    )

    # Ventas recientes
    ventas = (
        VentaGranel.objects.filter(caramelera=caramelera)
        .order_by('-vendido_en')[:20]
    )

    # Resumen de margen real total
    resumen_ventas = VentaGranel.objects.filter(caramelera=caramelera).aggregate(
        total_recaudado=Sum('precio_cobrado'),
        total_costo=Sum('costo_total'),
        total_ganancia=Sum('ganancia'),
    )

    # Historial de auditorías (últimas 20)
    auditorias = (
        AuditoriaCaramelera.objects.filter(caramelera=caramelera)
        .select_related('auditado_por')
        .order_by('-auditado_en')[:20]
    )

    return render(request, 'granel/caramelera_detail.html', {
        'caramelera': caramelera,
        'autorizados': autorizados,
        'aperturas': aperturas,
        'ranking': ranking,
        'ventas': ventas,
        'resumen_ventas': resumen_ventas,
        'auditorias': auditorias,
    })


# ============================================================
# APIs JSON
# ============================================================

@login_required
@stock_manager_required
@require_POST
def api_abrir_paquete(request, pk):
    """POST {producto_id, cantidad?, notas?} — Abre paquetes del depósito hacia la caramelera."""
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        notas = data.get('notas', '')
        cantidad = int(data.get('cantidad', 1))

        if not producto_id:
            return JsonResponse({'error': 'Falta producto_id'}, status=400)
        if cantidad < 1:
            return JsonResponse({'error': 'La cantidad debe ser al menos 1'}, status=400)

        apertura = GranelService.abrir_paquete(
            caramelera_id=pk,
            producto_deposito_id=int(producto_id),
            user=request.user,
            notas=notas,
            cantidad=cantidad,
        )

        return JsonResponse({
            'success': True,
            'cantidad': cantidad,
            'gramos_agregados': float(apertura.gramos_agregados),
            'nuevo_stock': float(apertura.stock_gramos_despues),
            'nuevo_costo_ponderado': float(apertura.costo_ponderado_despues),
            'unidades_restantes_deposito': apertura.unidades_restantes_deposito,
            'producto_nombre': apertura.producto.name,
        })
    except (Caramelera.DoesNotExist, Product.DoesNotExist):
        return JsonResponse({'error': 'No encontrado'}, status=404)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@stock_manager_required
@require_POST
def api_auditoria(request, pk):
    """POST {peso_real, motivo?} — Registra una auditoría y ajusta el stock."""
    try:
        data = json.loads(request.body)
        peso_real = data.get('peso_real')
        motivo = data.get('motivo', '')

        if peso_real is None:
            return JsonResponse({'error': 'Falta peso_real'}, status=400)
        peso_real = Decimal(str(peso_real))
        if peso_real < 0:
            return JsonResponse({'error': 'El peso real no puede ser negativo'}, status=400)

        auditoria = GranelService.realizar_auditoria(
            caramelera_id=pk,
            peso_real_balanza=peso_real,
            user=request.user,
            motivo=motivo,
        )

        return JsonResponse({
            'success': True,
            'stock_sistema': float(auditoria.stock_sistema_gramos),
            'peso_real': float(auditoria.peso_real_balanza_gramos),
            'diferencia': float(auditoria.diferencia_gramos),
            'porcentaje_merma': float(auditoria.porcentaje_merma),
            'nuevo_stock': float(auditoria.peso_real_balanza_gramos),
        })
    except Caramelera.DoesNotExist:
        return JsonResponse({'error': 'No encontrado'}, status=404)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
def api_venta_granel(request, pk):
    """
    POST {gramos, precio_cobrado, pos_transaction_id?}
    Registra una VentaGranel y descuenta el stock.
    Puede ser llamado sin @stock_manager_required porque también lo llama el POS.
    Requiere login.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'No autenticado'}, status=401)

    caramelera = get_object_or_404(Caramelera, pk=pk)
    try:
        data = json.loads(request.body)
        gramos = data.get('gramos')
        precio_cobrado = data.get('precio_cobrado')
        pos_transaction_id = data.get('pos_transaction_id')

        if gramos is None or precio_cobrado is None:
            return JsonResponse({'error': 'Faltan gramos o precio_cobrado'}, status=400)

        venta = GranelService.registrar_venta(
            caramelera_id=caramelera.pk,
            gramos_vendidos=gramos,
            precio_cobrado=precio_cobrado,
            pos_transaction_id=pos_transaction_id,
        )
        caramelera.refresh_from_db()

        return JsonResponse({
            'success': True,
            'venta_id': venta.pk,
            'ganancia': float(venta.ganancia),
            'nuevo_stock': float(caramelera.stock_gramos_actual),
        })
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def api_caramelera_info(request, pk):
    """GET — Devuelve datos actuales de la caramelera para el POS."""
    caramelera = get_object_or_404(Caramelera, pk=pk, is_active=True)
    return JsonResponse({
        'id': caramelera.pk,
        'nombre': caramelera.nombre,
        'stock_gramos': float(caramelera.stock_gramos_actual),
        'precio_100g': float(caramelera.precio_100g),
        'precio_cuarto': float(caramelera.precio_cuarto),
        'costo_ponderado_gramo': float(caramelera.costo_ponderado_gramo),
        'margen_100g': float(caramelera.margen_100g),
    })
