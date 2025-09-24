from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

# --- IMPORTAÇÕES CORRIGIDAS ---
from core.models import (
    Despesa, MetaFinanceira, Categoria, Conta, Investimento, 
    AporteInvestimento, CartaoDeCredito, Receita
)
from core.forms import MetaFinanceiraForm, AporteForm

@login_required
def analise_gastos(request):
    user = request.user
    familia = user.perfil.familia
    hoje = date.today()

    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')

    if data_inicio_str and data_fim_str:
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
    else:
        data_inicio = hoje.replace(day=1)
        data_fim = hoje + relativedelta(months=1, day=1) - relativedelta(days=1)

    visao = request.GET.get('visao', 'conjunto')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)

    gastos_por_categoria = Despesa.objects.filter(
        user__in=usuarios_a_filtrar, 
        data__range=[data_inicio, data_fim]
    ).values('categoria__nome').annotate(total=Sum('valor')).order_by('-total')
    
    labels_pie = [gasto['categoria__nome'] for gasto in gastos_por_categoria]
    data_pie = [float(gasto['total']) for gasto in gastos_por_categoria]

    fluxo_caixa_data = []
    for i in range(12):
        mes_alvo = hoje - relativedelta(months=i)
        receitas_mes = Receita.objects.filter(user__in=usuarios_a_filtrar, data__year=mes_alvo.year, data__month=mes_alvo.month).aggregate(total=Sum('valor'))['total'] or 0
        despesas_mes = Despesa.objects.filter(user__in=usuarios_a_filtrar, data__year=mes_alvo.year, data__month=mes_alvo.month, conta__isnull=False).aggregate(total=Sum('valor'))['total'] or 0
        fluxo_caixa_data.append({'mes': mes_alvo.strftime('%b/%y'), 'receitas': float(receitas_mes), 'despesas': float(despesas_mes)})
    
    fluxo_caixa_data.reverse()
    labels_bar = [item['mes'] for item in fluxo_caixa_data]
    data_receitas_bar = [item['receitas'] for item in fluxo_caixa_data]
    data_despesas_bar = [item['despesas'] for item in fluxo_caixa_data]

    contexto = {
        'gastos_por_categoria': gastos_por_categoria,
        'labels_pie': labels_pie, 'data_pie': data_pie, 'visao': visao,
        'data_inicio': data_inicio, 'data_fim': data_fim, 'familia': familia,
        'labels_bar': labels_bar, 'data_receitas_bar': data_receitas_bar, 'data_despesas_bar': data_despesas_bar,
    }
    return render(request, 'core/analise_gastos.html', contexto)

@login_required
def lista_metas(request):
    user = request.user
    familia = user.perfil.familia

    if request.method == 'POST':
        if not familia:
            messages.error(request, "Você precisa criar ou pertencer a uma família para adicionar metas.")
            return redirect('gerenciar_familia')
            
        form_meta = MetaFinanceiraForm(request.POST)
        if form_meta.is_valid():
            meta = form_meta.save(commit=False)
            meta.familia = familia
            meta.save()
            messages.success(request, 'Nova meta criada com sucesso!')
            return redirect('lista_metas')
    else:
        form_meta = MetaFinanceiraForm()
        
    metas = MetaFinanceira.objects.filter(familia=familia) if familia else []
    form_aporte = AporteForm(user=user)

    contexto = {'metas': metas, 'form_meta': form_meta, 'form_aporte': form_aporte}
    return render(request, 'core/lista_metas.html', contexto)

@login_required
def adicionar_aporte(request, id):
    if request.method == 'POST':
        user = request.user
        familia = user.perfil.familia
        meta = get_object_or_404(MetaFinanceira, id=id, familia=familia)
        
        form = AporteForm(request.POST, user=user)

        if form.is_valid():
            valor_aporte = form.cleaned_data['valor']
            conta_origem = form.cleaned_data['conta_origem']

            meta.valor_atual += valor_aporte
            meta.save()

            categoria_aporte, _ = Categoria.objects.get_or_create(
                familia=familia, nome__iexact="Metas Financeiras", defaults={'nome': "Metas Financeiras"}
            )

            Despesa.objects.create(
                user=user,
                descricao=f"Aporte para a meta: {meta.nome}",
                valor=valor_aporte,
                data=date.today(),
                categoria=categoria_aporte,
                conta=conta_origem
            )
            messages.success(request, 'Aporte realizado e despesa registrada com sucesso!')
            
    return redirect('lista_metas')

@login_required
def evolucao_patrimonio(request):
    user = request.user
    familia = user.perfil.familia
    hoje = date.today()

    visao = request.GET.get('visao', 'conjunto')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)
    
    patrimonio_data = []
    for i in range(12):
        ponto_no_tempo = hoje - relativedelta(months=i)
        ultimo_dia_mes = ponto_no_tempo.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)

        # 1. Ativos em Contas
        contas = Conta.objects.filter(familia=familia) if familia else []
        saldo_contas = 0
        for conta in contas:
            # Precisamos ajustar o get_saldo_atual para aceitar data_base
            receitas = Receita.objects.filter(user__in=usuarios_a_filtrar, conta=conta, data__lte=ultimo_dia_mes).aggregate(total=Sum('valor'))['total'] or 0
            despesas = Despesa.objects.filter(user__in=usuarios_a_filtrar, conta=conta, data__lte=ultimo_dia_mes).aggregate(total=Sum('valor'))['total'] or 0
            saldo_contas += (conta.saldo_inicial + receitas) - despesas
        
        # 2. Ativos em Investimentos (valor aportado até a data)
        investimentos = Investimento.objects.filter(familia=familia, data_criacao__lte=ultimo_dia_mes) if familia else []
        valor_investido = 0
        for investimento in investimentos:
            aportes = AporteInvestimento.objects.filter(
                user__in=usuarios_a_filtrar,
                investimento=investimento,
                data__lte=ultimo_dia_mes
            ).aggregate(total=Sum('valor'))['total'] or 0
            valor_investido += aportes

        # 3. Dívidas em Cartões
        cartoes = CartaoDeCredito.objects.filter(familia=familia) if familia else []
        divida_cartoes = 0
        for cartao in cartoes:
            fatura = cartao.get_fatura_aberta(usuarios=usuarios_a_filtrar, data_base=ultimo_dia_mes)
            divida_cartoes += fatura['total']

        patrimonio_liquido = (saldo_contas + valor_investido) - divida_cartoes
        patrimonio_data.append({
            'mes': ultimo_dia_mes.strftime('%b/%y'),
            'valor': float(patrimonio_liquido)
        })

    patrimonio_data.reverse()
    labels = [item['mes'] for item in patrimonio_data]
    data = [item['valor'] for item in patrimonio_data]

    contexto = {
        'labels': labels,
        'data': data,
        'patrimonio_atual': patrimonio_data[-1]['valor'] if patrimonio_data else 0,
        'visao': visao,
        'familia': familia,
    }
    return render(request, 'core/evolucao_patrimonio.html', contexto)