import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from dateutil.relativedelta import relativedelta
from django.core.paginator import Paginator # IMPORTAR PAGINATOR

from core.models import Despesa, Receita
from core.forms import DespesaForm, ReceitaForm, RecorrenteDespesaForm, RecorrenteReceitaForm

@login_required
def lista_despesas(request):
    user = request.user
    familia = user.perfil.familia
    
    # A lógica de POST permanece a mesma
    if request.method == 'POST':
        form = DespesaForm(request.POST, user=user)
        if form.is_valid():
            # ... (código de salvar despesa/parcela sem alteração)
            return redirect('lista_despesas')
    else:
        form = DespesaForm(user=user)

    # Lógica de Visão
    visao = request.GET.get('visao', 'conjunto')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)

    # Busca a lista completa de despesas
    despesas_list = Despesa.objects.filter(user__in=usuarios_a_filtrar).order_by('-data', '-id')
    
    # --- LÓGICA DE PAGINAÇÃO ---
    paginator = Paginator(despesas_list, 20) # Mostra 20 despesas por página
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    # ---------------------------
    
    # ATUALIZAÇÃO: Passa o 'page_obj' para o template em vez de 'despesas'
    contexto = {'page_obj': page_obj, 'form': form, 'visao': visao, 'familia': familia}
    return render(request, 'core/lista_despesas.html', contexto)

@login_required
def editar_despesa(request, id):
    despesa = get_object_or_404(Despesa, id=id, user=request.user)
    if request.method == 'POST':
        form = DespesaForm(request.POST, instance=despesa, user=request.user)
        if 'numero_parcelas' in form.fields: form.fields.pop('numero_parcelas')
        if form.is_valid():
            form.save()
            messages.success(request, 'Despesa atualizada com sucesso!')
            return redirect('lista_despesas')
    else:
        form = DespesaForm(instance=despesa, user=request.user)
        if 'numero_parcelas' in form.fields: form.fields.pop('numero_parcelas')
    contexto = {'form': form, 'despesa': despesa}
    return render(request, 'core/editar_despesa.html', contexto)

@login_required
def excluir_despesa(request, id):
    despesa = get_object_or_404(Despesa, id=id, user=request.user)
    despesa.delete()
    messages.success(request, 'Despesa excluída com sucesso!')
    return redirect('lista_despesas')

@login_required
def adicionar_despesa_recorrente(request):
    user = request.user
    if request.method == 'POST':
        form = RecorrenteDespesaForm(request.POST, user=user)
        if form.is_valid():
            dados = form.cleaned_data
            id_rec = uuid.uuid4()
            for i in range(dados['repeticoes']):
                if dados['frequencia'] == 'semanal': delta = relativedelta(weeks=i)
                elif dados['frequencia'] == 'quinzenal': delta = relativedelta(weeks=i*2)
                elif dados['frequencia'] == 'mensal': delta = relativedelta(months=i)
                elif dados['frequencia'] == 'trimestral': delta = relativedelta(months=i*3)
                elif dados['frequencia'] == 'semestral': delta = relativedelta(months=i*6)
                elif dados['frequencia'] == 'anual': delta = relativedelta(years=i)
                data_recorrencia = dados['data_inicio'] + delta
                Despesa.objects.create(
                    user=user, descricao=dados['descricao'], valor=dados['valor'], data=data_recorrencia,
                    categoria=dados['categoria'], conta=dados['conta'], cartao=dados['cartao'],
                    recorrente=True, id_recorrencia=id_rec
                )
            messages.success(request, f"{dados['repeticoes']} despesas recorrentes foram criadas com sucesso!")
            return redirect('lista_despesas')
    else:
        form = RecorrenteDespesaForm(user=user)
    contexto = {'form': form}
    return render(request, 'core/adicionar_recorrente.html', contexto)

@login_required
def lista_receitas(request):
    user = request.user
    familia = user.perfil.familia

    if request.method == 'POST':
        form = ReceitaForm(request.POST, user=user)
        if form.is_valid():
            receita = form.save(commit=False)
            receita.user = user
            receita.save()
            messages.success(request, 'Receita salva com sucesso!')
            return redirect('lista_receitas')
    else:
        form = ReceitaForm(user=user)
    
    # Lógica de Visão
    visao = request.GET.get('visao', 'conjunto')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)

    # Busca a lista completa de receitas
    receitas_list = Receita.objects.filter(user__in=usuarios_a_filtrar).order_by('-data')
    
    # --- LÓGICA DE PAGINAÇÃO ---
    paginator = Paginator(receitas_list, 20) # Mostra 20 receitas por página
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    # ---------------------------
    
    # ATUALIZAÇÃO: Passa o 'page_obj' para o template em vez de 'receitas'
    contexto = {'page_obj': page_obj, 'form': form, 'visao': visao, 'familia': familia}
    return render(request, 'core/lista_receitas.html', contexto)
@login_required
def excluir_receita(request, id):
    receita = get_object_or_404(Receita, id=id, user=request.user)
    receita.delete()
    messages.success(request, 'Receita excluída com sucesso!')
    return redirect('lista_receitas')

@login_required
def adicionar_receita_recorrente(request):
    user = request.user
    if request.method == 'POST':
        form = RecorrenteReceitaForm(request.POST, user=user)
        if form.is_valid():
            dados = form.cleaned_data
            id_rec = uuid.uuid4()
            for i in range(dados['repeticoes']):
                if dados['frequencia'] == 'semanal': delta = relativedelta(weeks=i)
                elif dados['frequencia'] == 'quinzenal': delta = relativedelta(weeks=i*2)
                elif dados['frequencia'] == 'mensal': delta = relativedelta(months=i)
                elif dados['frequencia'] == 'trimestral': delta = relativedelta(months=i*3)
                elif dados['frequencia'] == 'semestral': delta = relativedelta(months=i*6)
                elif dados['frequencia'] == 'anual': delta = relativedelta(years=i)
                data_recorrencia = dados['data_inicio'] + delta
                Receita.objects.create(
                    user=user, descricao=dados['descricao'], valor=dados['valor'], data=data_recorrencia,
                    categoria=dados['categoria'], conta=dados['conta'],
                    recorrente=True, id_recorrencia=id_rec
                )
            messages.success(request, f"{dados['repeticoes']} receitas recorrentes foram criadas com sucesso!")
            return redirect('lista_receitas')
    else:
        form = RecorrenteReceitaForm(user=user)
    contexto = {'form': form, 'tipo': 'Receita'}
    return render(request, 'core/adicionar_recorrente.html', contexto)