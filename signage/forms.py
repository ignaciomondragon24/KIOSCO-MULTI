from django import forms
from .models import SignTemplate


class SignTemplateForm(forms.ModelForm):
    class Meta:
        model = SignTemplate
        fields = ['name', 'sign_type', 'width_mm', 'height_mm']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la plantilla',
            }),
            'sign_type': forms.HiddenInput(),
            'width_mm': forms.HiddenInput(),
            'height_mm': forms.HiddenInput(),
        }
