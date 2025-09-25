from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

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

    # --- Lógica de Filtros ---
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    periodo = request.GET.get('periodo', 'realizado')
    visao = request.GET.get('visao', 'individual')

    if data_inicio_str and data_fim_str:
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
    else:
        # Padrão: Mês atual se for 'realizado', próximos 6 meses se for 'projetado'
        data_inicio = hoje.replace(day=1)
        if periodo == 'projetado':
            data_fim = hoje + relativedelta(months=6)
        else:
            data_fim = hoje + relativedelta(months=1, day=1) - relativedelta(days=1)

    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)

    # --- Cálculo para Gráfico de Pizza (sempre usa o filtro de data) ---
    gastos_por_categoria = Despesa.objects.filter(
        user__in=usuarios_a_filtrar, 
        data__range=[data_inicio, data_fim]
    ).values('categoria__nome').annotate(total=Sum('valor')).order_by('-total')
    
    labels_pie = [gasto['categoria__nome'] for gasto in gastos_por_categoria]
    data_pie = [float(gasto['total']) for gasto in gastos_por_categoria]

    # --- Lógica de Fluxo de Caixa (passado recente e projeção futura) ---
    fluxo_caixa_data = []
    # Mostra 6 meses passados e 6 meses futuros
    for i in range(-6, 7): 
        mes_alvo = hoje + relativedelta(months=i)
        
        filtro_data_mes = {'data__year': mes_alvo.year, 'data__month': mes_alvo.month}
        # Se o período for 'realizado', só considera até hoje
        if periodo == 'realizado' and mes_alvo.year == hoje.year and mes_alvo.month == hoje.month:
            filtro_data_mes['data__lte'] = hoje

        receitas_mes = Receita.objects.filter(user__in=usuarios_a_filtrar, **filtro_data_mes).aggregate(total=Sum('valor'))['total'] or 0
        despesas_mes = Despesa.objects.filter(user__in=usuarios_a_filtrar, conta__isnull=False, **filtro_data_mes).aggregate(total=Sum('valor'))['total'] or 0
        
        fluxo_caixa_data.append({
            'mes': mes_alvo.strftime('%b/%y'),
            'receitas': float(receitas_mes),
            'despesas': float(despesas_mes)
        })
    
    labels_bar = [item['mes'] for item in fluxo_caixa_data]
    data_receitas_bar = [item['receitas'] for item in fluxo_caixa_data]
    data_despesas_bar = [item['despesas'] for item in fluxo_caixa_data]

    contexto = {
        'gastos_por_categoria': gastos_por_categoria, 'labels_pie': labels_pie, 'data_pie': data_pie,
        'visao': visao, 'periodo': periodo, 'data_inicio': data_inicio, 'data_fim': data_fim,
        'familia': familia, 'labels_bar': labels_bar, 'data_receitas_bar': data_receitas_bar,
        'data_despesas_bar': data_despesas_bar,
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
def orcamento_mensal(request):
    user = request.user
    familia = user.perfil.familia
    hoje = date.today()
    
    visao = request.GET.get('visao', 'conjunto')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)

    # Pega todas as categorias da família que têm um orçamento definido (> 0)
    categorias_orcadas = Categoria.objects.filter(familia=familia, orcamento_mensal__gt=0) if familia else []
    
    dados_orcamento = []
    total_orcado = 0
    total_gasto = 0

    for categoria in categorias_orcadas:
        gasto_mes = Despesa.objects.filter(
            user__in=usuarios_a_filtrar,
            categoria=categoria,
            data__year=hoje.year,
            data__month=hoje.month
        ).aggregate(total=Sum('valor'))['total'] or 0
        
        restante = categoria.orcamento_mensal - gasto_mes
        progresso = (gasto_mes / categoria.orcamento_mensal) * 100 if categoria.orcamento_mensal > 0 else 0
        
        dados_orcamento.append({
            'categoria': categoria,
            'orcado': categoria.orcamento_mensal,
            'gasto': gasto_mes,
            'restante': restante,
            'progresso': min(progresso, 100) # Garante que não passe de 100%
        })
        total_orcado += categoria.orcamento_mensal
        total_gasto += gasto_mes

    contexto = {
        'dados_orcamento': dados_orcamento,
        'total_orcado': total_orcado,
        'total_gasto': total_gasto,
        'total_restante': total_orcado - total_gasto,
        'visao': visao,
        'familia': familia
    }
    return render(request, 'core/orcamento_mensal.html', contexto)

@login_required
def evolucao_patrimonio(request):
    user = request.user
    familia = user.perfil.familia
    hoje = date.today()

    visao = request.GET.get('visao', 'individual')
    periodo = request.GET.get('periodo', 'realizado')

    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)
    
    patrimonio_data = []
    # Calcula 6 meses no passado e projeta 6 meses no futuro
    for i in range(-6, 7):
        ponto_no_tempo = hoje + relativedelta(months=i)
        ultimo_dia_mes = ponto_no_tempo.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)

        # Na visão 'realizado', não calculamos para meses futuros
        if periodo == 'realizado' and ponto_no_tempo > hoje:
            continue

        data_limite = ultimo_dia_mes if periodo == 'projetado' else min(ultimo_dia_mes, hoje)

        # 1. Ativos em Contas
        contas = Conta.objects.filter(familia=familia) if familia else []
        saldo_contas = sum(c.get_saldo_atual(usuarios=usuarios_a_filtrar, data_base=data_limite) for c in contas)
        
        # 2. Ativos em Investimentos (valor aportado até a data)
        investimentos = Investimento.objects.filter(familia=familia, data_criacao__lte=data_limite) if familia else []
        valor_investido = sum(inv.aportes.filter(user__in=usuarios_a_filtrar, data__lte=data_limite).aggregate(t=Sum('valor'))['t'] or 0 for inv in investimentos)

        # 3. Dívidas em Cartões
        cartoes = CartaoDeCredito.objects.filter(familia=familia) if familia else []
        divida_cartoes = sum(c.get_fatura_aberta(usuarios=usuarios_a_filtrar, data_base=ultimo_dia_mes)['total'] for c in cartoes)

        patrimonio_liquido = (saldo_contas + valor_investido) - divida_cartoes
        patrimonio_data.append({
            'mes': ultimo_dia_mes.strftime('%b/%y'),
            'valor': float(patrimonio_liquido)
        })

    labels = [item['mes'] for item in patrimonio_data]
    data = [item['valor'] for item in patrimonio_data]

    contexto = {
        'labels': labels, 'data': data,
        'patrimonio_atual': patrimonio_data[-1]['valor'] if patrimonio_data else 0,
        'visao': visao, 'periodo': periodo, 'familia': familia,
    }
    return render(request, 'core/evolucao_patrimonio.html', contexto)