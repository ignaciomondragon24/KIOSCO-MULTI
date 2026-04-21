"""
Middleware que evita que el navegador sirva HTML viejo desde cache.

Problema real reportado: despues de pushear, algunos botones/modales
quedaban colgados porque el navegador servia el HTML viejo (con JS
inline que no matcheaba con los archivos nuevos). El usuario tenia
que hacer Ctrl+Shift+R para arreglarlo.

Solucion: HTML responses llevan Cache-Control: no-cache, must-revalidate.
Con eso el navegador siempre revalida con el server (ETag / 304 si no
cambio, 200 si cambio) — nunca sirve ciegamente desde cache.

Los archivos estaticos (JS/CSS/imagenes) siguen con cache larga porque
tienen hash en el nombre (ForgivingManifestStaticFilesStorage). Cuando
cambian, cambia el hash, cambia la URL, el navegador fetchea automaticamente.
"""


class NoCacheHTMLMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        ctype = response.get('Content-Type', '')
        if ctype.startswith('text/html'):
            # No-cache: el navegador puede cachear pero DEBE revalidar
            # antes de usar la copia. Esto + ETag/Last-Modified del framework
            # hace que las respuestas no modificadas devuelvan 304 rapido
            # pero nunca se sirva un HTML stale tras un deploy.
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response
