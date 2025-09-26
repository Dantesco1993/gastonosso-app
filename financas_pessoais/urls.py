from django.contrib import admin
from django.urls import include, path

# Essas views de sucesso/cancelado/debug você já tem em core.views.planos
# Mantemos aqui apenas se elas NÃO estiverem registradas dentro de core.urls.
from core.views.planos import SucessoView, CanceladoView, debug_checkout_context

urlpatterns = [
    # Raiz do site -> todas as rotas do app principal
    path("", include("core.urls")),

    # Admin
    path("admin/", admin.site.urls),

    # Rotas padrão do Django Auth em /accounts/ (login/logout/reset padrão)
    # OBS: você também tem /login e /logout definidos no core, ok coexistirem.
    path("accounts/", include("django.contrib.auth.urls")),

    # Páginas auxiliares de checkout (se não estiverem no core.urls)
    path("sucesso/", SucessoView.as_view(), name="sucesso"),
    path("cancelado/", CanceladoView.as_view(), name="cancelado"),
    path("debug-checkout/", debug_checkout_context, name="debug_checkout"),
]
