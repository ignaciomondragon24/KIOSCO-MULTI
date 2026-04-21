# 3. Vender por el POS (caja)

## Abrir el turno de caja

### Cuándo
Al empezar el día o cambio de cajero. **No podés vender sin turno abierto.**

### Paso a paso

1. Ir a **Caja → Abrir Turno**.
2. Seleccionar la caja (si hay varias).
3. Ingresar el **monto inicial en efectivo** (lo que dejaste como fondo). Contalo antes.
4. Confirmar.

El sistema crea un `CashShift` activo y una sesión POS. Ya podés vender.

---

## Vender

### Paso a paso

1. Ir a **POS**.
2. Agregar productos:
   - **Escaneándolos** con la pistola.
   - **Buscándolos** por nombre o SKU.
   - **Botones rápidos** (para productos frecuentes).
3. Si el producto es **granel**: el sistema abre un modal pidiendo los gramos.
4. Si querés aplicar **descuento manual**: pulsar el ítem y poner el descuento en $ o %.
5. Las **promociones automáticas** (2x1, combos) se aplican solas al carrito.
6. Pulsar **Cobrar**.
7. Ingresar los métodos de pago:
   - Efectivo (si pagó con billete mayor, el sistema calcula vuelto).
   - Débito, crédito, transferencia, MercadoPago.
   - Se puede combinar varios (ej: $1000 efectivo + $500 tarjeta).
8. El sistema valida que la suma sea ≥ total. Si es menor, no procesa.
9. Confirmar. Se imprime el ticket.

### Qué pasa por atrás

Cuando confirmás el cobro (todo dentro de una transacción atómica, si algo falla se revierte):

1. Por cada ítem:
   - Si es granel: `GranelService.registrar_venta()` descuenta gramos de la caramelera y usa el costo ponderado.
   - Si es normal: descuenta stock **en cascada** (unidad, display, bulto) y consume lotes **FIFO** empezando por el más antiguo. El costo real del lote consumido queda guardado en el ítem (sobreescribe el promedio).
2. **Registra los movimientos de caja** por cada pago cobrado (no el vuelto).
3. Marca la transacción como `completed` y genera número de ticket formato `CAJA-XX-YYYYMMDD-NNNN`.
4. Imprime el ticket (ancho 58mm, compatible con XP-58IIH).

---

## Pausar una venta

Si un cliente se olvidó algo y querés liberar la caja para otro:

1. Pulsar **Pausar**.
2. La transacción queda en `suspended`. Podés seguir con la siguiente.
3. Para retomar: **POS → Transacciones Pendientes → Reanudar**.

---

## MercadoPago Point

Si usás la terminal Point integrada:

1. En cobro, seleccionar **MercadoPago Point**.
2. El sistema envía el monto a la terminal.
3. El cliente paga con su tarjeta en la terminal.
4. El POS detecta el pago (polling cada pocos segundos + webhook de respaldo) y cierra la venta automáticamente.

Si la terminal falla o pierde señal, el webhook eventualmente trae la confirmación cuando vuelva. Doble redundancia por diseño.
