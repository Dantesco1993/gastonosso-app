from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required # <<< IMPORTAÇÃO ADICIONADA
from core.forms import CustomUserCreationForm
from core.models import Familia, Perfil, Categoria, CategoriaReceita, Conta
from core.forms import EntrarFamiliaForm, CategoriaReceitaForm, ContaForm

def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # Redireciona para o tutorial em vez do dashboard
            return redirect("primeiros_passos") 
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/register.html", {"form": form})

# core/views/auth.py
def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/landing_page.html') # <--- NOME COMPLETO E CORRETO

@login_required
def primeiros_passos(request):
    perfil = request.user.perfil
    if perfil.primeiro_acesso_concluido:
        return redirect('dashboard')

    etapa = perfil.etapa_onboarding
    familia = perfil.familia

    # --- Lógica da Etapa 1: Família ---
    if etapa == 1:
        form_entrar = EntrarFamiliaForm()
        if request.method == 'POST':
            if 'criar_familia' in request.POST:
                nome_familia = request.POST.get('nome_familia')
                if nome_familia:
                    nova_familia = Familia.objects.create(nome=nome_familia)
                    perfil.familia = nova_familia
                    perfil.etapa_onboarding = 2 # Avança para a próxima etapa
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
                        perfil.etapa_onboarding = 2 # Avança para a próxima etapa
                        perfil.save()
                        messages.success(request, f'Você entrou na família "{familia_para_entrar.nome}"!')
                        return redirect('primeiros_passos')
                    except Familia.DoesNotExist:
                        messages.error(request, 'Código de convite inválido.')
        
        contexto = {'etapa': etapa, 'form_entrar': form_entrar}
        return render(request, 'core/primeiros_passos.html', contexto)

    # --- Lógica da Etapa 2: Categorias ---
    elif etapa == 2:
        if request.method == 'POST':
            if 'add_categoria_despesa' in request.POST:
                nome = request.POST.get('nome')
                Categoria.objects.create(familia=familia, nome=nome)
            elif 'add_categoria_receita' in request.POST:
                nome = request.POST.get('nome')
                CategoriaReceita.objects.create(familia=familia, nome=nome)
            elif 'pular_etapa' in request.POST:
                perfil.etapa_onboarding = 3 # Avança para a próxima etapa
                perfil.save()
            return redirect('primeiros_passos')

        contexto = {
            'etapa': etapa,
            'categorias': Categoria.objects.filter(familia=familia),
            'categorias_receita': CategoriaReceita.objects.filter(familia=familia)
        }
        return render(request, 'core/primeiros_passos.html', contexto)
    
    # --- Lógica da Etapa 3: Contas ---
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

    # Se a etapa for desconhecida, apenas redireciona para o final
    return redirect('concluir_primeiros_passos')

@login_required
def concluir_primeiros_passos(request):
    if request.method == 'POST':
        perfil = request.user.perfil
        perfil.primeiro_acesso_concluido = True
        perfil.save()
        messages.success(request, 'Configuração inicial concluída! Bem-vindo(a) ao seu Dashboard.')
        return redirect('dashboard')
    
    # Se não for POST, apenas redireciona
    return redirect('primeiros_passos')

@login_required
def redirect_apos_login(request):
    if request.user.perfil.primeiro_acesso_concluido:
        return redirect('dashboard')
    else:
        return redirect('primeiros_passos')