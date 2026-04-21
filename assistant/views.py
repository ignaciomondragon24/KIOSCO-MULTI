"""
Views for the AI Assistant module.
"""
import json
import logging
import os
import base64

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.paginator import Paginator
from django.conf import settings as django_settings
from django.db import transaction
from django.utils import timezone
from decimal import Decimal, InvalidOperation

from .models import Conversation, Message, AssistantSettings, QueryLog
from .services import AssistantService, InvoiceScanService
from decorators.decorators import group_required

logger = logging.getLogger(__name__)


@login_required
def assistant_home(request):
    """
    Main assistant page with chat interface.
    """
    # Get or create active conversation for the user
    conversation = Conversation.objects.filter(
        user=request.user,
        is_active=True
    ).first()
    
    if not conversation:
        conversation = Conversation.objects.create(
            user=request.user,
            title='Nueva conversación'
        )
    
    # Get service for insights, suggestions and business metrics
    service = AssistantService()
    suggested_questions = service.get_suggested_questions()
    
    # Business metrics for the sidebar panel
    collector = service.data_collector
    sales_7d = collector.get_sales_summary(days=7)
    sales_30d = collector.get_sales_summary(days=30)
    inv = collector.get_inventory_status()
    
    business_metrics = {
        'ventas_7d': sales_7d.get('total_ventas', 0) if 'error' not in sales_7d else 0,
        'transacciones_7d': sales_7d.get('cantidad_transacciones', 0) if 'error' not in sales_7d else 0,
        'ticket_promedio_7d': sales_7d.get('ticket_promedio', 0) if 'error' not in sales_7d else 0,
        'ventas_30d': sales_30d.get('total_ventas', 0) if 'error' not in sales_30d else 0,
        'transacciones_30d': sales_30d.get('cantidad_transacciones', 0) if 'error' not in sales_30d else 0,
        'total_productos': inv.get('total_productos', 0) if 'error' not in inv else 0,
        'stock_bajo': inv.get('cantidad_stock_bajo', 0) if 'error' not in inv else 0,
        'sin_stock': inv.get('sin_stock', 0) if 'error' not in inv else 0,
        'valor_inventario': inv.get('valor_inventario', 0) if 'error' not in inv else 0,
    }
    
    # Top productos de la semana
    top_products = sales_7d.get('top_productos', [])[:5] if 'error' not in sales_7d else []
    
    # Check if assistant is configured
    settings_obj = AssistantSettings.get_settings()
    is_configured = bool(settings_obj.openai_api_key) or bool(getattr(django_settings, 'GEMINI_API_KEY', None)) or bool(os.getenv('GEMINI_API_KEY'))
    
    context = {
        'conversation': conversation,
        'suggested_questions': suggested_questions,
        'business_metrics': business_metrics,
        'top_products': top_products,
        'is_configured': is_configured,
        'settings': settings_obj,
    }
    
    return render(request, 'assistant/chat.html', context)


@login_required
@require_POST
def send_message(request):
    """
    API endpoint to send a message to the assistant.
    Returns JSON response.
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        
        if not user_message:
            return JsonResponse({
                'success': False,
                'error': 'El mensaje no puede estar vacío'
            }, status=400)
        
        # Get or create conversation
        if conversation_id:
            conversation = get_object_or_404(
                Conversation,
                id=conversation_id,
                user=request.user
            )
        else:
            conversation = Conversation.objects.create(
                user=request.user,
                title=user_message[:50] + '...' if len(user_message) > 50 else user_message
            )
        
        # Get response from assistant
        service = AssistantService()
        result = service.chat(
            user_message=user_message,
            conversation=conversation,
            include_context=True
        )
        
        # Log the query
        QueryLog.objects.create(
            user=request.user,
            query=user_message,
            response_time_ms=result.get('elapsed_ms', 0),
            tokens_used=result.get('tokens_used', 0),
            was_successful=result['success'],
            error_message=result.get('error', '')
        )
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'response': result['response'],
                'conversation_id': conversation.id,
                'tokens_used': result.get('tokens_used', 0)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Error desconocido')
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Formato de datos inválido'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST  
def new_conversation(request):
    """
    Start a new conversation.
    """
    # Deactivate current conversations
    Conversation.objects.filter(
        user=request.user,
        is_active=True
    ).update(is_active=False)
    
    # Create new conversation
    conversation = Conversation.objects.create(
        user=request.user,
        title='Nueva conversación'
    )
    
    return JsonResponse({
        'success': True,
        'conversation_id': conversation.id
    })


@login_required
@require_GET
def conversation_history(request):
    """
    Get list of past conversations.
    """
    conversations = Conversation.objects.filter(
        user=request.user
    ).order_by('-updated_at')[:20]
    
    data = [{
        'id': c.id,
        'title': c.title,
        'created_at': c.created_at.strftime('%d/%m/%Y %H:%M'),
        'updated_at': c.updated_at.strftime('%d/%m/%Y %H:%M'),
        'is_active': c.is_active,
        'message_count': c.messages.count()
    } for c in conversations]
    
    return JsonResponse({
        'success': True,
        'conversations': data
    })


@login_required
@require_GET
def load_conversation(request, conversation_id):
    """
    Load a specific conversation.
    """
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        user=request.user
    )
    
    # Set this as active and deactivate others
    Conversation.objects.filter(
        user=request.user,
        is_active=True
    ).update(is_active=False)
    
    conversation.is_active = True
    conversation.save()
    
    messages_data = [{
        'role': m.role,
        'content': m.content,
        'created_at': m.created_at.strftime('%H:%M')
    } for m in conversation.messages.order_by('created_at')]
    
    return JsonResponse({
        'success': True,
        'conversation': {
            'id': conversation.id,
            'title': conversation.title,
            'messages': messages_data
        }
    })


@login_required
@require_GET
def get_insights(request):
    """
    Get quick insights without AI call.
    """
    service = AssistantService()
    insights = service.get_quick_insights()
    
    return JsonResponse({
        'success': True,
        'insights': insights
    })


@login_required
@group_required('Admin')
def assistant_settings(request):
    """
    Settings page for the assistant (admin only).
    """
    settings_obj = AssistantSettings.get_settings()
    
    if request.method == 'POST':
        settings_obj.openai_api_key = request.POST.get('openai_api_key', '')
        settings_obj.model = request.POST.get('model', 'gemini-2.0-flash')
        
        # Validate numeric fields
        try:
            max_tokens = request.POST.get('max_tokens', '2000').strip()
            settings_obj.max_tokens = int(max_tokens) if max_tokens else 2000
        except ValueError:
            settings_obj.max_tokens = 2000
        
        try:
            temperature = request.POST.get('temperature', '0.7').strip()
            settings_obj.temperature = float(temperature) if temperature else 0.7
        except ValueError:
            settings_obj.temperature = 0.7
        
        settings_obj.system_prompt = request.POST.get('system_prompt', '')
        settings_obj.is_enabled = request.POST.get('is_enabled') == 'on'
        settings_obj.save()
        
        messages.success(request, 'Configuración guardada correctamente')
        return redirect('assistant:settings')
    
    # Get usage stats
    from django.db.models import Sum
    from django.utils import timezone
    from datetime import timedelta
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    usage_stats = QueryLog.objects.filter(
        created_at__gte=thirty_days_ago
    ).aggregate(
        total_queries=Count('id'),
        total_tokens=Sum('tokens_used'),
        avg_response_time=Avg('response_time_ms')
    )
    
    context = {
        'settings': settings_obj,
        'usage_stats': usage_stats,
        'available_models': [
            ('gemini-2.5-flash', 'Gemini 2.5 Flash (Recomendado)'),
            ('gemini-2.5-pro', 'Gemini 2.5 Pro'),
            ('gemini-2.0-flash', 'Gemini 2.0 Flash'),
            ('gemini-2.0-flash-lite', 'Gemini 2.0 Flash Lite'),
        ]
    }
    
    return render(request, 'assistant/settings.html', context)


@login_required
@group_required('Admin')
def query_logs(request):
    """
    View query logs (admin only).
    """
    logs = QueryLog.objects.select_related('user').order_by('-created_at')
    
    paginator = Paginator(logs, 50)
    page = request.GET.get('page', 1)
    logs_page = paginator.get_page(page)
    
    context = {
        'logs': logs_page,
    }
    
    return render(request, 'assistant/logs.html', context)


# Import Count and Avg for the settings view
from django.db.models import Count, Avg


@login_required
@group_required(['Admin'])
def scan_invoice_page(request):
    """Render the invoice scanning page."""
    from purchase.models import Supplier
    from stocks.models import ProductCategory

    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    categories = ProductCategory.objects.filter(is_active=True).order_by('name')
    context = {
        'suppliers': suppliers,
        'categories': categories,
    }
    return render(request, 'assistant/scan_invoice.html', context)


@login_required
@require_POST
@group_required(['Admin'])
def api_scan_invoice(request):
    """
    API endpoint: receive an invoice image and return extracted data.
    Accepts multipart form with 'image' file, or JSON with 'image_base64'.
    """
    try:
        if request.FILES.get('image'):
            image_file = request.FILES['image']
            # Validate file size (max 10MB)
            if image_file.size > 10 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'error': 'La imagen es demasiado grande. Máximo 10MB.'
                }, status=400)

            image_data = image_file.read()
            mime_type = image_file.content_type or 'image/jpeg'
        else:
            data = json.loads(request.body)
            image_b64 = data.get('image_base64', '')
            if not image_b64:
                return JsonResponse({
                    'success': False,
                    'error': 'No se recibió ninguna imagen.'
                }, status=400)

            # Handle data URI format
            if ',' in image_b64:
                header, image_b64 = image_b64.split(',', 1)
                if 'png' in header:
                    mime_type = 'image/png'
                elif 'webp' in header:
                    mime_type = 'image/webp'
                else:
                    mime_type = 'image/jpeg'
            else:
                mime_type = 'image/jpeg'

            image_data = base64.b64decode(image_b64)

        # Call Gemini Vision
        scanner = InvoiceScanService()
        result = scanner.scan_invoice(image_data, mime_type)

        if result['success']:
            return JsonResponse({
                'success': True,
                'data': result['data'],
                'elapsed_ms': result.get('elapsed_ms', 0),
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Error desconocido'),
                'raw_response': result.get('raw_response', ''),
            }, status=500)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Formato de datos inválido.'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in api_scan_invoice: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
@group_required(['Admin'])
def api_confirm_invoice(request):
    """
    API endpoint: confirm scanned invoice data.
    Creates Purchase + PurchaseItems, updates stock, optionally creates Expense.
    """
    try:
        def _to_decimal(value, default=Decimal('0')):
            """Parsea números tolerando coma decimal y separadores de miles."""
            if value is None:
                return default
            if isinstance(value, Decimal):
                return value
            if isinstance(value, (int, float)):
                try:
                    return Decimal(str(value))
                except (InvalidOperation, ValueError, TypeError):
                    return default

            s = str(value).strip()
            if not s:
                return default

            # Soporta: 1.234,56 | 1234.56 | 1234,56
            if ',' in s and '.' in s:
                s = s.replace('.', '').replace(',', '.')
            elif ',' in s:
                s = s.replace(',', '.')

            try:
                return Decimal(s)
            except (InvalidOperation, ValueError, TypeError):
                return default

        def _to_int(value, default=0):
            dec = _to_decimal(value, Decimal(default))
            try:
                return int(dec)
            except (ValueError, TypeError):
                return default

        data = json.loads(request.body)

        supplier_id = data.get('supplier_id')
        supplier_name = data.get('supplier_name', '').strip()
        numero_comprobante = data.get('numero_comprobante', '').strip()
        fecha_str = data.get('fecha', '')
        productos = data.get('productos', [])
        total = _to_decimal(data.get('total', 0), Decimal('0'))
        subtotal = _to_decimal(data.get('subtotal', 0), Decimal('0'))
        iva = _to_decimal(data.get('iva', 0), Decimal('0'))
        metodo_pago = data.get('metodo_pago', 'cash')
        notas = data.get('notas', '')
        registrar_gasto = data.get('registrar_gasto', False)
        actualizar_stock = data.get('actualizar_stock', True)

        if not isinstance(productos, list) or not productos:
            return JsonResponse({
                'success': False,
                'error': 'No hay productos para registrar.'
            }, status=400)

        # Parse date
        from datetime import datetime
        try:
            if fecha_str:
                for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
                    try:
                        fecha = datetime.strptime(fecha_str, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    fecha = timezone.now().date()
            else:
                fecha = timezone.now().date()
        except Exception:
            fecha = timezone.now().date()

        with transaction.atomic():
            from purchase.models import Supplier, Purchase, PurchaseItem
            from stocks.models import Product
            from stocks.services import StockManagementService

            # Get or create supplier
            supplier = None
            if supplier_id:
                try:
                    supplier = Supplier.objects.get(pk=supplier_id)
                except Supplier.DoesNotExist:
                    pass

            if not supplier and supplier_name:
                supplier, _ = Supplier.objects.get_or_create(
                    name=supplier_name,
                    defaults={'is_active': True}
                )

            if not supplier:
                supplier, _ = Supplier.objects.get_or_create(
                    name='Proveedor General',
                    defaults={'is_active': True}
                )

            # Create purchase order
            today = timezone.now().strftime('%Y%m%d')
            count = Purchase.objects.filter(
                order_number__startswith=f'OC-{today}'
            ).count() + 1
            order_number = f'OC-{today}-{count:04d}'

            purchase = Purchase.objects.create(
                supplier=supplier,
                order_number=order_number,
                status='received',
                order_date=fecha,
                received_date=fecha,
                subtotal=subtotal or total,
                tax=iva,
                total=total,
                notes=f"Cargado por escaneo de remito. {notas}".strip(),
                created_by=request.user,
            )

            # Process each product
            items_created = 0
            stock_updated = 0
            products_not_found = []
            auto_created_products = []

            for prod_data in productos:
                nombre = prod_data.get('nombre', '').strip()
                cantidad = _to_int(prod_data.get('cantidad', 0), 0)
                precio_unitario = _to_decimal(prod_data.get('precio_unitario', 0), Decimal('0'))
                codigo_barras = prod_data.get('codigo_barras', '').strip() or None
                product_id = prod_data.get('product_id') or None

                if not nombre or cantidad <= 0:
                    continue

                # Range validation for AI-sourced data
                if cantidad > 99999:
                    continue
                if precio_unitario < 0 or precio_unitario > Decimal('9999999'):
                    precio_unitario = Decimal('0')

                # Try to find matching product
                product = None

                # 1) Direct ID from frontend match
                if product_id:
                    try:
                        product = Product.objects.get(pk=int(product_id), is_active=True)
                    except (Product.DoesNotExist, ValueError, TypeError):
                        pass

                # 2) Barcode
                if not product and codigo_barras:
                    product = Product.objects.filter(
                        barcode=codigo_barras, is_active=True
                    ).first()

                # 3) Exact name
                if not product:
                    product = Product.objects.filter(
                        name__iexact=nombre, is_active=True
                    ).first()

                # 4) Partial name
                if not product:
                    product = Product.objects.filter(
                        name__icontains=nombre, is_active=True
                    ).first()

                if not product:
                    # Producto no encontrado → auto-crear con los datos del remito
                    p_cost = precio_unitario if precio_unitario > 0 else Decimal('0.01')
                    p_sale = (p_cost * Decimal('1.30')).quantize(Decimal('0.01'))
                    # Solo asignar el código de barras si no está ya en uso
                    safe_barcode = None
                    if codigo_barras and not Product.objects.filter(barcode=codigo_barras).exists():
                        safe_barcode = codigo_barras
                    product = Product.objects.create(
                        name=nombre,
                        barcode=safe_barcode,
                        purchase_price=p_cost,
                        cost_price=p_cost,
                        sale_price=p_sale,
                        is_active=False,
                    )
                    auto_created_products.append(nombre)

                # PurchaseItem exige unit_cost >= 0.01
                unit_cost_for_item = precio_unitario if precio_unitario > 0 else (product.purchase_price if product.purchase_price > 0 else Decimal('0.01'))

                # Create purchase item
                PurchaseItem.objects.create(
                    purchase=purchase,
                    product=product,
                    quantity=cantidad,
                    unit_cost=unit_cost_for_item,
                    received_quantity=cantidad,
                )
                items_created += 1

                # Mantener actualizado el último precio de compra del producto
                if precio_unitario > 0:
                    product.purchase_price = precio_unitario
                    product.save(update_fields=['purchase_price'])

                # Update stock
                if actualizar_stock:
                    StockManagementService.add_stock(
                        product=product,
                        quantity=cantidad,
                        cost=unit_cost_for_item,
                        reference=order_number,
                        reference_id=purchase.pk,
                        notes=f'Remito {numero_comprobante}' if numero_comprobante else f'Escaneo remito',
                        user=request.user,
                    )
                    stock_updated += 1

            # Optionally register as expense
            expense_id = None
            if registrar_gasto and total > 0:
                from expenses.models import Expense, ExpenseCategory
                cat, _ = ExpenseCategory.objects.get_or_create(
                    name='Compras Mercadería',
                    defaults={'color': '#198754', 'is_active': True}
                )

                # Map payment method
                payment_map = {
                    'efectivo': 'cash',
                    'cash': 'cash',
                    'tarjeta': 'card',
                    'card': 'card',
                    'transferencia': 'transfer',
                    'transfer': 'transfer',
                    'cheque': 'check',
                        'check': 'check',
                }
                pago = payment_map.get(metodo_pago.lower(), 'cash') if metodo_pago else 'cash'

                expense = Expense.objects.create(
                    category=cat,
                    description=f'Compra {supplier.name} - {numero_comprobante or order_number}',
                    amount=total,
                    expense_date=fecha,
                    payment_method=pago,
                    receipt_number=numero_comprobante or order_number,
                    supplier=supplier,
                    notes=notas,
                    created_by=request.user,
                )
                expense_id = expense.pk

            return JsonResponse({
                'success': True,
                'purchase_id': purchase.pk,
                'order_number': order_number,
                'items_created': items_created,
                'stock_updated': stock_updated,
                'products_not_found': products_not_found,
                'auto_created_products': auto_created_products,
                'expense_id': expense_id,
                'message': f'Compra {order_number} registrada: {items_created} productos, {stock_updated} stocks actualizados.'
            })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Formato de datos inválido.'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in api_confirm_invoice: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
@group_required(['Admin'])
def api_create_product_from_scan(request):
    """
    API endpoint: create a new product from the invoice scan review.
    Receives name, category_id, purchase_price, sale_price, barcode.
    Returns the created product id and name.
    """
    try:
        def _to_decimal(value, default=Decimal('0')):
            if value is None:
                return default
            if isinstance(value, Decimal):
                return value
            if isinstance(value, (int, float)):
                try:
                    return Decimal(str(value))
                except (InvalidOperation, ValueError, TypeError):
                    return default

            s = str(value).strip()
            if not s:
                return default
            if ',' in s and '.' in s:
                s = s.replace('.', '').replace(',', '.')
            elif ',' in s:
                s = s.replace(',', '.')

            try:
                return Decimal(s)
            except (InvalidOperation, ValueError, TypeError):
                return default

        data = json.loads(request.body)
        name = data.get('name', '').strip()
        category_id = data.get('category_id') or None
        purchase_price = _to_decimal(data.get('purchase_price', 0), Decimal('0'))
        sale_price = _to_decimal(data.get('sale_price', 0), Decimal('0'))
        barcode = data.get('barcode', '').strip() or None

        if not name:
            return JsonResponse({
                'success': False,
                'error': 'El nombre del producto es obligatorio.'
            }, status=400)

        if sale_price <= 0:
            return JsonResponse({
                'success': False,
                'error': 'El precio de venta debe ser mayor a 0.'
            }, status=400)

        from stocks.models import Product, ProductCategory

        # Check if a product with the same name already exists
        if Product.objects.filter(name__iexact=name, is_active=True).exists():
            existing = Product.objects.filter(name__iexact=name, is_active=True).first()
            return JsonResponse({
                'success': True,
                'product_id': existing.pk,
                'product_name': existing.name,
                'message': 'Ya existe un producto con ese nombre, se vinculó automáticamente.',
                'already_existed': True,
            })

        # Check barcode uniqueness
        if barcode and Product.objects.filter(barcode=barcode).exists():
            return JsonResponse({
                'success': False,
                'error': f'Ya existe un producto con el código de barras {barcode}.'
            }, status=400)

        category = None
        if category_id:
            try:
                category = ProductCategory.objects.get(pk=int(category_id))
            except (ProductCategory.DoesNotExist, ValueError):
                pass

        product = Product.objects.create(
            name=name,
            category=category,
            purchase_price=purchase_price,
            cost_price=purchase_price,
            sale_price=sale_price,
            barcode=barcode,
            is_active=True,
        )

        return JsonResponse({
            'success': True,
            'product_id': product.pk,
            'product_name': product.name,
            'message': f'Producto "{product.name}" creado exitosamente.',
            'already_existed': False,
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Formato de datos inválido.'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in api_create_product_from_scan: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
