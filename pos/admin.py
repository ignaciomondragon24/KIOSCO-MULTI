from django.contrib import admin
from django.utils.html import format_html
from .models import POSSession, POSTransaction, POSTransactionItem, POSPayment, QuickAccessButton, POSKeyboardShortcut


@admin.register(POSSession)
class POSSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'cash_shift', 'opened_at', 'closed_at', 'status', 'total_transactions', 'total_amount')
    list_filter = ('status', 'opened_at')
    search_fields = ('cash_shift__cash_register__code', 'cash_shift__cashier__username')
    date_hierarchy = 'opened_at'


@admin.register(POSTransaction)
class POSTransactionAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'session', 'status', 'subtotal', 'discount_total', 'total', 
                   'items_count', 'created_at', 'completed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('ticket_number',)
    date_hierarchy = 'created_at'
    readonly_fields = ('ticket_number', 'created_at', 'updated_at', 'completed_at', 'cancelled_at', 'suspended_at')


@admin.register(POSTransactionItem)
class POSTransactionItemAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'product', 'quantity', 'unit_price', 'discount', 'subtotal', 'promotion_name')
    list_filter = ('transaction__status',)
    search_fields = ('transaction__ticket_number', 'product__name')


@admin.register(POSPayment)
class POSPaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'payment_method', 'amount', 'reference', 'created_at')
    list_filter = ('payment_method', 'created_at')
    search_fields = ('transaction__ticket_number', 'reference')
    date_hierarchy = 'created_at'


@admin.register(QuickAccessButton)
class QuickAccessButtonAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'color', 'icon', 'position', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('product__name', 'name')
    ordering = ('position',)


@admin.register(POSKeyboardShortcut)
class POSKeyboardShortcutAdmin(admin.ModelAdmin):
    list_display = ('order', 'action_label', 'key_badge', 'is_enabled')
    list_editable = ('key', 'is_enabled')
    list_filter = ('is_enabled',)
    ordering = ('order',)
    actions = ['restore_defaults']

    # Expose key field in list_editable via list_display order trick
    list_display = ('order', 'action_label', 'key', 'is_enabled')

    def action_label(self, obj):
        return obj.get_action_display()
    action_label.short_description = 'Acción'

    def key_badge(self, obj):
        if obj.key == 'none':
            return format_html('<span style="color:#888">Sin atajo</span>')
        return format_html(
            '<kbd style="background:#222;color:#00d2d3;padding:2px 6px;border-radius:3px;font-family:monospace">{}</kbd>',
            obj.key
        )
    key_badge.short_description = 'Tecla'

    def restore_defaults(self, request, queryset):
        POSKeyboardShortcut.objects.all().delete()
        POSKeyboardShortcut.ensure_defaults()
        self.message_user(request, 'Atajos restaurados a los valores por defecto.')
    restore_defaults.short_description = 'Restaurar atajos por defecto'

    def save_model(self, request, obj, form, change):
        # Warn about duplicate keys
        dup = POSKeyboardShortcut.objects.filter(key=obj.key, is_enabled=True).exclude(pk=obj.pk)
        if obj.key != 'none' and obj.is_enabled and dup.exists():
            self.message_user(
                request,
                f'⚠️ La tecla "{obj.key}" ya está asignada a otra acción. Revise los atajos.',
                level='warning',
            )
        super().save_model(request, obj, form, change)
