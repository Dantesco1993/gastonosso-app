from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum
from datetime import date

from core.models import Despesa, MetaFinanceira, Categoria
from core.forms import MetaFinanceiraForm, AporteForm

@login_required
def analise_gastos(request):
    hoje = date.today()
    user = request.user
    familia = user.perfil.familia
    
    # Lógica de visão
    visao = request.GET.get('visao', 'conjunto')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)

    # A análise de gastos agora respeita a visão selecionada
    gastos_por_categoria = Despesa.objects.filter(
        user__in=usuarios_a_filtrar, 
        data__year=hoje.year, 
        data__month=hoje.month
    ).values('categoria__nome').annotate(total=Sum('valor')).order_by('-total')
    
    labels = [gasto['categoria__nome'] for gasto in gastos_por_categoria]
    data = [float(gasto['total']) for gasto in gastos_por_categoria]

    contexto = {
        'gastos_por_categoria': gastos_por_categoria,
        'labels': labels, 
        'data': data,
        'visao': visao, # Passa a visão para o template (para futuros seletores)
    }
    return render(request, 'core/analise_gastos.html', contexto)

@login_required
def lista_metas(request):
    user = request.user
    familia = user.perfil.familia

    if request.method == 'POST':
        # Usuário precisa de uma família para adicionar uma meta compartilhada
        if not familia:
            messages.error(request, "Você precisa criar ou pertencer a uma família para adicionar metas.")
            return redirect('gerenciar_familia')
            
        form_meta = MetaFinanceiraForm(request.POST)
        if form_meta.is_valid():
            meta = form_meta.save(commit=False)
            meta.familia = familia
            meta.save()
            messages.success(request, 'Nova meta criada com sucesso!')
            return redirect('lista_metas')
    else:
        form_meta = MetaFinanceiraForm()
        
    metas = MetaFinanceira.objects.filter(familia=familia) if familia else []
    form_aporte = AporteForm(user=user)

    contexto = {'metas': metas, 'form_meta': form_meta, 'form_aporte': form_aporte}
    return render(request, 'core/lista_metas.html', contexto)

@login_required
def adicionar_aporte(request, id):
    if request.method == 'POST':
        user = request.user
        familia = user.perfil.familia
        meta = get_object_or_404(MetaFinanceira, id=id, familia=familia)
        
        form = AporteForm(request.POST, user=user)

        if form.is_valid():
            valor_aporte = form.cleaned_data['valor']
            conta_origem = form.cleaned_data['conta_origem']

            # 1. Atualiza o valor da meta
            meta.valor_atual += valor_aporte
            meta.save()

            # 2. Cria a despesa correspondente para debitar da conta
            categoria_aporte, _ = Categoria.objects.get_or_create(
                familia=familia, 
                nome__iexact="Metas Financeiras", 
                defaults={'nome': "Metas Financeiras"}
            )

            Despesa.objects.create(
                user=user,
                descricao=f"Aporte para a meta: {meta.nome}",
                valor=valor_aporte,
                data=date.today(),
                categoria=categoria_aporte,
                conta=conta_origem
            )
            messages.success(request, 'Aporte realizado e despesa registrada com sucesso!')
            
    return redirect('lista_metas')