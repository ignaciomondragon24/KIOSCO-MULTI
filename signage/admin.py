from django.contrib import admin
from .models import SignTemplate, SignBatch, SignItem


@admin.register(SignTemplate)
class SignTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'sign_type', 'width_mm', 'height_mm', 'is_active', 'updated_at')
    list_filter = ('sign_type', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')


class SignItemInline(admin.TabularInline):
    model = SignItem
    extra = 0
    readonly_fields = ('product', 'data', 'copies')


@admin.register(SignBatch)
class SignBatchAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'template', 'paper_size', 'created_by', 'created_at')
    list_filter = ('paper_size', 'template')
    inlines = [SignItemInline]
    readonly_fields = ('created_at',)
