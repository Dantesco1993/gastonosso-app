import logging
import stripe

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from django.core.cache import cache  # opcional: para idempotência
from core.models import Plano, Assinatura, Familia

logger = logging.getLogger(__name__)

# Configure a API key (ou faça isso no settings.py)
stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")


def _get_free_plan():
    """Retorna (ou cria) o plano gratuito."""
    plano = Plano.objects.filter(preco_mensal=0).order_by("id").first()
    if not plano:
        plano = Plano.objects.create(nome="Gratuito", preco_mensal=0, stripe_price_id="")
    return plano


def _ativar_assinatura(familia: Familia, stripe_subscription_id: str, plano: Plano | None):
    """
    Ativa/atualiza a assinatura da família. Se não achar plano pago correspondente,
    mantém o plano atual ou cai para gratuito (conforme regra).
    """
    if plano is None:
        # fallback: primeira opção é manter o plano atual; se não houver, gratuito
        plano_atual = getattr(getattr(familia, "assinatura", None), "plano", None)
        plano = plano_atual or _get_free_plan()

    assinatura, _ = Assinatura.objects.update_or_create(
        familia=familia,
        defaults={
            "plano": plano,
            "stripe_subscription_id": stripe_subscription_id,
            "status": Assinatura.StatusAssinatura.ATIVA,
        },
    )
    return assinatura


def _cancelar_assinatura(assinatura: Assinatura, downgrader_para_gratuito: bool = True):
    """
    Cancela assinatura localmente. Opcionalmente, muda o plano para o gratuito.
    """
    assinatura.status = Assinatura.StatusAssinatura.CANCELADA
    updates = ["status"]

    if downgrader_para_gratuito:
        free = _get_free_plan()
        assinatura.plano = free
        updates.append("plano")

    assinatura.save(update_fields=updates)
    return assinatura


def _resolver_plano_por_price_id(price_id: str) -> Plano | None:
    """
    Encontra um Plano cujo stripe_price_id corresponda ao price_id do Stripe.
    """
    if not price_id:
        return None
    return Plano.objects.filter(stripe_price_id=price_id).first()


def _retrieve_session_with_expand(session_id: str) -> dict | None:
    """
    Busca a Checkout Session com expansões suficientes para ler o price_id do item.
    """
    try:
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=["line_items.data.price.product", "subscription", "customer"],
        )
        return session
    except Exception as e:
        logger.warning("Falha ao recuperar session %s: %s", session_id, e)
        return None


@csrf_exempt
def stripe_webhook(request):
    # ---------- Segurança básica ----------
    payload = request.body  # bytes
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET não configurado.")
        return HttpResponse(status=500)

    if not sig_header:
        logger.warning("Header HTTP_STRIPE_SIGNATURE ausente.")
        return HttpResponse(status=400)

    # ---------- Verificação de assinatura ----------
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=webhook_secret,
        )
    except stripe.error.SignatureVerificationError as e:
        logger.warning("Assinatura inválida do webhook: %s", e)
        return HttpResponse(status=400)
    except ValueError as e:
        logger.warning("Payload inválido no webhook: %s", e)
        return HttpResponse(status=400)
    except Exception as e:
        logger.exception("Erro inesperado ao construir evento: %s", e)
        return HttpResponse(status=400)

    event_id = event.get("id")
    event_type = event.get("type")
    logger.info("Stripe webhook recebido: %s (id=%s)", event_type, event_id)

    # ---------- Idempotência básica (opcional) ----------
    # Se você tiver cache configurado, evita processar o mesmo evento várias vezes
    if cache and event_id:
        cache_key = f"stripe_evt_{event_id}"
        if cache.get(cache_key):
            logger.info("Evento %s já processado — ignorando.", event_id)
            return HttpResponse(status=200)
        # marca por 1 hora
        cache.set(cache_key, True, timeout=3600)

    # ---------- Manipulação dos eventos ----------
    try:
        # ============================================================
        # 1) CHECKOUT CONCLUÍDO (sessão criada, primeira cobrança ok)
        # ============================================================
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            session_id = session.get("id")
            familia_id = session.get("client_reference_id")
            stripe_subscription_id = session.get("subscription")

            if not familia_id or not stripe_subscription_id:
                logger.warning("Dados faltando no checkout.session.completed")
                return HttpResponse(status=400)

            familia = Familia.objects.filter(id=familia_id).first()
            if not familia:
                logger.warning("Família %s não encontrada.", familia_id)
                return HttpResponse(status=404)

            # Tentar recuperar price_id do item comprado
            price_id = None
            # Em muitos casos vem em session['display_items'] (legado) ou precisa expand
            # Melhor caminho: retrieve com expand:
            sess_full = _retrieve_session_with_expand(session_id)
            if sess_full and sess_full.get("line_items") and sess_full["line_items"]["data"]:
                li = sess_full["line_items"]["data"][0]
                price_id = li.get("price", {}).get("id")

            plano = _resolver_plano_por_price_id(price_id)
            assinatura = _ativar_assinatura(familia, stripe_subscription_id, plano)

            logger.info(
                "Assinatura %s ativada para família %s (plano=%s).",
                assinatura.pk,
                familia.id,
                assinatura.plano.nome,
            )

        # ============================================================
        # 2) FATURA PAGA (confirmação financeira da assinatura)
        # ============================================================
        elif event_type == "invoice.paid":
            invoice = event["data"]["object"]
            sub_id = invoice.get("subscription")
            if sub_id:
                assinatura = Assinatura.objects.filter(stripe_subscription_id=sub_id).select_related("familia", "plano").first()
                if assinatura:
                    # garante status ativa
                    if assinatura.status != Assinatura.StatusAssinatura.ATIVA:
                        assinatura.status = Assinatura.StatusAssinatura.ATIVA
                        assinatura.save(update_fields=["status"])
                        logger.info("Assinatura %s marcada como ATIVA por invoice.paid.", assinatura.pk)

        # ============================================================
        # 3) ASSINATURA ATUALIZADA/DELETADA (ciclo de vida)
        # ============================================================
        elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
            sub = event["data"]["object"]
            sub_id = sub.get("id")
            status_stripe = sub.get("status")  # 'active', 'canceled', 'past_due', etc.

            assinatura = Assinatura.objects.filter(stripe_subscription_id=sub_id).select_related("familia", "plano").first()
            if assinatura:
                if event_type == "customer.subscription.deleted" or status_stripe in ("canceled", "unpaid", "incomplete_expired"):
                    _cancelar_assinatura(assinatura, downgrader_para_gratuito=True)
                    logger.info("Assinatura %s cancelada (downgrade).", assinatura.pk)
                else:
                    # Mantém ATIVA para 'active', 'trialing', 'past_due' (ajuste de regra se quiser)
                    if assinatura.status != Assinatura.StatusAssinatura.ATIVA:
                        assinatura.status = Assinatura.StatusAssinatura.ATIVA
                        assinatura.save(update_fields=["status"])
                        logger.info("Assinatura %s marcada como ATIVA por %s.", assinatura.pk, event_type)

        # ============================================================
        # Outros eventos podem ser tratados aqui conforme necessidade
        # ============================================================

    except Exception as e:
        # Evite 500: o Stripe vai reentregar. Só retorne 400/500 se for realmente necessário.
        logger.exception("Erro processando evento %s: %s", event_type, e)
        return HttpResponse(status=400)

    # Sempre 2xx quando processado com sucesso
    return HttpResponse(status=200)
