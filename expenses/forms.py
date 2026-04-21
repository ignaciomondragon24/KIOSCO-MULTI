"""
Expenses Forms
"""
from django import forms
from .models import ExpenseCategory, Expense, RecurringExpense


class ExpenseCategoryForm(forms.ModelForm):
    """Form for expense categories."""
    
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description', 'color', 'is_active', 'is_investment']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la categoría'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control form-control-color',
                'type': 'color'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_investment': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class ExpenseForm(forms.ModelForm):
    """Form for creating/editing expenses."""
    
    class Meta:
        model = Expense
        fields = [
            'category', 'description', 'amount', 'expense_date',
            'payment_method', 'affects_cash_drawer',
            'receipt_number', 'supplier',
            'notes', 'receipt_image'
        ]
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'affects_cash_drawer': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción del gasto'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'min': '1',
                'placeholder': '0'
            }),
            'expense_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select'
            }),
            'receipt_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de factura/recibo'
            }),
            'supplier': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas adicionales'
            }),
            'receipt_image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ExpenseCategory.objects.filter(is_active=True)
        self.fields['supplier'].required = False


class RecurringExpenseForm(forms.ModelForm):
    """Form for recurring expenses."""
    
    class Meta:
        model = RecurringExpense
        fields = [
            'category', 'description', 'amount',
            'frequency', 'next_due_date', 'is_active', 'notes'
        ]
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción del gasto'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'min': '1'
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'next_due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
