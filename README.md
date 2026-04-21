# CHE GOLOSO — Sistema de Gestión de Supermercado

Sistema integral de gestión para supermercados pequeños y medianos desarrollado con Django.  
Desplegado en **Railway** con PostgreSQL en producción.

---

## Características

- **Punto de Venta (POS)** — dark mode, atajos de teclado, búsqueda por código de barras o nombre
- **Pago Mixto Genérico** — cualquier combinación de métodos (efectivo, MercadoPago, etc.)
- **Integración MercadoPago Point** — envío de cobro al lector y polling de estado
- **Control de Inventario** — stock en tiempo real, carga por bultos, movimientos
- **Escaneo de Facturas con IA** — Gemini Vision extrae productos de fotos de facturas
- **Gestión de Caja y Turnos** — apertura, cierre, movimientos, arqueo
- **Sistema de Promociones** — 2x1, combos, descuentos porcentuales y fijos
- **Reportes y Estadísticas** — ventas diarias, por período, por método de pago, exportación a Excel
- **Control de Gastos y Compras** — registro de gastos operativos y compras a proveedores
- **Roles de Usuario** — Admin, Manager, Cajero, Stock Manager

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11, Django 4.2, Django REST Framework |
| Base de Datos | SQLite (desarrollo) / PostgreSQL (producción) |
| Frontend | HTML5, CSS3, Bootstrap 5, JavaScript ES6+ |
| Iconos | Font Awesome 6.0 |
| PDFs | ReportLab, xhtml2pdf |
| Excel | openpyxl |
| IA | Google Gemini (gemini-2.5-flash) |
| Pagos | MercadoPago Point API |
| Deploy | Railway, Gunicorn, WhiteNoise |

## Requisitos Previos

- Python 3.11+
- pip
- Git

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/ignaciomondragon24/golo2.git
cd golo2

# Crear y activar entorno virtual
python -m venv venv
.\venv\Scripts\activate        # Windows
source venv/bin/activate       # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
copy .env.example .env         # Windows
cp .env.example .env           # Linux/Mac
# Editar .env con tus datos

# Migraciones y superusuario
python manage.py migrate
python manage.py createsuperuser

# Datos iniciales (roles, métodos de pago)
python manage.py setup_initial_data

# Iniciar servidor
python manage.py runserver
```

El sistema estará disponible en `http://localhost:8000`

## Estructura del Proyecto

```
che-goloso/
├── accounts/          # Usuarios, roles, permisos, login, dashboard
├── assistant/         # Escaneo de facturas con IA (Gemini Vision)
├── cashregister/      # Cajas registradoras, turnos, movimientos
├── company/           # Datos de la empresa
├── decorators/        # Decoradores de permisos personalizados
├── expenses/          # Gastos operativos
├── helpers/           # Utilidades, generación de PDFs
├── mercadopago/       # Integración MercadoPago Point
├── pos/               # Punto de venta, transacciones, checkout
├── promotions/        # Motor de promociones (2x1, combos, descuentos)
├── purchase/          # Compras y proveedores
├── sales/             # Reportes de ventas y exportación
├── stocks/            # Productos, categorías, inventario, carga por bultos
├── superrecord/       # Configuración del proyecto (settings, urls)
├── static/            # CSS, JS, imágenes
├── templates/         # Plantillas HTML (Bootstrap 5, dark mode POS)
├── tests/             # Tests del proyecto
├── Dockerfile         # Imagen Docker para deploy
├── Procfile           # Comando de inicio para Railway
├── railway.toml       # Configuración de Railway
├── main.py            # Entry point alternativo (Railpack)
├── start.sh           # Script de inicio producción
├── manage.py          # CLI de Django
└── requirements.txt   # Dependencias Python
```

## Roles de Usuario

| Rol | Acceso |
|-----|--------|
| **Admin** | Acceso total al sistema |
| **Manager** | Gestión operativa, reportes, stock, caja |
| **Cashier** | POS y caja únicamente |
| **Stock Manager** | Inventario y productos |

## Comandos Útiles

```bash
# Migraciones
python manage.py makemigrations
python manage.py migrate

# Tests
python manage.py test tests

# Shell interactivo
python manage.py shell

# Recolectar estáticos (producción)
python manage.py collectstatic

# Datos iniciales
python manage.py setup_initial_data
```

## Atajos de Teclado (POS)

| Tecla | Acción |
|-------|--------|
| `F2` | Enfocar búsqueda |
| `F3` | Vaciar carrito |
| `F8` | Ir a cobrar |
| `Enter` | Agregar producto / Confirmar pago |
| `Tab` | Cambiar campo (en pago mixto) |
| `Esc` | Cancelar / Cerrar overlay |

## Formato de Moneda

Formato argentino: `$1.234,56` (punto = miles, coma = decimales).

## Formato de Ticket

```
CAJA-XX-YYYYMMDD-NNNN
```

Ejemplo: `CAJA-01-20260314-0001`

## Deploy en Railway

El proyecto está configurado para Railway con:

- `Dockerfile` + `start.sh` para el build y arranque
- `Procfile` como fallback
- `railway.toml` con healthcheck en `/health/`
- Variables de entorno: `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`, `GEMINI_API_KEY`, `MP_ACCESS_TOKEN`

## Licencia

Proyecto propietario. Todos los derechos reservados.

---

**CHE GOLOSO** — Sistema de Gestión de Supermercado  
© 2024–2026
