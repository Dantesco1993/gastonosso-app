import stripe
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.forms import CustomUserCreationForm, EntrarFamiliaForm, ContaForm
from core.models import (
    Perfil,
    Familia,
    Plano,
    Assinatura,
    Categoria,
    CategoriaReceita,
    Conta,
)

# Inicializa a API do Stripe com a chave secreta (não explode se faltar em dev)
stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")


# ---------------------------------------------------------------------------
# Helpers de Planos/Assinatura (família)
# ---------------------------------------------------------------------------
def _seed_default_plans():
    """
    Garante que existam ao menos 2 planos:
      - Gratuito (preco_mensal = 0)
      - Pro (19.90)  [ajuste o preço/Stripe se desejar]
    Não duplica se já existirem.
    """
    Plano.objects.get_or_create(
        nome="Gratuito",
        defaults={"preco_mensal": Decimal("0.00"), "stripe_price_id": ""},
    )
    Plano.objects.get_or_create(
        nome="Pro",
        defaults={"preco_mensal": Decimal("19.90"), "stripe_price_id": ""},
    )


def _get_free_plan():
    plan = Plano.objects.filter(preco_mensal=Decimal("0.00")).order_by("id").first()
    if not plan:
        _seed_default_plans()
        plan = Plano.objects.filter(preco_mensal=Decimal("0.00")).order_by("id").first()
    return plan


def _ensure_family_subscription(familia: Familia) -> Assinatura | None:
    """
    Garante que a família tenha uma assinatura; se não houver, cria com plano gratuito.
    Retorna a assinatura (ou None se familia for None).
    """
    if not familia:
        return None
    with transaction.atomic():
        assinatura, _ = Assinatura.objects.select_related("plano", "familia").get_or_create(
            familia=familia,
            defaults={"plano": _get_free_plan()},
        )
        if assinatura.plano_id is None:
            assinatura.plano = _get_free_plan()
            assinatura.save(update_fields=["plano"])
        return assinatura


def _get_or_create_perfil(user):
    """
    Garante que o usuário possua Perfil (evita DoesNotExist ao acessar user.perfil).
    """
    perfil, _ = Perfil.objects.get_or_create(user=user)
    return perfil


# ---------------------------------------------------------------------------
# Auth / Onboarding / Landing
# ---------------------------------------------------------------------------
def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # garante Perfil desde o cadastro
            _get_or_create_perfil(user)
            login(request, user)
            messages.success(request, f"Cadastro realizado com sucesso! Bem-vindo(a), {user.username}.")
            return redirect("primeiros_passos")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/register.html", {"form": form})


def landing_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "core/landing_page.html")


@login_required
def primeiros_passos(request):
    # evita erro caso o usuário ainda não tenha Perfil
    perfil = _get_or_create_perfil(request.user)

    if getattr(perfil, "primeiro_acesso_concluido", False):
        return redirect("dashboard")

    etapa = getattr(perfil, "etapa_onboarding", 1)
    familia = getattr(perfil, "familia", None)

    # Etapa 1: Família
    if etapa == 1:
        form_entrar = EntrarFamiliaForm()
        if request.method == "POST":
            if "criar_familia" in request.POST:
                nome_familia = request.POST.get("nome_familia") or ""
                nome_familia = nome_familia.strip()
                if nome_familia:
                    with transaction.atomic():
                        nova_familia = Familia.objects.create(nome=nome_familia)
                        perfil.familia = nova_familia
                        perfil.etapa_onboarding = 2
                        perfil.save(update_fields=["familia", "etapa_onboarding"])
                        _ensure_family_subscription(nova_familia)  # assinatura gratuita
                    messages.success(
                        request, f'Família "{nome_familia}" criada! Agora vamos criar algumas categorias.'
                    )
                    return redirect("primeiros_passos")
                else:
                    messages.error(request, "Informe um nome para a família.")

            elif "entrar_familia" in request.POST:
                form_entrar = EntrarFamiliaForm(request.POST)
                if form_entrar.is_valid():
                    codigo = form_entrar.cleaned_data["codigo_convite"]
                    try:
                        familia_para_entrar = Familia.objects.get(codigo_convite=codigo)
                        with transaction.atomic():
                            perfil.familia = familia_para_entrar
                            perfil.etapa_onboarding = 2
                            perfil.save(update_fields=["familia", "etapa_onboarding"])
                            _ensure_family_subscription(familia_para_entrar)  # assinatura gratuita
                        messages.success(request, f'Você entrou na família "{familia_para_entrar.nome}"!')
                        return redirect("primeiros_passos")
                    except Familia.DoesNotExist:
                        messages.error(request, "Código de convite inválido.")

        contexto = {"etapa": etapa, "form_entrar": form_entrar}
        return render(request, "core/primeiros_passos.html", contexto)

    # Etapa 2: Categorias
    elif etapa == 2:
        if request.method == "POST":
            if "add_categoria_despesa" in request.POST:
                nome = (request.POST.get("nome") or "").strip()
                if nome and familia:
                    Categoria.objects.create(familia=familia, nome=nome)
            elif "add_categoria_receita" in request.POST:
                nome = (request.POST.get("nome") or "").strip()
                if nome and familia:
                    CategoriaReceita.objects.create(familia=familia, nome=nome)
            elif "pular_etapa" in request.POST:
                perfil.etapa_onboarding = 3
                perfil.save(update_fields=["etapa_onboarding"])
            return redirect("primeiros_passos")

        contexto = {
            "etapa": etapa,
            "categorias": Categoria.objects.filter(familia=familia),
            "categorias_receita": CategoriaReceita.objects.filter(familia=familia),
        }
        return render(request, "core/primeiros_passos.html", contexto)

    # Etapa 3: Contas
    elif etapa == 3:
        if request.method == "POST":
            if "add_conta" in request.POST and familia:
                form_conta = ContaForm(request.POST)
                if form_conta.is_valid():
                    conta = form_conta.save(commit=False)
                    conta.familia = familia
                    conta.save()
            return redirect("primeiros_passos")

        contexto = {
            "etapa": etapa,
            "contas": Conta.objects.filter(familia=familia) if familia else [],
            "form_conta": ContaForm(),
        }
        return render(request, "core/primeiros_passos.html", contexto)

    return redirect("concluir_primeiros_passos")


@login_required
def concluir_primeiros_passos(request):
    if request.method == "POST":
        perfil = _get_or_create_perfil(request.user)
        perfil.primeiro_acesso_concluido = True
        perfil.save(update_fields=["primeiro_acesso_concluido"])
        messages.success(request, "Configuração inicial concluída! Bem-vindo(a) ao seu Dashboard.")
        return redirect("dashboard")
    return redirect("primeiros_passos")


@login_required
def redirect_apos_login(request):
    perfil = _get_or_create_perfil(request.user)
    if not getattr(perfil, "primeiro_acesso_concluido", False):
        return redirect("primeiros_passos")
    else:
        return redirect("dashboard")


# ---------------------------------------------------------------------------
# Planos / Assinatura (página e checkout)
# ---------------------------------------------------------------------------
@login_required
def pagina_planos(request):
    """
    Versão compatível com templates antigos.
    - Garante seed dos planos
    - Garante assinatura (por família) com plano gratuito por padrão
    - Envia 'planos' e 'assinatura_atual' para o template
    """
    if not Plano.objects.exists():
        _seed_default_plans()

    perfil = _get_or_create_perfil(request.user)
    familia = getattr(perfil, "familia", None)
    assinatura_atual = _ensure_family_subscription(familia) if familia else None

    planos = Plano.objects.all().order_by("preco_mensal", "id")
    contexto = {
        "planos": planos,
        "assinatura_atual": assinatura_atual,
        # opcional: expor publishable key se for usar Stripe.js
        # "STRIPE_PUBLISHABLE_KEY": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
    }
    return render(request, "core/pagina_planos.html", contexto)


@login_required
@require_POST
def criar_checkout_session(request, plano_id: int):
    """
    Versão compatível com rotas antigas (POST).
    Preferencialmente use a view `criar_sessao_checkout` de core/views/planos.py,
    mas esta função mantém compatibilidade caso sua rota aponte aqui.
    """
    plano = get_object_or_404(Plano, id=plano_id)
    perfil = _get_or_create_perfil(request.user)
    familia = getattr(perfil, "familia", None)

    if not familia:
        messages.error(request, "Você precisa criar ou pertencer a uma família para assinar um plano.")
        return redirect("planos")

    # Não permita checkout para plano gratuito ou sem price_id configurado
    if plano.preco_mensal == 0 or not getattr(plano, "stripe_price_id", ""):
        messages.info(request, "Plano gratuito já está disponível, ou falta configurar o preço do Stripe.")
        return redirect("planos")

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[{"price": plano.stripe_price_id, "quantity": 1}],
            mode="subscription",
            client_reference_id=str(familia.id),  # usado no webhook
            success_url=request.build_absolute_uri(reverse("sucesso")),
            cancel_url=request.build_absolute_uri(reverse("planos")),
        )
        # Redireciona para o Stripe (HTTP 303)
        response = redirect(checkout_session.url)
        response.status_code = 303
        return response
    except Exception as e:
        messages.error(request, f"Não foi possível iniciar o checkout. Erro: {e}")
        return redirect("planos")
