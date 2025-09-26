# core/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views

# Views “genéricas” (transações, análises etc.) que você já tem no módulo views
from . import views

# Views que estão em core/views/auth.py (ajuste se seu caminho for outro)
from .views.auth import (
    landing_page,
    dashboard,                  # @login_required no auth.py
    register,
    primeiros_passos,
    concluir_primeiros_passos,
    redirect_apos_login,
    pagina_planos,              # página de planos com seed/assinatura
    criar_checkout_session,     # checkout Stripe
)

# Opcional: debug de checkout (se existir em core/views/planos.py)
from core.views.planos import debug_checkout_context  # mantenha se a função existir

urlpatterns = [
    # --- Público / Autenticação / Onboarding ---
    path("", landing_page, name="landing"),                              # HOME = landing (pública)
    path("bemvindo/", landing_page, name="landing_page"),                # alias opcional

    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,   # se já logado, manda p/ LOGIN_REDIRECT_URL
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", register, name="register"),

    path("primeiros-passos/", primeiros_passos, name="primeiros_passos"),
    path("primeiros-passos/concluir/", concluir_primeiros_passos, name="concluir_primeiros_passos"),
    path("redirect/", redirect_apos_login, name="redirect_apos_login"),

    # --- Área logada principal ---
    path("dashboard/", dashboard, name="dashboard"),                     # NÃO colocar na raiz

    # --- Planos / Stripe ---
    path("planos/", pagina_planos, name="planos"),                       # apenas UMA definição
    path("planos/criar-checkout-session/<int:plano_id>/", criar_checkout_session, name="criar_checkout_session"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),  # garanta que a view exista

    # --- Debug opcional ---
    path("debug-checkout/", debug_checkout_context, name="debug_checkout"),
    
    # --- Demais rotas do seu app (já existiam) ---
    path("despesas/", views.lista_despesas, name="lista_despesas"),
    path("despesas/editar/<int:id>/", views.editar_despesa, name="editar_despesa"),
    path("despesas/excluir/<int:id>/", views.excluir_despesa, name="excluir_despesa"),
    path("despesas/recorrente/adicionar/", views.adicionar_despesa_recorrente, name="adicionar_despesa_recorrente"),

    path("receitas/", views.lista_receitas, name="lista_receitas"),
    path("receitas/editar/<int:id>/", views.editar_receita, name="editar_receita"),
    path("receitas/excluir/<int:id>/", views.excluir_receita, name="excluir_receita"),
    path("receitas/recorrente/adicionar/", views.adicionar_receita_recorrente, name="adicionar_receita_recorrente"),

    path("contas/", views.lista_contas, name="lista_contas"),
    path("contas/editar/<int:id>/", views.editar_conta, name="editar_conta"),
    path("contas/<int:id>/", views.detalhe_conta, name="detalhe_conta"),

    path("cartoes/", views.lista_cartoes, name="lista_cartoes"),
    path("cartoes/editar/<int:id>/", views.editar_cartao, name="editar_cartao"),
    path("cartoes/<int:id>/fatura/", views.fatura_cartao, name="fatura_cartao"),
    path("cartoes/<int:cartao_id>/pagar/", views.pagar_fatura, name="pagar_fatura"),

    path("analise/", views.analise_gastos, name="analise_gastos"),
    path("analise/drilldown_categoria/", views.analise_drilldown_categoria, name="analise_drilldown_categoria"),
    path("orcamento/", views.orcamento_mensal, name="orcamento_mensal"),
    path("orcamento-50-30-20/", views.orcamento_50_30_20, name="orcamento_50_30_20"),
    path("patrimonio/", views.evolucao_patrimonio, name="evolucao_patrimonio"),
    path("relatorio/", views.relatorio_transacoes, name="relatorio_transacoes"),
    path("metas/", views.lista_metas, name="lista_metas"),
    path("metas/<int:id>/aporte/", views.adicionar_aporte, name="adicionar_aporte"),

    path("investimentos/", views.lista_investimentos, name="lista_investimentos"),
    path("investimentos/excluir/<int:id>/", views.excluir_investimento, name="excluir_investimento"),
    path("investimentos/<int:id>/", views.detalhe_investimento, name="detalhe_investimento"),
    path("investimentos/aporte/<int:investimento_id>/", views.adicionar_aporte_investimento, name="adicionar_aporte_investimento"),

    path("configuracoes/", views.configuracoes, name="configuracoes"),
    path("familia/", views.gerenciar_familia, name="gerenciar_familia"),
    path("configuracoes/categoria/excluir/<int:id>/", views.excluir_categoria, name="excluir_categoria"),
    path("configuracoes/categoria_receita/excluir/<int:id>/", views.excluir_categoria_receita, name="excluir_categoria_receita"),
    path("configuracoes/conta/excluir/<int:id>/", views.excluir_conta, name="excluir_conta"),
    path("configuracoes/cartao/excluir/<int:id>/", views.excluir_cartao, name="excluir_cartao"),
]
