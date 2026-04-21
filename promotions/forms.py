"""
Promotions Forms
"""
from django import forms
from .models import Promotion
from stocks.models import Product


class PromotionForm(forms.ModelForm):
    """Form for promotions."""
    
    products = forms.ModelMultipleChoiceField(
        label='Productos',
        queryset=Product.objects.filter(is_active=True),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': '10'
        })
    )
    
    class Meta:
        model = Promotion
        fields = [
            'name', 'description', 'promo_type', 'status',
            'start_date', 'end_date', 'priority', 'is_combinable',
            'applies_to_packaging_type',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'hour_start', 'hour_end',
            'min_quantity', 'min_purchase_amount', 'max_uses_per_sale',
            'quantity_required', 'quantity_charged',
            'discount_percent', 'discount_amount', 'final_price', 'second_unit_discount',
            'products'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'promo_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'priority': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_combinable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'applies_to_packaging_type': forms.Select(attrs={'class': 'form-select'}),
            'monday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tuesday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'wednesday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'thursday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'friday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'saturday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sunday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'hour_start': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hour_end': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'min_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_purchase_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'max_uses_per_sale': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity_required': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity_charged': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'final_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'second_unit_discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
        }
