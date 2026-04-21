# 6. Cierre de caja (Z)

## Cuándo cerrar caja

Al final del turno del cajero o del día. Una vez cerrada, el turno queda auditado y no se pueden agregar ventas a ese turno.

---

## Paso a paso

1. Ir a **Caja → Turno Actual → Cerrar Turno**.
2. El sistema muestra el **monto esperado en efectivo**:

   ```
   monto esperado = inicial + ingresos en efectivo − egresos en efectivo
   ```

3. Contá físicamente la caja. Opcionalmente completá el **desglose de billetes** (20k, 10k, 5k, 2k, 1k, 500, 200, 100, monedas). El sistema suma automáticamente.
4. Ingresar el **monto real contado** (`actual_amount`).
5. (Opcional) Notas.
6. Confirmar.

### Resultado

- **Diferencia = real − esperado**.
  - Positiva: sobrante (entró más de lo registrado).
  - Negativa: faltante (falta plata en caja).
  - Cero: perfecto.
- Se muestra el **resumen por método de pago**: efectivo, débito, crédito, transferencia, MercadoPago. Cada uno con total y cantidad de transacciones.
- El turno queda con estado `closed`.

---

## Qué entra en "efectivo" y qué no

**Solo cuenta como efectivo** lo cobrado por métodos con `is_cash=True` (efectivo). Débito, crédito, transferencia y MercadoPago **no afectan** el monto esperado en caja — van a sus propias cuentas.

Esto es importante: si vendiste $10.000 con tarjeta, **no esperés** esos $10.000 en la caja física. El sistema ya sabe que fueron por tarjeta.

---

## Si hay faltante

1. Revisá en el detalle del turno si hubo ventas suspendidas que no se cerraron.
2. Fijáte si un cliente pagó con tarjeta pero quedó cargado como efectivo.
3. Revisá devoluciones no registradas.
4. Si no se explica, dejálo asentado en las **notas** del cierre.

---

## No hay cierre X

El sistema **no implementa** reporte intermedio tipo "cierre X" (reporte sin cerrar el turno). Si necesitás ver el estado del turno en curso, usá **Caja → Turno Actual** que muestra ingresos, egresos y esperado en tiempo real sin cerrar.
