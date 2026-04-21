"""
Company Admin Configuration
"""
from django.contrib import admin
from .models import Company, Branch


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'cuit', 'phone', 'email']
    
    def has_add_permission(self, request):
        # Only allow one company record
        return not Company.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'phone', 'is_main', 'is_active']
    list_filter = ['is_active', 'is_main']
    search_fields = ['name', 'code']
