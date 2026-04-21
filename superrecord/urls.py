"""
URL Configuration for CHE GOLOSO Supermarket Management System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({'status': 'ok', 'db': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'db': str(e)}, status=503)


urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('pos/', include('pos.urls')),
    path('cashregister/', include('cashregister.urls')),
    path('stocks/', include('stocks.urls')),
    path('promotions/', include('promotions.urls')),
    path('purchase/', include('purchase.urls')),
    path('expenses/', include('expenses.urls')),
    path('sales/', include('sales.urls')),
    path('company/', include('company.urls')),
    path('mercadopago/', include('mercadopago.urls')),
    path('assistant/', include('assistant.urls')),
    path('signage/', include('signage.urls')),
    path('granel/', include('granel.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = 'CHE GOLOSO - Administración'
admin.site.site_title = 'CHE GOLOSO Admin'
admin.site.index_title = 'Panel de Administración'
