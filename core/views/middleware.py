from urllib.parse import urlencode, urlsplit
from django.conf import settings
from django.shortcuts import redirect, resolve_url

class ForceAuthMiddleware:
    """
    Exige autenticação para páginas internas, mas libera:
    - landing (home pública), login, register e rotas de reset de senha
    - static/media/favicon/admin
    Evita loops com ?next= e não re-encoda múltiplas vezes.
    """

    ALLOW_PREFIXES = ('/static/', '/media/', '/favicon.ico')
    # nomes de URL que devem ficar públicos (ajuste conforme seu projeto)
    ALLOW_NAMES = {
        'landing',
        'login',
        'logout',
        'register',
        'password_reset',
        'password_reset_done',
        'password_reset_confirm',
        'password_reset_complete',
        'admin:index',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Já autenticado? libera
        if request.user.is_authenticated:
            return None

        path = request.path

        # Libera assets e admin
        if path.startswith(self.ALLOW_PREFIXES) or path.startswith('/admin/'):
            return None

        # Nome da rota (seguro em process_view)
        view_name = getattr(getattr(request, "resolver_match", None), "view_name", None)

        # Se a rota atual está na whitelist de nomes, libera
        if view_name in self.ALLOW_NAMES:
            return None

        # Não intercepta a própria página de login (mesmo sem nome resolvido)
        login_url = resolve_url(getattr(settings, 'LOGIN_URL', 'login'))
        login_path = urlsplit(login_url).path or '/login/'
        if path == login_path:
            return None

        # Se já tem ?next=, não reapende (evita %2525 chuva)
        if 'next' in request.GET:
            return None

        # Redireciona 1x para login com next (sem double-encode)
        next_url = request.get_full_path()
        return redirect(f"{login_url}?{urlencode({'next': next_url})}")
