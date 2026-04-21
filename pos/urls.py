"""
POS URLs
"""
from django.urls import path
from . import views

app_name = 'pos'

urlpatterns = [
    # Main POS view
    path('', views.pos_main, name='main'),
    path('', views.pos_main, name='pos_main'),  # Alias for compatibility
    
    # Suspended transactions
    path('suspended/', views.suspended_transactions, name='suspended'),
    
    # Ticket printing
    path('ticket/<int:transaction_id>/', views.print_ticket, name='print_ticket'),
    
    # API endpoints
    path('api/search/', views.api_search, name='api_search'),
    path('api/cart/add/', views.api_cart_add, name='api_cart_add'),
    path('api/cart/add-by-amount/', views.api_cart_add_by_amount, name='api_cart_add_by_amount'),
    path('api/calculate-by-amount/', views.api_calculate_by_amount, name='api_calculate_by_amount'),
    path('api/cart/item/<int:item_id>/', views.api_cart_update, name='api_cart_update'),
    path('api/cart/item/<int:item_id>/remove/', views.api_cart_remove, name='api_cart_remove'),
    path('api/cart/item/<int:item_id>/discount/', views.api_cart_item_discount, name='api_cart_item_discount'),
    path('api/cart/<int:transaction_id>/clear/', views.api_cart_clear, name='api_cart_clear'),
    path('api/transaction/<int:transaction_id>/', views.api_transaction_detail, name='api_transaction_detail'),
    path('api/transaction/<int:transaction_id>/cost-total/', views.api_calculate_cost_total, name='api_calculate_cost_total'),
    path('api/checkout/', views.api_checkout, name='api_checkout'),
    path('api/checkout/cost-sale/', views.api_checkout_cost_sale, name='api_checkout_cost_sale'),
    path('api/checkout/internal-consumption/', views.api_checkout_internal_consumption, name='api_checkout_internal_consumption'),
    path('api/transaction/<int:transaction_id>/suspend/', views.api_transaction_suspend, name='api_transaction_suspend'),
    path('api/transaction/<int:transaction_id>/resume/', views.api_transaction_resume, name='api_transaction_resume'),
    path('api/transaction/<int:transaction_id>/cancel/', views.api_transaction_cancel, name='api_transaction_cancel'),
    path('api/transaction/<int:transaction_id>/discount/', views.api_apply_discount, name='api_apply_discount'),
    path('api/last-transaction/', views.api_last_transaction, name='api_last_transaction'),
    path('api/suspended-transactions/', views.api_suspended_transactions, name='api_suspended_transactions'),
    path('api/quick-add-product/', views.api_quick_add_product, name='api_quick_add_product'),
    # Nuevas APIs
    path('api/keyboard-shortcuts/', views.api_keyboard_shortcuts, name='api_keyboard_shortcuts'),
    path('api/keyboard-shortcuts/update/', views.api_update_keyboard_shortcut, name='api_update_keyboard_shortcut'),
    path('api/sales-history/', views.api_sales_history, name='api_sales_history'),
    path('api/quick-checkout/', views.api_quick_checkout, name='api_quick_checkout'),
    path('api/all-products/', views.api_all_products, name='api_all_products'),
    path('api/toggle-quick-access/', views.api_toggle_quick_access, name='api_toggle_quick_access'),
]
