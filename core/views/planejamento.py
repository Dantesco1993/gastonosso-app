from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.http import HttpResponse
from itertools import chain
from operator import attrgetter
from django.core.paginator import Paginator
from decimal import Decimal # <<< IMPORTAÇÃO ADICIONADA
from django.shortcuts import redirect

from core.models import (
    Despesa, Receita, MetaFinanceira, Categoria, Conta, Investimento, 
    AporteInvestimento, CartaoDeCredito
)
from core.forms import MetaFinanceiraForm, AporteForm

def analise_gastos(request):
    user = request.user
    familia = user.perfil.familia

    has_premium_access = familia.has_premium() if familia else False
    visao = request.GET.get('visao', 'individual')
    if visao == 'conjunto' and not has_premium_access:
        visao = 'individual'

    hoje = date.today()

    # --- Lógica de Filtros (sem alteração) ---
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    periodo = request.GET.get('periodo', 'realizado')
    visao = request.GET.get('visao', 'individual')
    agrupamento = request.GET.get('agrupamento', 'mensal')

    if data_inicio_str and data_fim_str:
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
    else:
        data_inicio = hoje - relativedelta(months=5); data_inicio = data_inicio.replace(day=1)
        data_fim = hoje

    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)

    # --- Lógica para o Gráfico de Pizza (Agrupado por Categoria Principal) ---
    gastos_agregados = []
    if familia:
        # Pega todas as categorias que não são subcategorias de ninguém (as principais)
        categorias_principais = Categoria.objects.filter(familia=familia, categoria_mae__isnull=True)
        for cat_principal in categorias_principais:
            # Pega a ID da categoria principal e de todas as suas filhas
            ids_categorias = [cat_principal.id] + list(cat_principal.subcategorias.all().values_list('id', flat=True))
            
            # Soma todas as despesas que pertencem a essa família de categorias
            total_gasto = Despesa.objects.filter(
                user__in=usuarios_a_filtrar,
                data__range=[data_inicio, data_fim],
                categoria_id__in=ids_categorias
            ).aggregate(total=Sum('valor'))['total'] or 0
            
            if total_gasto > 0:
                gastos_agregados.append({'categoria__nome': cat_principal.nome, 'total': total_gasto})
    
    gastos_por_categoria = sorted(gastos_agregados, key=lambda item: item['total'], reverse=True)
    labels_pie = [gasto['categoria__nome'] for gasto in gastos_por_categoria]
    data_pie = [float(gasto['total']) for gasto in gastos_por_categoria]
    
    # --- Lógica de Fluxo de Caixa Agrupado ---
    if agrupamento == 'semanal':
        trunc_func = TruncWeek
        date_format = "Sem %W/%Y"
    elif agrupamento == 'diario':
        trunc_func = TruncDay
        date_format = "%d/%m/%Y"
    else:
        trunc_func = TruncMonth
        date_format = "%b/%y"

    receitas = Receita.objects.filter(user__in=usuarios_a_filtrar, data__range=[data_inicio, data_fim]).annotate(periodo_agrupado=trunc_func('data')).values('periodo_agrupado').annotate(total=Sum('valor')).order_by('periodo_agrupado')
    despesas = Despesa.objects.filter(user__in=usuarios_a_filtrar, conta__isnull=False, data__range=[data_inicio, data_fim]).annotate(periodo_agrupado=trunc_func('data')).values('periodo_agrupado').annotate(total=Sum('valor')).order_by('periodo_agrupado')
    periodos = sorted(list(set([r['periodo_agrupado'] for r in receitas] + [d['periodo_agrupado'] for d in despesas])))
    labels_bar = [p.strftime(date_format) for p in periodos]
    data_receitas_bar = [float(next((item['total'] for item in receitas if item['periodo_agrupado'] == p), 0)) for p in periodos]
    data_despesas_bar = [float(next((item['total'] for item in despesas if item['periodo_agrupado'] == p), 0)) for p in periodos]

    contexto = {
        'has_premium_access': has_premium_access,
        'gastos_por_categoria': gastos_por_categoria, 'labels_pie': labels_pie, 'data_pie': data_pie, 'visao': visao,
        'periodo': periodo, 'data_inicio': data_inicio, 'data_fim': data_fim, 'familia': familia, 'labels_bar': labels_bar,
        'data_receitas_bar': data_receitas_bar, 'data_despesas_bar': data_despesas_bar, 'agrupamento': agrupamento,
    }
    return render(request, 'core/analise_gastos.html', contexto)

@login_required
def analise_drilldown_categoria(request):
    familia = request.user.perfil.familia
    categoria_mae_nome = request.GET.get('categoria_mae')
    visao = request.GET.get('visao', 'individual')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [request.user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)
        
    try:
        categoria_mae = Categoria.objects.get(familia=familia, nome=categoria_mae_nome, categoria_mae__isnull=True)
        subcategorias = categoria_mae.subcategorias.all()
        gastos = Despesa.objects.filter(user__in=usuarios_a_filtrar, data__range=[data_inicio, data_fim], categoria__in=subcategorias).values('categoria__nome').annotate(total=Sum('valor')).order_by('-total')
        labels = [g['categoria__nome'] for g in gastos]
        data = [float(g['total']) for g in gastos]
        contexto = {'categoria_mae_nome': categoria_mae_nome, 'labels': labels, 'data': data}
        return render(request, 'core/partials/_analise_drilldown_chart.html', contexto)
    except Categoria.DoesNotExist:
        return HttpResponse("")

@login_required
def orcamento_mensal(request):
    user = request.user
    familia = user.perfil.familia
    hoje = date.today()
    visao = request.GET.get('visao', 'individual')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)
    categorias_orcadas = Categoria.objects.filter(familia=familia, orcamento_mensal__gt=0) if familia else []
    dados_orcamento = []
    total_orcado = 0
    total_gasto = 0
    for categoria in categorias_orcadas:
        gasto_mes = Despesa.objects.filter(user__in=usuarios_a_filtrar, categoria=categoria, data__year=hoje.year, data__month=hoje.month).aggregate(total=Sum('valor'))['total'] or 0
        restante = categoria.orcamento_mensal - gasto_mes
        progresso = (gasto_mes / categoria.orcamento_mensal) * 100 if categoria.orcamento_mensal > 0 else 0
        dados_orcamento.append({'categoria': categoria, 'orcado': categoria.orcamento_mensal, 'gasto': gasto_mes, 'restante': restante, 'progresso': min(progresso, 100)})
        total_orcado += categoria.orcamento_mensal
        total_gasto += gasto_mes
    contexto = {
        'dados_orcamento': dados_orcamento, 'total_orcado': total_orcado,
        'total_gasto': total_gasto, 'total_restante': total_orcado - total_gasto,
        'visao': visao, 'familia': familia
    }
    return render(request, 'core/orcamento_mensal.html', contexto)

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
            categoria_aporte, _ = Categoria.objects.get_or_create(familia=familia, nome__iexact="Metas Financeiras", defaults={'nome': "Metas Financeiras"})
            Despesa.objects.create(user=user, descricao=f"Aporte para a meta: {meta.nome}", valor=valor_aporte, data=date.today(), categoria=categoria_aporte, conta=conta_origem)
            messages.success(request, 'Aporte realizado e despesa registrada com sucesso!')
    return redirect('lista_metas')

@login_required
def relatorio_transacoes(request):
    user = request.user
    familia = user.perfil.familia
    hoje = date.today()

    # --- Filtros ---
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    visao = request.GET.get('visao', 'individual')
    
    if data_inicio_str and data_fim_str:
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
    else:
        data_fim = hoje
        data_inicio = hoje - relativedelta(days=30)
    
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)
    
    # --- Consultas ao Banco de Dados ---
    receitas = Receita.objects.filter(user__in=usuarios_a_filtrar, data__range=[data_inicio, data_fim])
    despesas = Despesa.objects.filter(user__in=usuarios_a_filtrar, data__range=[data_inicio, data_fim])
    
    # --- Cálculos de Resumo ---
    total_receitas = receitas.aggregate(total=Sum('valor'))['total'] or 0
    total_despesas = despesas.aggregate(total=Sum('valor'))['total'] or 0
    saldo_periodo = total_receitas - total_despesas
    
    # --- Unindo e Ordenando as Transações ---
    transacoes_list = sorted(
        chain(receitas, despesas),
        key=attrgetter('data'),
        reverse=True
    )
    
    # --- Paginação ---
    paginator = Paginator(transacoes_list, 25) # 25 itens por página
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    contexto = {
        'page_obj': page_obj,
        'total_receitas': total_receitas,
        'total_despesas': total_despesas,
        'saldo_periodo': saldo_periodo,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'visao': visao,
        'familia': familia,
    }
    return render(request, 'core/relatorio_transacoes.html', contexto)

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
    for i in range(-6, 7):
        ponto_no_tempo = hoje + relativedelta(months=i)
        ultimo_dia_mes = ponto_no_tempo.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)
        if periodo == 'realizado' and ponto_no_tempo > hoje:
            continue
        data_limite = ultimo_dia_mes if periodo == 'projetado' else min(ultimo_dia_mes, hoje)
        contas = Conta.objects.filter(familia=familia) if familia else []
        saldo_contas = sum(c.get_saldo_atual(usuarios=usuarios_a_filtrar, data_base=data_limite) for c in contas)
        investimentos = Investimento.objects.filter(familia=familia, data_criacao__lte=data_limite) if familia else []
        valor_investido = sum(inv.aportes.filter(user__in=usuarios_a_filtrar, data__lte=data_limite).aggregate(t=Sum('valor'))['t'] or 0 for inv in investimentos)
        cartoes = CartaoDeCredito.objects.filter(familia=familia) if familia else []
        divida_cartoes = sum(c.get_fatura_aberta(usuarios=usuarios_a_filtrar, data_base=ultimo_dia_mes)['total'] for c in cartoes)
        patrimonio_liquido = (saldo_contas + valor_investido) - divida_cartoes
        patrimonio_data.append({'mes': ultimo_dia_mes.strftime('%b/%y'), 'valor': float(patrimonio_liquido)})
    labels = [item['mes'] for item in patrimonio_data]
    data = [item['valor'] for item in patrimonio_data]
    contexto = {
        'labels': labels, 'data': data,
        'patrimonio_atual': patrimonio_data[-1]['valor'] if patrimonio_data else 0,
        'visao': visao, 'periodo': periodo, 'familia': familia,
    }
    return render(request, 'core/evolucao_patrimonio.html', contexto)

@login_required
def orcamento_50_30_20(request):
    user = request.user
    familia = user.perfil.familia
    hoje = date.today()

    # Filtros de visão e data (vamos usar o mês atual para esta análise)
    visao = request.GET.get('visao', 'individual')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)

    # 1. Calcular a Renda Total do Mês
    receita_total_mes = Receita.objects.filter(
        user__in=usuarios_a_filtrar,
        data__year=hoje.year,
        data__month=hoje.month
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

    # 2. Calcular os Alvos (50/30/20)
    alvos = {
        'necessidades': receita_total_mes * Decimal('0.5'),
        'desejos': receita_total_mes * Decimal('0.3'),
        'metas': receita_total_mes * Decimal('0.2'),
    }

    # 3. Calcular os Gastos Reais por Macro-Categoria
    gastos_reais_query = Despesa.objects.filter(
        user__in=usuarios_a_filtrar,
        data__year=hoje.year,
        data__month=hoje.month
    ).values('categoria__macro_categoria').annotate(total=Sum('valor'))
    
    gastos_reais = {
        item['categoria__macro_categoria']: item['total'] for item in gastos_reais_query
    }

    # 4. Preparar dados para o template
    dados_orcamento = {
        'necessidades': {
            'nome': 'Necessidades',
            'alvo_percentual': 50,
            'alvo_valor': alvos['necessidades'],
            'gasto_real': gastos_reais.get(Categoria.MacroCategoria.NECESSIDADE, Decimal('0.00')),
        },
        'desejos': {
            'nome': 'Desejos Pessoais',
            'alvo_percentual': 30,
            'alvo_valor': alvos['desejos'],
            'gasto_real': gastos_reais.get(Categoria.MacroCategoria.DESEJO, Decimal('0.00')),
        },
        'metas': {
            'nome': 'Metas Financeiras',
            'alvo_percentual': 20,
            'alvo_valor': alvos['metas'],
            'gasto_real': gastos_reais.get(Categoria.MacroCategoria.META, Decimal('0.00')),
        }
    }
    
    for chave, valor in dados_orcamento.items():
        if valor['alvo_valor'] > 0:
            valor['progresso'] = min((valor['gasto_real'] / valor['alvo_valor']) * 100, 100)
        else:
            valor['progresso'] = 0
        valor['restante'] = valor['alvo_valor'] - valor['gasto_real']

    contexto = {
        'receita_total_mes': receita_total_mes,
        'dados_orcamento': dados_orcamento,
        'visao': visao,
        'familia': familia,
    }
    return render(request, 'core/orcamento_50_30_20.html', contexto)