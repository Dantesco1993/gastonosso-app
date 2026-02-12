from django.contrib import admin
from django.urls import include, path

from core.views.planos import PlanosView, criar_sessao_checkout, SucessoView, CanceladoView
from core.views.pagamentos import stripe_webhook
from core.views.planos import PlanosView, criar_sessao_checkout, SucessoView, CanceladoView, debug_checkout_context

urlpatterns = [
    path("", include("core.urls")),

    path("admin/", admin.site.urls),

    path("planos/", PlanosView.as_view(), name="planos"),

    # 👉 Agora recebemos o ID do plano na URL e fazemos POST
    path("criar-sessao/<int:plano_id>/", criar_sessao_checkout, name="criar_sessao"),

    path("sucesso/", SucessoView.as_view(), name="sucesso"),
    path("cancelado/", CanceladoView.as_view(), name="cancelado"),
    path("debug-checkout/", debug_checkout_context, name="debug_checkout"),

    path("stripe-webhook/", stripe_webhook, name="stripe_webhook"),
]
