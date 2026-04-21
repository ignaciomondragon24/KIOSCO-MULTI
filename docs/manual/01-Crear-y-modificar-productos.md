# 1. Crear y modificar productos

## Crear un producto nuevo

### Cuándo usarlo
Cada vez que llega un artículo nuevo que nunca vendiste. Si ya existe, no lo vuelvas a crear — modificá el existente.

### Paso a paso

1. Ir a **Productos → Nuevo Producto**.
2. Completar los datos básicos:
   - **Nombre** (ej: "Coca-Cola 500ml").
   - **Categoría** (Bebidas, Golosinas, Cigarrillos, etc.). Si no existe, creá una.
   - **Unidad de medida** (Unidad, Gramo, Litro…).
   - **Código de barras** (escaneándolo con la pistola). El sistema alerta si está duplicado.
3. Precios:
   - **Precio de costo:** lo que te cuesta la unidad base.
   - **Precio de venta:** lo que le cobrás al cliente.
4. **Stock inicial:** si ya tenés el producto en el local, poné cuántas unidades tenés. Si no, dejá en 0.
5. **Stock mínimo / máximo:** para alertas de faltante y sobrestock.
6. *(Opcional)* Imagen, color e ícono para el botón del POS.

---

## Configuración de empaques (bulto → display → unidad)

### Cuándo configurarlo
Cuando el producto viene en más de un formato: ej. un bulto de cigarrillos trae 10 displays, cada display tiene 10 atados. Así podés vender por unidad, por display o el bulto entero, y el sistema lleva el stock sincronizado en los tres niveles.

### Paso a paso

En el mismo formulario de producto, marcá los checkboxes y completá:

**Bulto (tildar "Tiene bulto"):**
- Nombre ("Bulto x144").
- Código de barras propio (distinto al del producto base).
- `units_quantity`: unidades totales del bulto (ej: 144).
- `displays_per_bulk`: cuántos displays trae (ej: 12).
- Precio de compra y de venta del bulto.

**Display (tildar "Tiene display"):**
- Nombre ("Display x12").
- Código de barras propio.
- `units_per_display`: unidades por display (ej: 12).
- Precio de compra y venta. Si dejaste vacío, se calcula desde el precio del bulto.

**Unidad (tildar "Tiene unidad"):**
- Nombre ("Unidad").
- Código de barras individual (si existe).
- Precio de compra y venta derivados del bulto.

### Qué pasa por atrás

Cuando guardás por primera vez con empaques, el sistema **reparte** tu stock inicial entre los tres niveles automáticamente. Si tenés 288 unidades y el bulto es de 144:

- Unidad: 288
- Display: 288 ÷ 12 = 24
- Bulto: 288 ÷ 144 = 2

Así todos los niveles muestran la misma realidad en su unidad.

---

## Producto granel / caramelera

### Qué es
Un producto que se vende **por peso** (gomitas, caramelos, fiambres). La caja reconoce una "caramelera" — el frasco donde mezclás varias marcas.

### Cómo crearlo
1. Mismos datos básicos que un producto normal.
2. **Tildar `is_granel`**.
3. Configurar:
   - **Precio cada X gramos:** por ejemplo `$2500 cada 100g`.
   - **Precio por cuarto kilo (oferta):** si tenés precio especial por 250g o más.
   - **Gramos por unidad del paquete de depósito:** si comprás un paquete de 900g que va a ir a la caramelera, poné 900.
4. Vincular con la caramelera física donde se va a volcar (si aplica).

### Particularidades
- **No** usa FIFO: usa **costo promedio ponderado** (se recalcula cada vez que abrís un paquete nuevo en la caramelera).
- Se vende indicando **gramos**, no unidades.
- El precio se calcula proporcional al peso (con reglas distintas arriba/abajo de 250g si tenés precio kilo).
