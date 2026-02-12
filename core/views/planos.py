# core/views/planos.py
import logging
import stripe

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django.db.models import Q

from core.models import Plano, Familia

logger = logging.getLogger(__name__)

# Configure a chave secreta do Stripe (também pode ser feita no settings.py)
stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")


def get_familia_for_user(user):
    """
    Resolve a Família do usuário sem usar 'membros' (campo que não existe em Familia).

    Estratégia:
      A) Tenta se 'perfil' de Familia aponta direto para User -> Familia.objects.filter(perfil=user)
      B) Se existir model Perfil:
           - tenta user.perfil
           - tenta Perfil.objects.filter(user=user) ou Perfil.objects.filter(usuario=user)
           - com o Perfil encontrado, tenta: perfil.familia (se existir) OU Familia.objects.filter(perfil=perfil)
      C) Tenta 'perfil__user' ou 'perfil__usuario' (quando 'perfil' é outro model que referencia User)
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
            # Perfil -> familia (atributo direto)
            if hasattr(perfil, "familia"):
                fam = getattr(perfil, "familia", None)
                if isinstance(fam, Familia):
                    return fam
            # Familia -> perfil (FK)
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


@method_decorator(login_required, name="dispatch")
class PlanosView(TemplateView):
    """
    Página de listagem de planos. Mostra o plano atual (se houver)
    e renderiza o template `templates/core/pagina_planos.html`.
    """
    template_name = "core/pagina_planos.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["planos"] = Plano.objects.all().order_by("preco_mensal", "nome")

        familia = get_familia_for_user(self.request.user)
        ctx["assinatura_atual"] = getattr(familia, "assinatura", None) if familia else None

        # Opcional: caso queira usar Stripe.js no futuro
        ctx["STRIPE_PUBLISHABLE_KEY"] = getattr(settings, "STRIPE_PUBLISHABLE_KEY", "")
        return ctx


@login_required
@require_POST
def criar_sessao_checkout(request, plano_id: int):
    """
    Cria uma Stripe Checkout Session (modo assinatura) e redireciona o usuário
    para a URL do Stripe (HTTP 303). Recebe o plano pela URL.
    """
    # 1) Resolver Família do usuário
    familia = get_familia_for_user(request.user)
    if not familia:
        msg = ("Não foi possível identificar sua Família. "
               "Verifique o vínculo com Perfil/Família no banco de dados.")
        logger.warning("[checkout] Família não encontrada para user=%s", request.user.pk)
        return HttpResponseBadRequest(msg)

    # 2) Obter o Plano
    try:
        plano = Plano.objects.get(id=plano_id)
    except Plano.DoesNotExist:
        msg = "Plano inválido."
        logger.warning("[checkout] Plano inválido. plano_id=%s", plano_id)
        return HttpResponseBadRequest(msg)

    # 3) Obter o price_id do Stripe
    # Recomenda-se um campo no model Plano, por ex.: stripe_price_id = CharField(...)
    price_id = getattr(plano, "stripe_price_id", None)
    if not price_id:
        # Fallback: variável de settings (ex.: STRIPE_DEFAULT_PRICE_ID) — opcional
        price_id = getattr(settings, "STRIPE_DEFAULT_PRICE_ID", "")
    if not price_id:
        msg = ("Price ID do Stripe não configurado para este plano. "
               "Preencha 'stripe_price_id' no Plano ou STRIPE_DEFAULT_PRICE_ID no settings.")
        logger.warning("[checkout] Price ID ausente para plano_id=%s", plano_id)
        return HttpResponseBadRequest(msg)

    # 4) Criar a sessão de checkout
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            client_reference_id=str(familia.id),  # usado pelo webhook para vincular a Família
            success_url=request.build_absolute_uri("/sucesso/"),
            cancel_url=request.build_absolute_uri("/cancelado/"),
        )
    except Exception as e:
        logger.exception("[checkout] Erro ao criar sessão Stripe: %s", e)
        # Em produção, evite retornar detalhes do erro para o usuário.
        return HttpResponseBadRequest("Erro ao criar sessão no Stripe.")

    # 5) Redirecionar para a URL do Stripe (recomendado)
    resp = redirect(session.url)
    resp.status_code = 303  # redirect após POST
    return resp


class SucessoView(TemplateView):
    """
    Página exibida após o sucesso no Stripe Checkout.
    """
    template_name = "core/sucesso.html"


class CanceladoView(TemplateView):
    """
    Página exibida quando o usuário cancela no Stripe Checkout.
    """
    template_name = "core/cancelado.html"


# ---------------------------
# Endpoint de diagnóstico
# ---------------------------
@login_required
def debug_checkout_context(request):
    """
    Retorna dados úteis para depurar o fluxo de checkout:
      - user_id
      - familia_id / familia_nome (resolvidos por get_familia_for_user)
      - lista de planos com seus price_ids (stripe_price_id)
    """
    fam = get_familia_for_user(request.user)
    planos = list(Plano.objects.values("id", "nome", "stripe_price_id").order_by("preco_mensal", "nome"))
    return JsonResponse({
        "user_id": request.user.id,
        "familia_id": getattr(fam, "id", None),
        "familia_nome": getattr(fam, "nome", None),
        "planos": planos,
    })
