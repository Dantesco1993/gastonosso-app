import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from dateutil.relativedelta import relativedelta
from django.core.paginator import Paginator

from core.models import Despesa, Receita
from core.forms import DespesaForm, ReceitaForm, RecorrenteDespesaForm, RecorrenteReceitaForm

@login_required
def lista_despesas(request):
    user = request.user
    familia = user.perfil.familia
    
    visao = request.GET.get('visao', 'individual')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)

    if request.method == 'POST':
        form = DespesaForm(request.POST, user=user)
        if form.is_valid():
            # Lógica de salvar despesa/parcela (sem alteração)
            dados_despesa = form.cleaned_data
            num_parcelas = dados_despesa.get('numero_parcelas', 1)

            if num_parcelas > 1:
                # ... lógica de parcelamento ...
                messages.success(request, f'{num_parcelas} parcelas foram criadas com sucesso!')
            else:
                despesa = form.save(commit=False)
                despesa.user = user
                despesa.save()
                messages.success(request, 'Despesa salva com sucesso!')
            
            if request.htmx:
                # SUCESSO HTMX: Retorna a lista ATUALIZADA E um formulário LIMPO
                despesas_list = Despesa.objects.filter(user__in=usuarios_a_filtrar).order_by('-data', '-id')
                paginator = Paginator(despesas_list, 20)
                page_obj = paginator.get_page(1)
                contexto = {
                    'page_obj': page_obj,
                    'form': DespesaForm(user=user), # <<< CORREÇÃO: Envia um formulário novo e limpo
                    'visao': visao, 
                    'familia': familia
                }
                return render(request, 'core/partials/despesas_response.html', contexto)
            
            return redirect('lista_despesas')
        else: # Se o formulário for inválido
            if request.htmx:
                return render(request, 'core/partials/form_despesa_partial.html', {'form': form})
    
    # Lógica GET
    form = DespesaForm(user=user)
    despesas_list = Despesa.objects.filter(user__in=usuarios_a_filtrar).order_by('-data', '-id')
    paginator = Paginator(despesas_list, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
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
    
    visao = request.GET.get('visao', 'individual')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)

    if request.method == 'POST':
        form = ReceitaForm(request.POST, user=user)
        if form.is_valid():
            receita = form.save(commit=False)
            receita.user = user
            receita.save()
            messages.success(request, 'Receita salva com sucesso!')

            if request.htmx:
                receitas_list = Receita.objects.filter(user__in=usuarios_a_filtrar).order_by('-data')
                paginator = Paginator(receitas_list, 20)
                page_obj = paginator.get_page(1)
                contexto = {
                    'page_obj': page_obj,
                    'form': ReceitaForm(user=user),
                    'visao': visao, 'familia': familia
                }
                return render(request, 'core/partials/receitas_response.html', contexto)
            
            return redirect('lista_receitas')
        else:
            if request.htmx:
                contexto = {'form': form}
                return render(request, 'core/partials/form_receita_partial.html', contexto)
    
    form = ReceitaForm(user=user)
    receitas_list = Receita.objects.filter(user__in=usuarios_a_filtrar).order_by('-data')
    paginator = Paginator(receitas_list, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    contexto = {'page_obj': page_obj, 'form': form, 'visao': visao, 'familia': familia}
    return render(request, 'core/lista_receitas.html', contexto)

@login_required
def excluir_receita(request, id):
    receita = get_object_or_404(Receita, id=id, user=request.user)
    receita.delete()
    messages.success(request, 'Receita excluída com sucesso!')
    return redirect('lista_receitas')

@login_required
def editar_receita(request, id):
    receita = get_object_or_404(Receita, id=id, user=request.user)
    if request.method == 'POST':
        form = ReceitaForm(request.POST, instance=receita, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Receita atualizada com sucesso!')
            return redirect('lista_receitas')
    else:
        form = ReceitaForm(instance=receita, user=request.user)
    
    contexto = {'form': form, 'receita': receita}
    return render(request, 'core/editar_receita.html', contexto)

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