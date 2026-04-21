"""
Granel Services — Aperturas de bulto, ventas granel, auditorías de caramelera.

El servicio legacy BatchService se mantiene para compatibilidad con pos/services.py.
"""
from decimal import Decimal
from django.db import transaction, OperationalError
from django.utils import timezone

from stocks.models import Product, StockMovement
from .models import (
    StockBatch,
    Caramelera,
    AperturaBulto,
    VentaGranel,
    AuditoriaCaramelera,
)


class GranelService:
    """Servicio para operaciones de carameleras: apertura de bultos, ventas, auditorías."""

    @staticmethod
    @transaction.atomic
    def abrir_paquete(caramelera_id, producto_deposito_id, user, notas='', cantidad=1):
        """
        Abre `cantidad` bolsas del depósito y transfiere su contenido a la caramelera.

        - Valida que el producto esté autorizado para esa caramelera
        - Valida que haya stock suficiente en el depósito
        - Descuenta `cantidad` unidades del stock del depósito
        - Suma los gramos totales a la caramelera
        - Recalcula el costo ponderado
        - Registra AperturaBulto para trazabilidad

        Returns: AperturaBulto creada
        """
        cantidad = int(cantidad)
        if cantidad < 1:
            raise ValueError('La cantidad debe ser al menos 1.')

        try:
            caramelera = Caramelera.objects.select_for_update(nowait=True).get(pk=caramelera_id)
            producto = Product.objects.select_for_update(nowait=True).get(pk=producto_deposito_id)
        except OperationalError:
            raise ValueError('La caramelera o producto está siendo modificado. Intentá de nuevo.')

        # Validaciones
        if not caramelera.productos_autorizados.filter(pk=producto.pk).exists():
            raise ValueError(
                f'"{producto.name}" no está autorizado para la caramelera "{caramelera.nombre}". '
                f'Editá la caramelera para agregar este producto.'
            )
        if not producto.es_deposito_caramelera:
            raise ValueError(f'"{producto.name}" no es un producto para caramelera.')
        if producto.current_stock < cantidad:
            raise ValueError(
                f'Stock insuficiente de "{producto.name}" en depósito. '
                f'Disponible: {int(producto.current_stock)}, solicitado: {cantidad}.'
            )
        if not producto.weight_per_unit_grams or producto.weight_per_unit_grams <= 0:
            raise ValueError(
                f'"{producto.name}" no tiene gramos por unidad configurados. '
                f'Editá el producto para agregar los gramos.'
            )

        gramos_por_unidad = producto.weight_per_unit_grams
        gramos_nuevos = gramos_por_unidad * cantidad
        costo_nuevo_por_gramo = producto.costo_por_gramo

        # Snapshot antes
        stock_antes = caramelera.stock_gramos_actual
        costo_antes = caramelera.costo_ponderado_gramo

        # Fórmula de costo ponderado
        if stock_antes > 0 and costo_antes > 0:
            nuevo_costo = (
                (stock_antes * costo_antes) + (gramos_nuevos * costo_nuevo_por_gramo)
            ) / (stock_antes + gramos_nuevos)
        else:
            nuevo_costo = costo_nuevo_por_gramo

        nuevo_costo = nuevo_costo.quantize(Decimal('0.000001'))

        # Actualizar caramelera
        caramelera.stock_gramos_actual = stock_antes + gramos_nuevos
        caramelera.costo_ponderado_gramo = nuevo_costo
        caramelera.save(update_fields=['stock_gramos_actual', 'costo_ponderado_gramo', 'updated_at'])

        # Descontar unidades del depósito
        producto.current_stock -= cantidad
        producto.save(update_fields=['current_stock', 'updated_at'])

        # Log de apertura
        notas_final = notas
        if cantidad > 1:
            notas_final = f'{cantidad} paquetes' + (f' · {notas}' if notas else '')

        apertura = AperturaBulto.objects.create(
            caramelera=caramelera,
            producto=producto,
            gramos_agregados=gramos_nuevos,
            costo_por_gramo_al_abrir=costo_nuevo_por_gramo,
            costo_ponderado_antes=costo_antes,
            costo_ponderado_despues=nuevo_costo,
            stock_gramos_antes=stock_antes,
            stock_gramos_despues=caramelera.stock_gramos_actual,
            unidades_restantes_deposito=int(producto.current_stock),
            abierto_por=user,
            notas=notas_final,
        )

        # Sincronizar producto POS: stock y costo ponderado
        pos_product = caramelera.producto_pos.filter(is_granel=True).first()
        if pos_product is not None:
            pos_product.current_stock = caramelera.stock_gramos_actual
            pos_product.weighted_avg_cost_per_gram = nuevo_costo
            pos_product.save(update_fields=['current_stock', 'weighted_avg_cost_per_gram', 'updated_at'])

        return apertura

    @staticmethod
    @transaction.atomic
    def realizar_auditoria(caramelera_id, peso_real_balanza, user, motivo=''):
        """
        Compara el stock del sistema con el peso real medido en la balanza.
        Si ajuste_aplicado=True (por defecto), actualiza el stock al peso real.

        Returns: AuditoriaCaramelera creada
        """
        try:
            caramelera = Caramelera.objects.select_for_update(nowait=True).get(pk=caramelera_id)
        except OperationalError:
            raise ValueError('La caramelera está siendo modificada. Intentá de nuevo.')
        peso_real = Decimal(str(peso_real_balanza))
        stock_sistema = caramelera.stock_gramos_actual

        diferencia = stock_sistema - peso_real

        if stock_sistema > 0:
            porcentaje = (diferencia / stock_sistema * Decimal('100')).quantize(Decimal('0.01'))
        else:
            porcentaje = Decimal('0.00')

        auditoria = AuditoriaCaramelera.objects.create(
            caramelera=caramelera,
            stock_sistema_gramos=stock_sistema,
            peso_real_balanza_gramos=peso_real,
            diferencia_gramos=diferencia,
            porcentaje_merma=porcentaje,
            ajuste_aplicado=True,
            motivo=motivo,
            auditado_por=user,
        )

        # Ajustar stock al peso real
        caramelera.stock_gramos_actual = peso_real
        caramelera.save(update_fields=['stock_gramos_actual', 'updated_at'])

        # Sincronizar producto POS
        pos_product = caramelera.producto_pos.filter(is_granel=True).first()
        if pos_product is not None:
            pos_product.current_stock = caramelera.stock_gramos_actual
            pos_product.save(update_fields=['current_stock', 'updated_at'])

        return auditoria

    @staticmethod
    def calcular_precio_venta(caramelera, gramos):
        """
        Calcula el precio de venta para una cantidad de gramos.

        - < 250g → proporcional: (gramos / 100) × precio_100g
        - >= 250g con precio kilo oferta > 0 → regla de tres: (gramos / 1000) × precio_kilo

        Returns: Decimal
        """
        return caramelera.calcular_precio(gramos)

    @staticmethod
    @transaction.atomic
    def registrar_venta(caramelera_id, gramos_vendidos, precio_cobrado,
                        pos_transaction_id=None):
        """
        Registra una venta granel y descuenta el stock de la caramelera.
        Se llama desde el checkout del POS.

        Returns: VentaGranel creada
        """
        try:
            caramelera = Caramelera.objects.select_for_update(nowait=True).get(pk=caramelera_id)
        except OperationalError:
            raise ValueError('La caramelera está siendo modificada. Intentá de nuevo.')
        gramos = Decimal(str(gramos_vendidos))
        precio = Decimal(str(precio_cobrado))

        if gramos <= 0:
            raise ValueError('Los gramos vendidos deben ser mayor a 0')
        if caramelera.stock_gramos_actual < gramos:
            raise ValueError(
                f'Stock insuficiente. Disponible: {caramelera.stock_gramos_actual}g, '
                f'solicitado: {gramos}g'
            )

        costo_gramo = caramelera.costo_ponderado_gramo
        costo_total = (gramos * costo_gramo).quantize(Decimal('0.01'))
        ganancia = (precio - costo_total).quantize(Decimal('0.01'))

        # Determinar tipo de venta
        tipo = 'kilo' if gramos >= Decimal('250') and caramelera.precio_cuarto > 0 else 'libre'

        venta = VentaGranel.objects.create(
            caramelera=caramelera,
            gramos_vendidos=gramos,
            tipo_venta=tipo,
            precio_cobrado=precio,
            costo_gramo_al_vender=costo_gramo,
            costo_total=costo_total,
            ganancia=ganancia,
            pos_transaction_id=pos_transaction_id,
        )

        # Descontar stock
        caramelera.stock_gramos_actual -= gramos
        caramelera.save(update_fields=['stock_gramos_actual', 'updated_at'])

        # Sincronizar producto POS
        pos_product = caramelera.producto_pos.filter(is_granel=True).first()
        if pos_product is not None:
            pos_product.current_stock = caramelera.stock_gramos_actual
            pos_product.save(update_fields=['current_stock', 'updated_at'])

        return venta


# ============================================================
# SERVICIO LEGACY — requerido por pos/services.py
# ============================================================

class BatchService:
    """Servicio FIFO para lotes de stock. Mantenido para compatibilidad con el POS."""

    @staticmethod
    @transaction.atomic
    def create_batch(product_id, quantity, unit_cost, purchased_at=None,
                     supplier_name='', purchase=None, notes='', user=None):
        """Crea un nuevo lote de stock al recibir mercadería."""
        product = Product.objects.select_for_update().get(pk=product_id)
        if purchased_at is None:
            purchased_at = timezone.now()

        batch = StockBatch.objects.create(
            product=product,
            purchase=purchase,
            supplier_name=supplier_name,
            quantity_purchased=Decimal(str(quantity)),
            quantity_remaining=Decimal(str(quantity)),
            purchase_price=Decimal(str(unit_cost)),
            purchased_at=purchased_at,
            created_by=user,
            notes=notes,
        )
        return batch

    @staticmethod
    @transaction.atomic
    def deduct_fifo(product_id, quantity):
        """
        Descuenta la cantidad de los lotes disponibles en orden FIFO.
        Retorna lista de (batch, qty_descontada).
        """
        quantity = Decimal(str(quantity))
        remaining = quantity
        deductions = []

        batches = (
            StockBatch.objects.select_for_update()
            .filter(product_id=product_id, quantity_remaining__gt=0)
            .order_by('purchased_at', 'created_at')
        )

        for batch in batches:
            if remaining <= 0:
                break
            take = min(batch.quantity_remaining, remaining)
            batch.quantity_remaining -= take
            batch.save()
            deductions.append((batch, take))
            remaining -= take

        return deductions

    @staticmethod
    def get_fifo_cost(product_id, quantity):
        """Calcula el costo exacto de vender `quantity` unidades por FIFO, sin descontar."""
        quantity = Decimal(str(quantity))
        remaining = quantity
        total_cost = Decimal('0.00')

        batches = (
            StockBatch.objects
            .filter(product_id=product_id, quantity_remaining__gt=0)
            .order_by('purchased_at', 'created_at')
        )

        for batch in batches:
            if remaining <= 0:
                break
            take = min(batch.quantity_remaining, remaining)
            total_cost += take * batch.unit_cost
            remaining -= take

        return total_cost

    @staticmethod
    def get_batch_summary(product_id):
        """Retorna los lotes activos de un producto en orden FIFO."""
        return (
            StockBatch.objects
            .filter(product_id=product_id, quantity_remaining__gt=0)
            .order_by('purchased_at', 'created_at')
        )
