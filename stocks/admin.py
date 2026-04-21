from django.contrib import admin
from .models import Product, ProductCategory, UnitOfMeasure, StockMovement, ProductPresentation, ProductPackaging


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'default_margin_percent', 'product_count', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'symbol', 'unit_type', 'is_active')
    list_filter = ('unit_type', 'is_active')
    search_fields = ('name', 'abbreviation')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'sale_price', 'current_stock', 'is_low_stock', 'is_active')
    list_filter = ('category', 'is_active', 'is_quick_access')
    search_fields = ('name', 'sku', 'barcode')
    ordering = ('name',)
    readonly_fields = ('margin_percent', 'stock_value')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('sku', 'barcode', 'name', 'description', 'category', 'unit_of_measure', 'image')
        }),
        ('Precios', {
            'fields': ('purchase_price', 'sale_price', 'cost_price', 'margin_percent')
        }),
        ('Stock', {
            'fields': ('current_stock', 'min_stock', 'max_stock', 'location', 'stock_value')
        }),
        ('Acceso Rápido POS', {
            'fields': ('is_quick_access', 'quick_access_color', 'quick_access_icon', 'quick_access_position'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
    )


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity', 'stock_before', 'stock_after', 'created_at', 'created_by')
    list_filter = ('movement_type', 'created_at')
    search_fields = ('product__name', 'reference')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('product', 'movement_type', 'quantity', 'unit_cost', 'stock_before', 'stock_after', 
                      'reference', 'reference_id', 'notes', 'created_by', 'created_at')


@admin.register(ProductPresentation)
class ProductPresentationAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'quantity', 'barcode', 'sale_price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('product__name', 'name', 'barcode')


@admin.register(ProductPackaging)
class ProductPackagingAdmin(admin.ModelAdmin):
    list_display = ('product', 'packaging_type', 'name', 'barcode', 'units_quantity', 
                   'displays_per_bulk', 'purchase_price', 'sale_price', 'margin_percent', 'is_active')
    list_filter = ('packaging_type', 'is_active', 'calculate_margin_on')
    search_fields = ('product__name', 'barcode', 'name')
    readonly_fields = ('created_at', 'updated_at', 'units_quantity')
    ordering = ('product', 'packaging_type')
    
    fieldsets = (
        ('Producto y Tipo', {
            'fields': ('product', 'packaging_type', 'name', 'barcode')
        }),
        ('Configuración de Cantidades', {
            'fields': ('units_per_display', 'displays_per_bulk', 'units_quantity'),
            'description': 'Define cuántas unidades contiene cada empaque'
        }),
        ('Precios y Margen', {
            'fields': ('purchase_price', 'sale_price', 'margin_percent', 'calculate_margin_on')
        }),
        ('Estado', {
            'fields': ('is_default', 'is_active')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
