Sos un QA engineer y developer senior. Tu tarea es hacer un testing EXHAUSTIVO del sistema CHE GOLOSO y ARREGLAR todo lo que esté roto.

## MÉTODO DE TRABAJO

Para cada módulo del sistema, seguí este ciclo:
1. Leé las URLs del módulo (urls.py)
2. Leé las vistas (views.py) y los services si existen
3. Leé los templates asociados
4. Leé el JavaScript asociado (archivos en static/)
5. Levantá el servidor con 'python manage.py runserver 8111' en background
6. Hacé requests reales con curl/python contra cada endpoint (GET y POST)
7. Verificá que cada respuesta sea 200 (o el código correcto), que el HTML no tenga errores, y que la lógica sea correcta
8. Si algo falla o tiene bugs: ARREGLALO inmediatamente
9. Después de arreglar, volvé a testear para confirmar que funciona
10. Pasá al siguiente módulo

## SETUP INICIAL

- Activá el venv: source venv/Scripts/activate
- Corré migraciones: python manage.py migrate
- Cargá datos iniciales: python manage.py setup_initial_data
- Creá un superusuario de test si no existe: python manage.py shell -c "from accounts.models import User; User.objects.create_superuser('testadmin', 'test@test.com', 'TestPass123!') if not User.objects.filter(username='testadmin').exists() else print('ya existe')"
- Levantá el server en background en puerto 8111

## MÓDULOS A TESTEAR (en este orden)

### 1. ACCOUNTS - Autenticación y Usuarios
- Login/logout funciona
- Dashboard carga para cada rol
- CRUD de usuarios (crear, editar, activar/desactivar, eliminar)
- Permisos: un cajero NO puede acceder a gestión de usuarios
- Cambio de contraseña funciona

### 2. STOCKS - Productos e Inventario
- Listar productos funciona y muestra datos correctos
- Crear producto con todos los campos (nombre, código de barras, precio, stock, categoría)
- Editar producto
- Eliminar producto
- Búsqueda y filtros funcionan
- Categorías CRUD completo
- Jerarquía padre-hijo (cajas → displays → unidades) y conversiones
- Movimientos de stock (ingreso, ajuste)
- APIs de búsqueda devuelven JSON válido

### 3. POS - Punto de Venta
- La pantalla POS carga sin errores JS
- Búsqueda de productos funciona (por nombre y código de barras)
- Agregar producto al carrito
- Cambiar cantidades (incrementar, decrementar, eliminar)
- No permite agregar más que el stock disponible
- Total se calcula correctamente
- Descuentos por porcentaje y monto fijo
- Checkout con pago efectivo (calcular vuelto)
- Checkout con pago tarjeta
- Checkout con pago mixto
- Verificar que el stock se descuenta después de vender
- Suspender y retomar ventas
- Historial de ventas del turno
- VERIFICAR que el JS del POS (pos.js o similar) no tenga endpoints rotos o funciones que tiren error

### 4. CASHREGISTER - Caja Registradora
- Abrir turno con monto inicial
- No permitir segundo turno si ya hay uno abierto
- Cerrar turno con resumen correcto
- Movimientos de caja (ingresos/egresos manuales)
- Historial de turnos
- PDF de reporte de turno se genera sin error

### 5. PROMOTIONS - Promociones
- CRUD de promociones (2x1, combo, descuento %)
- Activar/pausar promociones
- API calculate devuelve descuento correcto
- Promoción vencida no se aplica

### 6. PURCHASE - Compras y Proveedores
- CRUD de proveedores
- Crear orden de compra con items
- Recibir mercadería (stock sube)
- Cancelar orden
- API de búsqueda de productos para la orden

### 7. EXPENSES - Gastos
- CRUD de gastos y categorías
- Gastos recurrentes
- Reporte por categoría y período

### 8. SALES - Ventas y Reportes
- Dashboard con estadísticas del día
- Listado con filtros
- Reportes por período, producto, categoría, cajero
- Exportar Excel y PDF

### 9. GRANEL - Venta por peso
- Todo el flujo de productos a granel
- Transferencias de bulto a contenedor
- Venta por peso en el POS

### 10. COMPANY - Empresa
- Configuración de datos de la empresa
- CRUD de sucursales

### 11. MERCADOPAGO - Pagos
- Dashboard de integración
- Gestión de credenciales
- Lista de dispositivos Point
- Intenciones de pago

### 12. ASSISTANT - Asistente IA
- Chat carga
- Escaneo de facturas (la vista carga sin error)

### 13. SIGNAGE - Cartelería
- Todo el módulo de cartelería funciona

## QUÉ BUSCAR Y ARREGLAR

- Vistas que devuelven 500 (errores de servidor)
- Templates que referencian variables inexistentes
- URLs que devuelven 404 por mala configuración
- JavaScript que llama a endpoints que no existen o tienen la URL mal
- Formularios que no guardan o dan error al hacer submit
- Queries que fallan (campos que no existen en el modelo, relaciones rotas)
- Filtros de template inexistentes (por ejemplo |currency o |format_price que no están definidos)
- Lógica de negocio incorrecta (stock que no se descuenta, totales mal calculados, permisos que no se verifican)
- Imports rotos
- Migraciones pendientes o inconsistentes

## FORMATO DE REPORTE

Al terminar CADA módulo, reportá así:
- MÓDULO: nombre
- ENDPOINTS TESTEADOS: lista
- BUGS ENCONTRADOS: descripción de cada bug
- FIXES APLICADOS: qué cambiaste y en qué archivo
- ESTADO FINAL: OK o con observaciones

Al terminar TODO, hacé un resumen general con la cantidad de bugs encontrados y arreglados.

## REGLAS

- NO hagas cambios cosméticos ni refactors innecesarios. Solo arreglá lo que está ROTO.
- NO agregues features nuevas.
- NO modifiques tests existentes para que pasen - arreglá el código de producción.
- Si un bug requiere una migración, creala.
- Commiteá los fixes agrupados por módulo.
- Usá la DB SQLite de desarrollo (db.sqlite3).
- El server debe correr en puerto 8111 para no conflictuar con nada.
