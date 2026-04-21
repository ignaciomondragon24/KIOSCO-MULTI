"""
Accounts Forms
"""
from django import forms
from .models import User, Role


class LoginForm(forms.Form):
    """Login form."""
    username = forms.CharField(
        label='Usuario',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu usuario',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu contraseña'
        })
    )


class UserForm(forms.ModelForm):
    """Form for creating users."""
    
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password_confirm = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    role = forms.ChoiceField(
        label='Rol',
        choices=[('', '-- Seleccionar --')] + Role.ROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'required': 'Debe seleccionar un rol'}
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        error_messages = {
            'username': {
                'unique': 'Ya existe un usuario con ese nombre. Elegí otro.',
            },
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Las contraseñas no coinciden. Asegurate de escribirlas igual.')
        
        if password and len(password) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        
        return cleaned_data


class UserEditForm(forms.ModelForm):
    """Form for editing users."""
    
    role = forms.ChoiceField(
        label='Rol',
        choices=[('', '-- Seleccionar --')] + Role.ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
