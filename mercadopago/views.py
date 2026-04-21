"""
MercadoPago Views - Vistas para administración y webhooks
"""
import json
import hmac
import hashlib
import logging
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.utils import timezone
from django.db import transaction, models

from decorators.decorators import group_required
from .models import MPCredentials, PointDevice, PaymentIntent, WebhookLog
from .services import MPPointService, payment_manager

logger = logging.getLogger(__name__)


# ==================== DASHBOARD Y CONFIG ====================

@login_required
@group_required(['Admin'])
def mp_dashboard(request):
    """Dashboard principal de Mercado Pago."""
    credentials = MPCredentials.get_active()
    devices = PointDevice.objects.all()
    
    # Estadísticas recientes
    recent_intents = PaymentIntent.objects.all()[:10]
    
    # Totales del día
    today = timezone.now().date()
    today_intents = PaymentIntent.objects.filter(
        created_at__date=today
    )
    
    stats = {
        'total_devices': devices.count(),
        'active_devices': devices.filter(status='active').count(),
        'today_total': today_intents.filter(status='approved').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0'),
        'today_approved': today_intents.filter(status='approved').count(),
        'today_rejected': today_intents.filter(status='rejected').count(),
        'today_pending': today_intents.filter(status='processing').count(),
    }
    
    return render(request, 'mercadopago/dashboard.html', {
        'credentials': credentials,
        'devices': devices,
        'recent_intents': recent_intents,
        'stats': stats,
    })


@login_required
@group_required(['Admin'])
def credentials_form(request):
    """Formulario para configurar credenciales de MP."""
    credentials = MPCredentials.get_active()
    
    if request.method == 'POST':
        access_token = request.POST.get('access_token', '').strip()
        public_key = request.POST.get('public_key', '').strip()
        is_sandbox = request.POST.get('is_sandbox') == 'on'
        webhook_secret = request.POST.get('webhook_secret', '').strip()
        external_pos_id = request.POST.get('external_pos_id', '').strip()

        if not access_token:
            messages.error(request, 'El Access Token es requerido')
            return redirect('mercadopago:credentials')

        if credentials:
            credentials.access_token = access_token
            credentials.public_key = public_key
            credentials.is_sandbox = is_sandbox
            credentials.webhook_secret = webhook_secret
            credentials.external_pos_id = external_pos_id
            credentials.save()
            messages.success(request, 'Credenciales actualizadas correctamente')
        else:
            MPCredentials.objects.create(
                name='Producción' if not is_sandbox else 'Sandbox',
                access_token=access_token,
                public_key=public_key,
                is_sandbox=is_sandbox,
                webhook_secret=webhook_secret,
                external_pos_id=external_pos_id,
                is_active=True
            )
            messages.success(request, 'Credenciales guardadas correctamente')
        
        return redirect('mercadopago:dashboard')
    
    return render(request, 'mercadopago/credentials_form.html', {
        'credentials': credentials,
    })


@login_required
@group_required(['Admin'])
def test_connection(request):
    """Prueba la conexión con Mercado Pago y muestra diagnóstico."""
    try:
        service = MPPointService()
        success, response = service.get_devices()

        if success:
            devices_raw = response.get('devices', [])
            devices_info = [
                {
                    'id': d.get('id'),
                    'operating_mode': d.get('operating_mode'),
                    'store_name': d.get('store_name'),
                }
                for d in devices_raw
            ]
            # Local DB state
            local_devices = list(PointDevice.objects.values(
                'device_id', 'device_name', 'operating_mode', 'status',
                'cash_register__name',
            ))
            return JsonResponse({
                'success': True,
                'message': 'Conexión exitosa con Mercado Pago',
                'devices_count': len(devices_raw),
                'devices_mp': devices_info,
                'devices_local': local_devices,
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"Error: {response}"
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error de conexión: {str(e)}'
        })


@login_required
@group_required(['Admin'])
@require_POST
def assign_pos_external_id_view(request):
    """
    Asigna programáticamente un external_id alfanumérico a un POS existente
    en la cuenta MP. Esto es lo que destraba el QR estático cuando MP creó
    el POS sin external_id (caso típico al pedir el QR físico desde el panel).

    Body JSON:
        pos_id: int — ID interno del POS a actualizar
        external_id: str — external_id alfanumérico a asignar (ej "CHEPOS-001")

    Si la actualización en MP es exitosa, además guarda ese external_id como
    el `external_pos_id` activo en MPCredentials para que el POS lo use ya.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'JSON inválido'}, status=400)

    pos_id = data.get('pos_id')
    external_id = (data.get('external_id') or '').strip()

    if not pos_id:
        return JsonResponse({'success': False, 'message': 'Falta pos_id'}, status=400)
    if not external_id:
        return JsonResponse({'success': False, 'message': 'Falta external_id'}, status=400)

    credentials = MPCredentials.get_active()
    if not credentials or not credentials.access_token:
        return JsonResponse({
            'success': False,
            'message': 'No hay credenciales de MP con Access Token cargado.'
        }, status=400)

    try:
        service = MPPointService(credentials=credentials)
        success, response = service.update_pos(pos_id=pos_id, external_id=external_id)
        if not success:
            error_msg = response.get('message') or response.get('error') or str(response)
            return JsonResponse({
                'success': False,
                'message': f'MP rechazó la actualización: {error_msg}',
                'raw': response,
            }, status=400)

        # Guardar como external_pos_id activo en credenciales
        credentials.external_pos_id = external_id
        credentials.save(update_fields=['external_pos_id'])

        return JsonResponse({
            'success': True,
            'message': f'POS actualizado en MP. Ahora usa external_id="{external_id}".',
            'pos': response,
        })
    except Exception as e:
        logger.exception(f"Error assigning external_id to POS: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error inesperado: {str(e)}',
        }, status=500)


@login_required
@group_required(['Admin'])
def list_pos_view(request):
    """
    Lista los POS (puntos de venta) del seller en MP.
    Sirve para que el admin sepa qué external_pos_id usar para el QR estático.

    Devuelve JSON con la lista cruda + indicador de cuál coincide con
    el external_pos_id actualmente configurado en credenciales.
    """
    try:
        credentials = MPCredentials.get_active()
        if not credentials:
            return JsonResponse({
                'success': False,
                'message': 'No hay credenciales de MP configuradas. Cargá el Access Token primero.'
            }, status=400)

        service = MPPointService(credentials=credentials)
        success, response = service.list_pos()
        if not success:
            error_msg = response.get('message') or response.get('error') or str(response)
            return JsonResponse({
                'success': False,
                'message': f'MP rechazó la consulta: {error_msg}',
                'raw': response,
            }, status=400)

        results = response.get('results', []) if isinstance(response, dict) else []
        configured = credentials.external_pos_id or ''

        pos_list = []
        for pos in results:
            external_id = str(pos.get('external_id', ''))
            pos_list.append({
                'id': pos.get('id'),
                'name': pos.get('name'),
                'external_id': external_id,
                'store_id': pos.get('store_id'),
                'category': pos.get('category'),
                'fixed_amount': pos.get('fixed_amount'),
                'is_configured': configured and external_id == configured,
            })

        return JsonResponse({
            'success': True,
            'count': len(pos_list),
            'configured_external_pos_id': configured,
            'results': pos_list,
        })
    except Exception as e:
        logger.exception(f"Error listing POS: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error inesperado: {str(e)}',
        }, status=500)


# ==================== DISPOSITIVOS ====================

@login_required
@group_required(['Admin'])
def device_list(request):
    """Lista de dispositivos Point."""
    devices = PointDevice.objects.select_related('cash_register').all()
    return render(request, 'mercadopago/device_list.html', {
        'devices': devices,
    })


@login_required
@group_required(['Admin'])
def sync_devices(request):
    """Sincroniza dispositivos desde Mercado Pago."""
    success, result = payment_manager.sync_devices()

    if success:
        count = len(result)
        messages.success(request, f'Se sincronizaron {count} dispositivo(s)')
        # Check if any device still has no register
        unassigned = PointDevice.objects.filter(cash_register__isnull=True, status='active')
        if unassigned.exists():
            messages.warning(
                request,
                'Hay dispositivos sin caja asignada. '
                'Asigne cada dispositivo a una caja para poder cobrar desde el POS.'
            )
    else:
        messages.error(request, f'Error al sincronizar: {result}')

    return redirect('mercadopago:device_list')


@login_required
@group_required(['Admin'])
def device_edit(request, device_id):
    """Editar asignación de dispositivo a caja."""
    from cashregister.models import CashRegister
    
    device = get_object_or_404(PointDevice, pk=device_id)
    registers = CashRegister.objects.filter(is_active=True)
    
    if request.method == 'POST':
        register_id = request.POST.get('cash_register')
        device_name = request.POST.get('device_name', '').strip()
        
        if register_id:
            # Verificar que la caja no tenga otro dispositivo asignado
            existing = PointDevice.objects.filter(
                cash_register_id=register_id
            ).exclude(pk=device.pk).first()
            
            if existing:
                messages.error(request, f'La caja ya tiene el dispositivo {existing.device_name} asignado')
                return redirect('mercadopago:device_edit', device_id=device_id)
            
            device.cash_register_id = register_id
        else:
            device.cash_register = None
        
        if device_name:
            device.device_name = device_name
        
        device.save()
        messages.success(request, 'Dispositivo actualizado correctamente')
        return redirect('mercadopago:device_list')
    
    return render(request, 'mercadopago/device_form.html', {
        'device': device,
        'registers': registers,
    })


@login_required
@group_required(['Admin'])
def device_change_mode(request, device_id):
    """Cambia el modo de operación del dispositivo."""
    device = get_object_or_404(PointDevice, pk=device_id)
    mode = request.POST.get('mode', 'PDV')
    
    try:
        service = MPPointService()
        success, response = service.change_device_mode(device.device_id, mode)
        
        if success:
            device.operating_mode = mode
            device.save()
            messages.success(request, f'Modo cambiado a {mode}')
        else:
            messages.error(request, f"Error: {response.get('message', 'Error desconocido')}")
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    
    return redirect('mercadopago:device_list')


# ==================== INTENCIONES DE PAGO ====================

@login_required
@group_required(['Admin'])
def payment_intent_list(request):
    """Lista de intenciones de pago."""
    intents = PaymentIntent.objects.select_related(
        'device', 'pos_transaction', 'created_by'
    ).all()[:100]
    
    return render(request, 'mercadopago/payment_intent_list.html', {
        'intents': intents,
    })


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
def payment_intent_detail(request, intent_id):
    """Detalle de una intención de pago."""
    intent = get_object_or_404(
        PaymentIntent.objects.select_related('device', 'pos_transaction', 'created_by'),
        pk=intent_id
    )
    
    return render(request, 'mercadopago/payment_intent_detail.html', {
        'intent': intent,
    })


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
def payment_intent_check_status(request, intent_id):
    """Consulta el estado actual de una intención de pago."""
    intent = get_object_or_404(PaymentIntent, pk=intent_id)
    
    success, result = payment_manager.check_status(intent)
    
    if success:
        return JsonResponse({
            'success': True,
            'status': intent.status,
            'mp_status': result.get('state'),
            'data': result
        })
    else:
        return JsonResponse({
            'success': False,
            'error': result
        })


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
def payment_intent_cancel(request, intent_id):
    """Cancela una intención de pago."""
    intent = get_object_or_404(PaymentIntent, pk=intent_id)
    
    success, message = payment_manager.cancel(intent)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': message})
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    return redirect('mercadopago:payment_intent_detail', intent_id=intent_id)


# ==================== API PARA POS ====================

@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
@require_POST
def api_create_payment_intent(request):
    """
    API para crear una intención de pago desde el POS.
    
    POST /mercadopago/api/create-intent/
    {
        "amount": 1500.00,
        "transaction_id": 123,  // opcional
        "description": "Venta"  // opcional
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    
    amount = data.get('amount')
    transaction_id = data.get('transaction_id')
    description = data.get('description', 'Venta CHE GOLOSO')
    payment_type = data.get('payment_type')  # None = cualquier método, "credit_card"/"debit_card" para específico
    
    if not amount:
        return JsonResponse({'success': False, 'error': 'Monto requerido'}, status=400)
    
    try:
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Monto inválido'}, status=400)
    
    # Obtener el dispositivo asociado a la caja del usuario
    # Primero buscar el turno activo del usuario
    from cashregister.models import CashShift
    
    active_shift = CashShift.objects.filter(
        cashier=request.user,
        status='open'
    ).select_related('cash_register').first()
    
    if not active_shift:
        return JsonResponse({
            'success': False, 
            'error': 'No hay turno de caja abierto'
        }, status=400)
    
    # Buscar dispositivo Point asociado a la caja
    device = PointDevice.objects.filter(
        cash_register=active_shift.cash_register,
        status='active'
    ).first()

    # Fallback: if no device assigned to this register, use any active device
    if not device:
        device = PointDevice.objects.filter(status='active').first()

    if not device:
        return JsonResponse({
            'success': False,
            'error': 'No hay dispositivo Point activo. Sincronice los dispositivos desde Admin > Mercado Pago.'
        }, status=400)

    if device.operating_mode != 'PDV':
        return JsonResponse({
            'success': False,
            'error': f'El dispositivo Point está en modo {device.operating_mode}. Debe estar en modo PDV para recibir cobros desde el POS.'
        }, status=400)
    
    # Obtener transacción POS si se proporcionó
    pos_transaction = None
    if transaction_id:
        from pos.models import POSTransaction
        pos_transaction = POSTransaction.objects.filter(pk=transaction_id).first()
    
    # Crear y enviar la intención de pago
    success, result = payment_manager.create_and_send(
        device=device,
        amount=amount,
        pos_transaction=pos_transaction,
        user=request.user,
        description=description,
        payment_type=payment_type
    )
    
    if success:
        return JsonResponse({
            'success': True,
            'payment_intent': {
                'id': str(result.id),
                'external_reference': result.external_reference,
                'amount': float(result.amount),
                'status': result.status,
                'device_name': device.device_name,
            },
            'message': 'Pago enviado al dispositivo Point. Esperando pago del cliente.'
        })
    else:
        return JsonResponse({
            'success': False,
            'error': result
        }, status=400)


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
@require_POST
def api_create_qr(request):
    """
    API para asignar un monto al QR estático de MercadoPago asociado al
    seller. El cliente escanea el QR físico ya impreso y la app de MP le
    muestra el cobro creado en esta llamada.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)

    amount = data.get('amount')
    transaction_id = data.get('transaction_id')

    if not amount:
        return JsonResponse({'success': False, 'error': 'Monto requerido'}, status=400)

    try:
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Monto inválido'}, status=400)

    # Validar credenciales antes de tocar el modelo
    credentials = MPCredentials.get_active()
    if not credentials:
        return JsonResponse({
            'success': False,
            'error': (
                'No hay credenciales de Mercado Pago configuradas. '
                'Pedile al Admin que las cargue en Admin → Mercado Pago → Credenciales.'
            )
        }, status=400)
    if not credentials.access_token:
        return JsonResponse({
            'success': False,
            'error': 'Las credenciales de MP no tienen Access Token cargado.'
        }, status=400)
    if not credentials.external_pos_id:
        return JsonResponse({
            'success': False,
            'error': (
                'Falta configurar el External POS ID del QR estático. '
                'Pedile al Admin que lo cargue en Admin → Mercado Pago → Credenciales '
                '(debe coincidir con el ID del POS asociado al QR impreso en tu cuenta MP).'
            )
        }, status=400)

    # Verificar turno activo
    from cashregister.models import CashShift
    active_shift = CashShift.objects.filter(
        cashier=request.user,
        status='open'
    ).first()

    if not active_shift:
        return JsonResponse({'success': False, 'error': 'No hay turno de caja abierto'}, status=400)

    # Obtener transacción POS
    pos_transaction = None
    if transaction_id:
        from pos.models import POSTransaction
        pos_transaction = POSTransaction.objects.filter(pk=transaction_id).first()

    # Crear registro local (QR no requiere device)
    payment_intent = PaymentIntent(
        payment_flow='qr',
        device=None,
        amount=amount,
        pos_transaction=pos_transaction,
        created_by=request.user,
        description="Venta QR CHE GOLOSO"
    )
    payment_intent.save()

    try:
        service = MPPointService(credentials=credentials)
        success, response = service.create_qr_order(
            amount=amount,
            external_reference=payment_intent.external_reference,
            title=f"Venta CHE GOLOSO ${amount}"
        )

        if success:
            # Instore Orders v2: PUT devuelve 204 No Content (sin body).
            # El seguimiento se hace por external_reference vía /v1/payments/search.
            payment_intent.mp_payment_intent_id = (response or {}).get('in_store_order_id', '') or payment_intent.external_reference
            payment_intent.status = 'processing'
            payment_intent.sent_at = timezone.now()
            payment_intent.save()

            return JsonResponse({
                'success': True,
                'payment_intent': {
                    'id': str(payment_intent.id),
                    'external_reference': payment_intent.external_reference,
                    'amount': float(payment_intent.amount),
                    'status': payment_intent.status,
                },
                'message': 'Monto cargado al QR estático. El cliente debe escanear el QR físico de la caja.'
            })
        else:
            # Construir mensaje de error legible
            error_msg = response.get('message') or response.get('error')
            mp_status = response.get('status')
            mp_cause = response.get('cause')
            if isinstance(mp_cause, list) and mp_cause:
                first = mp_cause[0]
                if isinstance(first, dict):
                    error_msg = first.get('description') or first.get('message') or error_msg
            if not error_msg:
                error_msg = str(response)

            # Hint específico cuando MP no encuentra el POS
            lower = (error_msg or '').lower()
            if 'pos' in lower and ('not found' in lower or 'no encontr' in lower):
                error_msg = (
                    f"MercadoPago no encontró el POS '{credentials.external_pos_id}' en tu cuenta. "
                    f"Verificá el External POS ID en Admin → Mercado Pago → Credenciales."
                )
            elif mp_status in (401, 403):
                error_msg = (
                    "MercadoPago rechazó el Access Token (401/403). "
                    "Verificá que sea de Producción y que tenga permisos sobre el QR estático."
                )

            payment_intent.mark_error(str(response))
            return JsonResponse({'success': False, 'error': error_msg}, status=400)

    except ValueError as e:
        payment_intent.mark_error(str(e))
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        payment_intent.mark_error(str(e))
        logger.exception(f"Error creating QR: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
@require_GET
def api_check_payment_status(request, intent_id):
    """
    API para consultar el estado de un pago.
    
    GET /mercadopago/api/status/<intent_id>/
    """
    intent = get_object_or_404(PaymentIntent, pk=intent_id)
    
    # Si ya está en estado terminal, devolver sin consultar MP
    if intent.is_terminal_state:
        return JsonResponse({
            'success': True,
            'status': intent.status,
            'is_final': True,
            'payment_intent': {
                'id': str(intent.id),
                'external_reference': intent.external_reference,
                'amount': float(intent.amount),
                'status': intent.status,
                'status_display': intent.get_status_display(),
                'payment_method': intent.payment_method,
                'card_brand': intent.card_brand,
                'card_last_four': intent.card_last_four,
                'authorization_code': intent.authorization_code,
            }
        })
    
    # Consultar estado en MP según el flujo de pago
    if intent.payment_flow == 'qr':
        # QR: buscar pago por external_reference en la API de payments
        try:
            credentials = MPCredentials.get_active()
            service = MPPointService(credentials=credentials)
            success, result = service.search_payments(
                external_reference=intent.external_reference
            )
            if success:
                results = result.get('results', [])
                if results:
                    payment = results[0]
                    if payment.get('status') == 'approved':
                        intent.mark_approved(payment)
                        complete_pos_transaction(intent)
                    elif payment.get('status') in ('rejected', 'cancelled'):
                        intent.mark_rejected(payment.get('status_detail', ''))
                # Si no hay results, el pago sigue pendiente
        except Exception as e:
            logger.warning(f"QR status check error: {e}")
    else:
        # Point: consultar por payment_intent_id en la API de Point
        success, result = payment_manager.check_status(intent)

        if success:
            mp_state = result.get('state', '')

            if mp_state == 'FINISHED':
                payment = result.get('payment', {})
                if payment.get('status') == 'approved':
                    intent.mark_approved(payment)
                    complete_pos_transaction(intent)
                else:
                    intent.mark_rejected(payment.get('status_detail', ''))
            elif mp_state == 'CANCELED':
                intent.mark_cancelled()
            elif mp_state == 'ERROR':
                intent.mark_error(result.get('error_reason', 'Error desconocido'))
    
    return JsonResponse({
        'success': True,
        'status': intent.status,
        'is_final': intent.is_terminal_state,
        'payment_intent': {
            'id': str(intent.id),
            'external_reference': intent.external_reference,
            'amount': float(intent.amount),
            'status': intent.status,
            'status_display': intent.get_status_display(),
            'payment_method': intent.payment_method,
            'card_brand': intent.card_brand,
            'card_last_four': intent.card_last_four,
            'authorization_code': intent.authorization_code,
        }
    })


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
@require_POST
def api_cancel_payment(request, intent_id):
    """
    API para cancelar un pago pendiente.

    POST /mercadopago/api/cancel/<intent_id>/
    """
    intent = get_object_or_404(PaymentIntent, pk=intent_id)

    success, message = payment_manager.cancel(intent)

    return JsonResponse({
        'success': success,
        'message': message,
        'status': intent.status
    })


# ==================== WEBHOOK ====================

@csrf_exempt
@require_POST
def webhook_receiver(request):
    """
    Endpoint para recibir webhooks de Mercado Pago.
    
    Mercado Pago envía notificaciones cuando:
    - Se completa un pago (approved, rejected)
    - Cambia el estado de una intención de pago
    - Eventos de dispositivos
    
    URL a configurar en MP: https://tudominio.com/mercadopago/webhook/
    """
    # Guardar log del webhook
    webhook_log = WebhookLog(
        event_type='unknown',
        ip_address=get_client_ip(request)
    )
    
    try:
        # Parsear el payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            webhook_log.event_type = 'invalid_json'
            webhook_log.processing_result = 'JSON inválido'
            webhook_log.save()
            return HttpResponse(status=400)
        
        webhook_log.payload = json.dumps(payload, indent=2, default=str)
        webhook_log.headers = json.dumps(dict(request.headers), indent=2, default=str)
        
        # Extraer información del evento
        event_type = payload.get('type', payload.get('action', 'unknown'))
        event_id = payload.get('id', '')
        
        webhook_log.event_type = event_type
        webhook_log.event_id = str(event_id)
        
        # Validar firma si está configurada
        credentials = MPCredentials.get_active()
        if credentials and credentials.webhook_secret:
            signature = request.headers.get('X-Signature')
            if not verify_webhook_signature(request.body, signature, credentials.webhook_secret):
                webhook_log.processing_result = 'Firma inválida'
                webhook_log.save()
                logger.warning(f"Webhook con firma inválida: {event_id}")
                return HttpResponse(status=401)
        
        # Procesar según el tipo de evento
        result = process_webhook_event(event_type, payload)
        
        webhook_log.processed = True
        webhook_log.processing_result = result
        webhook_log.save()
        
        logger.info(f"Webhook procesado: {event_type} - {result}")
        return HttpResponse(status=200)
        
    except Exception as e:
        webhook_log.processing_result = f'Error: {str(e)}'
        webhook_log.save()
        logger.exception(f"Error procesando webhook: {e}")
        return HttpResponse(status=500)


def verify_webhook_signature(body, signature, secret):
    """Verifica la firma del webhook."""
    if not secret:
        logger.warning("Webhook secret no configurado — rechazando webhook por seguridad")
        return False
    if not signature:
        return False
    
    try:
        # MP usa HMAC-SHA256
        expected = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


def process_webhook_event(event_type, payload):
    """
    Procesa un evento de webhook.
    
    Args:
        event_type: Tipo de evento
        payload: Datos del evento
    
    Returns:
        str: Resultado del procesamiento
    """
    # Eventos de Point
    if event_type in ['point_integration_wh', 'point']:
        return process_point_event(payload)
    
    # Eventos de pagos
    elif event_type == 'payment':
        return process_payment_event(payload)
    
    # Otros eventos
    else:
        return f'Evento {event_type} no procesado'


def process_point_event(payload):
    """Procesa eventos del Point."""
    data = payload.get('data', {})
    resource_id = data.get('id')
    
    if not resource_id:
        return 'Sin ID de recurso'
    
    # Buscar la intención de pago
    intent = PaymentIntent.objects.filter(
        mp_payment_intent_id=resource_id
    ).first()
    
    if not intent:
        # Intentar buscar por external_reference en el payload
        external_ref = data.get('external_reference')
        if external_ref:
            intent = PaymentIntent.objects.filter(
                external_reference=external_ref
            ).first()
    
    if not intent:
        return f'Intención de pago no encontrada: {resource_id}'
    
    # Obtener estado actual desde MP
    try:
        service = MPPointService()
        success, response = service.get_payment_intent(
            intent.device.device_id,
            intent.mp_payment_intent_id
        )
        
        if success:
            state = response.get('state', '')
            
            if state == 'FINISHED':
                payment = response.get('payment', {})
                if payment.get('status') == 'approved':
                    intent.mark_approved(payment)
                    # Completar la transacción POS si está asociada
                    complete_pos_transaction(intent)
                    return f'Pago aprobado: {intent.external_reference}'
                else:
                    intent.mark_rejected(payment.get('status_detail', ''))
                    return f'Pago rechazado: {intent.external_reference}'
            
            elif state == 'CANCELED':
                intent.mark_cancelled()
                return f'Pago cancelado: {intent.external_reference}'
            
            elif state == 'ERROR':
                intent.mark_error(response.get('error_reason', ''))
                return f'Error en pago: {intent.external_reference}'
            
            return f'Estado {state}: {intent.external_reference}'
        else:
            return f'Error consultando MP: {response}'
            
    except Exception as e:
        return f'Error: {str(e)}'


def process_payment_event(payload):
    """Procesa eventos de pagos."""
    data = payload.get('data', {})
    payment_id = data.get('id')
    
    if not payment_id:
        return 'Sin ID de pago'
    
    # Buscar por mp_payment_id
    intent = PaymentIntent.objects.filter(
        mp_payment_id=str(payment_id)
    ).first()
    
    if not intent:
        return f'Pago no encontrado en sistema: {payment_id}'
    
    # Obtener detalles del pago
    try:
        service = MPPointService()
        success, payment_data = service.get_payment(payment_id)
        
        if success:
            status = payment_data.get('status')
            
            if status == 'approved' and intent.status != 'approved':
                intent.mark_approved(payment_data)
                complete_pos_transaction(intent)
                return f'Pago confirmado: {intent.external_reference}'
            elif status in ['rejected', 'cancelled']:
                intent.mark_rejected(payment_data.get('status_detail', ''))
                return f'Pago rechazado/cancelado: {intent.external_reference}'
            
            return f'Estado {status}: {intent.external_reference}'
        else:
            return f'Error consultando pago: {payment_data}'
            
    except Exception as e:
        return f'Error: {str(e)}'


def complete_pos_transaction(payment_intent):
    """
    Completa la transacción POS cuando el pago es aprobado.
    Crea el pago, descuenta stock y registra movimiento de caja.

    Usa select_for_update() para prevenir doble-completación cuando
    el webhook y el polling llegan al mismo tiempo.
    """
    if not payment_intent.pos_transaction:
        return

    try:
        with transaction.atomic():
            from pos.models import POSTransaction, POSPayment
            from cashregister.models import PaymentMethod, CashMovement
            from stocks.services import StockManagementService

            # Lock the transaction row to prevent race condition
            pos_transaction = POSTransaction.objects.select_for_update().get(
                pk=payment_intent.pos_transaction_id
            )

            if pos_transaction.status != 'pending':
                return  # Already completed by other thread

            # Crear el registro de pago
            mp_method = PaymentMethod.objects.filter(code='mercadopago').first()
            
            if mp_method:
                POSPayment.objects.create(
                    transaction=pos_transaction,
                    payment_method=mp_method,
                    amount=payment_intent.amount,
                    reference=f"MP:{payment_intent.mp_payment_id} {payment_intent.card_brand} ****{payment_intent.card_last_four}".strip(),
                )
                
                # Registrar movimiento de caja
                CashMovement.objects.create(
                    cash_shift=pos_transaction.session.cash_shift,
                    movement_type='income',
                    amount=payment_intent.amount,
                    payment_method=mp_method,
                    description=f'Venta MP {pos_transaction.ticket_number}',
                    reference=pos_transaction.ticket_number
                )
            
            # Descontar stock — mismo ruteo que pos/_process_payment_atomic:
            # granel → registrar_venta, no-granel → deduct_stock.
            from granel.services import GranelService, BatchService
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
                            reference=f'Venta MP {pos_transaction.ticket_number}{pkg_note}',
                            reference_id=pos_transaction.id
                        )
                    else:
                        StockManagementService.deduct_stock(
                            product=item.product,
                            quantity=units_to_deduct,
                            reference=f'Venta MP {pos_transaction.ticket_number}{pkg_note}',
                            reference_id=pos_transaction.id
                        )
                    BatchService.deduct_fifo(item.product.pk, units_to_deduct)
            
            # Actualizar totales
            pos_transaction.amount_paid = payment_intent.amount
            pos_transaction.status = 'completed'
            pos_transaction.completed_at = timezone.now()
            pos_transaction.save()
            
            logger.info(f"Transacción POS completada: {pos_transaction.ticket_number}")
            
    except Exception as e:
        logger.exception(f"Error completando transacción POS: {e}")


def get_client_ip(request):
    """Obtiene la IP del cliente."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ==================== LOGS ====================

@login_required
@group_required(['Admin'])
def webhook_logs(request):
    """Lista de logs de webhooks."""
    logs = WebhookLog.objects.all()[:100]
    return render(request, 'mercadopago/webhook_logs.html', {
        'logs': logs,
    })
