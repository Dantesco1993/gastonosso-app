from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum

from core.models import Investimento, AporteInvestimento, Categoria, Despesa
from core.forms import InvestimentoForm, AporteInvestimentoForm

@login_required
def lista_investimentos(request):
    familia = request.user.perfil.familia

    if request.method == 'POST':
        if not familia:
            messages.error(request, "Você precisa criar ou pertencer a uma família para adicionar investimentos.")
            return redirect('gerenciar_familia')

        form = InvestimentoForm(request.POST)
        if form.is_valid():
            investimento = form.save(commit=False)
            investimento.familia = familia
            investimento.save()
            messages.success(request, 'Novo investimento cadastrado com sucesso!')
            return redirect('lista_investimentos')
    else:
        form = InvestimentoForm()

    investimentos = Investimento.objects.filter(familia=familia) if familia else []
    total_investido = investimentos.aggregate(total=Sum('valor_atual'))['total'] or 0

    contexto = {
        'investimentos': investimentos,
        'total_investido': total_investido,
        'form': form,
    }
    return render(request, 'core/lista_investimentos.html', contexto)


@login_required
def detalhe_investimento(request, id):
    familia = request.user.perfil.familia
    investimento = get_object_or_404(Investimento, id=id, familia=familia)
    aportes = AporteInvestimento.objects.filter(investimento=investimento).order_by('-data')
    
    form_aporte = AporteInvestimentoForm(user=request.user)

    contexto = {
        'investimento': investimento,
        'aportes': aportes,
        'form_aporte': form_aporte,
    }
    return render(request, 'core/detalhe_investimento.html', contexto)


@login_required
def adicionar_aporte_investimento(request, investimento_id):
    familia = request.user.perfil.familia
    investimento = get_object_or_404(Investimento, id=investimento_id, familia=familia)

    if request.method == 'POST':
        form = AporteInvestimentoForm(request.POST, user=request.user)
        if form.is_valid():
            aporte = form.save(commit=False)
            aporte.user = request.user
            aporte.investimento = investimento
            aporte.save()

            investimento.valor_atual += aporte.valor
            investimento.save()

            categoria_investimento, _ = Categoria.objects.get_or_create(
                familia=familia, 
                nome__iexact="Investimentos", 
                defaults={'nome': "Investimentos"}
            )

            Despesa.objects.create(
                user=request.user,
                descricao=f"Aporte para o investimento: {investimento.nome}",
                valor=aporte.valor,
                data=aporte.data,
                categoria=categoria_investimento,
                conta=aporte.conta_origem
            )

            messages.success(request, 'Aporte realizado e despesa registrada com sucesso!')
            return redirect('detalhe_investimento', id=investimento.id)
    
    messages.error(request, 'Houve um erro ao processar o aporte. Verifique os dados.')
    return redirect('detalhe_investimento', id=investimento.id)