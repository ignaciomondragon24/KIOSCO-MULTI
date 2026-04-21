"""
Genera docs/Plan-SaaS-Kiosco.pdf con el plan de escalado del sistema CHE GOLOSO
a un producto SaaS multi-tenant con landing + panel super-admin.

Uso: python docs/build_plan_pdf.py
"""
from pathlib import Path
from xhtml2pdf import pisa

ROOT = Path(__file__).resolve().parent
OUT_PDF = ROOT / 'Plan-SaaS-Kiosco.pdf'

CSS = """
@page {
    size: A4;
    margin: 2.2cm 2cm 2cm 2cm;
    @frame footer {
        -pdf-frame-content: footerContent;
        left: 2cm; right: 2cm;
        bottom: 1cm; height: 0.7cm;
    }
}
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11pt;
    color: #1a1a2e;
    line-height: 1.5;
}
.cover {
    text-align: center;
    padding-top: 5cm;
}
.cover h1 {
    font-size: 38pt;
    color: #E91E8C;
    margin: 0 0 6pt 0;
    border: 0;
}
.cover .sub {
    font-size: 16pt;
    color: #2D1E5F;
    margin-bottom: 20pt;
}
.cover .tagline {
    font-size: 12pt;
    color: #555;
    margin: 0 2cm 30pt 2cm;
    font-style: italic;
}
.cover .meta {
    font-size: 10pt;
    color: #777;
    margin-top: 2cm;
}
h1 {
    color: #E91E8C;
    font-size: 22pt;
    border-bottom: 2pt solid #E91E8C;
    padding-bottom: 4pt;
    margin-top: 0;
    -pdf-keep-with-next: true;
}
h2 {
    color: #2D1E5F;
    font-size: 14pt;
    margin-top: 18pt;
    margin-bottom: 6pt;
    -pdf-keep-with-next: true;
}
h3 {
    color: #2D1E5F;
    font-size: 12pt;
    margin-top: 12pt;
    margin-bottom: 4pt;
    -pdf-keep-with-next: true;
}
p { margin: 4pt 0 8pt 0; }
ul, ol { margin: 4pt 0 10pt 16pt; }
li { margin-bottom: 3pt; }
strong { color: #2D1E5F; }
code {
    font-family: Courier, monospace;
    background: #f4f4f8;
    padding: 1pt 4pt;
    border-radius: 2pt;
    font-size: 10pt;
    color: #c7296b;
}
pre {
    background: #f4f4f8;
    border-left: 3pt solid #E91E8C;
    padding: 8pt 10pt;
    font-family: Courier, monospace;
    font-size: 9pt;
    color: #2D1E5F;
    margin: 8pt 0;
    white-space: pre-wrap;
}
hr {
    border: 0;
    border-top: 1pt solid #ddd;
    margin: 14pt 0;
}
.page-break { page-break-before: always; }
.footer {
    text-align: center;
    font-size: 8pt;
    color: #999;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 8pt 0 12pt 0;
    font-size: 10pt;
}
th {
    background: #2D1E5F;
    color: #fff;
    padding: 5pt 7pt;
    text-align: left;
    font-weight: bold;
}
td {
    padding: 5pt 7pt;
    border-bottom: 1pt solid #e0e0e0;
    vertical-align: top;
}
tr:nth-child(even) td {
    background: #faf7fb;
}
.highlight {
    background: #fff3e0;
    border-left: 3pt solid #F5D000;
    padding: 8pt 10pt;
    margin: 8pt 0;
    font-size: 10.5pt;
}
.warning {
    background: #fdecea;
    border-left: 3pt solid #E91E8C;
    padding: 8pt 10pt;
    margin: 8pt 0;
    font-size: 10.5pt;
}
.checklist {
    list-style: none;
    padding-left: 0;
    margin-left: 0;
}
.checklist li {
    padding: 2pt 0 2pt 22pt;
    text-indent: -22pt;
    margin-bottom: 4pt;
}
.checklist li:before {
    content: "\\2610   ";
    font-size: 13pt;
    color: #2D1E5F;
}
.phase-header {
    background: linear-gradient(90deg, #E91E8C, #2D1E5F);
    background-color: #2D1E5F;
    color: #fff;
    padding: 6pt 12pt;
    margin: 12pt 0 8pt 0;
    font-size: 13pt;
    font-weight: bold;
    border-radius: 3pt;
}
.badge {
    display: inline-block;
    background: #F5D000;
    color: #2D1E5F;
    padding: 1pt 6pt;
    font-size: 9pt;
    font-weight: bold;
    border-radius: 8pt;
    margin-right: 4pt;
}
.toc {
    margin: 12pt 0;
    font-size: 11pt;
}
.toc ol {
    list-style-position: inside;
    padding-left: 0;
}
.toc li {
    margin-bottom: 4pt;
}
"""


HTML_BODY = """
<div class="cover">
    <h1>CHE GOLOSO</h1>
    <div class="sub">Plan de escalado a producto SaaS</div>
    <div class="tagline">
        De sistema propio a plataforma multi-tenant<br/>
        con landing comercial y panel de administración central
    </div>
    <div class="meta">
        Plan de trabajo &middot; Abril 2026<br/>
        Autor: Ignacio Mondragon
    </div>
</div>
<div class="page-break"></div>

<h1>1. Resumen ejecutivo</h1>

<p>
El objetivo es transformar el sistema CHE GOLOSO (hoy monolito Django para un solo
kiosco) en un producto vendible a multiples kioscos, con las siguientes decisiones
de negocio ya tomadas:
</p>

<ul>
    <li><strong>La venta es cara a cara.</strong> La landing es catalogo y gancho, no checkout. El precio se arregla en persona.</li>
    <li><strong>El onboarding es manual.</strong> El dueno del SaaS (Nacho) crea cada tenant desde un panel de administracion central, carga logo, nombre y datos del kiosco, y entrega las credenciales.</li>
    <li><strong>No hay billing automatico.</strong> El cobro es a mano (transferencia, MP personal, efectivo). El sistema solo necesita marcar un tenant como activo o suspendido.</li>
    <li><strong>No se integra facturacion electronica AFIP.</strong> El mercado objetivo factura mayormente en negro. Los diferenciadores de venta son otros.</li>
</ul>

<div class="highlight">
    <strong>Recomendacion de arranque:</strong> empezar por la landing (3-5 dias de trabajo) para
    poder salir a vender con material concreto esta misma semana. El desarrollo multi-tenant
    se hace en paralelo, y el primer cliente (si aparece antes) se atiende con una instancia
    dedicada de Railway hasta que el sistema multi-tenant este listo para migrarlo.
</div>

<h1 class="page-break">2. Indice</h1>
<div class="toc">
<ol>
    <li>Resumen ejecutivo</li>
    <li>Indice</li>
    <li>Estrategia de arranque y orden de trabajo</li>
    <li>Cronograma general</li>
    <li>Arquitectura del producto</li>
    <li>Diferenciadores comerciales (ya existentes y a construir)</li>
    <li>Plan por fases con checklist accionable</li>
    <li>Riesgos y decisiones tecnicas sensibles</li>
    <li>Proximos pasos concretos para esta semana</li>
</ol>
</div>

<h1 class="page-break">3. Estrategia de arranque</h1>

<h2>Por que empezar por la landing y no por el multi-tenant</h2>
<ol>
    <li><strong>Vender se puede esta semana.</strong> Con una landing simple y un video demo, hay material para ir al kiosco, mandar por WhatsApp, imprimir QR. No hace falta esperar 3 semanas de desarrollo.</li>
    <li><strong>El primer cliente no necesita multi-tenant.</strong> Se clona el repo, se levanta un project nuevo en Railway, se deploya, se entrega la URL. Despues se migra al sistema multi-tenant con un <code>pg_dump</code> + restore en un schema.</li>
    <li><strong>La landing genera contactos mientras se programa.</strong> El desarrollo del multi-tenant se hace sin presion, sin romper el sistema actual que ya esta sirviendo a clientes piloto.</li>
</ol>

<h2>Por que no empezar por multi-tenant</h2>
<ul>
    <li>Son 4 a 6 semanas de trabajo sin ver un peso.</li>
    <li>Hasta no tener un cliente real, no sabemos si el precio, el plan, o los features priorizados son los correctos.</li>
    <li>Riesgo alto de romper el POS que ya funciona por tocar <code>settings.py</code>, middleware, rutas y modelos.</li>
</ul>

<h2>Por que no empezar por un feature killer (ej. cuenta corriente o PWA)</h2>
<p>
Son features que agregan valor, pero hasta no tener el canal comercial (landing) y la
arquitectura para escalar (multi-tenant), construir features es arar en el mar. Primero
hay que tener a quien venderle.
</p>

<h1 class="page-break">4. Cronograma general</h1>

<table>
    <thead>
        <tr>
            <th style="width:12%">Semana</th>
            <th style="width:48%">Entregable</th>
            <th style="width:40%">Resultado esperado</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>1</strong></td>
            <td>Landing minima + video demo + dominio</td>
            <td>Material de venta listo. Primeras visitas agendadas.</td>
        </tr>
        <tr>
            <td><strong>2</strong></td>
            <td>Primer cliente (instancia dedicada) + arranque multi-tenant</td>
            <td>Primer ingreso. Base tecnica en marcha.</td>
        </tr>
        <tr>
            <td><strong>3-4</strong></td>
            <td>django-tenants integrado + refactor SHARED/TENANT apps</td>
            <td>Multi-tenancy funcionando con un tenant de prueba.</td>
        </tr>
        <tr>
            <td><strong>5</strong></td>
            <td>Panel super-admin (crear, editar, suspender tenants)</td>
            <td>Onboarding manual 100% self-service desde el panel.</td>
        </tr>
        <tr>
            <td><strong>6</strong></td>
            <td>Migracion del primer cliente al sistema multi-tenant</td>
            <td>Unificacion. Una sola base de codigo en produccion.</td>
        </tr>
        <tr>
            <td><strong>7-10</strong></td>
            <td>Features de valor: cuenta corriente, PWA dueno, vencimientos, alertas</td>
            <td>Sistema mas vendible. Margen para subir precio.</td>
        </tr>
        <tr>
            <td><strong>10+</strong></td>
            <td>Iteracion comercial + mejoras segun feedback</td>
            <td>Crecimiento basado en datos reales.</td>
        </tr>
    </tbody>
</table>

<h1 class="page-break">5. Arquitectura del producto</h1>

<h2>5.1. Landing (schema public)</h2>
<p>Pagina unica dentro del mismo proyecto Django, en el schema <code>public</code>. URL: <code>tugoloteca.com</code> (o dominio definitivo).</p>

<h3>Secciones de la landing</h3>
<ol>
    <li><strong>Hero</strong>: titular corto + video de 30s del POS en accion + boton "Hablar por WhatsApp".</li>
    <li><strong>Lo que te damos</strong>: grilla con 6-8 features con iconos.</li>
    <li><strong>Capturas reales</strong>: POS, stock, promociones, dashboard, granel, MP Point.</li>
    <li><strong>Planes</strong>: Bronce / Plata / Oro con "desde $X" y boton "Contactar" (no boton "Pagar").</li>
    <li><strong>Testimonios</strong>: se agregan a medida que haya clientes.</li>
    <li><strong>FAQ</strong>: internet, impresora, soporte, tiempo de instalacion, que pasa si dejo de pagar.</li>
    <li><strong>Footer</strong>: WhatsApp, Instagram, email.</li>
</ol>

<h2>5.2. Panel super-admin (schema public, solo Nacho)</h2>
<p>
Ruta protegida <code>/super-admin/</code>. Solo superuser con rol especial puede entrar.
Este es el centro de control del negocio.
</p>

<h3>Pantallas del panel</h3>

<h3>Lista de tenants</h3>
<p>Tabla con: subdomain, nombre del kiosco, plan, estado (activo/suspendido), fecha de creacion, ultimo acceso, ventas del mes. Botones por fila: Entrar, Editar, Suspender, Eliminar.</p>

<h3>Crear tenant (wizard en 4 pasos)</h3>
<ul>
    <li><strong>Paso 1 - Datos del kiosco</strong>: subdomain (<code>kiosco-pepito</code>), nombre comercial, logo (upload), direccion, telefono, email, CUIT, condicion fiscal.</li>
    <li><strong>Paso 2 - Plan</strong>: Bronce / Plata / Oro (activa o desactiva features segun el plan via permisos).</li>
    <li><strong>Paso 3 - Usuario admin inicial</strong>: nombre, username, password, email.</li>
    <li><strong>Paso 4 - Datos demo</strong>: checkbox "cargar 20 productos tipicos de kiosco" para que el dueno pruebe inmediatamente.</li>
    <li><strong>Boton "Crear"</strong>: corre la creacion del schema, migraciones, seeds y usuario admin.</li>
</ul>

<h3>Editar tenant</h3>
<p>Editar logo, nombre, datos fiscales, plan. Se persiste en la <code>Company</code> del schema correspondiente.</p>

<h3>Impersonar ("Entrar como")</h3>
<p>Boton que loguea a Nacho automaticamente dentro del tenant, con fines de soporte tecnico. Se registra en auditoria.</p>

<h3>Metricas globales</h3>
<ul>
    <li>Total de tenants activos vs suspendidos.</li>
    <li>Ventas totales del mes sumando todos los tenants.</li>
    <li>Tenants sin actividad en los ultimos 7 dias (alerta de posible churn).</li>
</ul>

<h2>5.3. Multi-tenant tecnico</h2>

<h3>Estrategia elegida: schema-per-tenant con django-tenants</h3>
<p>
Una sola base de datos Postgres en Railway. Cada kiosco tiene su propio schema
dentro de esa base. Aislamiento fuerte de datos, backups por tenant, y si un
cliente se va, se borra su schema y listo.
</p>

<div class="warning">
    <strong>Importante:</strong> descartada la opcion "tenant_id en cada fila" porque con
    el tamano del modelo de datos actual (<code>POSTransaction</code>, <code>POSTransactionItem</code>,
    promociones con FKs cruzadas), un filtro olvidado = fuga de datos entre kioscos.
    Schema-per-tenant previene eso por arquitectura.
</div>

<h3>Refactor del monolito</h3>

<h3>SHARED_APPS (schema public)</h3>
<ul>
    <li><code>django.contrib.contenttypes</code>, <code>auth</code>, <code>sessions</code>, <code>admin</code></li>
    <li><code>tenants</code> (nueva): modelos <code>Client</code> y <code>Domain</code> de django-tenants.</li>
    <li><code>landing</code> (nueva): paginas publicas.</li>
    <li><code>super_admin</code> (nueva): panel de administracion central.</li>
</ul>

<h3>TENANT_APPS (uno por kiosco)</h3>
<ul>
    <li><code>accounts</code>, <code>cashregister</code>, <code>pos</code>, <code>stocks</code>, <code>promotions</code>,
    <code>purchase</code>, <code>expenses</code>, <code>sales</code>, <code>company</code>,
    <code>mercadopago</code>, <code>assistant</code>, <code>signage</code>, <code>granel</code>.</li>
</ul>

<h3>Cambios concretos en settings.py</h3>
<ul>
    <li>Partir <code>INSTALLED_APPS</code> en <code>SHARED_APPS</code> + <code>TENANT_APPS</code>.</li>
    <li>Cambiar <code>DATABASES['default']['ENGINE']</code> a <code>django_tenants.postgresql_backend</code>.</li>
    <li>Agregar <code>django_tenants.middleware.main.TenantMainMiddleware</code> al inicio del <code>MIDDLEWARE</code>.</li>
    <li>Agregar <code>DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)</code>.</li>
    <li>Crear <code>public_urls.py</code> (landing + super-admin) y dejar <code>superrecord/urls.py</code> para tenants.</li>
    <li>Revisar <code>Company.get_company()</code> singleton: con django-tenants sigue funcionando pero ahora existe uno por schema.</li>
    <li>Media files: prefijar con schema (<code>company/&lt;schema&gt;/logo.png</code>) o migrar a S3/R2.</li>
</ul>

<h3>Provisioning: management command create_tenant</h3>
<p>
Un comando reutilizable que se llama desde el wizard del panel super-admin
o directamente desde la shell.
</p>
<pre>python manage.py create_tenant \\
    --subdomain kiosco-pepito \\
    --name "Kiosco Pepito" \\
    --admin-username pepito \\
    --admin-password XXXX \\
    --plan plata \\
    --seed-demo-data</pre>

<p>Internamente ejecuta:</p>
<ol>
    <li>Crea <code>Client(schema_name='kiosco_pepito', name=..., plan='plata', status='active')</code>.</li>
    <li>django-tenants corre migraciones sobre el schema.</li>
    <li>Corre <code>setup_initial_data</code> (roles, metodos de pago).</li>
    <li>Crea el usuario admin del tenant.</li>
    <li>Crea la <code>Company</code> singleton con el logo.</li>
    <li>Si <code>--seed-demo-data</code>: 20 productos tipicos de kiosco.</li>
    <li>Crea el <code>Domain</code> <code>kiosco-pepito.tugoloteca.com</code>.</li>
</ol>

<h3>Estado del tenant y control de acceso</h3>
<p>
Un middleware chequea <code>request.tenant.status</code>. Si es <code>suspended</code>, muestra
una pantalla "Contacta al administrador" y no deja operar el sistema. Esto permite
cortar el servicio manualmente cuando un cliente no paga, sin necesidad de billing
automatico.
</p>

<h3>Infraestructura en Railway</h3>
<ul>
    <li>Un Postgres compartido (schema por tenant).</li>
    <li>Un service Django (web).</li>
    <li>Opcional: un service Celery worker + Redis para tareas async (provisioning pesado, alertas).</li>
    <li>Dominio wildcard <code>*.tugoloteca.com</code> configurado en Cloudflare apuntado al CNAME de Railway.</li>
</ul>

<h1 class="page-break">6. Diferenciadores comerciales</h1>

<h2>Features ya existentes que son gancho de venta fuerte</h2>
<table>
    <thead>
        <tr>
            <th>Feature</th>
            <th>Donde vive</th>
            <th>Gancho de venta</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Cobro con posnet Mercado Pago Point</td>
            <td><code>mercadopago/services.py</code></td>
            <td>Cobras con debito/credito sin salir del sistema.</td>
        </tr>
        <tr>
            <td>Escaneo de facturas con IA (Gemini)</td>
            <td><code>assistant/services.py</code></td>
            <td>Foto a la factura y carga 30 productos en 10 segundos.</td>
        </tr>
        <tr>
            <td>Granel con costo ponderado y merma</td>
            <td><code>granel/</code></td>
            <td>Vende gomitas al peso sin perder plata.</td>
        </tr>
        <tr>
            <td>Motor de promociones con prioridad</td>
            <td><code>promotions/engine.py</code></td>
            <td>2x1, 3ro al 50%, combos: sin programar.</td>
        </tr>
        <tr>
            <td>Atajos de teclado configurables</td>
            <td><code>pos/models.py</code></td>
            <td>El cajero va tan rapido como tipea.</td>
        </tr>
        <tr>
            <td>Carteleria digital</td>
            <td><code>signage/</code></td>
            <td>Muestra ofertas en una pantalla incluida.</td>
        </tr>
        <tr>
            <td>Padre-hijo de productos (bulto-display-unidad)</td>
            <td><code>stocks/services.py</code></td>
            <td>Cargas el bulto, descontas la unidad.</td>
        </tr>
    </tbody>
</table>

<h2>Features a construir (en orden de prioridad, sin AFIP)</h2>

<h3>1. Cuenta corriente de clientes (fiado) <span class="badge">CRITICO</span></h3>
<p>Oro puro en kiosco argentino. Sin esto no es competencia. Modelos: <code>Customer</code>, <code>CustomerAccount</code> con saldo, <code>AccountMovement</code> (venta a fiado, pago recibido). Nuevo <code>PaymentMethod</code> "Cuenta corriente" que en vez de plata real suma al saldo del cliente. Listado "quien me debe y cuanto".</p>

<h3>2. Dashboard movil del dueno (PWA) <span class="badge">ALTO</span></h3>
<p>Vista mobile-first en <code>/owner/</code>. Ventas del dia, ranking de productos, comparacion con ayer/semana pasada. El dueno se va a casa y desde el celular ve si el cajero le robo.</p>

<h3>3. Control de vencimientos <span class="badge">ALTO</span></h3>
<p>Campo <code>expires_at</code> en producto o lote (<code>ProductBatch</code>). Alerta "vence en 7 dias". Salva plata real en chocolates, lacteos, tabaco.</p>

<h3>4. Alertas por Telegram <span class="badge">MEDIO</span></h3>
<p>Bot simple que avisa: caja abierta hace 14 horas, stock bajo, venta mayor a $X, producto mas vendido del dia a las 23hs. Gratis y vendible como "seguridad".</p>

<h3>5. Modo offline del POS <span class="badge">MEDIO</span></h3>
<p>Service worker + IndexedDB. Si no hay internet, vende igual y sincroniza al volver. Esta es la diferencia entre "software real" y "webapp".</p>

<h3>6. Asistente IA conversacional <span class="badge">DIFERENCIADOR</span></h3>
<p>Reusa <code>GoogleGeminiService</code>. El dueno escribe "cuanto vendi de Coca 2.25 este mes vs el anterior?". Gemini + <code>BusinessDataCollector</code> con function-calling sobre los modelos.</p>

<h3>7. Sugerencia automatica de reposicion <span class="badge">DIFERENCIADOR</span></h3>
<p>Con historial en <code>POSTransactionItem</code> se calcula rotacion semanal y se genera orden de compra sugerida. Se engancha a <code>purchase/</code>.</p>

<h2>Propuesta de planes</h2>
<table>
    <thead>
        <tr>
            <th>Feature</th>
            <th>Bronce</th>
            <th>Plata</th>
            <th>Oro</th>
        </tr>
    </thead>
    <tbody>
        <tr><td>POS + Stock + Turnos</td><td>Si</td><td>Si</td><td>Si</td></tr>
        <tr><td>Cajas simultaneas</td><td>1</td><td>2</td><td>Ilimitadas</td></tr>
        <tr><td>Mercado Pago QR</td><td>Si</td><td>Si</td><td>Si</td></tr>
        <tr><td>Mercado Pago Point (posnet)</td><td>-</td><td>Si</td><td>Si</td></tr>
        <tr><td>Promociones avanzadas</td><td>-</td><td>Si</td><td>Si</td></tr>
        <tr><td>Granel (venta al peso)</td><td>-</td><td>Si</td><td>Si</td></tr>
        <tr><td>Carteleria digital</td><td>-</td><td>Si</td><td>Si</td></tr>
        <tr><td>Cuenta corriente clientes</td><td>-</td><td>Si</td><td>Si</td></tr>
        <tr><td>Control de vencimientos</td><td>-</td><td>Si</td><td>Si</td></tr>
        <tr><td>Dashboard movil dueno</td><td>-</td><td>Si</td><td>Si</td></tr>
        <tr><td>Escaneo de facturas con IA</td><td>-</td><td>-</td><td>Si</td></tr>
        <tr><td>Asistente IA conversacional</td><td>-</td><td>-</td><td>Si</td></tr>
        <tr><td>Alertas Telegram/WhatsApp</td><td>-</td><td>-</td><td>Si</td></tr>
        <tr><td>Multi-sucursal</td><td>-</td><td>-</td><td>Si</td></tr>
        <tr><td>Sugerencia de reposicion</td><td>-</td><td>-</td><td>Si</td></tr>
        <tr><td>Soporte</td><td>Email</td><td>Email + WhatsApp</td><td>Prioritario</td></tr>
    </tbody>
</table>

<h1 class="page-break">7. Plan por fases con checklist</h1>

<div class="phase-header">Fase 1 &mdash; Landing y venta manual (semana 1)</div>
<ul class="checklist">
    <li>Comprar dominio definitivo (ej. tugoloteca.com) y configurar DNS hacia Railway.</li>
    <li>Grabar video screencast de 2-3 minutos mostrando POS, stock, promos, escaneo de factura IA.</li>
    <li>Editar video con subtitulos (muchos kiosqueros lo van a ver con el sonido en mute).</li>
    <li>Crear app Django <code>landing</code> con una unica vista de home.</li>
    <li>Maquetar template con las 7 secciones (hero, features, capturas, planes, testimonios, FAQ, footer).</li>
    <li>Tomar capturas reales del sistema (POS, stock, dashboard, promociones, granel, signage).</li>
    <li>Escribir copy definitivo de cada seccion.</li>
    <li>Agregar CTA de WhatsApp con mensaje pre-cargado ("Hola, quiero info del sistema para mi kiosco").</li>
    <li>Deploy a Railway en el dominio definitivo.</li>
    <li>Armar lista de 15-20 kioscos prospectos (zona, nombre, contacto si se puede).</li>
    <li>Empezar visitas o mensajes por WhatsApp.</li>
</ul>

<div class="phase-header">Fase 2 &mdash; Preparar el monolito (semana 2)</div>
<ul class="checklist">
    <li>Auditar modelos: buscar singletons (ej. <code>Company.get_company()</code>), asunciones de "unica empresa".</li>
    <li>Auditar management commands y signals para ver cuales suponen DB unica.</li>
    <li>Escribir tests de smoke para POS, stock, cashregister (confirmar que no se rompe en el refactor).</li>
    <li>Si aparece un cliente piloto: clonar repo, deploy a un project Railway aparte, entregar URL y credenciales.</li>
    <li>Documentar el flujo de setup manual del cliente piloto (va a servir como base del provisioning).</li>
</ul>

<div class="phase-header">Fase 3 &mdash; django-tenants integrado (semanas 3-4)</div>
<ul class="checklist">
    <li>Instalar <code>django-tenants</code> y agregarlo a <code>requirements.txt</code>.</li>
    <li>Partir <code>INSTALLED_APPS</code> en <code>SHARED_APPS</code> y <code>TENANT_APPS</code>.</li>
    <li>Cambiar engine de DB a <code>django_tenants.postgresql_backend</code>.</li>
    <li>Agregar <code>TenantMainMiddleware</code> al inicio del middleware stack.</li>
    <li>Crear app <code>tenants</code> con modelos <code>Client</code> y <code>Domain</code>.</li>
    <li>Crear <code>public_urls.py</code> y mover URLs publicas ahi.</li>
    <li>Migrar: <code>migrate_schemas --shared</code> y <code>migrate_schemas --tenant</code>.</li>
    <li>Crear tenant de prueba local y verificar que el POS funciona en <code>prueba.localhost:8000</code>.</li>
    <li>Ajustar <code>MEDIA_ROOT</code> para que los uploads esten aislados por tenant.</li>
    <li>Configurar wildcard DNS en Cloudflare para <code>*.tugoloteca.com</code>.</li>
    <li>Deploy a Railway y verificar con tenant real.</li>
</ul>

<div class="phase-header">Fase 4 &mdash; Panel super-admin (semana 5)</div>
<ul class="checklist">
    <li>Crear app <code>super_admin</code>.</li>
    <li>Definir permiso especial <code>is_platform_admin</code> en <code>User</code> (o mediante Group).</li>
    <li>Vista "Lista de tenants" con tabla y filtros.</li>
    <li>Vista "Crear tenant" con wizard de 4 pasos.</li>
    <li>Management command <code>create_tenant</code> y llamarlo desde la vista.</li>
    <li>Seed de 20 productos demo tipicos de kiosco (coca, manaos, pepitos, marlboro, alfajores, etc.).</li>
    <li>Vista "Editar tenant" que modifica <code>Company</code> del schema target.</li>
    <li>Boton "Suspender" que cambia <code>Client.status</code>.</li>
    <li>Middleware que bloquea acceso si el tenant esta suspendido.</li>
    <li>Vista "Impersonar" con registro de auditoria.</li>
    <li>Vista "Metricas globales" con totales cross-tenant.</li>
</ul>

<div class="phase-header">Fase 5 &mdash; Migracion de cliente piloto (semana 6)</div>
<ul class="checklist">
    <li>Hacer <code>pg_dump</code> de la DB del cliente piloto.</li>
    <li>Crear tenant nuevo desde el panel super-admin.</li>
    <li>Restore del dump dentro del schema del tenant.</li>
    <li>Reconfigurar <code>Company</code>, <code>Domain</code>, usuarios.</li>
    <li>Test completo: login, ventas, reportes, promociones, stock.</li>
    <li>Corte de servicio breve, cambio de URL hacia el subdomain del sistema multi-tenant.</li>
    <li>Apagar la instancia dedicada vieja (conservar backup durante 30 dias).</li>
</ul>

<div class="phase-header">Fase 6 &mdash; Features de valor (semanas 7-10)</div>
<ul class="checklist">
    <li>Cuenta corriente de clientes (modelos, vistas, nuevo metodo de pago, reportes).</li>
    <li>Control de vencimientos (campo en producto o modelo <code>ProductBatch</code>, alertas, listado).</li>
    <li>Dashboard movil PWA del dueno en <code>/owner/</code> con manifest.json y service worker.</li>
    <li>Alertas Telegram (bot + config por tenant con chat_id).</li>
    <li>Modo offline del POS (service worker + IndexedDB + cola de sync).</li>
</ul>

<div class="phase-header">Fase 7 &mdash; Hardening y crecimiento</div>
<ul class="checklist">
    <li>Integrar Sentry para captura de errores por tenant.</li>
    <li>Script de backup diario por tenant con <code>pg_dump --schema</code>.</li>
    <li>Rate limiting en endpoints criticos.</li>
    <li>Logs estructurados con tenant_id en cada linea.</li>
    <li>Programa de referidos (30% descuento al que te refiere un cliente nuevo).</li>
    <li>Seguimiento comercial: CRM simple o planilla con estado de cada prospecto.</li>
</ul>

<h1 class="page-break">8. Riesgos y decisiones sensibles</h1>

<div class="warning">
    <strong>Credenciales de Mercado Pago por tenant.</strong> Hoy el <code>access_token</code> de MP esta global.
    En multi-tenant, cada kiosco tiene que tener su propio token para que la plata caiga en su cuenta
    y no en la de Nacho. Agregar campo <code>mp_access_token</code> en la <code>Company</code> del tenant,
    encriptado con <code>cryptography.fernet</code> o similar.
</div>

<div class="warning">
    <strong>Singleton Company.</strong> El codigo actual asume "una sola empresa" (<code>Company.get_company()</code>).
    Con django-tenants sigue funcionando porque es un singleton por schema, pero hay que revisar
    signals, management commands y templates que pudieran depender de un PK fijo.
</div>

<div class="warning">
    <strong>Migraciones en produccion multi-tenant.</strong> Cuando haya 50 tenants, cada <code>makemigrations</code>
    corre sobre 50 schemas. Usar <code>migrate_schemas --parallel</code>, tener CI que corra migraciones
    contra un snapshot de produccion antes de deployar, y scripts de rollback a mano.
</div>

<div class="warning">
    <strong>Datos cruzados en desarrollo.</strong> Si durante desarrollo se trabaja en el schema equivocado
    se pueden arruinar datos del demo. Siempre tener un tenant <code>dev</code> separado y un chequeo visual
    (banner de color en el top bar) que indique en que tenant se esta operando.
</div>

<div class="warning">
    <strong>Media files por tenant.</strong> Si se queda el default <code>MEDIA_ROOT = BASE_DIR / 'media'</code>,
    el logo del kiosco A puede sobrescribir al del kiosco B. Prefijar con schema (<code>media/&lt;schema&gt;/...</code>)
    o migrar a S3/R2 con keys prefijadas.
</div>

<div class="warning">
    <strong>Memoria Gemini API key.</strong> Si todos los tenants usan la misma key de Google, el costo se
    comparte. Opciones: (1) cobrarlo dentro del plan Oro como limite mensual, (2) cada tenant trae su
    propia key, (3) empezar con key compartida y monitorear consumo.
</div>

<h1 class="page-break">9. Proximos pasos concretos</h1>

<h2>Hoy</h2>
<ul class="checklist">
    <li>Decidir el dominio definitivo y comprarlo.</li>
    <li>Hacer lista de 10 kioscos conocidos donde empezar a ofrecer.</li>
    <li>Planificar la grabacion del video demo (guion de 2 minutos).</li>
</ul>

<h2>Esta semana</h2>
<ul class="checklist">
    <li>Grabar y editar el video demo.</li>
    <li>Crear la app <code>landing</code> y maquetar el template.</li>
    <li>Escribir el copy definitivo de la landing.</li>
    <li>Tomar las capturas del sistema.</li>
    <li>Deploy a Railway.</li>
    <li>Primer contacto con 3 kioscos de la lista.</li>
</ul>

<h2>Este mes</h2>
<ul class="checklist">
    <li>Cerrar 1 cliente piloto (aunque sea con instancia dedicada).</li>
    <li>Tener django-tenants funcionando en desarrollo.</li>
    <li>Primer boceto del panel super-admin.</li>
</ul>

<h2>Proximos 3 meses</h2>
<ul class="checklist">
    <li>Sistema multi-tenant en produccion con panel super-admin completo.</li>
    <li>3-5 clientes pagando.</li>
    <li>Al menos 2 de los 5 features de valor (cuenta corriente + PWA o vencimientos) construidos.</li>
    <li>Proceso comercial repetible: prospectos, visitas, cierre, alta en el panel.</li>
</ul>

<hr/>

<p style="text-align:center; color:#999; font-size:10pt; margin-top:2cm;">
Fin del documento &middot; Plan SaaS CHE GOLOSO &middot; Abril 2026
</p>
"""


def build_html() -> str:
    footer = '<div id="footerContent" class="footer">Plan SaaS CHE GOLOSO &middot; pagina <pdf:pagenumber/></div>'
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <style>{CSS}</style>
</head>
<body>
    {footer}
    {HTML_BODY}
</body>
</html>
"""


def main() -> int:
    html = build_html()
    with OUT_PDF.open('wb') as f:
        result = pisa.CreatePDF(src=html, dest=f, encoding='utf-8')
    if result.err:
        print(f'ERROR al generar PDF: {result.err}')
        return 1
    print(f'OK PDF generado: {OUT_PDF}')
    print(f'    Tamaño: {OUT_PDF.stat().st_size / 1024:.1f} KB')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
