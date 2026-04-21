# 4. Caramelera (granel)

## Qué es la caramelera

Un **frasco/contenedor** donde se mezclan distintas marcas de golosinas que se venden al mismo precio por gramo. Ejemplo: caramelera de "gomitas surtidas" con Mogul, Beldent y marcas blancas adentro.

Como los costos son distintos pero el precio de venta es único, el sistema usa **costo promedio ponderado** para calcular la ganancia (no FIFO).

---

## Abrir un paquete hacia la caramelera

### Cuándo
Cada vez que vaciás un bulto nuevo en el frasco.

### Paso a paso

1. Ir a **Granel → Abrir Paquete**.
2. Seleccionar:
   - La **caramelera destino** (frasco físico).
   - El **producto de depósito** (el bulto cerrado).
   - **Cantidad de paquetes** a abrir.
3. Confirmar.

### Qué pasa por atrás

1. Calcula los gramos nuevos: `cantidad_paquetes × weight_per_unit_grams`.
2. **Recalcula el costo ponderado** de la caramelera (ver sección siguiente).
3. Suma los gramos al stock de la caramelera.
4. Descuenta el paquete del stock de depósito.
5. Sincroniza el "producto POS" vinculado a esa caramelera (para que al escanear/buscar aparezcan los gramos actualizados).

---

## Cómo se calcula el costo ponderado

El sistema **no promedia por cantidad de productos distintos**. Promedia **por gramos**: cada gramo dentro del frasco hereda un costo promedio que refleja de dónde vinieron los gramos que ya había y los que acabás de agregar.

### Fórmula

```
costo_nuevo =  (stock_antes × costo_antes) + (gramos_nuevos × costo_nuevo_bolsa)
               ────────────────────────────────────────────────────────────────
                                stock_antes + gramos_nuevos
```

Es decir: **total de plata invertida ÷ gramos totales**.

### Costo por gramo de la bolsa que abrís

Se calcula a partir del precio de costo del producto de depósito:

```
costo_por_gramo_bolsa = cost_price_del_bulto / weight_per_unit_grams
```

Ejemplo: bolsa de 500 g que costó $5.000 → $10 por gramo.

### Ejemplo con dos bolsas distintas

Caramelera arranca vacía (stock = 0, costo = 0).

**Paso 1 — abrís una bolsa de 500 g que costó $5.000:**

- Costo por gramo de la bolsa: `5.000 / 500 = $10/g`
- Como no hay gramos previos, el costo ponderado queda directo en **$10/g**.
- Caramelera: **500 g a $10/g**.

**Paso 2 — abrís una bolsa de 900 g que costó $13.500:**

- Costo por gramo de la bolsa: `13.500 / 900 = $15/g`
- Aplicamos la fórmula ponderada:

  ```
  costo =  (500 × 10) + (900 × 15)   =   5.000 + 13.500   =   18.500
           ─────────────────────         ────────────────       ──────
                500 + 900                       1.400            1.400
  ```

- Costo ponderado final: **≈ $13,2143/g**.
- Caramelera: **1.400 g a $13,21/g**.

### Cosas clave a entender

- **Pondera por gramos, no por unidades**: una bolsa de 900 g "pesa" más en el promedio que una de 500 g, aunque sea un solo paquete.
- **Cada apertura recalcula el promedio completo**: los gramos viejos se mezclan con los nuevos y todos pasan a compartir el nuevo costo. No se trackean lotes individuales dentro del frasco (sí se guarda cada apertura en `AperturaBulto` para auditoría histórica).
- **El POS usa este costo ponderado** para calcular la ganancia de cada venta por peso (`weighted_avg_cost_per_gram` del producto POS).
- **Las auditorías de peso no tocan el costo ponderado** — solo ajustan gramos (merma/sobrante). Si vendés 200 g después del paso 2, los 1.200 g restantes siguen a $13,21/g; cuando abras otra bolsa, se promedia contra esos 1.200 g × $13,21.

---

## Vender por gramos en el POS

1. En el POS, buscá la caramelera (o escaneá su código asociado).
2. Se abre el modal: ingresá los **gramos** a vender.
3. El sistema calcula el precio:
   - < 250g → proporcional al precio cada 100g.
   - ≥ 250g con **precio kilo oferta** activo → se aplica la regla de tres sobre el precio del kilo.
4. Seguí con el cobro normal.

---

## Auditoría de merma

### Cuándo
Periódicamente (una vez por semana recomendado) o cuando sospéches diferencias.

### Paso a paso

1. **Pesar físicamente** la caramelera en la balanza.
2. Ir a **Granel → Auditoría**.
3. Seleccionar la caramelera.
4. Ingresar el **peso real en gramos** medido.
5. (Opcional) Notas: causa probable (humedad, derrame, robo).
6. Confirmar.

### Qué pasa por atrás

1. Calcula `diferencia = stock_sistema - peso_real`.
2. Guarda la auditoría con `% merma` y fecha.
3. **Ajusta automáticamente** el stock de la caramelera al peso real.
4. Queda registrada en el historial — podés ver todas las auditorías en el detalle de la caramelera.

Esto te permite detectar robos o desvíos sistemáticos.
