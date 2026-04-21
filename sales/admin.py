"""
Sales Admin Configuration (Legacy)
"""
from django.contrib import admin
from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['product_name', 'quantity', 'unit_price', 'subtotal']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['sale_number', 'date', 'status', 'total', 'cashier']
    list_filter = ['status', 'date']
    search_fields = ['sale_number']
    readonly_fields = ['sale_number', 'date', 'subtotal', 'discount', 'total']
    inlines = [SaleItemInline]
    date_hierarchy = 'date'
