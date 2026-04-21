"""
Purchase Admin Configuration
"""
from django.contrib import admin
from .models import Supplier, Purchase, PurchaseItem


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    readonly_fields = ['subtotal']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_name', 'phone', 'email', 'cuit', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'contact_name', 'cuit', 'email']
    ordering = ['name']


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'supplier', 'status', 'order_date',
        'total', 'created_by', 'created_at'
    ]
    list_filter = ['status', 'order_date', 'supplier']
    search_fields = ['order_number', 'supplier__name']
    readonly_fields = ['order_number', 'subtotal', 'total', 'created_at', 'updated_at']
    inlines = [PurchaseItemInline]
    date_hierarchy = 'created_at'


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ['purchase', 'product', 'quantity', 'unit_cost', 'subtotal']
    list_filter = ['purchase__status']
    search_fields = ['purchase__order_number', 'product__name']
