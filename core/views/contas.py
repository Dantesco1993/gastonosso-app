from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from datetime import date
from django.contrib import messages

from core.models import Conta, Receita, Despesa
from core.forms import ContaForm # <<< IMPORTAÇÃO ADICIONADA

@login_required
def lista_contas(request):
    user = request.user
    familia = user.perfil.familia
    periodo = request.GET.get('periodo', 'realizado')
    usuarios_familia = User.objects.filter(perfil__familia=familia) if familia else [user]
    contas = Conta.objects.filter(familia=familia) if familia else []
    
    data_limite = (date.today() + relativedelta(months=6)) if periodo == 'projetado' else date.today()

    saldos = [{'conta': c, 'saldo_atual': c.get_saldo_atual(usuarios=usuarios_familia, data_base=data_limite)} for c in contas]
        
    contexto = {'contas_com_saldo': saldos, 'periodo': periodo, 'visao': 'conjunto', 'familia': familia, 'data_projecao': data_limite}
    return render(request, 'core/lista_contas.html', contexto)

@login_required
def detalhe_conta(request, id):
    user = request.user
    familia = user.perfil.familia
    conta = get_object_or_404(Conta, id=id, familia=familia)
    
    has_premium_access = familia.has_premium() if familia else False
    visao = request.GET.get('visao', 'individual')
    periodo = request.GET.get('periodo', 'realizado')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)
    
    data_limite = (date.today() + relativedelta(months=6)) if periodo == 'projetado' else date.today()
    saldo_atual = conta.get_saldo_atual(usuarios=usuarios_a_filtrar, data_base=data_limite)
    
    despesas = Despesa.objects.filter(user__in=usuarios_a_filtrar, conta=conta).order_by('-data')
    receitas = Receita.objects.filter(user__in=usuarios_a_filtrar, conta=conta).order_by('-data')
    contexto = {
        'has_premium_access': has_premium_access,
        'conta': conta, 'saldo_atual': saldo_atual,
        'despesas': despesas, 'receitas': receitas,
        'visao': visao, 'periodo': periodo, 'familia': familia, 'data_projecao': data_limite
    }
    return render(request, 'core/detalhe_conta.html', contexto)

@login_required
def editar_conta(request, id):
    familia = request.user.perfil.familia
    conta = get_object_or_404(Conta, id=id, familia=familia)
    if request.method == 'POST':
        form = ContaForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta atualizada com sucesso!')
            return redirect('lista_contas')
    else:
        form = ContaForm(instance=conta)
    contexto = {'form': form, 'instance': conta, 'tipo_instancia': 'Conta'}
    return render(request, 'core/editar_generico.html', contexto)