# Manual CHE GOLOSO — Guía de uso del sistema

Esta guía explica **paso a paso** cómo operar el sistema: cargar productos, comprar, vender, hacer mermas, modificar stock y cerrar la caja. Está pensada para que cualquier persona del equipo pueda usar el sistema sin conocer Django ni el código por dentro.

---

## Cómo leer este manual

Cada sección tiene dos partes:

- **Paso a paso:** lo que hace el operador desde la pantalla.
- **Qué pasa por atrás:** para entender por qué el sistema se comporta así (útil si algo no coincide con lo esperado).

---

## Índice

1. [Crear y modificar productos](01-Crear-y-modificar-productos.md) (normales y caramelera)
2. [Compras y recepción de mercadería](02-Compras-y-recepcion.md)
3. [Vender por el POS (caja)](03-Vender-por-el-POS.md)
4. [Caramelera — abrir paquetes, vender por gramos, auditorías](04-Caramelera.md)
5. [Ajustes manuales de stock y conteos físicos](05-Ajustes-de-stock.md)
6. [Cierre de caja (Z)](06-Cierre-de-caja.md)
7. [Reportes](07-Reportes.md)

---

## Reglas de negocio críticas (leer antes de empezar)

**1. FIFO real en ventas.** Al vender, el costo que se usa para calcular la ganancia es el **costo del lote más antiguo disponible** (el primero que entró). No el costo promedio. Esto hace que el margen del reporte refleje la ganancia real de ese ticket.

**2. Costo promedio ponderado SOLO en carameleras.** Porque una misma caramelera mezcla varias marcas con distintos costos pero se vende al mismo precio por gramo, ahí sí se usa promedio ponderado.

**3. Cascada automática en empaques.** Cuando sumás 288 unidades al stock base, el sistema actualiza automáticamente el stock de *unidad*, *display* (288÷12=24) y *bulto* (288÷144=2). Nunca tenés que hacer la cuenta a mano. Al vender pasa lo mismo en sentido contrario.

**4. Las compras detectan el empaque automáticamente.** Al escanear el código de barras del bulto, el sistema reconoce que es un bulto y sabe cuántas unidades contiene. Podés cargar la OC diciendo "2 bultos" o "3 displays" o "50 unidades" — el sistema calcula las unidades base solo y las distribuye a todos los niveles al recibir. Si el código no corresponde a ningún empaque configurado, se carga como unidad base.

**5. Stock negativo está permitido.** Si vendés sin tener stock el sistema te deja y marca una alerta en el movimiento. Nunca te bloquea una venta por falta de stock registrado (porque a veces hay mercadería que todavía no fue cargada).

**6. El movimiento de caja solo registra lo cobrado, no el vuelto.** Si el cliente paga $2000 y llevó $1500, la caja registra ingreso de $1500 (el vuelto no se registra como gasto).

---

## Roles de usuario

- **Admin:** acceso total. Crea productos, hace compras, ve reportes, cierra caja.
- **Cajero Manager:** opera POS y puede cerrar caja. No ve compras ni reportes sensibles.
- **Cashier (Cajero):** solo opera el POS y consulta sus propias ventas.
- **Stock Manager:** carga productos, hace ajustes de stock, no toca caja.

Los permisos se basan en grupos de Django. El superusuario pasa todos los controles.
