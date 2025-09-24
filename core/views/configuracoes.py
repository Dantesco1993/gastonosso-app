from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db.utils import IntegrityError

from core.models import Categoria, CategoriaReceita, Conta, CartaoDeCredito, Familia, Perfil
from core.forms import (
    CategoriaForm, CategoriaReceitaForm, ContaForm, CartaoDeCreditoForm, EntrarFamiliaForm
)

@login_required
def configuracoes(request):
    user = request.user
    familia = user.perfil.familia

    if request.method == 'POST':
        if not familia:
            messages.error(request, "Você precisa criar ou pertencer a uma família para adicionar itens.")
            return redirect('gerenciar_familia')
        
        active_tab = request.POST.get('active_tab', 'cat-despesas')
        
        if 'form_categoria' in request.POST:
            # CORREÇÃO: Passa a família também no POST para a validação funcionar
            form = CategoriaForm(request.POST, familia=familia)
            if form.is_valid():
                categoria = form.save(commit=False)
                categoria.familia = familia
                categoria.save()
                messages.success(request, 'Categoria de despesa salva com sucesso!')
        
        elif 'form_categoria_receita' in request.POST:
            form = CategoriaReceitaForm(request.POST)
            if form.is_valid():
                # CORREÇÃO: Adiciona a lógica de salvar com 'commit=False'
                cat = form.save(commit=False)
                cat.familia = familia
                cat.save()
                messages.success(request, 'Categoria de receita adicionada!')
        
        elif 'form_conta' in request.POST:
            form = ContaForm(request.POST)
            if form.is_valid():
                conta = form.save(commit=False)
                conta.familia = familia
                conta.save()
                messages.success(request, 'Conta adicionada com sucesso!')

        elif 'form_cartao' in request.POST:
            form = CartaoDeCreditoForm(request.POST)
            if form.is_valid():
                cartao = form.save(commit=False)
                cartao.familia = familia
                cartao.save()
                messages.success(request, 'Cartão de crédito adicionado!')

        # Se o formulário for inválido, o redirect não acontece e a página é re-renderizada
        # com os erros graças ao crispy-forms.
        # Se for válido, redireciona.
        if form.is_valid():
            return redirect(f"{reverse('configuracoes')}?active_tab={active_tab}")
    
    # Lógica para GET
    categorias_principais = Categoria.objects.filter(familia=familia, categoria_mae__isnull=True).prefetch_related('subcategorias') if familia else []
    
    active_tab_get = request.GET.get('active_tab', 'cat-despesas')
    contexto = {
        'categorias_principais': categorias_principais,
        'categorias_receita': CategoriaReceita.objects.filter(familia=familia) if familia else [],
        'contas': Conta.objects.filter(familia=familia) if familia else [],
        'cartoes': CartaoDeCredito.objects.filter(familia=familia) if familia else [],
        'form_categoria': CategoriaForm(familia=familia),
        'form_categoria_receita': CategoriaReceitaForm(),
        'form_conta': ContaForm(),
        'form_cartao': CartaoDeCreditoForm(),
        'active_tab': active_tab_get,
    }
    return render(request, 'core/configuracoes.html', contexto)

@login_required
def excluir_categoria(request, id):
    familia = request.user.perfil.familia
    categoria = get_object_or_404(Categoria, id=id, familia=familia)
    try:
        categoria.delete()
        messages.success(request, 'Categoria de despesa excluída!')
    except IntegrityError:
        messages.error(request, 'Esta categoria não pode ser excluída pois está em uso.')
    return redirect(f"{reverse('configuracoes')}?active_tab=cat-despesas")

@login_required
def excluir_categoria_receita(request, id):
    familia = request.user.perfil.familia
    categoria = get_object_or_404(CategoriaReceita, id=id, familia=familia)
    try:
        categoria.delete()
        messages.success(request, 'Categoria de receita excluída!')
    except IntegrityError:
        messages.error(request, 'Esta categoria não pode ser excluída pois está em uso.')
    return redirect(f"{reverse('configuracoes')}?active_tab=cat-receitas")

@login_required
def excluir_conta(request, id):
    familia = request.user.perfil.familia
    conta = get_object_or_404(Conta, id=id, familia=familia)
    try:
        conta.delete()
        messages.success(request, 'Conta excluída com sucesso!')
    except IntegrityError:
        messages.error(request, 'Esta conta não pode ser excluída pois possui transações.')
    return redirect(f"{reverse('configuracoes')}?active_tab=contas")

@login_required
def excluir_cartao(request, id):
    familia = request.user.perfil.familia
    cartao = get_object_or_404(CartaoDeCredito, id=id, familia=familia)
    try:
        cartao.delete()
        messages.success(request, 'Cartão excluído com sucesso!')
    except IntegrityError:
        messages.error(request, 'Este cartão não pode ser excluído pois está em uso.')
    return redirect(f"{reverse('configuracoes')}?active_tab=cartoes")

@login_required
def gerenciar_familia(request):
    perfil = request.user.perfil
    familia = perfil.familia
    form_entrar = EntrarFamiliaForm()

    if request.method == 'POST':
        if 'criar_familia' in request.POST:
            nome_familia = request.POST.get('nome_familia')
            if nome_familia:
                nova_familia = Familia.objects.create(nome=nome_familia)
                perfil.familia = nova_familia
                perfil.save()
                messages.success(request, f'Família "{nome_familia}" criada com sucesso!')
                return redirect('gerenciar_familia')
        
        elif 'entrar_familia' in request.POST:
            form_entrar = EntrarFamiliaForm(request.POST)
            if form_entrar.is_valid():
                codigo = form_entrar.cleaned_data['codigo_convite']
                try:
                    familia_para_entrar = Familia.objects.get(codigo_convite=codigo)
                    perfil.familia = familia_para_entrar
                    perfil.save()
                    messages.success(request, f'Você entrou na família "{familia_para_entrar.nome}"!')
                    return redirect('gerenciar_familia')
                except Familia.DoesNotExist:
                    messages.error(request, 'Código de convite inválido.')

    contexto = {
        'familia': familia,
        'form_entrar': form_entrar,
    }
    return render(request, 'core/gerenciar_familia.html', contexto)