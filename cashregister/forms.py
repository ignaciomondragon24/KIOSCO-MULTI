"""
Cash Register Forms
"""
from django import forms
from .models import CashRegister, CashShift, CashMovement, PaymentMethod


class OpenShiftForm(forms.Form):
    """Form to open a cash shift."""
    
    cash_register = forms.ModelChoiceField(
        label='Caja',
        queryset=CashRegister.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    initial_amount = forms.DecimalField(
        label='Monto Inicial (Efectivo)',
        max_digits=10,
        decimal_places=2,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '1',
            'placeholder': '0'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show available registers
        self.fields['cash_register'].queryset = CashRegister.objects.filter(
            is_active=True
        ).exclude(
            shifts__status='open'
        )


class CloseShiftForm(forms.Form):
    """Form to close a cash shift."""
    
    actual_amount = forms.DecimalField(
        label='Monto Real (Conteo de Efectivo)',
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '1',
            'placeholder': '0'
        })
    )
    notes = forms.CharField(
        label='Notas',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones del cierre...'
        })
    )


class MovementForm(forms.ModelForm):
    """Form for cash movements."""
    
    class Meta:
        model = CashMovement
        fields = ['movement_type', 'amount', 'payment_method', 'description', 'reference']
        widgets = {
            'movement_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'placeholder': '0'
            }),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción del movimiento'
            }),
            'reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Referencia (opcional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_method'].queryset = PaymentMethod.objects.filter(is_active=True)


class CashRegisterForm(forms.ModelForm):
    """Form for cash register CRUD."""
    
    class Meta:
        model = CashRegister
        fields = ['code', 'name', 'location', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
