from django.contrib import admin
from .models import PaymentMethod, CashRegister, CashShift, CashMovement


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_cash', 'icon', 'position', 'is_active')
    list_filter = ('is_cash', 'is_active')
    search_fields = ('code', 'name')
    ordering = ('position', 'name')


@admin.register(CashRegister)
class CashRegisterAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'location', 'is_active', 'is_available')
    list_filter = ('is_active',)
    search_fields = ('code', 'name')


@admin.register(CashShift)
class CashShiftAdmin(admin.ModelAdmin):
    list_display = ('cash_register', 'cashier', 'opened_at', 'closed_at', 'status', 
                   'initial_amount', 'expected_amount', 'actual_amount', 'difference')
    list_filter = ('status', 'cash_register', 'opened_at')
    search_fields = ('cashier__username', 'cash_register__code')
    date_hierarchy = 'opened_at'
    readonly_fields = ('expected_amount', 'difference')


@admin.register(CashMovement)
class CashMovementAdmin(admin.ModelAdmin):
    list_display = ('cash_shift', 'movement_type', 'amount', 'payment_method', 
                   'description', 'created_by', 'created_at')
    list_filter = ('movement_type', 'payment_method', 'created_at')
    search_fields = ('description', 'reference')
    date_hierarchy = 'created_at'
