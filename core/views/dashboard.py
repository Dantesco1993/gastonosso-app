from decimal import Decimal
from datetime import date

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.shortcuts import render
from dateutil.relativedelta import relativedelta

from core.models import (
    Perfil, Conta, Receita, Despesa, CartaoDeCredito,
    MetaFinanceira, Investimento
)

@login_required
def dashboard(request):
    user = request.user
    # garante Perfil (evita DoesNotExist)
    perfil, _ = Perfil.objects.get_or_create(user=user)
    familia = getattr(perfil, "familia", None)
    hoje = date.today()

    # ---- filtros da UI ----
    visao = request.GET.get("visao", "individual")          # 'individual' | 'conjunto'
    periodo = request.GET.get("periodo", "realizado")       # 'realizado' | 'projetado'

    # checa premium
    has_premium = (familia and callable(getattr(familia, "has_premium", None)) and familia.has_premium()) or False
    if visao == "conjunto" and (not familia or not has_premium):
        visao = "individual"

    # define conjunto de usuários
    if visao == "individual" or not familia:
        usuarios_qs = User.objects.filter(pk=user.pk)
    else:
        usuarios_qs = User.objects.filter(perfil__familia=familia)

    # ---- querysets base (nunca None) ----
    if familia:
        contas = Conta.objects.filter(familia=familia).order_by("nome")
        cartoes = CartaoDeCredito.objects.filter(familia=familia)
        investimentos = Investimento.objects.filter(familia=familia)
        metas = MetaFinanceira.objects.filter(familia=familia).order_by("-valor_atual")[:3]
    else:
        contas = Conta.objects.none()
        cartoes = CartaoDeCredito.objects.none()
        investimentos = Investimento.objects.none()
        metas = MetaFinanceira.objects.none()

    data_limite = (hoje + relativedelta(months=6)) if periodo == "projetado" else hoje

    # ---- saldos por conta ----
    saldos_por_conta = {
        c.id: c.get_saldo_atual(usuarios=usuarios_qs, data_base=data_limite)
        for c in contas
    }
    saldo_total_contas = sum(saldos_por_conta.values(), Decimal("0"))

    # ---- totais do mês ----
    receitas_mes = (
        Receita.objects.filter(
            user__in=usuarios_qs,
            data__year=hoje.year, data__month=hoje.month, data__lte=hoje
        ).aggregate(total=Sum("valor"))["total"] or Decimal("0")
    )
    despesas_caixa_mes = (
        Despesa.objects.filter(
            user__in=usuarios_qs, conta__isnull=False,
            data__year=hoje.year, data__month=hoje.month, data__lte=hoje
        ).aggregate(total=Sum("valor"))["total"] or Decimal("0")
    )
    despesas_cartao_mes = (
        Despesa.objects.filter(
            user__in=usuarios_qs, cartao__isnull=False,
            data__year=hoje.year, data__month=hoje.month, data__lte=hoje
        ).aggregate(total=Sum("valor"))["total"] or Decimal("0")
    )
    gastos_totais_mes = despesas_caixa_mes + despesas_cartao_mes
    balanco_caixa_mes = receitas_mes - despesas_caixa_mes

    # ---- faturas abertas ----
    faturas_abertas = []
    for c in cartoes:
        info = c.get_fatura_aberta(usuarios=usuarios_qs)
        total = (info or {}).get("total", Decimal("0"))
        faturas_abertas.append({"cartao": c, "total": total})

    # ---- patrimônio ----
    valor_investido = investimentos.aggregate(total=Sum("valor_atual"))["total"] or Decimal("0")
    divida_cartoes = sum((f["total"] for f in faturas_abertas), Decimal("0"))
    saldo_contas_realizado = sum(
        (c.get_saldo_atual(usuarios=usuarios_qs) for c in contas),
        Decimal("0"),
    )
    patrimonio_liquido = (saldo_contas_realizado + valor_investido) - divida_cartoes

    # ---- gráfico pizza: top categorias do mês ----
    gastos_mes_categoria = (
        Despesa.objects.filter(
            user__in=usuarios_qs, data__year=hoje.year, data__month=hoje.month
        )
        .values("categoria__nome")
        .annotate(total=Sum("valor"))
        .order_by("-total")[:5]
    )
    # construímos uma lista de pares para evitar filtro 'index' no template
    gastos_pie = [
        {
            "label": (g["categoria__nome"] or "Sem categoria"),
            "value": float(g["total"]),
        }
        for g in gastos_mes_categoria
    ]

    contexto = {
        # coleções
        "contas": contas,
        "cartoes": cartoes,
        "investimentos": investimentos,
        "metas": metas,

        # saldos e totais
        "saldos_por_conta": saldos_por_conta,
        "saldo_total_contas": saldo_total_contas,
        "balanco_caixa_mes": balanco_caixa_mes,
        "receitas_mes": receitas_mes,
        "despesas_caixa_mes": despesas_caixa_mes,
        "despesas_cartao_mes": despesas_cartao_mes,
        "gastos_totais_mes": gastos_totais_mes,
        "faturas": faturas_abertas,
        "patrimonio_liquido": patrimonio_liquido,

        # gráfico (sem filtros custom no template)
        "gastos_pie": gastos_pie,

        # UI
        "visao": visao,
        "periodo": periodo,
        "familia": familia,
        "data_projecao": data_limite,
        "has_premium_access": has_premium,

        # toggles
        "show_family_toggle": bool(familia),
        "family_toggle_enabled": bool(familia and has_premium),
        "current_params": request.GET.urlencode(),
    }
    return render(request, "core/dashboard.html", contexto)
