import stripe
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth.models import User

from core.forms import CustomUserCreationForm, EntrarFamiliaForm, ContaForm
from core.models import Perfil, Familia, Plano, Assinatura, Categoria, CategoriaReceita, Conta

# Inicializa a API do Stripe com a chave secreta
stripe.api_key = settings.STRIPE_SECRET_KEY

def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Cadastro realizado com sucesso! Bem-vindo(a), {user.username}.")
            return redirect("primeiros_passos")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/register.html", {"form": form})

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/landing_page.html')

@login_required
def primeiros_passos(request):
    perfil = request.user.perfil
    if perfil.primeiro_acesso_concluido:
        return redirect('dashboard')

    etapa = perfil.etapa_onboarding
    familia = perfil.familia

    # Etapa 1: Família
    if etapa == 1:
        form_entrar = EntrarFamiliaForm()
        if request.method == 'POST':
            if 'criar_familia' in request.POST:
                nome_familia = request.POST.get('nome_familia')
                if nome_familia:
                    nova_familia = Familia.objects.create(nome=nome_familia)
                    perfil.familia = nova_familia
                    perfil.etapa_onboarding = 2
                    perfil.save()
                    messages.success(request, f'Família "{nome_familia}" criada! Agora vamos criar algumas categorias.')
                    return redirect('primeiros_passos')
            
            elif 'entrar_familia' in request.POST:
                form_entrar = EntrarFamiliaForm(request.POST)
                if form_entrar.is_valid():
                    codigo = form_entrar.cleaned_data['codigo_convite']
                    try:
                        familia_para_entrar = Familia.objects.get(codigo_convite=codigo)
                        perfil.familia = familia_para_entrar
                        perfil.etapa_onboarding = 2
                        perfil.save()
                        messages.success(request, f'Você entrou na família "{familia_para_entrar.nome}"!')
                        return redirect('primeiros_passos')
                    except Familia.DoesNotExist:
                        messages.error(request, 'Código de convite inválido.')
        
        contexto = {'etapa': etapa, 'form_entrar': form_entrar}
        return render(request, 'core/primeiros_passos.html', contexto)

    # Etapa 2: Categorias
    elif etapa == 2:
        if request.method == 'POST':
            if 'add_categoria_despesa' in request.POST:
                nome = request.POST.get('nome')
                if nome: Categoria.objects.create(familia=familia, nome=nome)
            elif 'add_categoria_receita' in request.POST:
                nome = request.POST.get('nome')
                if nome: CategoriaReceita.objects.create(familia=familia, nome=nome)
            elif 'pular_etapa' in request.POST:
                perfil.etapa_onboarding = 3
                perfil.save()
            return redirect('primeiros_passos')

        contexto = {
            'etapa': etapa,
            'categorias': Categoria.objects.filter(familia=familia),
            'categorias_receita': CategoriaReceita.objects.filter(familia=familia)
        }
        return render(request, 'core/primeiros_passos.html', contexto)
    
    # Etapa 3: Contas
    elif etapa == 3:
        if request.method == 'POST':
            if 'add_conta' in request.POST:
                form_conta = ContaForm(request.POST)
                if form_conta.is_valid():
                    conta = form_conta.save(commit=False)
                    conta.familia = familia
                    conta.save()
            return redirect('primeiros_passos')

        contexto = {
            'etapa': etapa,
            'contas': Conta.objects.filter(familia=familia),
            'form_conta': ContaForm()
        }
        return render(request, 'core/primeiros_passos.html', contexto)

    return redirect('concluir_primeiros_passos')

@login_required
def concluir_primeiros_passos(request):
    if request.method == 'POST':
        perfil = request.user.perfil
        perfil.primeiro_acesso_concluido = True
        perfil.save()
        messages.success(request, 'Configuração inicial concluída! Bem-vindo(a) ao seu Dashboard.')
        return redirect('dashboard')
    return redirect('primeiros_passos')

@login_required
def redirect_apos_login(request):
    if not request.user.perfil.primeiro_acesso_concluido:
        return redirect('primeiros_passos')
    else:
        return redirect('dashboard')

@login_required
def pagina_planos(request):
    planos = Plano.objects.all().order_by('preco_mensal')
    assinatura_atual = None
    if request.user.perfil.familia:
        try:
            assinatura_atual = request.user.perfil.familia.assinatura
        except Assinatura.DoesNotExist:
            assinatura_atual = None
    contexto = {'planos': planos, 'assinatura_atual': assinatura_atual}
    return render(request, 'core/pagina_planos.html', contexto)

@login_required
def criar_checkout_session(request, plano_id):
    plano = get_object_or_404(Plano, id=plano_id)
    familia = request.user.perfil.familia

    if not familia:
        messages.error(request, "Você precisa criar ou pertencer a uma família para assinar um plano.")
        return redirect('gerenciar_familia')

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[{'price': plano.stripe_price_id, 'quantity': 1}],
            mode='subscription',
            client_reference_id=familia.id,
            success_url=request.build_absolute_uri(reverse('dashboard')) + '?upgrade=sucesso',
            cancel_url=request.build_absolute_uri(reverse('pagina_planos')),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        messages.error(request, f"Não foi possível iniciar o checkout. Erro: {e}")
        return redirect('pagina_planos')