# CHANGELOG — CHE GOLOSO

---

## [2026-03-26] Auditoría Integral de Seguridad y Corrección

Resultado de una auditoría arquitectónica completa sobre 5 pilares: atomicidad transaccional, integridad de stock, motor de promociones, seguridad de endpoints y validación de datos IA. Se identificaron **17 hallazgos** (9 críticos, 6 importantes, 2 mejoras) y se aplicaron correcciones en **6 archivos**.

### Archivos modificados

- `pos/services.py`
- `pos/views.py`
- `pos/models.py`
- `mercadopago/views.py`
- `promotions/engine.py`
- `assistant/views.py`

---

### 🔴 CRÍTICO — Atomicidad Transaccional (`pos/services.py`)

**Problema:** `process_payment()` y `process_cost_sale()` usaban `return False` dentro de un bloque `@transaction.atomic` cuando el pago era insuficiente. Esto causaba que Django hiciera **commit** (no rollback), dejando registros fantasma de `CashMovement` y `POSPayment` en la base de datos sin una transacción completada.

**Corrección:**
- Se refactorizaron ambos métodos separándolos en un método externo que captura excepciones y un método interno `_process_payment_atomic` / `_process_cost_sale_atomic` decorado con `@transaction.atomic`.
- El caso de pago insuficiente ahora lanza `raise ValueError(...)` en vez de `return False`, lo que fuerza el **rollback automático** de toda la transacción atómica.
- `process_cost_sale` tenía un bug adicional: modificaba los precios de los ítems a precio de costo **antes** de validar el pago. Si el pago era insuficiente, los precios quedaban alterados. Ahora la modificación de precios ocurre dentro del bloque atómico y se revierte si falla.

---

### 🔴 CRÍTICO — Stock no descontado en pagos MercadoPago (`mercadopago/views.py`)

**Problema:** La función `complete_pos_transaction()` solo creaba un `POSPayment` y marcaba la transacción como completada, pero **nunca descontaba stock** ni registraba el movimiento de caja. Todas las ventas cobradas por MercadoPago Point no afectaban el inventario.

**Corrección:**
- Se agregó la creación de `CashMovement` (ingreso) vinculado al turno activo.
- Se itera sobre todos los `POSTransactionItem` de la transacción y se llama a `StockManagementService.deduct_stock_with_cascade()` (para productos con packaging) o `deduct_stock()` (para productos simples).
- Se importan `CashMovement` y `StockManagementService` dentro de la función.

---

### 🔴 CRÍTICO — Polling no completaba transacción (`mercadopago/views.py`)

**Problema:** `api_check_payment_status()` consultaba el estado del pago y actualizaba el `PaymentIntent`, pero cuando el pago estaba aprobado vía polling, **no llamaba a `complete_pos_transaction()`**. Solo el webhook completaba la transacción, dejando un gap si el webhook fallaba.

**Corrección:**
- Se agregó la llamada a `complete_pos_transaction(intent)` dentro del bloque `if payment_status == 'approved'` en la vista de polling.

---

### 🔴 CRÍTICO — HMAC webhook sin validación real (`mercadopago/views.py`)

**Problema:** `verify_webhook_signature()` retornaba `True` cuando no había `webhook_secret` configurado o cuando no venía firma en el request, permitiendo que cualquier POST externo se procesara como webhook legítimo.

**Corrección:**
- Ahora retorna `False` con un `logger.warning()` cuando no hay secret configurado o no hay firma, rechazando webhooks no verificables.

---

### 🔴 CRÍTICO — Endpoints API sin control de permisos (`pos/views.py`)

**Problema:** Los endpoints API del POS (checkout, carrito, suspender/reanudar/cancelar transacciones) solo tenían `@login_required`, permitiendo que cualquier usuario autenticado (ej: Stock Manager) operara la caja.

**Corrección — 10 endpoints protegidos:**

| Endpoint | Decorador agregado |
|----------|-------------------|
| `api_cart_add` | `@group_required(['Admin', 'Cajero Manager', 'Cashier'])` |
| `api_cart_update` | `@group_required(['Admin', 'Cajero Manager', 'Cashier'])` |
| `api_cart_remove` | `@group_required(['Admin', 'Cajero Manager', 'Cashier'])` |
| `api_cart_clear` | `@group_required(['Admin', 'Cajero Manager', 'Cashier'])` |
| `api_checkout` | `@group_required(['Admin', 'Cajero Manager', 'Cashier'])` |
| `api_transaction_suspend` | `@group_required(['Admin', 'Cajero Manager', 'Cashier'])` |
| `api_transaction_resume` | `@group_required(['Admin', 'Cajero Manager', 'Cashier'])` |
| `api_transaction_cancel` | `@group_required(['Admin', 'Cajero Manager', 'Cashier'])` |
| `api_checkout_cost_sale` | `@group_required(['Admin', 'Cajero Manager'])` |
| `api_checkout_internal_consumption` | `@group_required(['Admin', 'Cajero Manager'])` |

> Nota: Venta a precio de costo y consumo interno están restringidos a Admin/Manager ya que implican pérdida de margen.

---

### 🔴 CRÍTICO — Endpoints API MercadoPago sin permisos (`mercadopago/views.py`)

**Problema:** `api_create_payment_intent`, `api_check_payment_status` y `api_cancel_payment` solo tenían `@login_required`.

**Corrección:**
- Se agregó `@group_required(['Admin', 'Cajero Manager', 'Cashier'])` a las tres vistas.

---

### 🟡 IMPORTANTE — Descuentos combinables se sobreescriben (`pos/services.py`)

**Problema:** En `apply_promotions()`, cuando múltiples promociones combinables aplicaban descuento al mismo ítem, se usaba `item.discount = discount` (asignación), haciendo que solo el último descuento prevaleciera.

**Corrección:**
- Cambiado a `item.discount += discount` para que los descuentos de promociones combinables se **acumulen** correctamente.

---

### 🟡 IMPORTANTE — Segunda unidad descuenta de más (`promotions/engine.py`)

**Problema:** `_apply_second_unit()` calculaba `discounted_qty = qty - 1`, lo que daba descuento a **todas las unidades menos la primera**. Por ejemplo, con 4 unidades se descontaban 3 en vez de 2.

**Corrección:**
- Cambiado a `discounted_qty = int(qty) // 2` (división entera), que representa correctamente "una unidad con descuento por cada par". Con 4 unidades → 2 con descuento. Con 3 → 1 con descuento.

---

### 🟡 IMPORTANTE — Subtotal puede ser negativo (`pos/models.py`)

**Problema:** `POSTransactionItem.save()` calculaba `subtotal = (unit_price * quantity) - discount` sin piso, permitiendo subtotales negativos si un descuento excedía el precio (error de dato o promoción mal configurada).

**Corrección:**
- Cambiado a `subtotal = max((unit_price * quantity) - discount, Decimal('0.00'))` para garantizar que nunca sea negativo.

---

### 🟡 IMPORTANTE — Validación de datos de IA insuficiente (`assistant/views.py`)

**Problema:** `api_confirm_invoice()` no validaba que `productos` fuera una lista (podía ser un dict o string si la IA devolvía formato inesperado), no limitaba rangos de precios/cantidades, y los productos auto-creados quedaban activos inmediatamente.

**Corrección (3 cambios):**

1. **Validación de tipo:** Se cambió `if not productos:` a `if not isinstance(productos, list) or not productos:` para rechazar datos malformados.

2. **Productos auto-creados como inactivos:** Cambiado `is_active=True` a `is_active=False` para que los productos creados automáticamente desde escaneo de remito requieran revisión manual antes de poder venderse.

3. **Validación de rangos:** Se agregaron guardas para rechazar cantidades mayores a 99.999 unidades y precios negativos o mayores a $9.999.999, evitando que datos erróneos de la IA contaminen la base.

---

### Verificación post-cambios

| Check | Resultado |
|-------|-----------|
| Syntax check (6 archivos) | ✅ OK |
| `python manage.py check` | ✅ 0 issues |
| `python manage.py makemigrations --dry-run` | ✅ Sin migraciones nuevas |
| `python manage.py test tests` | ✅ 28/28 tests OK |
