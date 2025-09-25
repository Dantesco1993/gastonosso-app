from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum
from datetime import date
from dateutil.relativedelta import relativedelta

from core.models import CartaoDeCredito, Despesa, Categoria, Conta
from core.forms import PagamentoFaturaForm

@login_required
def lista_cartoes(request):
    familia = request.user.perfil.familia
    cartoes = CartaoDeCredito.objects.filter(familia=familia) if familia else []
    contexto = {'cartoes': cartoes}
    return render(request, 'core/lista_cartoes.html', contexto)

@login_required
def fatura_cartao(request, id):
    user = request.user
    familia = user.perfil.familia
    cartao = get_object_or_404(CartaoDeCredito, id=id, familia=familia)
    
    visao = request.GET.get('visao', 'conjunto')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)
    
    # --- LÓGICA SIMPLIFICADA ---
    fatura = cartao.get_fatura_aberta(usuarios=usuarios_a_filtrar)

    form_pagamento = PagamentoFaturaForm(familia=familia)

    contexto = {
        'cartao': cartao,
        'despesas_abertas': fatura['despesas'],
        'total_fatura': fatura['total'],
        'data_inicio': fatura['data_inicio'],
        'data_fechamento': fatura['data_fechamento'],
        'form_pagamento': form_pagamento,
    }
    return render(request, 'core/fatura_cartao.html', contexto)

@login_required
def pagar_fatura(request, cartao_id):
    if request.method == 'POST':
        user = request.user
        familia = user.perfil.familia
        cartao = get_object_or_404(CartaoDeCredito, id=cartao_id, familia=familia)
        form = PagamentoFaturaForm(request.POST, familia=familia)

        if form.is_valid():
            conta_pagamento = form.cleaned_data['conta_pagamento']
            data_pagamento = form.cleaned_data['data_pagamento']
            
            hoje = date.today()
            if hoje.day <= cartao.dia_fechamento: data_fechamento = hoje.replace(day=cartao.dia_fechamento)
            else: data_fechamento = (hoje + relativedelta(months=1)).replace(day=cartao.dia_fechamento)
            data_inicio = (data_fechamento - relativedelta(months=1)) + relativedelta(days=1)
            
            usuarios_familia = User.objects.filter(perfil__familia=familia)
            despesas_fatura = Despesa.objects.filter(
                user__in=usuarios_familia,
                cartao=cartao, data__gte=data_inicio, data__lte=data_fechamento, fatura_paga=False
            )
            total_a_pagar = despesas_fatura.aggregate(Sum('valor'))['valor__sum'] or 0
            
            if total_a_pagar > 0:
                categoria_pagamento, _ = Categoria.objects.get_or_create(familia=familia, nome__iexact="Pagamento de Fatura", defaults={'nome': "Pagamento de Fatura"})
                Despesa.objects.create(
                    user=user,
                    descricao=f"Pagamento da fatura - {cartao.nome}",
                    valor=total_a_pagar,
                    data=data_pagamento,
                    categoria=categoria_pagamento,
                    conta=conta_pagamento
                )
                despesas_fatura.update(fatura_paga=True)
                messages.success(request, f'Pagamento da fatura de R$ {total_a_pagar} registrado com sucesso!')
            else:
                messages.warning(request, 'Não havia saldo em aberto para pagar nesta fatura.')

    return redirect('fatura_cartao', id=cartao_id)

# Adicione esta view no final do arquivo core/views/cartoes.py
@login_required
def editar_cartao(request, id):
    familia = request.user.perfil.familia
    cartao = get_object_or_404(CartaoDeCredito, id=id, familia=familia)
    if request.method == 'POST':
        form = CartaoDeCreditoForm(request.POST, instance=cartao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cartão atualizado com sucesso!')
            return redirect('lista_cartoes')
    else:
        form = CartaoDeCreditoForm(instance=cartao)
    contexto = {'form': form, 'instance': cartao}
    return render(request, 'core/editar_generico.html', contexto)