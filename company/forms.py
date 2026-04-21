"""
Company Forms
"""
from django import forms
from .models import Company, Branch


class CompanyForm(forms.ModelForm):
    """Form for company settings."""
    
    class Meta:
        model = Company
        fields = [
            'name', 'legal_name', 'cuit', 'address', 'phone',
            'email', 'website', 'logo', 'tax_condition', 'gross_income',
            'start_date', 'receipt_header', 'receipt_footer',
            'currency_symbol', 'decimal_separator', 'thousands_separator'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre comercial'
            }),
            'legal_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Razón social'
            }),
            'cuit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'XX-XXXXXXXX-X'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'tax_condition': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'gross_income': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'receipt_header': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'receipt_footer': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'currency_symbol': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'decimal_separator': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 1
            }),
            'thousands_separator': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 1
            }),
        }


class BranchForm(forms.ModelForm):
    """Form for branches."""
    
    class Meta:
        model = Branch
        fields = ['name', 'code', 'address', 'phone', 'is_active', 'is_main']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la sucursal'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código único'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_main': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
