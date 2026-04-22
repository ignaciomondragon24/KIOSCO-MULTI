"""
Vistas publicas de la landing comercial.

La home detecta si el usuario esta autenticado: si lo esta, lo manda al dashboard
del sistema interno; si no, muestra la landing comercial para vender el sistema
a kiosqueros.
"""
from django.shortcuts import redirect, render


LANDING_CONTEXT = {
    # Marca del producto SaaS.
    'brand_name': 'Kiosco Pro',
    'brand_tagline': 'El sistema de punto de venta pensado para el kiosco argentino',
    # Canal de contacto principal: WhatsApp (formato internacional sin + ni espacios).
    # 54 = Argentina, 9 = movil, 11 = area, 23866766 = numero.
    'whatsapp_number': '5491123866766',
    'whatsapp_message': 'Hola! Vi Kiosco Pro en la web y quiero mas info para mi kiosco.',
    # Redes sociales (placeholders, editar cuando esten).
    # Dejar en None hasta que haya cuenta real; el template oculta el link si no hay url.
    'instagram_url': None,
    'email_contact': 'contacto@kioskopro.com.ar',
}


def home(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    return render(request, 'landing/home.html', LANDING_CONTEXT)
