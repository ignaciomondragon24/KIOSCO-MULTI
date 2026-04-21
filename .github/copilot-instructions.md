# CHE GOLOSO - Sistema de Gestión de Supermercado

## Descripción del Proyecto
Sistema integral de gestión para supermercados pequeños y medianos que integra:
- Punto de Venta (POS) moderno con dark mode
- Pago mixto genérico (cualquier combinación de métodos)
- Integración MercadoPago Point
- Escaneo de facturas con IA (Gemini Vision)
- Control de inventario en tiempo real
- Gestión de caja y turnos
- Sistema de promociones avanzado (2x1, combos, descuentos)
- Reportes y estadísticas con exportación a Excel
- Control de gastos y compras

## Stack Tecnológico
- **Backend**: Python 3.11+, Django 4.2, Django REST Framework
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **Frontend**: HTML5, CSS3 (Bootstrap 5), JavaScript ES6+
- **Iconos**: Font Awesome 6.0
- **PDFs**: ReportLab, xhtml2pdf
- **Excel**: openpyxl
- **IA**: Google Gemini (gemini-2.5-flash) vía google-genai
- **Pagos**: MercadoPago Point API
- **Deploy**: Railway, Gunicorn, WhiteNoise

## Estructura de Apps Django
- `superrecord/` - Proyecto principal (settings, urls, wsgi)
- `accounts/` - Usuarios, roles, permisos, login, dashboard
- `assistant/` - Escaneo de facturas con IA (Gemini Vision)
- `cashregister/` - Cajas registradoras, turnos, movimientos
- `pos/` - Punto de venta, transacciones, carrito, checkout
- `stocks/` - Productos, categorías, unidades, movimientos de stock
- `promotions/` - Motor de promociones (2x1, combos, descuentos)
- `purchase/` - Compras y proveedores
- `expenses/` - Gastos operativos
- `sales/` - Reportes de ventas y exportación
- `mercadopago/` - Integración MercadoPago Point
- `company/` - Datos de la empresa
- `helpers/` - Utilidades y generación de PDFs
- `decorators/` - Decoradores de permisos

## Convenciones de Código
- Usar formato de moneda argentina: $1.234,56
- Dark mode en POS (#1a1a2e background)
- Colores marca: --che-pink: #E91E8C, --che-purple: #2D1E5F, --che-yellow: #F5D000
- Código de barras EAN-13
- Ticket format: CAJA-XX-YYYYMMDD-NNNN

## Comandos Útiles
```bash
# Activar entorno virtual
python -m venv venv
.\venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Datos iniciales
python manage.py setup_initial_data

# Ejecutar servidor
python manage.py runserver

# Tests
python manage.py test tests
```

## Roles de Usuario
- **Admin**: Acceso total
- **Manager**: Gestión operativa
- **Cashier**: Solo POS y caja
- **Stock Manager**: Solo inventario
