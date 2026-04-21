from django.contrib import admin
from .models import (
    ProductoDeposito,
    Caramelera,
    AperturaBulto,
    VentaGranel,
    AuditoriaCaramelera,
    # Legacy
    StockBatch,
    BulkToGranelTransfer,
    ShrinkageAudit,
    CarameleraComponent,
)


@admin.register(ProductoDeposito)
class ProductoDepositoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'marca', 'costo_bulto', 'gramos_por_bulto', 'stock_unidades', 'is_active')
    list_filter = ('is_active', 'marca')
    search_fields = ('nombre', 'marca')
    list_editable = ('stock_unidades',)


@admin.register(Caramelera)
class CarameleraAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_100g', 'precio_cuarto', 'stock_gramos_actual',
                    'costo_ponderado_gramo', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('nombre',)
    filter_horizontal = ('productos_autorizados',)
    readonly_fields = ('costo_ponderado_gramo', 'stock_gramos_actual')


@admin.register(AperturaBulto)
class AperturaBultoAdmin(admin.ModelAdmin):
    list_display = ('caramelera', 'producto', 'gramos_agregados', 'costo_por_gramo_al_abrir',
                    'costo_ponderado_despues', 'abierto_por', 'abierto_en')
    list_filter = ('caramelera', 'abierto_en')
    search_fields = ('caramelera__nombre', 'producto__name')
    readonly_fields = ('abierto_en',)


@admin.register(VentaGranel)
class VentaGranelAdmin(admin.ModelAdmin):
    list_display = ('caramelera', 'gramos_vendidos', 'tipo_venta', 'precio_cobrado',
                    'costo_total', 'ganancia', 'vendido_en')
    list_filter = ('caramelera', 'tipo_venta', 'vendido_en')
    readonly_fields = ('vendido_en',)


@admin.register(AuditoriaCaramelera)
class AuditoriaCarameleraAdmin(admin.ModelAdmin):
    list_display = ('caramelera', 'stock_sistema_gramos', 'peso_real_balanza_gramos',
                    'diferencia_gramos', 'porcentaje_merma', 'ajuste_aplicado', 'auditado_en')
    list_filter = ('caramelera', 'auditado_en')
    readonly_fields = ('auditado_en',)


# Legacy models
@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    list_display = ('product', 'supplier_name', 'quantity_purchased', 'quantity_remaining',
                    'purchase_price', 'purchased_at')
    list_filter = ('product', 'purchased_at')
    search_fields = ('product__name', 'supplier_name')
    readonly_fields = ('created_at',)


@admin.register(BulkToGranelTransfer)
class BulkToGranelTransferAdmin(admin.ModelAdmin):
    list_display = ('bulk_product', 'granel_product', 'grams_transferred',
                    'granel_weighted_cost_after', 'transferred_by', 'transferred_at')
    list_filter = ('granel_product', 'transferred_at')
    readonly_fields = ('transferred_at',)


@admin.register(CarameleraComponent)
class CarameleraComponentAdmin(admin.ModelAdmin):
    list_display = ('caramelera', 'bulk_product', 'notes', 'added_at')
    list_filter = ('caramelera',)


@admin.register(ShrinkageAudit)
class ShrinkageAuditAdmin(admin.ModelAdmin):
    list_display = ('granel_product', 'theoretical_grams', 'actual_grams',
                    'shrinkage_grams', 'shrinkage_percent', 'reason', 'audited_at')
    list_filter = ('granel_product', 'reason', 'audited_at')
    readonly_fields = ('audited_at',)
