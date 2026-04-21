---
name: Granel System Architecture
description: Current state of the caramelera/granel system after the April 2026 full rewrite — models, services, URLs, POS integration
type: project
---

## Current Architecture (post-rewrite, April 2026)

The granel system was completely rewritten to use independent models decoupled from `stocks.Product`. New models live in `granel/models.py`.

### New Models
- `ProductoDeposito` — sealed bags/boxes in storeroom. Fields: `costo_bulto`, `gramos_por_bulto`, `stock_unidades`, computed `costo_por_gramo`.
- `Caramelera` — the candy jar. Fields: `precio_100g`, `precio_cuarto` (250g special price), `stock_gramos_actual`, `costo_ponderado_gramo` (WAC), `productos_autorizados` M2M to ProductoDeposito. Methods: `calcular_precio(gramos)`, `margen_100g`.
- `AperturaBulto` — full before/after snapshot log of every bag opened.
- `VentaGranel` — POS sale record with cost snapshot and profit.
- `AuditoriaCaramelera` — physical scale weighing, records diff, adjusts stock.

### Legacy Models (kept for migration history, no new features)
`BulkToGranelTransfer`, `CarameleraComponent`, `ShrinkageAudit` — do not add new functionality.

### GranelService Methods
- `abrir_paquete(caramelera_id, producto_deposito_id, user, notas)` — validates authorization + stock, runs WAC, returns `AperturaBulto`
- `realizar_auditoria(caramelera_id, peso_real_balanza, user, motivo)` — records diff, adjusts stock
- `registrar_venta(caramelera_id, gramos_vendidos, precio_cobrado, pos_transaction_id)` — deducts stock, records `VentaGranel`

### WAC Formula
`new_cost = (stock_antes * costo_antes + gramos_nuevos * cpg_bulto) / (stock_antes + gramos_nuevos)`
Edge case: stock_antes == 0 → new_cost = cpg_bulto directly.

### POS Integration
- `stocks.Product` has optional FK `granel_caramelera = ForeignKey('granel.Caramelera', null=True, blank=True)`
- In `pos/services.py` `CheckoutService.process_payment()`, after stock deduction, calls `GranelService.registrar_venta()` for items where `product.granel_caramelera` is set. Wrapped in try/except so it never blocks checkout.

### URL Namespace `granel:`
- `deposito_list`, `deposito_create`, `deposito_edit`, `api_deposito_stock`
- `caramelera_list`, `caramelera_create`, `caramelera_detail`, `caramelera_edit`
- `api_abrir_paquete`, `api_auditoria`, `api_venta_granel`, `api_caramelera_info`

### Migrations
- `granel/migrations/0006_new_caramelera_system.py`
- `stocks/migrations/0013_new_caramelera_system.py` — adds `granel_caramelera` FK to `stocks.Product`

**Why:** Previous system overloaded `stocks.Product` with `is_granel`, `weight_per_unit_grams`, `weighted_avg_cost_per_gram` etc. New system has dedicated models with clear semantics and better audit trail.

**How to apply:** Use new models for all granel features. Link a POS product to a caramelera via `product.granel_caramelera`. Never write new code against legacy models.
