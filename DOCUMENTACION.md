# CHE GOLOSO - Documentacion Tecnica

Sistema integral de gestion para supermercados/kioscos. Punto de venta, inventario, caja, compras, gastos, promociones, MercadoPago y asistente IA.

---

## 1. Requisitos

| Componente | Version |
|---|---|
| Python | 3.8+ |
| Django | 4.2 |
| Base de datos | SQLite (dev) / PostgreSQL (prod) |
| Node.js | No requerido (vanilla JS) |

### Dependencias principales
- `gunicorn` - Servidor WSGI para produccion
- `dj-database-url` - Parseo de DATABASE_URL
- `openpyxl` - Importacion Excel
- `Pillow` - Manejo de imagenes
- `google-generativeai` - API Gemini (asistente IA)
- `mercadopago` - SDK MercadoPago

---

## 2. Instalacion Local

```bash
# 1. Clonar repositorio
git clone <url-repo>
cd "che goloso"

# 2. Crear entorno virtual
python -m venv venv
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Variables de entorno (crear archivo .env o exportar)
# Minimo necesario para desarrollo:
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True

# Opcionales:
GEMINI_API_KEY=xxx               # Para asistente IA
MP_ACCESS_TOKEN=xxx              # Para MercadoPago

# 5. Crear base de datos y datos iniciales
python manage.py migrate
python manage.py setup_initial_data

# 6. Crear superusuario (si no usas variables de entorno)
python manage.py createsuperuser

# 7. Ejecutar servidor
python manage.py runserver
```

### Datos que crea `setup_initial_data`
- **Roles**: Admin, Cajero Manager, Cashier
- **Metodos de pago**: Efectivo, Debito, Credito, Transferencia, MercadoPago
- **Cajas registradoras**: CAJA-01 (Principal), CAJA-02 (Secundaria)
- **Unidades de medida**: Unidad, Kilogramo, Gramo, Litro, etc.

---

## 3. Deployment en Railway

El proyecto esta configurado para Railway con Docker.

### Variables de entorno requeridas en Railway

| Variable | Descripcion | Ejemplo |
|---|---|---|
| `SECRET_KEY` | Clave secreta Django | `django-insecure-xxx` |
| `DATABASE_URL` | URL PostgreSQL (auto en Railway) | `postgresql://...` |
| `DJANGO_SUPERUSER_USERNAME` | Usuario admin inicial | `admin` |
| `DJANGO_SUPERUSER_PASSWORD` | Password admin inicial | `MiPassword123` |
| `DJANGO_SUPERUSER_EMAIL` | Email admin (opcional) | `admin@chegoloso.com` |
| `ALLOWED_HOSTS` | Hosts permitidos | `chegoloso.up.railway.app` |
| `GEMINI_API_KEY` | API Key de Google Gemini | (opcional) |
| `MP_ACCESS_TOKEN` | Token MercadoPago | (opcional) |

### Proceso de deploy
El archivo `start.sh` ejecuta automaticamente:
1. `python manage.py migrate`
2. `python manage.py setup_initial_data`
3. `python manage.py collectstatic --noinput`
4. `gunicorn superrecord.wsgi`

### Health check
Endpoint: `GET /health/` - Retorna 200 OK si el sistema esta operativo.

---

## 4. Arquitectura

### Estructura de apps

```
superrecord/          # Proyecto Django (settings, urls, wsgi)
accounts/             # Usuarios, roles, autenticacion
cashregister/         # Cajas registradoras, turnos, movimientos
stocks/               # Productos, categorias, empaques, stock
pos/                  # Punto de venta (POS)
purchase/             # Ordenes de compra, proveedores
expenses/             # Gastos operativos
promotions/           # Promociones (NxM, combos, descuentos)
mercadopago/          # Integracion MercadoPago Point
sales/                # Reportes de ventas
signage/              # Generacion de carteleria
assistant/            # Asistente IA (Gemini)
company/              # Datos de empresa y sucursales
decorators/           # Decoradores de permisos
```

### Patron de servicio
La logica de negocio vive en `services.py` dentro de cada app, NO en las vistas:
- `pos/services.py` - `POSService`, `CartService`, `CheckoutService`
- `stocks/services.py` - `StockManagementService` (cascada de stock)
- `promotions/engine.py` - `PromotionEngine` (motor de promociones)
- `mercadopago/services.py` - `MPPointService` (integracion Point)

### Flujo del POS
```
CashShift (turno) --> POSSession --> POSTransaction --> POSTransactionItem
                                                    --> POSPayment
                                                    --> CashMovement
```

### Jerarquia de productos y empaques
```
Producto (stock base en unidades)
  |-- Empaque Unidad    (1 unidad)
  |-- Empaque Display   (N unidades, ej: 12)
  |-- Empaque Bulto     (N displays x N unidades, ej: 12 x 24 = 288)
```

Cuando se recibe mercaderia a nivel bulto, el stock se actualiza en TODOS los niveles proporcionalmente. Cuando se vende, se descuenta del producto base y se recalculan los niveles.

### Sistema de permisos

| Rol | Acceso |
|---|---|
| **Admin** | Acceso total a todo el sistema |
| **Cajero Manager** | POS, Caja, Inventario, Promociones, Carteleria, Reportes |
| **Cashier** | Solo POS y operaciones de caja |

Los decoradores de permisos estan en `decorators/decorators.py`:
- `@group_required(['Admin', 'Cajero Manager'])` - Requiere uno de los roles
- `@admin_required` - Solo Admin
- `@open_shift_required` - Requiere turno de caja abierto
- `@ajax_login_required` - Retorna JSON 401 para APIs

Los superusuarios bypasean TODAS las verificaciones de grupo.

---

## 5. Importacion de Productos por Excel

### Formato del archivo
- Archivo `.xlsx`
- **Cada hoja** = una categoria de producto
- El nombre de la hoja se usa como nombre de la categoria

### Columnas soportadas (nombres flexibles)

| Campo | Nombres aceptados | Requerido |
|---|---|---|
| Nombre | `nombre`, `producto`, `descripcion`, `articulo`, `detalle` | Si |
| Codigo de barras | `cod. barra`, `barcode`, `ean` | No |
| Codigo interno | `cod. interno`, `sku`, `codigo` | No |
| Precio compra | `costo`, `compra`, `p. costo` | No |
| Precio venta | `venta`, `pvp`, `precio`, `p. venta` | No |
| Unidad | `unidad`, `u.m.`, `medida` | No |
| Margen | `margen`, `markup`, `ganancia`, `%` | No |

### Proceso
1. Subir archivo Excel
2. El sistema muestra preview de lo que va a importar
3. Opcion de **flush** (borrar todo el inventario anterior)
4. Confirmar importacion
5. Productos existentes (por barcode o SKU) se actualizan; nuevos se crean

### Formato de precios
Acepta formato argentino (`1.234,56`) y estandar (`1234.56`).

---

## 6. Integracion MercadoPago

### Configuracion
1. Ir a **Admin > Mercado Pago**
2. Ingresar `Access Token` (de la cuenta MP del comercio)
3. Configurar dispositivo Point (Device ID)

### Flujo de pago
1. Cajero cobra en POS seleccionando MercadoPago
2. Sistema crea Payment Intent via API de MP
3. Intent se envia al dispositivo Point
4. Cliente paga en el Point
5. Sistema verifica estado por **polling** + **webhook** (doble redundancia)
6. Transaccion se completa automaticamente

### Webhook
URL a configurar en MercadoPago: `https://tu-dominio.com/mercadopago/webhook/`

---

## 7. Asistente IA (Gemini)

### Configuracion
1. Ir a **Admin > Configurar Asistente IA**
2. Ingresar `GEMINI_API_KEY` (Google AI Studio)
3. Modelo recomendado: `gemini-2.5-flash`

### Funcionalidades
- **Chat**: Consultas sobre ventas, stock, productos, tendencias
- **Escaneo de remitos**: Sube foto de un remito y el sistema extrae los datos automaticamente con vision IA

---

## 8. Base de Datos

### Desarrollo
SQLite: `db.sqlite3` (creado automaticamente)

### Produccion
PostgreSQL via `DATABASE_URL`:
```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### Comandos utiles
```bash
# Crear migraciones despues de cambios en modelos
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Flush completo (BORRA TODO)
python manage.py flush

# Recrear datos iniciales
python manage.py setup_initial_data

# Cargar productos de ejemplo
python manage.py create_sample_products
```

---

## 9. Tests

```bash
# Todos los tests (164+)
python manage.py test tests

# Un modulo especifico
python manage.py test tests.test_pos_api

# Un test especifico
python manage.py test tests.test_pos_api.POSAPITest.test_add_item
```

---

## 10. Convenios del Codigo

- **Moneda**: Formato argentino `$1.234,56` (punto = miles, coma = decimales)
- **Locale**: `es-ar`, timezone `America/Argentina/Buenos_Aires`
- **Colores de marca**: Pink `#E91E8C`, Purple `#2D1E5F`, Yellow `#F5D000`
- **POS**: Modo oscuro dedicado (`pos-dark.css`)
- **Frontend**: Bootstrap 5 + Font Awesome 6, vanilla JS (sin frameworks)
- **Codigos de barras**: EAN-13
- **Ticket**: Formato `CAJA-XX-YYYYMMDD-NNNN`
