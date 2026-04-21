# CHE GOLOSO - Manual de Usuario

Guia practica para usar el sistema CHE GOLOSO. Organizada por rol y tarea.

---

## Acceso al Sistema

1. Abrir el navegador e ir a la direccion del sistema (ej: `https://chegoloso.up.railway.app`)
2. Ingresar **usuario** y **contrasena**
3. El sistema te lleva al Dashboard segun tu rol

### Roles del sistema
- **Admin**: Acceso total (usuarios, configuracion, reportes, todo)
- **Cajero Manager**: POS, caja, inventario, promociones, carteleria, reportes
- **Cajero**: Solo punto de venta y operaciones de caja

### Modo oscuro
El sistema tiene un boton de luna/sol en la barra de navegacion (arriba a la derecha). Haga clic para activar/desactivar el modo oscuro. La preferencia se guarda automaticamente.

---

## PRIMER USO: Carga Inicial de Productos

Antes de empezar a vender, hay que cargar los productos. Hay 3 formas:

### Opcion 1: Importar desde Excel (Recomendado para carga masiva)

1. Ir a **Inventario > Importar Excel**
2. Preparar archivo `.xlsx` con este formato:
   - Cada **hoja** del Excel es una **categoria** (ej: "Bebidas", "Galletitas", "Limpieza")
   - Columnas: `Nombre`, `Precio Compra`, `Precio Venta`, `Codigo de Barras` (opcional)
   - Los nombres de columna son flexibles (acepta "producto", "costo", "venta", etc.)
3. Subir el archivo
4. Revisar el preview que muestra el sistema
5. Marcar "Reemplazar inventario existente" si queres borrar lo anterior
6. Confirmar importacion

**Ejemplo de Excel:**

| Nombre | Precio Compra | Precio Venta | Cod. Barra |
|---|---|---|---|
| Coca Cola 2.25L | 800 | 1200 | 7790895000201 |
| Agua Mineral 2L | 400 | 650 | |
| Galletitas Oreo | 500 | 750 | 7622210111111 |

### Opcion 2: Crear producto individual

1. Ir a **Inventario > Productos > Nuevo Producto**
2. Completar: nombre, categoria, precio compra, precio venta
3. Opcional: codigo de barras, foto, stock inicial
4. Guardar

### Opcion 3: Crear producto rapido desde el POS

1. Escanear un codigo de barras desconocido en el POS
2. Aparece la opcion "Producto Nuevo"
3. Completar nombre y precios
4. El producto se crea y se agrega al carrito

---

## Gestion de Caja

### Abrir un turno

**Obligatorio antes de vender.** Sin turno abierto, no se puede usar el POS.

1. Ir a **Caja > Turnos**
2. Click en **Abrir Turno**
3. Seleccionar caja (CAJA-01 o CAJA-02)
4. Ingresar el monto inicial en efectivo (contado real)
5. Confirmar

### Cerrar un turno

1. Ir a **Caja > Turnos**
2. Click en **Cerrar** en el turno activo
3. Contar el efectivo en caja e ingresarlo
4. El sistema muestra la diferencia entre lo esperado y lo contado
5. Confirmar cierre

### Movimientos de caja

Cada venta en efectivo, gasto, o retiro queda registrado automaticamente como movimiento de caja vinculado al turno activo.

---

## Punto de Venta (POS)

### Acceder al POS
Click en **POS** en la barra de navegacion (requiere turno abierto).

### Buscar y agregar productos

**Con lector de codigo de barras:**
- Escanear el producto. Se agrega automaticamente al carrito.
- Si el codigo no existe, el sistema ofrece crear el producto.

**Busqueda por texto:**
- Escribir en la barra de busqueda: nombre, SKU o codigo de barras
- Aparecen resultados predictivos
- Click en el producto para agregarlo
- Presionar Enter selecciona el primer resultado

**Panel lateral de productos (sin codigo de barras):**
- Click en la pestana "Productos" del panel derecho
- Muestra productos sin codigo de barras con su **codigo interno (SKU)** resaltado
- Click en el producto para agregarlo al carrito
- Usar el filtro de texto para buscar dentro del listado

### Modificar cantidades en el carrito
- Click en **+** o **-** para ajustar cantidad
- Click en el icono de basura para eliminar un producto
- Click en **Vaciar** (o F3) para borrar todo el carrito

### Cobrar una venta

**Cobro rapido (un solo metodo de pago):**
- Usar los botones del panel lateral: Efectivo, MercadoPago, Debito, etc.
- O presionar **F8** para abrir el modal de cobro

**Cobro con pago mixto:**
- Click en "Mixto (MP + Efectivo)" en el panel lateral
- Ingresar monto de MercadoPago
- El resto se cobra en efectivo
- Confirmar

**Cobro con MercadoPago Point:**
- Seleccionar MercadoPago como metodo de pago
- El sistema envia la operacion al dispositivo Point
- Esperar que el cliente pague en el lector
- La venta se completa automaticamente

### Descuentos
- Solo **Admin** y **Cajero Manager** pueden aplicar descuentos
- Click en el icono de descuento en un item del carrito
- Ingresar el monto del descuento

### Tipos de venta especiales

**Venta al costo (F10):**
- Los productos se venden al precio de costo
- Util para empleados o situaciones especiales

**Consumo interno (F11):**
- Registra productos consumidos internamente (no genera ingreso)
- El stock se descuenta igualmente

### Apartar venta (F4)
- Suspende la venta actual sin perderla
- Para recuperarla: F5 (Ver Apartados) y seleccionar la venta

### Reimprimir ticket (F9)
- Reimprime el ultimo ticket emitido
- Tambien disponible desde el historial de ventas

### Historial de ventas del turno
- Panel derecho > pestana "Historial"
- Muestra todas las ventas del turno actual
- Se puede reimprimir cualquier ticket

### Atajos de teclado

| Tecla | Accion |
|---|---|
| F1 | Ayuda |
| F2 | Enfocar busqueda |
| F3 | Vaciar carrito |
| F4 | Apartar venta |
| F5 | Ver apartados |
| F6 | Aplicar descuento |
| F7 | Cancelar venta |
| F8 | Cobrar (abrir modal) |
| F9 | Reimprimir ultimo ticket |
| F10 | Venta al costo |
| F11 | Consumo interno |
| F12 | Ir al dashboard |
| Enter | Buscar / Seleccionar resultado |
| Escape | Cerrar resultados / modal |

---

## Inventario y Productos

### Ver productos
**Inventario > Productos** - Lista todos los productos con buscador y filtros.

### Crear/Editar producto
Campos principales:
- **Nombre**: Nombre del producto
- **Categoria**: Para organizar (se crean desde Inventario > Categorias)
- **Codigo de barras**: EAN-13 (opcional, para escaneo)
- **SKU**: Codigo interno (se genera automaticamente si no se ingresa)
- **Precio compra**: Cuanto cuesta al proveedor
- **Precio venta**: Cuanto se cobra al cliente
- **Stock actual**: Cantidad disponible
- **Stock minimo**: Alerta cuando baja de esta cantidad

### Sistema de empaques (Unidad / Display / Bulto)

Para productos que vienen en distintas presentaciones (ej: un chicle que viene en unidad, display de 12, y bulto de 12 displays).

1. Ir al producto > **Empaques**
2. Configurar:
   - **Unidades por Display**: cuantas unidades tiene un display
   - **Displays por Bulto**: cuantos displays tiene un bulto
3. Para cada nivel configurar: codigo de barras, precio compra, precio venta

**Recibir mercaderia por empaque:**
- En la pantalla de empaques, click "Recibir" en el nivel correspondiente
- Ingresar cantidad y precio de compra (opcional)
- El stock se actualiza en TODOS los niveles automaticamente

**Abrir empaque:**
- Click "Abrir" en un bulto o display
- Convierte el empaque al nivel inferior:
  - Bulto -> Displays (si hay displays configurados)
  - Bulto -> Unidades (si no hay displays)
  - Display -> Unidades

### Lista de precios
**Inventario > Lista de Precios** - Vista rapida de todos los precios para consulta.

### Stock bajo
**Inventario > Stock Bajo** - Productos que estan por debajo del stock minimo.

### Inventario de empaques
**Inventario > Inventario Empaques** - Vista global de stock por niveles de empaque.

---

## Compras (Ordenes de Compra)

### Crear orden de compra
1. **Compras > Ordenes de Compra > Nueva**
2. Seleccionar proveedor (o crear uno nuevo)
3. Agregar productos con cantidad y precio unitario
4. Guardar como borrador

### Recibir compra
1. Abrir la orden de compra (o desde la lista, click en **Recibir** directo)
2. Revisar el detalle de productos y cantidades
3. Click en **Confirmar Recepcion**
4. El sistema automaticamente:
   - Actualiza el stock de cada producto
   - Calcula el costo promedio ponderado (costo FIFO)
   - Crea un lote de stock para historial de precios por proveedor
   - Registra un gasto en la categoria **Proveedores**
5. La orden pasa a estado "Recibida"




### Proveedores
**Compras > Proveedores** - Crear y gestionar proveedores con datos de contacto.

---

## Gastos

### Registrar un gasto
1. **Gastos > Gastos > Nuevo**
2. Completar: descripcion, monto, categoria, metodo de pago, fecha
3. Si el gasto es en **efectivo**, DEBE haber un turno de caja abierto (el sistema valida esto)
4. El gasto en efectivo se registra automaticamente como movimiento de caja

### Categorias de gasto
**Gastos > Categorias** - Crear categorias para organizar los gastos (ej: "Alquiler", "Servicios", "Limpieza").

### Reporte de gastos
**Gastos > Reporte de Gastos** - Ver gastos por periodo y categoria.

---

## Promociones

### Crear promocion
1. **Promociones > Nueva Promocion**
2. Configurar:
   - **Nombre**: Nombre descriptivo
   - **Tipo**: NxM (ej: 2x1), Combo, Descuento porcentual, Descuento fijo
   - **Productos** que aplican
   - **Prioridad**: Numero mayor = se aplica primero
   - **Combinable**: Si puede aplicarse junto con otras promociones
   - **Fechas** de vigencia

### Tipos de promocion

| Tipo | Ejemplo | Descripcion |
|---|---|---|
| NxM | 2x1, 3x2 | Compras N unidades, pagas M |
| Combo | Combo snack | Productos especificos a precio fijo |
| % Descuento | 20% OFF | Porcentaje de descuento |
| $ Descuento | -$200 | Monto fijo de descuento |

Las promociones se aplican **automaticamente** en el POS cuando se agregan los productos al carrito.

---

## Reportes de Ventas

Acceder desde **Reportes** en la barra de navegacion.

### Dashboard de Ventas
Vista general con graficos de ventas del dia, semana y mes.

### Reporte Diario
Ventas del dia actual: total, cantidad de transacciones, por metodo de pago.

### Reporte por Periodo
Seleccionar rango de fechas para ver ventas, ganancias y tendencias.

### Por Producto
Ranking de productos mas vendidos y su rentabilidad.

### Por Categoria
Ventas agrupadas por categoria de producto.

### Por Cajero
Performance de cada cajero: ventas, transacciones, ticket promedio.

---

## Carteleria

### Generar carteles de precios
1. **Carteleria > Plantillas** - Elegir un diseno
2. Seleccionar productos para generar carteles
3. El sistema genera carteles con precios actualizados listos para imprimir

---

## Asistente IA

### Chat
1. **Asistente IA > Chat**
2. Hacer preguntas sobre el negocio:
   - "Cuales fueron los 10 productos mas vendidos esta semana?"
   - "Que productos tienen stock bajo?"
   - "Cual es el margen promedio por categoria?"

### Escanear Remito
1. **Asistente IA > Escanear Remito**
2. Subir foto del remito/factura del proveedor
3. La IA extrae automaticamente los datos (productos, cantidades, precios)
4. Revisar y confirmar para crear la orden de compra

---

## Configuracion (Solo Admin)

### Datos de empresa
**Admin > Empresa** - Nombre, CUIT, direccion, logo.

### Sucursales
**Admin > Sucursales** - Configurar sucursales del negocio.

### Usuarios
**Admin > Usuarios** - Crear usuarios, asignar roles, activar/desactivar cuentas.

**Para crear un cajero nuevo:**
1. Admin > Usuarios > Nuevo
2. Completar nombre de usuario y contrasena
3. Asignar rol "Cashier"
4. Guardar

### Cajas registradoras
**Caja > Cajas Registradoras** - Agregar o editar cajas fisicas.

### Metodos de pago
Ya vienen configurados: Efectivo, Debito, Credito, Transferencia, MercadoPago.

### MercadoPago
**Admin > Mercado Pago** - Configurar Access Token y dispositivo Point.

### Asistente IA
**Admin > Configurar Asistente IA** - Ingresar API Key de Google Gemini.

---

## Flujo de Trabajo Diario Recomendado

### Apertura (manana)
1. Iniciar sesion
2. Abrir turno de caja (contar efectivo inicial)
3. Verificar stock bajo (Inventario > Stock Bajo)
4. Listo para vender

### Durante el dia
1. Usar el POS para las ventas
2. Registrar gastos en efectivo cuando ocurran
3. Recibir mercaderia cuando lleguen proveedores

### Cierre (noche)
1. Cerrar turno de caja (contar efectivo final)
2. Revisar reporte diario
3. Verificar que no haya diferencias en caja

---

## Preguntas Frecuentes

**P: No puedo acceder al POS**
R: Necesitas tener un turno de caja abierto. Ve a Caja > Turnos > Abrir Turno.

**P: Escaneo un codigo de barras y no lo encuentra**
R: El producto no esta cargado. El sistema te ofrece crearlo rapido desde el POS.

**P: Como cargo productos sin codigo de barras?**
R: Crealos desde Inventario > Productos. Cada producto recibe un codigo interno (SKU) automatico. En el POS, busca por nombre o SKU, o usa el panel lateral "Productos" que muestra los productos sin codigo con su SKU resaltado.

**P: Quiero cambiar los precios de muchos productos**
R: Usa Inventario > Importar Excel con los mismos productos y nuevos precios. El sistema actualiza los existentes por codigo de barras o SKU.

**P: Como veo cuanto gane hoy?**
R: Ve a Reportes > Reporte Diario. Muestra ventas totales, por metodo de pago y ganancia.

**P: Puedo usar el sistema desde el celular?**
R: Si, el sistema es responsive. Pero el POS esta optimizado para pantalla grande + lector de codigo de barras.

**P: Se fue la luz / se cerro el navegador**
R: No pasa nada. El turno de caja sigue abierto. Volve a entrar y continua normalmente. Las ventas completadas ya estan guardadas.

**P: Quiero dar un descuento a un cliente**
R: Solo Admin y Cajero Manager pueden aplicar descuentos en el POS. Usa el icono de descuento en el item del carrito.
