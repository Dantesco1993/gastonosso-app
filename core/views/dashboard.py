from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from datetime import date
from dateutil.relativedelta import relativedelta
from itertools import chain
from operator import attrgetter

from core.models import Conta, Receita, Despesa, CartaoDeCredito, MetaFinanceira, Investimento

@login_required
def dashboard(request):
    user = request.user
    familia = user.perfil.familia
    hoje = date.today()
    
    visao = request.GET.get('visao', 'individual')
    periodo = request.GET.get('periodo', 'realizado')

    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)
        
    contas = Conta.objects.filter(familia=familia) if familia else []
    cartoes = CartaoDeCredito.objects.filter(familia=familia) if familia else []
    investimentos = Investimento.objects.filter(familia=familia) if familia else []
    
    data_limite = (hoje + relativedelta(months=6)) if periodo == 'projetado' else hoje

    # --- Cálculos Aprimorados ---
    saldo_total_contas = sum(c.get_saldo_atual(usuarios=usuarios_a_filtrar, data_base=data_limite) for c in contas)
    
    # Balanço do Mês (Realizado)
    receitas_mes = Receita.objects.filter(user__in=usuarios_a_filtrar, data__year=hoje.year, data__month=hoje.month, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    despesas_caixa_mes = Despesa.objects.filter(user__in=usuarios_a_filtrar, conta__isnull=False, data__year=hoje.year, data__month=hoje.month, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    balanco_caixa_mes = receitas_mes - despesas_caixa_mes
    
    # Novos cálculos para o card aprimorado
    despesas_cartao_mes = Despesa.objects.filter(user__in=usuarios_a_filtrar, cartao__isnull=False, data__year=hoje.year, data__month=hoje.month, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    gastos_totais_mes = despesas_caixa_mes + despesas_cartao_mes

    # Faturas de Cartão
    faturas_abertas = [{'cartao': c, 'total': c.get_fatura_aberta(usuarios=usuarios_a_filtrar)['total']} for c in cartoes]

    # Patrimônio Líquido
    valor_investido = investimentos.aggregate(total=Sum('valor_atual'))['total'] or 0
    divida_cartoes = sum(f['total'] for f in faturas_abertas)
    saldo_contas_realizado = sum(c.get_saldo_atual(usuarios=usuarios_a_filtrar) for c in contas)
    patrimonio_liquido = (saldo_contas_realizado + valor_investido) - divida_cartoes

    # Top 5 Gastos
    gastos_mes_categoria = Despesa.objects.filter(user__in=usuarios_a_filtrar, data__year=hoje.year, data__month=hoje.month).values('categoria__nome').annotate(total=Sum('valor')).order_by('-total')[:5]
    labels_gastos_pie = [g['categoria__nome'] for g in gastos_mes_categoria]
    data_gastos_pie = [float(g['total']) for g in gastos_mes_categoria]

    # Metas
    metas = MetaFinanceira.objects.filter(familia=familia).order_by('-valor_atual')[:3] if familia else []

    contexto = {
        'saldo_total_contas': saldo_total_contas,
        'balanco_caixa_mes': balanco_caixa_mes,
        'receitas_mes': receitas_mes,
        'despesas_caixa_mes': despesas_caixa_mes,
        'despesas_cartao_mes': despesas_cartao_mes,
        'gastos_totais_mes': gastos_totais_mes,
        'faturas': faturas_abertas,
        'patrimonio_liquido': patrimonio_liquido,
        'labels_gastos_pie': labels_gastos_pie,
        'data_gastos_pie': data_gastos_pie,
        'metas': metas,
        'visao': visao, 'periodo': periodo, 'familia': familia,
        'data_projecao': data_limite
    }
    return render(request, 'core/dashboard.html', contexto)