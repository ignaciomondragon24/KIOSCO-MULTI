# 5. Ajustes manuales de stock y conteos físicos

## Cuándo hacer un ajuste manual

Cuando el stock del sistema **no coincide** con la realidad física, y la diferencia no viene de una compra o venta. Casos típicos:

- Conteo físico mensual.
- Mercadería rota, vencida o dañada.
- Robo / merma.
- Devolución sin registrar.
- Consumo interno (mate, galletitas para el equipo).
- Error de carga previo.

---

## Conteo físico de un producto

### Paso a paso

1. Ir a **Productos → [Producto] → Conteo Físico**.
2. Contá las unidades reales en el local.
3. Ingresar la **cantidad real contada**.
4. Seleccionar **motivo** (obligatorio): Conteo Físico, Mercadería Dañada, Vencida, Robo/Pérdida, Devolución, Error de carga, Consumo interno, Otro.
5. (Opcional) **Notas** libres (ej: "3 cajas robadas viernes 12").
6. Confirmar.

### Qué pasa por atrás

1. Calcula `diferencia = cantidad_real - cantidad_sistema`.
2. Actualiza el stock del producto al nuevo valor.
3. Crea un `StockMovement` con:
   - Tipo: `adjustment_in` o `adjustment_out` según el signo.
   - Cantidad: la diferencia.
   - Motivo y notas guardadas.
4. Si la diferencia es negativa (hubo merma), **descuenta del lote FIFO más antiguo** para mantener sincronizados los lotes con el stock total.

---

## Ver el historial de movimientos

**Productos → [Producto] → Movimientos**

Ahí ves:

- Compras (entrada).
- Ventas (salida).
- Ajustes manuales con su motivo.
- Apertura de empaques (si aplica).
- Aperturas y ventas de granel.

Se puede filtrar por fecha, tipo y motivo.

---

## Buenas prácticas

- **No uses ajustes manuales para simular compras**. Usá el flujo de OC → recepción para tener trazabilidad y gasto automático.
- **Poné motivo preciso**. "Otro" dificulta análisis posterior. "Robo / Pérdida" te ayuda a detectar patrones.
- **Notá fechas y responsables** en el campo notas cuando hay mercadería perdida o rota.
