from django.contrib import admin
from .models import Promotion, PromotionProduct, PromotionGroup


@admin.register(PromotionGroup)
class PromotionGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'promo_count', 'created_at')
    search_fields = ('name', 'description')

    def promo_count(self, obj):
        return obj.promotions.count()
    promo_count.short_description = 'Promos enlazadas'


class PromotionProductInline(admin.TabularInline):
    model = PromotionProduct
    extra = 1
    autocomplete_fields = ['product']


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('name', 'promo_type', 'status', 'priority', 'group', 'start_date', 'end_date',
                   'is_combinable', 'usages', 'is_valid_today')
    list_filter = ('status', 'promo_type', 'is_combinable', 'group', 'start_date')
    search_fields = ('name', 'description')
    inlines = [PromotionProductInline]
    autocomplete_fields = ['group']

    def get_actions(self, request):
        """Deshabilitar 'delete selected' para evitar borrado masivo accidental."""
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def has_delete_permission(self, request, obj=None):
        """Solo superusers pueden borrar promociones desde el admin."""
        return request.user.is_superuser

    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'promo_type', 'status')
        }),
        ('Vigencia', {
            'fields': ('start_date', 'end_date', 'priority', 'is_combinable', 'group')
        }),
        ('Días Activos', {
            'fields': (('monday', 'tuesday', 'wednesday', 'thursday'), 
                      ('friday', 'saturday', 'sunday'))
        }),
        ('Horario', {
            'fields': ('hour_start', 'hour_end'),
            'classes': ('collapse',)
        }),
        ('Condiciones', {
            'fields': ('min_quantity', 'min_purchase_amount', 'max_uses_per_sale')
        }),
        ('Configuración NxM', {
            'fields': ('quantity_required', 'quantity_charged'),
            'classes': ('collapse',)
        }),
        ('Descuentos', {
            'fields': ('discount_percent', 'discount_amount', 'final_price', 'second_unit_discount')
        }),
        ('Estadísticas', {
            'fields': ('usages', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('usages', 'created_at', 'updated_at')
