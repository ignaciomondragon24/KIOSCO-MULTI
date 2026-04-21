"""
Purchase Forms
"""
from django import forms
from django.forms import inlineformset_factory
from .models import Supplier, Purchase, PurchaseItem


class SupplierForm(forms.ModelForm):
    """Form for creating/editing suppliers."""
    
    class Meta:
        model = Supplier
        fields = [
            'name', 'contact_name', 'phone', 'email',
            'address', 'cuit', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del proveedor'
            }),
            'contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del contacto'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@ejemplo.com'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dirección completa'
            }),
            'cuit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'XX-XXXXXXXX-X'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas adicionales'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class PurchaseForm(forms.ModelForm):
    """Form for creating/editing purchases."""
    
    class Meta:
        model = Purchase
        fields = ['supplier', 'order_date', 'tax_percent', 'notes']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'order_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tax_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=True)


class PurchaseItemForm(forms.ModelForm):
    """Form for purchase items."""
    
    class Meta:
        model = PurchaseItem
        fields = ['product', 'quantity', 'unit_cost', 'sale_price']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select product-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '1'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'Opcional'}),
        }


# Formset for purchase items
PurchaseItemFormSet = inlineformset_factory(
    Purchase,
    PurchaseItem,
    form=PurchaseItemForm,
    extra=1,
    can_delete=True,
    fields=['product', 'quantity', 'unit_cost', 'sale_price'],
)
