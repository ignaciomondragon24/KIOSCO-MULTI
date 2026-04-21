# ✅ CHECKLIST DE TESTING MANUAL — CHE GOLOSO

> Fecha de creación: 19/03/2026  
> Marcar con `[x]` cada caso al verificarlo.

---

## 🔐 1. AUTENTICACIÓN Y ACCESOS (`/accounts/`)

### Login / Logout
- [ ] Acceder a `/` redirige al login si no está autenticado
- [ ] Login con credenciales incorrectas muestra error
- [ ] Login con usuario inactivo muestra error
- [ ] Login exitoso redirige al dashboard
- [ ] Logout cierra sesión y redirige al login

### Dashboard
- [ ] Dashboard carga correctamente para cada rol (Admin, Manager, Cashier, Stock Manager)
- [ ] Cards/métricas del dashboard se muestran correctamente
- [ ] Menú lateral muestra solo las secciones autorizadas según rol

### Gestión de Usuarios (solo Admin/Manager)
- [ ] Listar usuarios: `/accounts/users/`
- [ ] Crear usuario: formulario completo, validaciones, contraseña
- [ ] Editar usuario: cambiar nombre, email, rol
- [ ] Activar/desactivar usuario con toggle
- [ ] Eliminar usuario (confirmación de modal)
- [ ] Un Cashier NO puede acceder a `/accounts/users/` (403 o redirect)

### Perfil
- [ ] Ver perfil propio: `/accounts/profile/`
- [ ] Cambiar contraseña: `/accounts/change-password/` con contraseña actual válida
- [ ] Cambiar contraseña con contraseña actual incorrecta muestra error

---

## 🛒 2. PUNTO DE VENTA — POS (`/pos/`)

### Pantalla Principal
- [ ] POS carga en dark mode sin errores JS en consola
- [ ] Búsqueda de productos por nombre
- [ ] Búsqueda por código de barras (escribir EAN-13)
- [ ] Resultado de búsqueda muestra nombre, precio y stock disponible
- [ ] Agregar producto al carrito

### Carrito
- [ ] Producto se agrega con cantidad 1
- [ ] Incrementar cantidad de un item
- [ ] Decrementar cantidad de un item
- [ ] Eliminar item del carrito
- [ ] Vaciar carrito completo
- [ ] Total se actualiza en tiempo real
- [ ] No se puede agregar más unidades que el stock disponible

### Descuentos
- [ ] Aplicar descuento por porcentaje a un item
- [ ] Aplicar descuento en monto fijo a un item
- [ ] Descuento se refleja en el subtotal del item y en el total

### Promociones
- [ ] Agregar producto con promo 2x1 → aplica automáticamente
- [ ] Agregar combo → descuento correcto
- [ ] Producto sin promo no recibe descuento

### Checkout — Pago
- [ ] Pago solo en efectivo: ingresar monto, ver vuelto
- [ ] Pago solo con tarjeta
- [ ] Pago mixto (ej: 50% efectivo + 50% tarjeta)
- [ ] Venta se registra correctamente en base de datos
- [ ] Stock se descuenta al confirmar venta
- [ ] Ticket se genera y muestra para imprimir

### Transacciones Suspendidas
- [ ] Suspender una venta en curso
- [ ] Ver lista de suspendidas
- [ ] Retomar venta suspendida (carrito se restaura)
- [ ] Cancelar venta suspendida

### Historial de Ventas
- [ ] Ver historial de ventas del turno actual
- [ ] Imprimir ticket de venta anterior

---

## 💰 3. CAJA REGISTRADORA (`/cashregister/`)

### Dashboard de Caja
- [ ] Dashboard muestra estado de la caja (abierta/cerrada)
- [ ] Resumen del turno actual (ventas, efectivo, etc.)

### Turnos
- [ ] Abrir turno: confirmar monto inicial de caja
- [ ] No se puede abrir un segundo turno si ya hay uno abierto
- [ ] Ver detalle de turno en curso
- [ ] Cerrar turno: muestra resumen de ventas y diferencias
- [ ] Ver listado de turnos anteriores
- [ ] Ver turno individual con reporte completo
- [ ] Descargar PDF del reporte de turno

### Movimientos de Caja
- [ ] Registrar ingreso de efectivo (fondo adicional)
- [ ] Registrar egreso de efectivo (retiro)
- [ ] Movimiento aparece en el listado de movimientos del turno
- [ ] Total de caja se actualiza tras el movimiento

### Cajas Registradoras
- [ ] Listar cajas: `/cashregister/registers/`
- [ ] Crear nueva caja
- [ ] No se puede crear caja sin nombre

---

## 📦 4. INVENTARIO / STOCKS (`/stocks/`)

### Productos
- [ ] Listar productos: búsqueda, filtro por categoría, filtro por stock bajo
- [ ] Crear producto: nombre, categoría, código de barras, precio de costo, precio de venta
- [ ] Código de barras duplicado debe dar error
- [ ] Editar producto: cambiar precio, descripción
- [ ] Ver detalle del producto con historial de movimientos
- [ ] Eliminar producto (confirmación)
- [ ] Ajuste manual de stock: ingresar cantidad y motivo

### Categorías
- [ ] Listar categorías
- [ ] Crear categoría con nombre
- [ ] Editar categoría
- [ ] Eliminar categoría (verificar si tiene productos)

### Stock Bajo
- [ ] `/stocks/low-stock/` muestra productos bajo el umbral
- [ ] Umbral de stock bajo es configurable en el producto

### Lista de Precios
- [ ] `/stocks/price-list/` carga y muestra todos los productos con precios
- [ ] Exportar lista de precios a Excel

### Importación / Exportación
- [ ] Exportar productos a Excel (`.xlsx` se descarga correctamente)
- [ ] Importar productos desde Excel (formato correcto)
- [ ] Importar con errores de formato muestra mensaje descriptivo

### Empaquetado / Packaging
- [ ] Configurar unidades de empaque (ej: caja × 30u.)
- [ ] API de cálculo de precios por packaging funciona

---

## 🎁 5. PROMOCIONES (`/promotions/`)

### Gestión
- [ ] Listar promociones activas, pausadas y vencidas
- [ ] Crear promoción tipo **2x1**: seleccionar producto
- [ ] Crear promoción tipo **combo**: seleccionar 2+ productos, precio combo
- [ ] Crear promoción tipo **descuento %**: porcentaje y vigencia
- [ ] Editar promoción existente
- [ ] Eliminar promoción (confirmación)

### Activar / Pausar
- [ ] Activar promoción pausada
- [ ] Pausar promoción activa
- [ ] Promoción vencida (por fecha) no se aplica en POS

### API
- [ ] `api/calculate` devuelve descuento correcto para un combo dado

---

## 🛒 6. COMPRAS Y PROVEEDORES (`/purchase/`)

### Proveedores
- [ ] Listar proveedores
- [ ] Crear proveedor: nombre, CUIT, teléfono, email
- [ ] Editar proveedor
- [ ] Eliminar proveedor (con compras asociadas → advertencia)

### Órdenes de Compra
- [ ] Listar compras con filtros (estado, proveedor, fecha)
- [ ] Crear orden de compra: seleccionar proveedor, agregar ítems
- [ ] Buscar producto en la orden: API `api/products/search`
- [ ] Editar orden en estado borrador
- [ ] Recibir mercadería: `/purchase/<id>/receive/` — stock sube automáticamente
- [ ] Cancelar orden
- [ ] Ver detalle de compra

---

## 💸 8. GASTOS (`/expenses/`)

### Gastos
- [ ] Listar gastos con filtro por fecha y categoría
- [ ] Registrar gasto: monto, categoría, descripción, fecha
- [ ] Editar gasto existente
- [ ] Eliminar gasto (confirmación)

### Categorías de Gastos
- [ ] Listar categorías de gastos
- [ ] Crear nueva categoría
- [ ] Editar categoría
- [ ] Eliminar categoría

### Gastos Recurrentes
- [ ] Listar gastos recurrentes
- [ ] Crear gasto recurrente: frecuencia (mensual, semanal), monto
- [ ] Gasto recurrente genera registro automáticamente en fecha

### Reporte de Gastos
- [ ] `/expenses/report/` muestra totales por categoría y período
- [ ] API `api/by-category` devuelve JSON con datos del gráfico

---

## 📊 9. VENTAS Y REPORTES (`/sales/`)

### Dashboard
- [ ] `/sales/` carga con resumen del día y métricas clave
- [ ] API `api/today-stats` devuelve datos actualizados

### Listado de Ventas
- [ ] Listar todas las ventas con filtros (fecha, cajero, método de pago)
- [ ] Click en venta muestra detalle de items

### Reportes
- [ ] Reporte diario: ventas totales, por método de pago
- [ ] Reporte por período: seleccionar rango de fechas
- [ ] Reporte por productos: más vendidos, unidades y montos
- [ ] Reporte por categorías: qué categorías generan más ingresos
- [ ] Reporte por cajeros: ventas desglosadas por usuario

### Exportación
- [ ] Exportar a Excel: archivo `.xlsx` se descarga
- [ ] Exportar a PDF: archivo `.pdf` se descarga con datos correctos

---

## 🏢 10. EMPRESA (`/company/`)

### Configuración
- [ ] `/company/settings/` muestra datos actuales de la empresa
- [ ] Guardar: nombre, RUT/CUIT, dirección, teléfono, logo
- [ ] Logo cargado aparece en tickets y PDFs

### Sucursales
- [ ] Listar sucursales
- [ ] Crear sucursal con nombre y dirección
- [ ] Editar sucursal
- [ ] Eliminar sucursal (confirmación)

---

## 💳 11. MERCADOPAGO (`/mercadopago/`)

### Dashboard y Credenciales
- [ ] `/mercadopago/` muestra estado de integración
- [ ] `/mercadopago/credentials/` — ingresar Access Token y Public Key
- [ ] Test de conexión: botón "Probar" muestra OK o error de credenciales

### Dispositivos Point
- [ ] `/mercadopago/devices/` lista dispositivos vinculados
- [ ] Sincronizar dispositivos: botón sync actualiza la lista desde la API
- [ ] Editar dispositivo: cambiar nombre o asignación
- [ ] Cambiar modo de dispositivo (online/offline)

### Intenciones de Pago
- [ ] Lista de intenciones con su estado
- [ ] Ver detalle de intención de pago
- [ ] Verificar estado: actualiza el estado desde la API de MP
- [ ] Cancelar intención activa

### Webhook
- [ ] `/mercadopago/webhook/` responde correctamente a POST
- [ ] `/mercadopago/logs/` muestra los webhooks recibidos

### Flujo integrado con POS
- [ ] En checkout del POS, seleccionar "MercadoPago Point" como método
- [ ] Se crea intención de pago y espera confirmación del dispositivo

---

## 🤖 12. ASISTENTE IA (`/assistant/`)

### Chat
- [ ] `/assistant/` carga la interfaz de chat
- [ ] Enviar mensaje — respuesta del asistente Gemini se recibe correctamente
- [ ] Crear nueva conversación: `api/new/`
- [ ] Historial de conversaciones carga mensajes anteriores
- [ ] Cargar conversación específica por ID

### Escaneo de Facturas
- [ ] `/assistant/scan/` carga la pantalla de escaneo
- [ ] Subir imagen de factura (JPG/PNG)
- [ ] Gemini detecta productos, cantidades y precios
- [ ] Confirmar factura importa los datos como compra
- [ ] Crear producto desde escaneo: API crea producto en stocks

### Configuración y Logs
- [ ] `/assistant/settings/` muestra configuración de la API Gemini
- [ ] `/assistant/logs/` muestra historial de consultas a la IA
- [ ] API `api/insights/` devuelve sugerencias/análisis

---

## 🔒 13. PERMISOS Y SEGURIDAD

- [ ] Cashier NO puede acceder a: reportes de ventas, compras, gastos, empresa, usuarios
- [ ] Stock Manager NO puede acceder a: POS, caja, reportes de ventas
- [ ] Usuario sin login es redirigido al login en TODAS las URLs protegidas
- [ ] Token CSRF presente en todos los formularios
- [ ] No hay datos sensibles (passwords, tokens) visibles en HTML renderizado

---

## 🌐 14. PRODUCCIÓN (Railway)

- [ ] `chegoloso.up.railway.app` carga correctamente
- [ ] Login funciona en producción
- [ ] Archivos estáticos (CSS, JS, imágenes) cargan sin 404
- [ ] Fuentes de Google Fonts cargan (requiere internet)
- [ ] No hay errores 500 en ninguna sección
- [ ] Logs de Railway no muestran excepciones críticas

---

## 🖨️ 15. IMPRESIÓN Y PDFs

- [ ] Ticket de venta: formato correcto, número de ticket `CAJA-XX-YYYYMMDD-NNNN`
- [ ] PDF de reporte de turno: datos completos, sin caracteres rotos
- [ ] PDF de reporte de ventas: exporta el rango correcto
- [ ] Precio en formato argentino: `$1.234,56`

---

## 📋 RESUMEN DE PROGRESO

| Sección | Total | ✅ OK | ❌ Falla | ⚠️ Pendiente |
|---|---|---|---|---|
| 1. Autenticación | 13 | | | |
| 2. POS | 24 | | | |
| 3. Caja | 12 | | | |
| 4. Stocks | 20 | | | |
| 5. Promociones | 9 | | | |
| 6. Compras | 11 | | | |
| 8. Gastos | 12 | | | |
| 9. Ventas | 11 | | | |
| 10. Empresa | 7 | | | |
| 11. MercadoPago | 14 | | | |
| 12. Asistente IA | 13 | | | |
| 13. Seguridad | 5 | | | |
| 14. Producción | 7 | | | |
| 15. Impresión | 5 | | | |
| **TOTAL** | **183** | | | |
