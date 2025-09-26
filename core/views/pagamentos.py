import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Plano, Assinatura, Familia

@csrf_exempt
def stripe_webhook(request):
    print("\n--- Webhook do Stripe recebido! ---")
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        print(f"Evento construído com sucesso. Tipo: {event['type']}")
    except Exception as e:
        print(f"ERRO ao construir evento: {e}")
        return HttpResponse(status=400)

    # Lidando com o evento que confirma o sucesso do checkout
    if event['type'] == 'checkout.session.completed':
        print("Evento: checkout.session.completed detectado.")
        session = event['data']['object']
        
        familia_id = session.get('client_reference_id')
        stripe_subscription_id = session.get('subscription')

        print(f"ID da Família recebido do Stripe: {familia_id}")
        print(f"ID da Assinatura do Stripe: {stripe_subscription_id}")

        if not familia_id or not stripe_subscription_id:
            print("ERRO: Dados essenciais faltando no webhook.")
            return HttpResponse(status=400)

        familia = Familia.objects.filter(id=familia_id).first()
        if not familia:
            print(f"ERRO: Família com ID {familia_id} não encontrada no banco de dados.")
            return HttpResponse(status=404)
        print(f"Família encontrada no banco: '{familia.nome}'")

        plano_pago = Plano.objects.filter(preco_mensal__gt=0).first()
        if not plano_pago:
            print("ERRO: Nenhum plano pago configurado no banco de dados.")
            return HttpResponse(status=500)
        print(f"Plano pago encontrado: '{plano_pago.nome}'")

        print("Tentando executar Assinatura.objects.update_or_create...")
        try:
            assinatura, created = Assinatura.objects.update_or_create(
                familia=familia,
                defaults={
                    'plano': plano_pago,
                    'stripe_subscription_id': stripe_subscription_id,
                    'status': Assinatura.StatusAssinatura.ATIVA,
                }
            )
            print("Comando update_or_create executado com SUCESSO.")
            if created:
                print("Uma nova assinatura foi CRIADA.")
            else:
                print("Uma assinatura existente foi ATUALIZADA.")
            
            # Verificação final logo após salvar
            familia.refresh_from_db()
            print(f"VERIFICAÇÃO PÓS-SALVAMENTO:")
            print(f"  - Plano da família agora é: '{familia.assinatura.plano.nome}'")
            print(f"  - Status da assinatura: '{familia.assinatura.status}'")
            print(f"  - O plano é gratuito? {familia.assinatura.plano.is_free()}")
            print(f"  - Resultado do método has_premium(): {familia.has_premium()}")

        except Exception as e:
            print(f"ERRO CRÍTICO DURANTE O UPDATE_OR_CREATE: {e}")

    return HttpResponse(status=200)