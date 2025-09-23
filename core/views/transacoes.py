import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from dateutil.relativedelta import relativedelta

from core.models import Despesa, Receita
from core.forms import DespesaForm, ReceitaForm, RecorrenteDespesaForm, RecorrenteReceitaForm

@login_required
def lista_despesas(request):
    user = request.user
    if request.method == 'POST':
        form = DespesaForm(request.POST, user=user)
        if form.is_valid():
            dados_despesa = form.cleaned_data
            valor_total = dados_despesa['valor']
            num_parcelas = dados_despesa['numero_parcelas']
            data_inicial = dados_despesa['data']
            descricao_base = dados_despesa['descricao']
            if num_parcelas > 1:
                valor_parcela = valor_total / num_parcelas
                id_compra = uuid.uuid4()
                for i in range(num_parcelas):
                    data_parcela = data_inicial + relativedelta(months=i)
                    Despesa.objects.create(
                        user=user, descricao=f"{descricao_base} ({i+1}/{num_parcelas})",
                        valor=valor_parcela, data=data_parcela, categoria=dados_despesa['categoria'],
                        conta=dados_despesa['conta'], cartao=dados_despesa['cartao'],
                        parcelada=True, parcela_atual=i + 1, parcelas_totais=num_parcelas,
                        id_compra_parcelada=id_compra
                    )
                messages.success(request, f'{num_parcelas} parcelas foram criadas com sucesso!')
            else:
                despesa = form.save(commit=False)
                despesa.user = user
                despesa.save()
                messages.success(request, 'Despesa salva com sucesso!')
            return redirect('lista_despesas')
    else:
        form = DespesaForm(user=user)
    despesas = Despesa.objects.filter(user=user).order_by('-data', '-id')
    contexto = {'despesas': despesas, 'form': form}
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
    receitas = Receita.objects.filter(user=user).order_by('-data')
    contexto = {'receitas': receitas, 'form': form}
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