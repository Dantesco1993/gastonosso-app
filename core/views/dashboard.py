from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from datetime import date
from dateutil.relativedelta import relativedelta
from itertools import chain
from operator import attrgetter
from core.models import Conta, Receita, Despesa, CartaoDeCredito

@login_required
def dashboard(request):
    hoje = date.today()
    user = request.user
    familia = user.perfil.familia
    visao = request.GET.get('visao', 'conjunto')

    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)
        
    contas = Conta.objects.filter(familia=familia) if familia else []
    cartoes = CartaoDeCredito.objects.filter(familia=familia) if familia else []
    
    saldo_total_contas = 0
    for conta in contas:
        receitas = Receita.objects.filter(user__in=usuarios_a_filtrar, conta=conta, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
        despesas = Despesa.objects.filter(user__in=usuarios_a_filtrar, conta=conta, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
        saldo_total_contas += (conta.saldo_inicial + receitas) - despesas
    
    total_receitas_mes = Receita.objects.filter(user__in=usuarios_a_filtrar, data__year=hoje.year, data__month=hoje.month, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    total_despesas_mes = Despesa.objects.filter(user__in=usuarios_a_filtrar, conta__isnull=False, data__year=hoje.year, data__month=hoje.month, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    balanco_mensal = total_receitas_mes - total_despesas_mes

    faturas_abertas = []
    for cartao in cartoes:
        if hoje.day <= cartao.dia_fechamento: data_fechamento = hoje.replace(day=cartao.dia_fechamento)
        else: data_fechamento = (hoje + relativedelta(months=1)).replace(day=cartao.dia_fechamento)
        data_inicio = (data_fechamento - relativedelta(months=1)) + relativedelta(days=1)
        despesas_cartao = Despesa.objects.filter(user__in=usuarios_a_filtrar, cartao=cartao, data__gte=data_inicio, data__lte=data_fechamento)
        total_fatura = despesas_cartao.aggregate(Sum('valor'))['valor__sum'] or 0
        faturas_abertas.append({'cartao': cartao, 'total': total_fatura})
        
    transacoes_recentes = sorted(chain(Despesa.objects.filter(user__in=usuarios_a_filtrar), Receita.objects.filter(user__in=usuarios_a_filtrar)), key=attrgetter('data'), reverse=True)[:5]

    contexto = {
        'saldo_total': saldo_total_contas, 'receitas_mes': total_receitas_mes,
        'despesas_mes': total_despesas_mes, 'balanco_mensal': balanco_mensal,
        'faturas': faturas_abertas, 'transacoes_recentes': transacoes_recentes,
        'visao': visao, 'familia': familia
    }
    return render(request, 'core/dashboard.html', contexto)