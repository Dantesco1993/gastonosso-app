from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.functional import SimpleLazyObject
from django.db import transaction
from django.db.models import Q
import logging

from core.models import Plano, Assinatura, Familia

logger = logging.getLogger(__name__)


def get_familia_for_user(user):
    """
    Resolve a Família do usuário sem usar 'membros' (campo não existente).
    Estratégia:
      A) Familia.perfil -> User
      B) Via Perfil (user.perfil, Perfil.user/Perfil.usuario) -> Familia.perfil = perfil ou perfil.familia
      C) Tentativas genéricas (perfil__user / perfil__usuario)
    """
    # A) Familia.perfil -> User
    try:
        fam = Familia.objects.filter(perfil=user).first()
        if fam:
            return fam
    except Exception:
        pass

    # B) Via model Perfil (se existir)
    try:
        from core.models import Perfil  # ajuste se seu model tiver outro nome
    except Exception:
        Perfil = None

    perfil = None
    if Perfil is not None:
        # B1) user.perfil (reverse OneToOne comum)
        if hasattr(user, "perfil"):
            try:
                perfil = user.perfil
            except Exception:
                perfil = None

        # B2) procurar Perfil que referencie o User (campo 'user' ou 'usuario')
        if perfil is None:
            for user_field in ("user", "usuario"):
                try:
                    perfil = Perfil.objects.filter(**{user_field: user}).first()
                    if perfil:
                        break
                except Exception:
                    pass

        # B3) com Perfil em mãos, tentar obter família
        if perfil is not None:
            if hasattr(perfil, "familia"):
                fam = getattr(perfil, "familia", None)
                if isinstance(fam, Familia):
                    return fam
            fam = Familia.objects.filter(perfil=perfil).first()
            if fam:
                return fam

    # C) Tentativas genéricas (perfil é outro model que referencia User)
    try:
        fam = Familia.objects.filter(Q(perfil__user=user) | Q(perfil__usuario=user)).first()
        if fam:
            return fam
    except Exception:
        pass

    return None


def _get_or_create_free_plan():
    """
    Considera como plano gratuito aquele com preco_mensal == 0.
    Se não existir, cria um 'Gratuito' (sem mexer em stripe_price_id).
    """
    plano = Plano.objects.filter(preco_mensal=0).order_by("id").first()
    if plano is None:
        plano = Plano.objects.create(
            nome="Gratuito",
            preco_mensal=0,
            # stripe_price_id=""  # descomente se o campo não aceitar NULL
        )
    return plano


def _get_assinatura_atual(user):
    """
    Garante que a FAMÍLIA do usuário autenticado tenha uma assinatura.
    - Se não existir, cria com o plano gratuito.
    - Se existir mas sem plano, corrige para o gratuito.
    Retorna a Assinatura (ou None se não houver família).
    """
    if not user.is_authenticated:
        return None

    familia = get_familia_for_user(user)
    if not familia:
        logger.warning("[assinaturas] Família não encontrada para user=%s", user.pk)
        return None

    with transaction.atomic():
        free_plan = _get_or_create_free_plan()
        assinatura, _ = Assinatura.objects.select_related("plano", "familia").get_or_create(
            familia=familia,
            defaults={"plano": free_plan},
        )
        if assinatura.plano_id is None:
            assinatura.plano = free_plan
            assinatura.save(update_fields=["plano"])
    return assinatura


@login_required
def planos(request):
    """
    Página de Planos e Assinaturas (por FAMÍLIA).
    - Garante assinatura para a família do usuário (gratuita por padrão).
    - Lista todos os planos.
    - Renderiza 'core/pagina_planos.html' com 'assinatura_atual' e 'planos'.
    """
    assinatura_atual = SimpleLazyObject(lambda: _get_assinatura_atual(request.user))
    planos_qs = Plano.objects.all().order_by("preco_mensal", "id")

    context = {
        "planos": planos_qs,
        "assinatura_atual": assinatura_atual,
        # Opcional: publicar a chave do Stripe se você for usar Stripe.js nessa página
        # "STRIPE_PUBLISHABLE_KEY": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
    }
    return render(request, "core/pagina_planos.html", context)
