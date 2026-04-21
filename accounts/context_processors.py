"""
Context Processors for Accounts
Provides permission context to all templates
"""


def role_context(request):
    """Add user permissions to template context."""
    if not request.user.is_authenticated:
        return {
            'is_superadmin': False,
            'is_admin': False,
            'is_cajero_manager': False,
            'is_manager': False,
            'is_cashier': False,
            'is_stock_manager': False,
            'is_general_manager': False,
        }
    
    user = request.user
    user_groups = list(user.groups.values_list('name', flat=True))

    # Role checks - hierarchical
    # Aliases legacy: Manager/Stock Manager → Cajero Manager; General Manager → Admin
    is_superadmin = user.is_superuser
    is_admin = (
        is_superadmin
        or user.is_admin
        or 'Admin' in user_groups
        or 'General Manager' in user_groups
    )
    is_cajero_manager = (
        is_admin
        or 'Cajero Manager' in user_groups
        or 'Manager' in user_groups
        or 'Stock Manager' in user_groups
    )
    is_cashier = is_cajero_manager or 'Cashier' in user_groups
    
    # Backward compat aliases
    is_manager = is_admin
    is_general_manager = is_admin
    is_stock_manager = is_cajero_manager
    
    return {
        'user_roles': user_groups,
        'is_admin_user': is_admin,
        
        # Role flags for templates
        'is_superadmin': is_superadmin,
        'is_admin': is_admin,
        'is_cajero_manager': is_cajero_manager,
        'is_manager': is_manager,
        'is_general_manager': is_general_manager,
        'is_cashier': is_cashier,
        'is_stock_manager': is_stock_manager,
        
        # Module permissions
        'can_pos': is_cashier,
        'can_cash': is_cashier,
        'can_stocks': is_cajero_manager,
        'can_purchases': is_admin,           # Solo Admin
        'can_expenses': is_admin,            # Solo Admin
        'can_promotions': is_cajero_manager,
        'can_sales': is_admin,               # Solo Admin (reportes)
        'can_reports': is_admin,             # Solo Admin (reportes)
        'can_settings': is_admin,
        'can_users': is_admin,
        'can_price_list': is_cajero_manager,
        'can_signage': is_cajero_manager,
        'can_assistant': is_admin,           # IA solo Admin
    }
