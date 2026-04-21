"""
Expenses Admin Configuration
"""
from django.contrib import admin
from .models import ExpenseCategory, Expense, RecurringExpense


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = [
        'description', 'category', 'amount', 'expense_date',
        'payment_method', 'created_by', 'created_at'
    ]
    list_filter = ['category', 'payment_method', 'expense_date']
    search_fields = ['description', 'receipt_number']
    date_hierarchy = 'expense_date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ['description', 'category', 'amount', 'frequency', 'next_due_date', 'is_active']
    list_filter = ['category', 'frequency', 'is_active']
    search_fields = ['description']
