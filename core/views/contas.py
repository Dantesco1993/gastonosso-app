from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from datetime import date

from core.models import Conta, Receita, Despesa

@login_required
def lista_contas(request):
    hoje = date.today()
    user = request.user
    familia = user.perfil.familia
    
    # Contas são sempre um recurso da família
    contas = Conta.objects.filter(familia=familia) if familia else []
    
    saldos = []
    # O saldo na lista geral reflete o saldo total da conta da família
    usuarios_familia = User.objects.filter(perfil__familia=familia) if familia else [user]

    for conta in contas:
        total_receitas = Receita.objects.filter(user__in=usuarios_familia, conta=conta, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
        total_despesas = Despesa.objects.filter(user__in=usuarios_familia, conta=conta, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
        saldo_atual = (conta.saldo_inicial + total_receitas) - total_despesas
        saldos.append({'conta': conta, 'saldo_atual': saldo_atual})
        
    contexto = {'contas_com_saldo': saldos}
    return render(request, 'core/lista_contas.html', contexto)

@login_required
def detalhe_conta(request, id):
    hoje = date.today()
    user = request.user
    familia = user.perfil.familia
    
    # Garante que o usuário só pode ver contas da sua família
    conta = get_object_or_404(Conta, id=id, familia=familia)
    
    # Lógica de visão
    visao = request.GET.get('visao', 'conjunto')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)

    # Cálculo do saldo considera a visão selecionada
    total_receitas = Receita.objects.filter(user__in=usuarios_a_filtrar, conta=conta, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    total_despesas = Despesa.objects.filter(user__in=usuarios_a_filtrar, conta=conta, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    saldo_atual = (conta.saldo_inicial + total_receitas) - total_despesas
    
    # O extrato de transações também considera a visão
    despesas = Despesa.objects.filter(user__in=usuarios_a_filtrar, conta=conta).order_by('-data')
    receitas = Receita.objects.filter(user__in=usuarios_a_filtrar, conta=conta).order_by('-data')

    contexto = {
        'conta': conta,
        'saldo_atual': saldo_atual,
        'despesas': despesas,
        'receitas': receitas,
        'visao': visao,
        'familia': familia
    }
    return render(request, 'core/detalhe_conta.html', contexto)