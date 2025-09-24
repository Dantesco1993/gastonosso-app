from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from core.models import Conta, Receita, Despesa

@login_required
def lista_contas(request):
    user = request.user
    familia = user.perfil.familia
    contas = Conta.objects.filter(familia=familia) if familia else []
    
    # --- LÓGICA SIMPLIFICADA ---
    usuarios_familia = User.objects.filter(perfil__familia=familia) if familia else [user]
    saldos = [{'conta': conta, 'saldo_atual': conta.get_saldo_atual(usuarios=usuarios_familia)} for conta in contas]
        
    contexto = {'contas_com_saldo': saldos}
    return render(request, 'core/lista_contas.html', contexto)

@login_required
def detalhe_conta(request, id):
    user = request.user
    familia = user.perfil.familia
    conta = get_object_or_404(Conta, id=id, familia=familia)
    
    visao = request.GET.get('visao', 'conjunto')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)

    # --- LÓGICA SIMPLIFICADA ---
    saldo_atual = conta.get_saldo_atual(usuarios=usuarios_a_filtrar)
    
    despesas = Despesa.objects.filter(user__in=usuarios_a_filtrar, conta=conta).order_by('-data')
    receitas = Receita.objects.filter(user__in=usuarios_a_filtrar, conta=conta).order_by('-data')

    contexto = {
        'conta': conta, 'saldo_atual': saldo_atual,
        'despesas': despesas, 'receitas': receitas,
        'visao': visao, 'familia': familia
    }
    return render(request, 'core/detalhe_conta.html', contexto)