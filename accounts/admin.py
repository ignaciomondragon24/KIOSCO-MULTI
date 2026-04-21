from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for custom User model."""
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_admin', 'date_joined')
    list_filter = ('is_active', 'is_admin', 'is_staff', 'groups', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permisos', {'fields': ('is_active', 'is_admin', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'first_name', 'last_name', 'is_active', 'is_admin'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin for Role (Group proxy) model."""
    
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('permissions',)
