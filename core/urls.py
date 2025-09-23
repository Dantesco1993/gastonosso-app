# core/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # URLs de Autenticação
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),

    # URLs da Aplicação
    path('', views.dashboard, name='dashboard'), 
    path('despesas/', views.lista_despesas, name='lista_despesas'), 
    path('despesas/editar/<int:id>/', views.editar_despesa, name='editar_despesa'),
    path('despesas/excluir/<int:id>/', views.excluir_despesa, name='excluir_despesa'),
    path('receitas/', views.lista_receitas, name='lista_receitas'),
    path('receitas/excluir/<int:id>/', views.excluir_receita, name='excluir_receita'),
    path('contas/', views.lista_contas, name='lista_contas'),
    path('contas/<int:id>/', views.detalhe_conta, name='detalhe_conta'),
    path('cartoes/', views.lista_cartoes, name='lista_cartoes'),
    path('cartoes/<int:id>/fatura/', views.fatura_cartao, name='fatura_cartao'),
    path('analise/', views.analise_gastos, name='analise_gastos'),
    path('metas/', views.lista_metas, name='lista_metas'),
    path('metas/<int:id>/aporte/', views.adicionar_aporte, name='adicionar_aporte'),
    path('configuracoes/', views.configuracoes, name='configuracoes'),
    path('configuracoes/categoria/excluir/<int:id>/', views.excluir_categoria, name='excluir_categoria'),
    path('configuracoes/categoria_receita/excluir/<int:id>/', views.excluir_categoria_receita, name='excluir_categoria_receita'),
    path('configuracoes/conta/excluir/<int:id>/', views.excluir_conta, name='excluir_conta'),
    path('configuracoes/cartao/excluir/<int:id>/', views.excluir_cartao, name='excluir_cartao'),
    path('despesas/recorrente/adicionar/', views.adicionar_despesa_recorrente, name='adicionar_despesa_recorrente'),
    path('receitas/recorrente/adicionar/', views.adicionar_receita_recorrente, name='adicionar_receita_recorrente'),
    path('familia/', views.gerenciar_familia, name='gerenciar_familia'),
    path('investimentos/', views.lista_investimentos, name='lista_investimentos'),
    path('investimentos/<int:id>/', views.detalhe_investimento, name='detalhe_investimento'),
    path('investimentos/aporte/<int:investimento_id>/', views.adicionar_aporte_investimento, name='adicionar_aporte_investimento'),
    path('cartoes/<int:cartao_id>/pagar/', views.pagar_fatura, name='pagar_fatura'),
]