"""
AI Assistant Service for CHE GOLOSO.
Integrates with Google Gemini API and provides business context.
"""
import json
import time
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from django.db.models import Sum, Count, Avg, F, Q, DecimalField
from django.db.models.functions import TruncDate, TruncMonth, Cast
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


class BusinessDataCollector:
    """
    Collects business data from the system to provide context to the AI.
    """
    
    def __init__(self):
        self.today = timezone.now().date()
        self.yesterday = self.today - timedelta(days=1)
        self.start_of_month = self.today.replace(day=1)
        self.start_of_week = self.today - timedelta(days=self.today.weekday())
    
    def _format_money(self, amount):
        """Format as Argentine currency."""
        return f"${amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    def get_sales_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get sales summary for the specified period."""
        try:
            from pos.models import POSTransaction, POSTransactionItem
            
            start_date = self.today - timedelta(days=days)
            
            transactions = POSTransaction.objects.filter(
                created_at__date__gte=start_date,
                status='completed'
            )
            
            summary = transactions.aggregate(
                total_ventas=Sum('total'),
                cantidad_transacciones=Count('id'),
                ticket_promedio=Avg('total')
            )
            
            # Ventas por día (todos los días del período)
            daily_sales = list(transactions.annotate(
                fecha=TruncDate('created_at')
            ).values('fecha').annotate(
                total=Sum('total'),
                cantidad=Count('id')
            ).order_by('-fecha'))
            
            # Top productos
            top_products = list(POSTransactionItem.objects.filter(
                transaction__created_at__date__gte=start_date,
                transaction__status='completed'
            ).values(
                'product__name'
            ).annotate(
                cantidad_vendida=Sum('quantity'),
                ingresos=Sum('subtotal')
            ).order_by('-ingresos')[:15])
            
            return {
                'periodo': f'Últimos {days} días',
                'total_ventas': float(summary['total_ventas'] or 0),
                'cantidad_transacciones': summary['cantidad_transacciones'] or 0,
                'ticket_promedio': float(summary['ticket_promedio'] or 0),
                'ventas_diarias': daily_sales,
                'top_productos': top_products
            }
        except Exception as e:
            logger.error(f"Error getting sales summary: {e}")
            return {'error': str(e)}
    
    def get_daily_detail(self, date) -> Dict[str, Any]:
        """Get detailed sales for a specific date."""
        try:
            from pos.models import POSTransaction, POSTransactionItem, POSPayment
            
            transactions = POSTransaction.objects.filter(
                created_at__date=date,
                status='completed'
            )
            
            summary = transactions.aggregate(
                total_ventas=Sum('total'),
                cantidad=Count('id'),
                ticket_promedio=Avg('total')
            )
            
            # Productos vendidos ese día
            products_sold = list(POSTransactionItem.objects.filter(
                transaction__created_at__date=date,
                transaction__status='completed'
            ).values(
                'product__name'
            ).annotate(
                cantidad=Sum('quantity'),
                ingresos=Sum('subtotal')
            ).order_by('-ingresos'))
            
            # Ventas por método de pago
            by_payment = list(POSPayment.objects.filter(
                transaction__created_at__date=date,
                transaction__status='completed'
            ).values(
                'payment_method__name'
            ).annotate(
                total=Sum('amount'),
                cantidad=Count('id')
            ).order_by('-total'))
            
            # Ventas por hora
            by_hour = list(transactions.extra(
                select={'hora': "strftime('%%H', created_at)"}
            ).values('hora').annotate(
                total=Sum('total'),
                cantidad=Count('id')
            ).order_by('hora'))
            
            return {
                'fecha': date.strftime('%d/%m/%Y'),
                'total': float(summary['total_ventas'] or 0),
                'cantidad_transacciones': summary['cantidad'] or 0,
                'ticket_promedio': float(summary['ticket_promedio'] or 0),
                'productos_vendidos': products_sold,
                'por_metodo_pago': by_payment,
                'por_hora': by_hour
            }
        except Exception as e:
            logger.error(f"Error getting daily detail: {e}")
            return {'error': str(e)}
    
    def get_inventory_full(self) -> Dict[str, Any]:
        """Get FULL inventory with all products."""
        try:
            from stocks.models import Product
            
            products = Product.objects.filter(is_active=True).select_related('category', 'unit_of_measure')
            
            all_products = []
            for p in products:
                all_products.append({
                    'nombre': p.name,
                    'categoria': p.category.name if p.category else 'Sin categoría',
                    'precio_venta': float(p.sale_price),
                    'precio_costo': float(p.cost_price),
                    'stock_actual': float(p.current_stock),
                    'stock_minimo': p.min_stock,
                    'unidad': p.unit_of_measure.abbreviation if p.unit_of_measure else 'u',
                    'margen': float(p.sale_price - p.cost_price) if p.cost_price > 0 else 0,
                })
            
            # Stats
            out_of_stock = [p for p in all_products if p['stock_actual'] <= 0]
            low_stock = [p for p in all_products if 0 < p['stock_actual'] < p['stock_minimo']]
            
            total_value = sum(p['stock_actual'] * p['precio_costo'] for p in all_products if p['precio_costo'] > 0)
            
            return {
                'total_productos': len(all_products),
                'sin_stock': len(out_of_stock),
                'stock_bajo': len(low_stock),
                'valor_inventario': total_value,
                'productos': all_products,
                'alertas_sin_stock': [p['nombre'] for p in out_of_stock],
                'alertas_stock_bajo': [f"{p['nombre']}: {p['stock_actual']} {p['unidad']} (mín: {p['stock_minimo']})" for p in low_stock],
            }
        except Exception as e:
            logger.error(f"Error getting inventory: {e}")
            return {'error': str(e)}
    
    def get_inventory_status(self) -> Dict[str, Any]:
        """Get current inventory status and alerts (legacy compat)."""
        full = self.get_inventory_full()
        if 'error' in full:
            return full
        return {
            'total_productos': full['total_productos'],
            'productos_stock_bajo': [],
            'cantidad_stock_bajo': full['stock_bajo'],
            'sin_stock': full['sin_stock'],
            'valor_inventario': full['valor_inventario'],
            'por_categoria': []
        }
    
    def get_cash_status(self) -> Dict[str, Any]:
        """Get current cash register status."""
        try:
            from cashregister.models import CashRegister, CashShift
            
            active_registers = CashRegister.objects.filter(is_active=True)
            
            open_shifts = CashShift.objects.filter(
                status='open'
            ).select_related('cash_register', 'cashier')
            
            shifts_data = []
            for shift in open_shifts:
                shifts_data.append({
                    'caja': shift.cash_register.name,
                    'cajero': shift.cashier.get_full_name() or shift.cashier.username,
                    'inicio': shift.opened_at.strftime('%H:%M'),
                    'monto_inicial': float(shift.initial_amount),
                })
            
            return {
                'cajas_activas': active_registers.count(),
                'turnos_abiertos': len(shifts_data),
                'detalle_turnos': shifts_data
            }
        except Exception as e:
            logger.error(f"Error getting cash status: {e}")
            return {'error': str(e)}
    
    def get_promotions_status(self) -> Dict[str, Any]:
        """Get active promotions and their performance."""
        try:
            from promotions.models import Promotion
            
            active_promos = Promotion.objects.filter(
                status='active'
            ).filter(
                Q(start_date__isnull=True) | Q(start_date__lte=self.today),
                Q(end_date__isnull=True) | Q(end_date__gte=self.today)
            )
            
            promos_data = []
            for promo in active_promos:
                promos_data.append({
                    'nombre': promo.name,
                    'tipo': promo.get_promo_type_display() if hasattr(promo, 'get_promo_type_display') else promo.promo_type,
                    'descuento': str(promo.discount_percent) if promo.discount_percent else 'N/A',
                    'vence': promo.end_date.strftime('%d/%m/%Y') if promo.end_date else 'Sin fecha'
                })
            
            return {
                'promociones_activas': len(promos_data),
                'detalle': promos_data
            }
        except Exception as e:
            logger.error(f"Error getting promotions status: {e}")
            return {'error': str(e)}
    
    def get_expenses_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get expenses summary."""
        try:
            from expenses.models import Expense
            
            start_date = self.today - timedelta(days=days)
            
            expenses = Expense.objects.filter(
                expense_date__gte=start_date
            )
            
            total = expenses.aggregate(total=Sum('amount'))['total'] or 0
            
            by_category = list(expenses.values(
                'category__name'
            ).annotate(
                total=Sum('amount')
            ).order_by('-total'))
            
            return {
                'periodo': f'Últimos {days} días',
                'total_gastos': float(total),
                'por_categoria': by_category
            }
        except Exception as e:
            logger.error(f"Error getting expenses summary: {e}")
            return {'error': str(e)}
    
    def get_purchases_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get purchases summary."""
        try:
            from purchase.models import Purchase
            
            start_date = self.today - timedelta(days=days)
            
            purchases = Purchase.objects.filter(
                order_date__gte=start_date
            )
            
            summary = purchases.aggregate(
                total=Sum('total'),
                cantidad=Count('id')
            )
            
            by_supplier = list(purchases.values(
                'supplier__name'
            ).annotate(
                total=Sum('total')
            ).order_by('-total')[:10])
            
            return {
                'periodo': f'Últimos {days} días',
                'total_compras': float(summary['total'] or 0),
                'cantidad_ordenes': summary['cantidad'] or 0,
                'por_proveedor': by_supplier
            }
        except Exception as e:
            logger.error(f"Error getting purchases summary: {e}")
            return {'error': str(e)}
    
    def get_full_context(self) -> str:
        """
        Get full business context as a formatted string for the AI.
        Includes daily breakdowns, full inventory, and payment details.
        """
        fm = self._format_money
        
        ventas_30d = self.get_sales_summary(30)
        ventas_7d = self.get_sales_summary(7)
        detalle_hoy = self.get_daily_detail(self.today)
        detalle_ayer = self.get_daily_detail(self.yesterday)
        inventario = self.get_inventory_full()
        caja = self.get_cash_status()
        promos = self.get_promotions_status()
        gastos = self.get_expenses_summary()
        compras = self.get_purchases_summary()
        
        parts = [f"📅 DATOS EN TIEMPO REAL - {self.today.strftime('%d/%m/%Y')}"]
        
        # === VENTAS DE HOY ===
        parts.append("\n═══ VENTAS DE HOY ═══")
        if 'error' not in detalle_hoy:
            d = detalle_hoy
            parts.append(f"Total: {fm(d['total'])} | Transacciones: {d['cantidad_transacciones']} | Ticket promedio: {fm(d['ticket_promedio'])}")
            if d['productos_vendidos']:
                parts.append("Productos vendidos hoy:")
                for p in d['productos_vendidos']:
                    parts.append(f"  - {p['product__name']}: {p['cantidad']} u → {fm(float(p['ingresos']))}")
            if d['por_metodo_pago']:
                parts.append("Por método de pago:")
                for m in d['por_metodo_pago']:
                    parts.append(f"  - {m['payment_method__name']}: {fm(float(m['total']))}")
            if d['por_hora']:
                parts.append("Por hora: " + " | ".join(f"{h['hora']}hs: {fm(float(h['total']))}" for h in d['por_hora']))
        else:
            parts.append("  Sin datos de hoy")
        
        # === VENTAS DE AYER ===
        parts.append(f"\n═══ VENTAS DE AYER ({self.yesterday.strftime('%d/%m/%Y')}) ═══")
        if 'error' not in detalle_ayer:
            d = detalle_ayer
            parts.append(f"Total: {fm(d['total'])} | Transacciones: {d['cantidad_transacciones']} | Ticket promedio: {fm(d['ticket_promedio'])}")
            if d['productos_vendidos']:
                parts.append("Productos vendidos ayer:")
                for p in d['productos_vendidos']:
                    parts.append(f"  - {p['product__name']}: {p['cantidad']} u → {fm(float(p['ingresos']))}")
            if d['por_metodo_pago']:
                parts.append("Por método de pago:")
                for m in d['por_metodo_pago']:
                    parts.append(f"  - {m['payment_method__name']}: {fm(float(m['total']))}")
        else:
            parts.append("  Sin datos de ayer")
        
        # === RESUMEN SEMANAL ===
        parts.append("\n═══ RESUMEN ÚLTIMOS 7 DÍAS ═══")
        if 'error' not in ventas_7d:
            v = ventas_7d
            parts.append(f"Total: {fm(v['total_ventas'])} | Transacciones: {v['cantidad_transacciones']} | Ticket promedio: {fm(v['ticket_promedio'])}")
            if v['ventas_diarias']:
                parts.append("Desglose diario:")
                for dia in v['ventas_diarias']:
                    fecha_str = dia['fecha'].strftime('%a %d/%m') if hasattr(dia['fecha'], 'strftime') else str(dia['fecha'])
                    parts.append(f"  - {fecha_str}: {fm(float(dia['total']))} ({dia['cantidad']} transacciones)")
        
        # === RESUMEN MENSUAL ===
        parts.append("\n═══ RESUMEN ÚLTIMOS 30 DÍAS ═══")
        if 'error' not in ventas_30d:
            v = ventas_30d
            parts.append(f"Total: {fm(v['total_ventas'])} | Transacciones: {v['cantidad_transacciones']} | Ticket promedio: {fm(v['ticket_promedio'])}")
            if v['top_productos']:
                parts.append("Top 15 productos más vendidos (30 días):")
                for i, p in enumerate(v['top_productos'], 1):
                    parts.append(f"  {i}. {p['product__name']}: {p['cantidad_vendida']} u → {fm(float(p['ingresos']))}")
        
        # === INVENTARIO COMPLETO ===
        parts.append("\n═══ INVENTARIO COMPLETO ═══")
        if 'error' not in inventario:
            inv = inventario
            parts.append(f"Total productos: {inv['total_productos']} | Sin stock: {inv['sin_stock']} | Stock bajo: {inv['stock_bajo']} | Valor inventario: {fm(inv['valor_inventario'])}")
            if inv['alertas_sin_stock']:
                parts.append(f"⚠️ SIN STOCK: {', '.join(inv['alertas_sin_stock'])}")
            if inv['alertas_stock_bajo']:
                parts.append("⚠️ STOCK BAJO:")
                for a in inv['alertas_stock_bajo']:
                    parts.append(f"  - {a}")
            parts.append("Lista completa de productos:")
            # Agrupar por categoría
            by_cat = {}
            for p in inv['productos']:
                cat = p['categoria']
                if cat not in by_cat:
                    by_cat[cat] = []
                by_cat[cat].append(p)
            for cat, prods in sorted(by_cat.items()):
                parts.append(f"  [{cat}]")
                for p in prods:
                    margen_pct = f" (margen: {p['margen']/p['precio_venta']*100:.0f}%)" if p['precio_venta'] > 0 and p['margen'] > 0 else ""
                    parts.append(f"    {p['nombre']}: stock={p['stock_actual']}{p['unidad']} | venta={fm(p['precio_venta'])} | costo={fm(p['precio_costo'])}{margen_pct}")
        
        # === CAJA ===
        parts.append("\n═══ ESTADO DE CAJA ═══")
        if 'error' not in caja:
            parts.append(f"Cajas activas: {caja['cajas_activas']} | Turnos abiertos: {caja['turnos_abiertos']}")
            for t in caja.get('detalle_turnos', []):
                parts.append(f"  - {t['caja']}: {t['cajero']} desde {t['inicio']} (inicio: {fm(t['monto_inicial'])})")
        
        # === PROMOCIONES ===
        parts.append("\n═══ PROMOCIONES ACTIVAS ═══")
        if 'error' not in promos:
            parts.append(f"Total activas: {promos['promociones_activas']}")
            for p in promos.get('detalle', []):
                parts.append(f"  - {p['nombre']} ({p['tipo']}) - Desc: {p['descuento']}% - Vence: {p['vence']}")
        
        # === GASTOS ===
        parts.append("\n═══ GASTOS (30 días) ═══")
        if 'error' not in gastos:
            parts.append(f"Total: {fm(gastos['total_gastos'])}")
            for c in gastos.get('por_categoria', []):
                parts.append(f"  - {c['category__name'] or 'Sin categoría'}: {fm(float(c['total']))}")
        
        # === COMPRAS ===
        parts.append("\n═══ COMPRAS (30 días) ═══")
        if 'error' not in compras:
            parts.append(f"Total: {fm(compras['total_compras'])} | Órdenes: {compras['cantidad_ordenes']}")
            for s in compras.get('por_proveedor', []):
                parts.append(f"  - {s['supplier__name'] or 'Sin proveedor'}: {fm(float(s['total']))}")
        
        return "\n".join(parts)


class InvoiceScanService:
    """
    Service for scanning invoices/receipts using Gemini Vision.
    Extracts product data from photos of invoices.
    """

    SCAN_PROMPT = """Analizá esta imagen de un remito/factura/comprobante de compra de un supermercado/kiosco en Argentina.

Extraé TODOS los productos que aparezcan con la siguiente información:
- nombre del producto (como aparece en el remito)
- cantidad (unidades, bultos, cajas, etc.)
- tipo_cantidad: "bulto", "display", "unidad" (interpretá del contexto)
- precio_unitario (precio por unidad/bulto como aparece)
- precio_total (precio total de esa línea si aparece)
- codigo_barras (si aparece EAN/código)

También extraé:
- proveedor: nombre del proveedor/empresa emisora
- numero_comprobante: número de factura/remito
- fecha: fecha del comprobante (formato DD/MM/YYYY)
- subtotal: subtotal si aparece
- iva: IVA si aparece
- total: total del comprobante
- metodo_pago: si se indica (efectivo, tarjeta, transferencia, etc.)
- notas: cualquier observación relevante

Respondé ÚNICAMENTE con JSON válido, sin markdown, sin explicaciones. Formato exacto:
{
    "proveedor": "Nombre del Proveedor",
    "numero_comprobante": "0001-00001234",
    "fecha": "14/03/2026",
    "productos": [
        {
            "nombre": "Coca Cola 500ml",
            "cantidad": 24,
            "tipo_cantidad": "unidad",
            "precio_unitario": 850.00,
            "precio_total": 20400.00,
            "codigo_barras": "7790895000126"
        }
    ],
    "subtotal": 20400.00,
    "iva": 4284.00,
    "total": 24684.00,
    "metodo_pago": "efectivo",
    "notas": ""
}

Si algún dato no es legible o no aparece, usá null. Siempre intentá extraer el máximo de información posible."""

    def scan_invoice(self, image_data: bytes, mime_type: str = 'image/jpeg') -> Dict[str, Any]:
        """
        Send an invoice image to Gemini Vision and extract structured data.

        Args:
            image_data: Raw image bytes
            mime_type: MIME type of the image

        Returns:
            Dict with extracted invoice data
        """
        from google import genai
        from google.genai import types
        from .models import AssistantSettings

        start_time = time.time()

        try:
            # Get Gemini client
            assistant_settings = AssistantSettings.get_settings()
            api_key = assistant_settings.openai_api_key
            if not api_key:
                api_key = getattr(settings, 'GEMINI_API_KEY', None)
                if not api_key:
                    import os
                    api_key = os.getenv('GEMINI_API_KEY')
                if not api_key:
                    raise ValueError("No se ha configurado la API key de Gemini")

            client = genai.Client(api_key=api_key)

            # Build multimodal content with image
            image_part = types.Part.from_bytes(data=image_data, mime_type=mime_type)
            text_part = types.Part(text=self.SCAN_PROMPT)

            contents = [
                types.Content(
                    role='user',
                    parts=[image_part, text_part]
                )
            ]

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=4096,
                )
            )

            raw_text = response.text or ''

            # Clean response - remove markdown code blocks if present
            cleaned = raw_text.strip()
            if cleaned.startswith('```'):
                cleaned = cleaned.split('\n', 1)[1] if '\n' in cleaned else cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            if cleaned.startswith('json'):
                cleaned = cleaned[4:].strip()

            invoice_data = json.loads(cleaned)

            elapsed_ms = int((time.time() - start_time) * 1000)

            return {
                'success': True,
                'data': invoice_data,
                'elapsed_ms': elapsed_ms,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Gemini response as JSON: {e}\nRaw: {raw_text[:500]}")
            return {
                'success': False,
                'error': f'No se pudo interpretar la respuesta de Gemini como datos estructurados. Intentá con una foto más clara.',
                'raw_response': raw_text[:1000],
                'elapsed_ms': int((time.time() - start_time) * 1000),
            }
        except Exception as e:
            logger.error(f"Error scanning invoice: {e}")
            error_msg = str(e)
            if '429' in error_msg or 'quota' in error_msg.lower():
                error_msg = "Se excedió la cuota de la API. Esperá un momento y volvé a intentar."
            elif '403' in error_msg:
                error_msg = "API key sin permisos. Verificá que la key sea válida."
            return {
                'success': False,
                'error': error_msg,
                'elapsed_ms': int((time.time() - start_time) * 1000),
            }


class AssistantService:
    """
    Main service for the AI Assistant.
    Handles communication with Google Gemini API and provides business insights.
    """
    
    def __init__(self):
        self.data_collector = BusinessDataCollector()
    
    def _get_gemini_client(self):
        """Get Gemini client and settings."""
        from google import genai
        from .models import AssistantSettings
        
        assistant_settings = AssistantSettings.get_settings()
        
        api_key = assistant_settings.openai_api_key  # Field reused for Gemini key
        if not api_key:
            api_key = getattr(settings, 'GEMINI_API_KEY', None)
            if not api_key:
                import os
                api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("No se ha configurado la API key de Gemini")
        
        client = genai.Client(api_key=api_key)
        return client, assistant_settings
    
    def chat(
        self,
        user_message: str,
        conversation=None,
        include_context: bool = True
    ) -> Dict[str, Any]:
        """
        Send a message to the AI assistant and get a response.
        """
        from google.genai import types
        from .models import Message, QueryLog, AssistantSettings
        
        start_time = time.time()
        
        try:
            client, assistant_settings = self._get_gemini_client()
            
            if not assistant_settings.is_enabled:
                return {
                    'success': False,
                    'error': 'El asistente está deshabilitado',
                    'response': None
                }
            
            # Build system instruction
            system_content = assistant_settings.system_prompt or AssistantSettings.get_default_system_prompt()
            
            if include_context:
                business_context = self.data_collector.get_full_context()
                system_content += f"\n\n--- DATOS ACTUALES DEL NEGOCIO ---\n{business_context}"
            
            # Build conversation history for Gemini SDK format
            contents = []
            if conversation:
                history = conversation.get_messages_for_api(limit=10)
                for msg in history:
                    role = 'user' if msg['role'] == 'user' else 'model'
                    contents.append(
                        types.Content(
                            role=role,
                            parts=[types.Part(text=msg['content'])]
                        )
                    )
            
            # Add current user message
            contents.append(
                types.Content(
                    role='user',
                    parts=[types.Part(text=user_message)]
                )
            )
            
            # Call Gemini API via SDK
            VALID_MODELS = {'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.0-flash', 'gemini-2.0-flash-lite'}
            model_name = assistant_settings.model or 'gemini-2.5-flash'
            if model_name not in VALID_MODELS:
                model_name = 'gemini-2.5-flash'
            
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_content,
                    temperature=assistant_settings.temperature,
                    max_output_tokens=assistant_settings.max_tokens,
                )
            )
            
            assistant_response = response.text or ''
            
            # Extract token usage
            tokens_used = 0
            if response.usage_metadata:
                tokens_used = response.usage_metadata.total_token_count or 0
            
            # Save messages to conversation
            if conversation:
                Message.objects.create(
                    conversation=conversation,
                    role='user',
                    content=user_message
                )
                Message.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=assistant_response,
                    tokens_used=tokens_used
                )
                conversation.save()
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            return {
                'success': True,
                'response': assistant_response,
                'tokens_used': tokens_used,
                'elapsed_ms': elapsed_ms
            }
            
        except Exception as e:
            logger.error(f"Error in assistant chat: {e}")
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            error_msg = str(e)
            if '429' in error_msg or 'quota' in error_msg.lower():
                error_msg = "Se excedió la cuota de la API de Gemini. Esperá un momento y volvé a intentar."
            elif '403' in error_msg:
                error_msg = "API key de Gemini sin permisos. Verificá que la key sea válida."
            
            return {
                'success': False,
                'error': error_msg,
                'response': None,
                'elapsed_ms': elapsed_ms
            }
    
    def get_quick_insights(self) -> List[Dict[str, str]]:
        """
        Get quick insights/recommendations without calling the AI.
        Based on current data analysis.
        """
        insights = []
        
        # Check stock alerts
        inv = self.data_collector.get_inventory_status()
        if 'error' not in inv:
            if inv['sin_stock'] > 0:
                insights.append({
                    'type': 'warning',
                    'icon': 'fa-box-open',
                    'title': 'Productos sin stock',
                    'message': f"Hay {inv['sin_stock']} productos sin stock disponible"
                })
            if inv['cantidad_stock_bajo'] > 0:
                insights.append({
                    'type': 'warning',
                    'icon': 'fa-exclamation-triangle',
                    'title': 'Stock bajo',
                    'message': f"{inv['cantidad_stock_bajo']} productos están por debajo del stock mínimo"
                })
        
        # Check sales performance
        sales = self.data_collector.get_sales_summary(days=7)
        if 'error' not in sales and sales['cantidad_transacciones'] > 0:
            insights.append({
                'type': 'info',
                'icon': 'fa-chart-line',
                'title': 'Ventas de la semana',
                'message': f"${sales['total_ventas']:,.2f} en {sales['cantidad_transacciones']} transacciones".replace(",", "X").replace(".", ",").replace("X", ".")
            })
        
        return insights
    
    def get_suggested_questions(self) -> List[str]:
        """
        Returns a list of suggested questions for the user.
        """
        return [
            "¿Cuáles fueron los productos más vendidos esta semana?",
            "¿Cómo están las ventas comparadas con el mes anterior?",
            "¿Qué productos necesitan reposición urgente?",
            "Dame un resumen del estado del negocio",
            "¿Cuáles son los horarios de mayor venta?",
            "¿Qué promociones me recomendás crear?",
            "Analizá la rentabilidad de las categorías",
            "¿Cuánto gasté este mes en comparación con los ingresos?",
        ]
