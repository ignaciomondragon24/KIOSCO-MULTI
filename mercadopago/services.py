"""
MercadoPago Point API Service
Servicio para comunicarse con la API de Mercado Pago Point.
"""
import uuid
import requests
import logging
from decimal import Decimal
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


class MPPointService:
    """
    Servicio para interactuar con la API de Mercado Pago Point.
    
    Documentación oficial:
    https://www.mercadopago.com.ar/developers/es/docs/mp-point/integration-api/introduction
    """
    
    BASE_URL = "https://api.mercadopago.com"
    SANDBOX_URL = "https://api.mercadopago.com"  # MP usa el mismo URL, el modo se controla con credenciales
    
    def __init__(self, credentials=None):
        """
        Inicializa el servicio con las credenciales.
        
        Args:
            credentials: Objeto MPCredentials. Si no se provee, busca las credenciales activas.
        """
        if credentials is None:
            from .models import MPCredentials
            credentials = MPCredentials.get_active()
        
        if not credentials:
            raise ValueError("No hay credenciales de Mercado Pago configuradas")
        
        self.credentials = credentials
        self.access_token = credentials.access_token
        self.is_sandbox = credentials.is_sandbox
        self.base_url = self.BASE_URL
    
    def _get_headers(self):
        """Obtiene los headers para las peticiones."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid.uuid4()),
        }
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """
        Realiza una petición a la API de MP.
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: Endpoint de la API (sin base URL)
            data: Datos para enviar en el body (dict)
            params: Query parameters (dict)
        
        Returns:
            tuple: (success: bool, data: dict)
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=data,
                params=params,
                timeout=30
            )
            
            logger.info(f"MP API {method} {endpoint} - Status: {response.status_code}")

            if response.status_code == 204:
                # No content (típico de PUT en Instore Orders v2 para QR estático)
                return True, {}
            if response.status_code in [200, 201]:
                try:
                    return True, response.json()
                except ValueError:
                    return True, {}
            else:
                try:
                    error_data = response.json()
                except Exception:
                    error_data = {"error": response.text or "Unknown error"}
                logger.error(
                    f"MP API Error {response.status_code}: {error_data} "
                    f"| endpoint={endpoint} payload={data}"
                )
                return False, error_data
                
        except requests.exceptions.Timeout:
            logger.error(f"MP API Timeout: {endpoint}")
            return False, {"error": "Timeout en la conexión con Mercado Pago"}
        except requests.exceptions.RequestException as e:
            logger.error(f"MP API Request Error: {e}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.error(f"MP API Unexpected Error: {e}")
            return False, {"error": f"Error inesperado: {str(e)}"}
    
    # ==================== DISPOSITIVOS ====================
    
    def get_devices(self):
        """
        Obtiene la lista de dispositivos Point vinculados.
        
        Returns:
            tuple: (success, data)
        """
        return self._make_request("GET", "/point/integration-api/devices")
    
    def get_device(self, device_id):
        """
        Obtiene información de un dispositivo específico.
        
        Args:
            device_id: ID del dispositivo
        
        Returns:
            tuple: (success, data)
        """
        return self._make_request("GET", f"/point/integration-api/devices/{device_id}")
    
    def change_device_mode(self, device_id, mode="PDV"):
        """
        Cambia el modo de operación del dispositivo.
        
        Args:
            device_id: ID del dispositivo
            mode: "PDV" para integrado, "STANDALONE" para independiente
        
        Returns:
            tuple: (success, data)
        """
        data = {"operating_mode": mode}
        return self._make_request(
            "PATCH", 
            f"/point/integration-api/devices/{device_id}",
            data=data
        )
    
    # ==================== INTENCIONES DE PAGO ====================
    
    def create_payment_intent(self, device_id, amount, description="Venta",
                              external_reference=None, additional_info=None,
                              payment_type=None):
        """
        Crea una intención de pago y la envía al dispositivo Point.

        Docs: https://www.mercadopago.com.ar/developers/es/docs/mp-point/integration-api/create-payment-intent

        Args:
            device_id: ID del dispositivo Point
            amount: Monto a cobrar (Decimal o float)
            description: Descripción del cobro
            external_reference: Referencia externa para rastrear el pago
            additional_info: Información adicional (dict)
            payment_type: (Aceptado pero IGNORADO actualmente) tipo de tarjeta.
                          Ver nota abajo sobre por qué no se manda a MP.

        Returns:
            tuple: (success, data)
        """
        # MP Point API espera monto en centavos (entero sin decimales)
        amount_cents = int(Decimal(str(amount)) * 100)

        # additional_info debe contener external_reference y print_on_terminal
        ai = additional_info or {}
        if external_reference:
            ai["external_reference"] = external_reference
        ai.setdefault("print_on_terminal", True)

        payload = {
            "amount": amount_cents,
            "additional_info": ai,
        }

        # NOTA sobre payment.type (débito/crédito forzado en el Point):
        # En el commit 13262be intentamos mandar
        #     payload["payment"] = {"type": "debit_card" | "credit_card"}
        # para que el POS forzara el tipo de tarjeta en el dispositivo cuando
        # el cajero elige "Débito" o "Crédito" como método de cobro. En la
        # práctica MP rechaza ese payload (el cobro nunca llega al Point) y
        # rompe el flujo para ambos métodos.
        #
        # El SDK oficial de Java (PointPaymentIntentPaymentRequest) documenta
        # "type" como un string opcional con valores credit_card/debit_card/
        # voucher_card y "installments" sólo válido para credit_card, pero la
        # API real parece tener validaciones extra (config del seller, firmware
        # del device, u otros campos requeridos que no figuran en los docs).
        # La integración de referencia de Odoo 19 (pos_mercado_pago) tampoco
        # manda el objeto "payment" y funciona establemente en producción.
        #
        # Por eso hoy NO enviamos payment.type: el Point Smart deja que el
        # cliente elija el tipo de tarjeta en el dispositivo y el POS sigue
        # registrando la venta bajo el método que eligió el cajero (débito/
        # crédito/tarjeta_mp) para la contabilidad. Se mantiene la firma del
        # argumento por si en el futuro descubrimos el payload correcto: con
        # sólo re-habilitar el bloque de abajo volvería a funcionar el forzado.
        #
        # if payment_type:
        #     payload["payment"] = {"type": payment_type}

        logger.info(
            f"Creating payment intent: device={device_id}, "
            f"amount_cents={amount_cents}, ref={external_reference}, "
            f"requested_type={payment_type} (ignored), payload={payload}"
        )

        return self._make_request(
            "POST",
            f"/point/integration-api/devices/{device_id}/payment-intents",
            data=payload
        )
    
    def get_payment_intent(self, device_id, payment_intent_id):
        """
        Obtiene el estado de una intención de pago.
        
        Args:
            device_id: ID del dispositivo
            payment_intent_id: ID de la intención de pago
        
        Returns:
            tuple: (success, data)
        """
        return self._make_request(
            "GET",
            f"/point/integration-api/devices/{device_id}/payment-intents/{payment_intent_id}"
        )
    
    def cancel_payment_intent(self, device_id, payment_intent_id):
        """
        Cancela una intención de pago pendiente.
        
        Args:
            device_id: ID del dispositivo
            payment_intent_id: ID de la intención de pago
        
        Returns:
            tuple: (success, data)
        """
        return self._make_request(
            "DELETE",
            f"/point/integration-api/devices/{device_id}/payment-intents/{payment_intent_id}"
        )
    
    def get_last_payment_intent_status(self, device_id):
        """
        Obtiene el estado de la última intención de pago del dispositivo.

        Args:
            device_id: ID del dispositivo

        Returns:
            tuple: (success, data)
        """
        return self._make_request(
            "GET",
            f"/point/integration-api/devices/{device_id}/payment-intents"
        )

    # ==================== QR DINÁMICO ====================

    def get_user_id(self):
        """Obtiene el user_id de MP consultando la API."""
        if self.credentials.user_id:
            return self.credentials.user_id
        success, response = self._make_request("GET", "/users/me")
        if success:
            user_id = str(response.get("id", ""))
            if user_id:
                self.credentials.user_id = user_id
                self.credentials.save(update_fields=["user_id"])
            return user_id
        return None

    def create_qr_order(self, amount, external_reference, title="Venta CHE GOLOSO"):
        """
        Asigna un monto al QR ESTÁTICO impreso del seller (Instore Orders v2).
        NO genera un QR nuevo: el cliente escanea el QR físico pegado en la
        caja y su app de MP le muestra el cobro recién creado.

        Endpoint: PUT /instore/qr/seller/collectors/{user_id}/stores/{external_store_id}/pos/{external_pos_id}/orders
        Docs: https://www.mercadopago.com.ar/developers/en/reference/instore_orders/_instore_qr_seller_collectors_user_id_stores_external_store_id_pos_external_pos_id_orders/put

        IMPORTANTE: la API legacy POST /instore/qr/.../pos/.../orders devuelve
        405 Not Allowed. Hay que usar PUT y el path con /stores/{store_id}/.

        Respuesta: 204 No Content si todo OK. No devuelve in_store_order_id;
        el seguimiento se hace con external_reference vía search_payments.

        Returns:
            tuple: (success, data)
        """
        user_id = self.get_user_id()
        if not user_id:
            return False, {"error": "No se pudo obtener el User ID de MP"}

        external_pos_id = self.credentials.external_pos_id
        if not external_pos_id:
            return False, {"error": "Falta external_pos_id en MPCredentials"}

        # Resolver el store_id consultando el POS (Instore Orders v2 lo exige
        # en la URL). MP devuelve store_id como string en el listado de POS.
        store_id = None
        ok, pos_data = self.get_pos_by_external_id(external_pos_id)
        if ok:
            store_id = str(pos_data.get("store_id") or "")
        if not store_id:
            return False, {
                "error": (
                    f"No se pudo resolver el store_id del POS '{external_pos_id}'. "
                    f"Verificá que el POS exista en MP."
                )
            }

        total_amount = float(Decimal(str(amount)).quantize(Decimal("0.01")))

        payload = {
            "external_reference": external_reference,
            "title": title,
            "description": title,
            "total_amount": total_amount,
            "items": [{
                "sku_number": "CHE-001",
                "category": "marketplace",
                "title": title,
                "description": title,
                "unit_price": total_amount,
                "quantity": 1,
                "unit_measure": "unit",
                "total_amount": total_amount,
            }],
        }

        logger.info(
            f"Creating QR order (PUT v2): amount={total_amount}, ref={external_reference}, "
            f"store={store_id}, pos={external_pos_id}"
        )

        return self._make_request(
            "PUT",
            f"/instore/qr/seller/collectors/{user_id}/stores/{store_id}/pos/{external_pos_id}/orders",
            data=payload
        )

    def get_qr_payment_status(self, external_reference):
        """Busca el estado del pago por external_reference."""
        return self.search_payments(external_reference=external_reference)

    # ==================== POS (sucursales) para QR estático ====================

    def list_pos(self):
        """
        Lista los puntos de venta (POS) del seller en MP.
        Útil para que el admin sepa qué external_pos_id cargar.

        Docs: https://www.mercadopago.com.ar/developers/es/reference/qr-payments/_pos/get
        """
        return self._make_request("GET", "/pos")

    def get_pos_by_external_id(self, external_id):
        """
        Verifica si existe un POS con el external_id dado en la cuenta MP.
        Devuelve (exists: bool, pos_data_or_error: dict).
        """
        success, data = self.list_pos()
        if not success:
            return False, data
        results = data.get("results", []) if isinstance(data, dict) else []
        for pos in results:
            if str(pos.get("external_id", "")) == str(external_id):
                return True, pos
        return False, {"message": f"No se encontró un POS con external_id={external_id}"}

    def update_pos(self, pos_id, external_id, name=None, fixed_amount=True):
        """
        Actualiza un POS existente vía PUT /pos/{id}. Sirve para ASIGNAR
        un external_id alfanumérico a un POS que MP creó automáticamente
        sin uno (caso típico: al pedir el QR físico desde el panel).

        Args:
            pos_id: ID interno (numérico) del POS en MP
            external_id: nuevo external_id alfanumérico (ej "CHEPOS-001")
            name: opcional, nombre del POS
            fixed_amount: True para QR estático tradicional sin monto fijo

        Docs: https://www.mercadopago.com.ar/developers/es/reference/qr-payments/_pos_id/put
        """
        payload = {
            "external_id": external_id,
            "fixed_amount": bool(fixed_amount),
        }
        if name:
            payload["name"] = name
        return self._make_request("PUT", f"/pos/{pos_id}", data=payload)

    def create_pos(self, external_id, store_id, name="QR CHE GOLOSO", fixed_amount=True):
        """
        Crea un nuevo POS dentro de un store existente.
        Útil cuando el seller no tiene ningún POS o quiere uno extra.

        Docs: https://www.mercadopago.com.ar/developers/es/reference/qr-payments/_pos/post
        """
        payload = {
            "name": name,
            "fixed_amount": bool(fixed_amount),
            "category": 621102,  # Otros
            "store_id": str(store_id),
            "external_id": external_id,
        }
        return self._make_request("POST", "/pos", data=payload)

    def list_stores(self):
        """
        Lista los stores (sucursales) del seller. Necesario para crear un POS
        nuevo, ya que cada POS pertenece a un store.

        Docs: https://www.mercadopago.com.ar/developers/es/reference/qr-payments/_stores/get
        """
        user_id = self.get_user_id()
        if not user_id:
            return False, {"error": "No se pudo obtener el User ID de MP"}
        return self._make_request("GET", f"/users/{user_id}/stores")

    # ==================== PAGOS ====================
    
    def get_payment(self, payment_id):
        """
        Obtiene información detallada de un pago.
        
        Args:
            payment_id: ID del pago en MP
        
        Returns:
            tuple: (success, data)
        """
        return self._make_request("GET", f"/v1/payments/{payment_id}")
    
    def search_payments(self, external_reference=None, date_from=None, date_to=None):
        """
        Busca pagos con filtros.
        
        Args:
            external_reference: Referencia externa
            date_from: Fecha desde (datetime)
            date_to: Fecha hasta (datetime)
        
        Returns:
            tuple: (success, data)
        """
        params = {}
        
        if external_reference:
            params["external_reference"] = external_reference
        if date_from:
            params["begin_date"] = date_from.isoformat()
        if date_to:
            params["end_date"] = date_to.isoformat()
        
        return self._make_request("GET", "/v1/payments/search", params=params)
    
    # ==================== REFUNDS ====================
    
    def create_refund(self, payment_id, amount=None):
        """
        Crea una devolución total o parcial.
        
        Args:
            payment_id: ID del pago a devolver
            amount: Monto a devolver (None para total)
        
        Returns:
            tuple: (success, data)
        """
        data = {}
        if amount:
            data["amount"] = float(amount)
        
        return self._make_request("POST", f"/v1/payments/{payment_id}/refunds", data=data)


class PaymentIntentManager:
    """
    Manager para manejar el flujo de intenciones de pago.
    """

    def _get_service(self):
        """Creates a fresh service each time to pick up credential changes."""
        return MPPointService()
    
    def create_and_send(self, device, amount, pos_transaction=None, user=None,
                        description=None, payment_type=None):
        """
        Crea una intención de pago y la envía al dispositivo.

        Args:
            device: PointDevice instance
            amount: Monto a cobrar
            pos_transaction: POSTransaction relacionada (opcional)
            user: Usuario que crea el pago
            description: Descripción personalizada
            payment_type: None = cualquier método (QR + tarjeta),
                          "credit_card"/"debit_card" para específico

        Returns:
            tuple: (success, PaymentIntent or error_message)
        """
        from .models import PaymentIntent
        
        # Crear el registro local
        payment_intent = PaymentIntent(
            payment_flow='point',
            device=device,
            amount=Decimal(str(amount)),
            pos_transaction=pos_transaction,
            created_by=user,
            description=description or "Venta CHE GOLOSO"
        )
        payment_intent.save()  # Esto genera el external_reference
        
        try:
            service = self._get_service()
            
            # Enviar al dispositivo
            success, response = service.create_payment_intent(
                device_id=device.device_id,
                amount=amount,
                description=payment_intent.description,
                external_reference=payment_intent.external_reference,
                payment_type=payment_type
            )
            
            if success:
                # Actualizar con el ID de MP
                payment_intent.mp_payment_intent_id = response.get("id", "")
                payment_intent.status = "processing"
                payment_intent.sent_at = timezone.now()
                payment_intent.save()
                
                logger.info(f"Payment intent enviado: {payment_intent.external_reference}")
                return True, payment_intent
            else:
                # Error al enviar — include full MP response for debugging
                error_msg = response.get("message", response.get("error", "Error desconocido"))
                status_code = response.get("status", "")
                cause = response.get("cause", [])

                # Extraer detalles de cause si es una lista
                cause_details = ""
                if isinstance(cause, list) and cause:
                    cause_details = "; ".join(
                        f"{c.get('code', '')}: {c.get('description', '')}"
                        for c in cause if isinstance(c, dict)
                    )
                elif cause:
                    cause_details = str(cause)

                full_error = error_msg
                if cause_details:
                    full_error += f" ({cause_details})"

                # Agregar sugerencia si es error de permisos o configuración
                if "allow" in str(response).lower() or "permission" in str(response).lower():
                    full_error += " - Verificar: dispositivo en modo PDV, credenciales válidas"

                logger.error(f"Error al enviar payment intent: {response}")
                payment_intent.mark_error(f"{full_error} | raw: {response}")
                return False, full_error
                
        except Exception as e:
            payment_intent.mark_error(str(e))
            logger.exception(f"Excepción al crear payment intent: {e}")
            return False, str(e)
    
    def check_status(self, payment_intent):
        """
        Consulta el estado actual de una intención de pago.
        
        Args:
            payment_intent: PaymentIntent instance
        
        Returns:
            tuple: (success, status_data or error)
        """
        try:
            service = self._get_service()
            
            if not payment_intent.mp_payment_intent_id:
                return False, "La intención de pago no tiene ID de MP"
            
            success, response = service.get_payment_intent(
                device_id=payment_intent.device.device_id,
                payment_intent_id=payment_intent.mp_payment_intent_id
            )
            
            if success:
                return True, response
            else:
                return False, response.get("error", "Error al consultar estado")
                
        except Exception as e:
            logger.exception(f"Error al consultar estado: {e}")
            return False, str(e)
    
    def cancel(self, payment_intent):
        """
        Cancela una intención de pago.
        
        Args:
            payment_intent: PaymentIntent instance
        
        Returns:
            tuple: (success, message)
        """
        if payment_intent.is_terminal_state:
            return False, "La intención de pago ya está en estado final"
        
        try:
            service = self._get_service()
            
            if payment_intent.mp_payment_intent_id:
                success, response = service.cancel_payment_intent(
                    device_id=payment_intent.device.device_id,
                    payment_intent_id=payment_intent.mp_payment_intent_id
                )
                
                if not success:
                    logger.warning(f"Error al cancelar en MP: {response}")
            
            payment_intent.mark_cancelled()
            return True, "Intención de pago cancelada"
            
        except Exception as e:
            logger.exception(f"Error al cancelar: {e}")
            return False, str(e)
    
    def sync_devices(self):
        """
        Sincroniza los dispositivos desde Mercado Pago.
        Auto-asigna dispositivo a caja registradora si hay uno solo sin asignar.

        Returns:
            tuple: (success, devices_synced or error)
        """
        from .models import PointDevice

        try:
            service = self._get_service()
            success, response = service.get_devices()

            if not success:
                return False, response.get("error", "Error al obtener dispositivos")

            devices = response.get("devices", [])
            synced = []

            for device_data in devices:
                device, created = PointDevice.objects.update_or_create(
                    device_id=device_data["id"],
                    defaults={
                        "device_name": device_data.get("store_name", device_data["id"]),
                        "serial_number": device_data.get("serial_number", ""),
                        "operating_mode": device_data.get("operating_mode", "PDV"),
                        "last_sync": timezone.now(),
                    }
                )
                synced.append(device)
                logger.info(f"Dispositivo sincronizado: {device.device_id} modo={device.operating_mode}")

                # Auto-switch to PDV mode if device is in STANDALONE
                if device.operating_mode != "PDV":
                    try:
                        ok, resp = service.change_device_mode(device.device_id, "PDV")
                        if ok:
                            device.operating_mode = "PDV"
                            device.save(update_fields=["operating_mode"])
                            logger.info(f"Dispositivo {device.device_id} cambiado a modo PDV")
                    except Exception as mode_err:
                        logger.warning(f"No se pudo cambiar modo del dispositivo: {mode_err}")

            # Auto-assign: if there are unassigned devices, try to pair them
            # with available cash registers
            self._auto_assign_devices()

            return True, synced
            
        except Exception as e:
            logger.exception(f"Error al sincronizar dispositivos: {e}")
            return False, str(e)

    def _auto_assign_devices(self):
        """
        Auto-assign unassigned devices to available cash registers.
        Only acts when exactly one unassigned device exists and there are
        cash registers without a device.
        """
        from .models import PointDevice
        from cashregister.models import CashRegister

        unassigned = list(PointDevice.objects.filter(cash_register__isnull=True, status='active'))
        if not unassigned:
            return

        # Registers that don't already have a device
        assigned_register_ids = PointDevice.objects.filter(
            cash_register__isnull=False
        ).values_list('cash_register_id', flat=True)
        free_registers = list(
            CashRegister.objects.filter(is_active=True).exclude(pk__in=assigned_register_ids)
        )

        if not free_registers:
            return

        # Pair them in order (most common case: 1 device, 1 register)
        for device, register in zip(unassigned, free_registers):
            device.cash_register = register
            device.save(update_fields=['cash_register'])
            logger.info(f"Auto-asignado dispositivo {device.device_id} a caja {register.name}")


# Instancia global del manager
payment_manager = PaymentIntentManager()
