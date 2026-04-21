"""
Decorators package for CHE GOLOSO
"""
from .decorators import (
    group_required,
    admin_required,
    manager_required,
    cashier_required,
    stock_manager_required,
    ajax_login_required,
    open_shift_required,
)

__all__ = [
    'group_required',
    'admin_required',
    'manager_required',
    'cashier_required',
    'stock_manager_required',
    'ajax_login_required',
    'open_shift_required',
]
