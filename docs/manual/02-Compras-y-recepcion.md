# 2. Compras y recepción de mercadería

## Cargar una orden de compra

### Cuándo usarla
Cada vez que le comprás mercadería a un proveedor. La OC te sirve para:
- Dejar registrado qué pediste y a qué precio.
- Al recibir, sumar stock automáticamente y generar el gasto.

### Paso a paso

1. Ir a **Compras → Nueva Orden de Compra**.
2. Seleccionar **proveedor**. Si no existe, crearlo (nombre, CUIT, teléfono).
3. Agregar items. Hay dos formas:

   **A) Escaneando el código de barras (recomendado):**
   - Apuntá la pistola al código del bulto, del display o de la unidad.
   - El sistema detecta automáticamente el empaque que corresponde y lo carga en la fila con su precio sugerido.
   - Abajo del selector vas a ver "= X unidades base" — así confirmás que entendió bien.

   **B) Buscando el producto manualmente:**
   - Escribí el nombre o SKU en el campo de búsqueda.
   - Elegilo del desplegable.
   - En la columna **Empaque** elegí cómo lo estás comprando: Bulto, Display, Unidad o "Unidad base" (si no usás empaques).

4. Por cada fila, completá:
   - **Cantidad:** en la unidad del empaque elegido (si seleccionaste "Bulto x144" y ponés `2`, son 2 bultos = 288 unidades).
   - **Costo:** el precio que te cobra el proveedor **por unidad del empaque** (ej: $14.400 el bulto). Si venías con precios sugeridos cargados en el empaque, aparecen solos.
   - **Precio de venta** (opcional): al recibir, actualiza el precio del producto.
5. Revisar el **IVA** (por defecto 21%).
6. **Crear Orden**. Queda con estado `pending` (pendiente de recibir).

---

## Recepcionar la mercadería

### Cuándo hacerlo
Cuando la mercadería llegó físicamente al local. **Hasta que no la recibás, no suma al stock.**

### Paso a paso

1. Ir a **Compras → [Tu OC pendiente] → Recibir**.
2. Confirmar.

Eso es todo. El sistema hace el resto.

### Qué pasa por atrás

Cuando confirmás la recepción, por cada ítem de la OC el sistema:

1. **Convierte la cantidad a unidades base** según el empaque:
   - Bulto x144 con cantidad 2 → 288 unidades base.
   - Display x12 con cantidad 3 → 36 unidades base.
   - Unidad con cantidad 50 → 50 unidades base.
   - Sin empaque → toma la cantidad tal cual (asume unidades base).
2. **Calcula el costo por unidad base** (costo del empaque ÷ unidades que contiene):
   - Bulto a $14.400 con 144 unidades → $100 por unidad.
3. **Suma el stock** al producto base y **cascadea a todos los empaques** (unidad, display, bulto) automáticamente.
4. **Recalcula el costo promedio** del producto.
5. **Crea un lote (StockBatch)** en unidades base con el precio por unidad. Este lote se consume FIFO al vender.
6. Si pusiste precio de venta en la OC, **actualiza el precio del producto**.
7. **Genera un gasto automático** en categoría "Proveedores" por el total de la OC.
8. Marca la OC como `received`.

---

## Ejemplo práctico

Comprás al proveedor:
- 2 bultos de Coca-Cola a $14.400 c/u.
- 3 displays del mismo producto a $1.200 c/u.
- 50 unidades sueltas a $105 c/u.

Al recibir, el sistema:

| Lo que cargaste | Se traduce a | Costo por unidad | StockBatch creado |
|---|---|---|---|
| 2 bultos × $14.400 | 288 unidades base | $14.400 ÷ 144 = **$100** | 288 @ $100 |
| 3 displays × $1.200 | 36 unidades base | $1.200 ÷ 12 = **$100** | 36 @ $100 |
| 50 unidades × $105 | 50 unidades base | **$105** | 50 @ $105 |

Stock resultante: **374 unidades** distribuidas automáticamente en los 3 niveles (unidad, display, bulto) con costo promedio ponderado correcto.

---

## Comprar el mismo producto a varios proveedores

Si comprás Coca-Cola al proveedor A a $100 y después al proveedor B a $150, el sistema:

- Crea **dos lotes distintos**, cada uno con su precio y fecha.
- El **costo promedio** del producto se recalcula (pasa a ser algo entre $100 y $150, ponderado por cantidad).
- Al vender, se consume **primero el lote más antiguo** (el de $100). La ganancia se calcula con ese costo real — no con el promedio. Esto refleja ganancia verdadera y trazabilidad.

---

## Errores comunes

- **Elegir mal el empaque en la fila.** Si escaneaste un display pero la fila quedó con "Bulto", verificá el selector antes de crear la OC. El hint "= X unidades base" te ayuda a confirmar.
- **Confundir el costo.** El costo que cargás es el costo **del empaque elegido**, no por unidad. Si elegiste "Bulto x144" y ponés costo $100, el sistema va a entender que el bulto de 144 unidades te costó $100, lo cual daría $0,69 por unidad.
- **Olvidarse de recepcionar.** Mientras esté `pending`, el stock no se actualiza y no se genera el gasto.
