"""
Custom middleware for accounts app.
"""
from django.http import JsonResponse


class AjaxLoginRedirectMiddleware:
    """
    Intercepta redirects 302 al login que se generan por @login_required y los
    convierte en respuestas JSON 401 cuando la request original es AJAX/API.

    De esta forma, los endpoints `api_*` que están decorados con `@login_required`
    devuelven JSON limpio en vez de HTML 302 cuando la sesión expira, sin tener
    que migrar uno por uno todos los views.

    Una request se considera AJAX/API si cumple cualquiera de:
      - Header `X-Requested-With: XMLHttpRequest`
      - Header `Accept` contiene `application/json`
      - El path contiene `/api/`
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Solo nos interesan redirects 302
        if response.status_code != 302:
            return response

        location = response.get('Location', '') or ''
        # Solo redirects al login (cubre /login/ y /login/?next=...)
        if '/login/' not in location:
            return response

        if self._is_ajax_request(request):
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Autenticación requerida',
                    'detail': 'La sesión expiró o no estás autenticado.',
                },
                status=401,
            )

        return response

    @staticmethod
    def _is_ajax_request(request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return True
        accept = request.headers.get('Accept', '') or ''
        if 'application/json' in accept:
            return True
        if '/api/' in request.path:
            return True
        return False
