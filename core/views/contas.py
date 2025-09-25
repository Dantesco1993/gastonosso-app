from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from datetime import date

from core.models import Conta, Receita, Despesa

@login_required
def lista_contas(request):
    user = request.user
    familia = user.perfil.familia
    hoje = date.today()
    periodo = request.GET.get('periodo', 'realizado')
    usuarios_familia = User.objects.filter(perfil__familia=familia) if familia else [user]
    contas = Conta.objects.filter(familia=familia) if familia else []
    
    data_limite = (hoje + relativedelta(months=6)) if periodo == 'projetado' else hoje

    saldos = [{'conta': c, 'saldo_atual': c.get_saldo_atual(usuarios=usuarios_familia, data_base=data_limite)} for c in contas]
        
    contexto = {'contas_com_saldo': saldos, 'periodo': periodo, 'visao': 'conjunto', 'familia': familia, 'data_projecao': data_limite}
    return render(request, 'core/lista_contas.html', contexto)

@login_required
def detalhe_conta(request, id):
    user = request.user
    familia = user.perfil.familia
    hoje = date.today()
    conta = get_object_or_404(Conta, id=id, familia=familia)
    
    visao = request.GET.get('visao', 'individual')
    periodo = request.GET.get('periodo', 'realizado')
    if visao == 'individual' or not familia: usuarios_a_filtrar = [user]
    else: usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)
    
    data_limite = (hoje + relativedelta(months=6)) if periodo == 'projetado' else hoje
    saldo_atual = conta.get_saldo_atual(usuarios=usuarios_a_filtrar, data_base=data_limite)
    
    despesas = Despesa.objects.filter(user__in=usuarios_a_filtrar, conta=conta).order_by('-data')
    receitas = Receita.objects.filter(user__in=usuarios_a_filtrar, conta=conta).order_by('-data')
    contexto = {
        'conta': conta, 'saldo_atual': saldo_atual,
        'despesas': despesas, 'receitas': receitas,
        'visao': visao, 'periodo': periodo, 'familia': familia, 'data_projecao': data_limite
    }
    return render(request, 'core/detalhe_conta.html', contexto)