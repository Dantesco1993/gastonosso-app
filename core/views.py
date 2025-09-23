# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from datetime import date
from dateutil.relativedelta import relativedelta
import uuid
from itertools import chain
from operator import attrgetter
from django.contrib import messages
from django.db.utils import IntegrityError
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User

from .models import (
    Despesa, Categoria, Conta, CartaoDeCredito, Receita, CategoriaReceita, 
    MetaFinanceira, Familia, Perfil
)
from .forms import (
    DespesaForm, ReceitaForm, MetaFinanceiraForm, AporteForm, CategoriaForm,
    CategoriaReceitaForm, ContaForm, CartaoDeCreditoForm, RecorrenteDespesaForm,
    RecorrenteReceitaForm, CustomUserCreationForm, EntrarFamiliaForm
)

# --- VIEWS DE AUTENTICAÇÃO E LANDING PAGE ---
def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Cadastro realizado com sucesso! Bem-vindo(a), {user.username}.")
            return redirect("dashboard")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/register.html", {"form": form})

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing_page.html')


# --- VIEWS PRINCIPAIS DA APLICAÇÃO ---
@login_required
def dashboard(request):
    hoje = date.today()
    user = request.user
    
    # Etapa 1: Obter a família do usuário.
    familia = user.perfil.familia
    
    # Etapa 2: Determinar a visão e quais usuários usar nos filtros de transação.
    visao = request.GET.get('visao', 'conjunto')
    
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else: # Visão em conjunto
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)
        
    # Etapa 3: Buscar recursos compartilhados (SEMPRE da família).
    contas = Conta.objects.filter(familia=familia) if familia else []
    cartoes = CartaoDeCredito.objects.filter(familia=familia) if familia else []
    
    # --- Cálculos ---
    
    # 1. Saldo Total das Contas
    saldo_total_contas = 0
    for conta in contas:
        # A consulta de transações usa a lista de usuários filtrados
        receitas = Receita.objects.filter(user__in=usuarios_a_filtrar, conta=conta, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
        despesas = Despesa.objects.filter(user__in=usuarios_a_filtrar, conta=conta, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
        saldo_total_contas += (conta.saldo_inicial + receitas) - despesas
    
    # 2. Resumo Mensal
    total_receitas_mes = Receita.objects.filter(user__in=usuarios_a_filtrar, data__year=hoje.year, data__month=hoje.month, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    total_despesas_mes = Despesa.objects.filter(user__in=usuarios_a_filtrar, conta__isnull=False, data__year=hoje.year, data__month=hoje.month, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    balanco_mensal = total_receitas_mes - total_despesas_mes

    # 3. Faturas de Cartão Abertas
    faturas_abertas = []
    for cartao in cartoes:
        if hoje.day <= cartao.dia_fechamento:
            data_fechamento = hoje.replace(day=cartao.dia_fechamento)
        else:
            data_fechamento = (hoje + relativedelta(months=1)).replace(day=cartao.dia_fechamento)
        data_inicio = (data_fechamento - relativedelta(months=1)) + relativedelta(days=1)
        
        despesas_cartao = Despesa.objects.filter(
            user__in=usuarios_a_filtrar, 
            cartao=cartao, 
            data__gte=data_inicio, 
            data__lte=data_fechamento
        )
        total_fatura = despesas_cartao.aggregate(Sum('valor'))['valor__sum'] or 0
        faturas_abertas.append({'cartao': cartao, 'total': total_fatura})
        
    # 4. Atividade Recente
    transacoes_recentes = sorted(
        chain(Despesa.objects.filter(user__in=usuarios_a_filtrar), Receita.objects.filter(user__in=usuarios_a_filtrar)),
        key=attrgetter('data'), reverse=True
    )[:5]

    contexto = {
        'saldo_total': saldo_total_contas, 'receitas_mes': total_receitas_mes,
        'despesas_mes': total_despesas_mes, 'balanco_mensal': balanco_mensal,
        'faturas': faturas_abertas, 'transacoes_recentes': transacoes_recentes,
        'visao': visao,
        'familia': familia
    }
    return render(request, 'core/dashboard.html', contexto)
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
                        user=user,
                        descricao=f"{descricao_base} ({i+1}/{num_parcelas})",
                        valor=valor_parcela,
                        data=data_parcela,
                        categoria=dados_despesa['categoria'],
                        conta=dados_despesa['conta'],
                        cartao=dados_despesa['cartao'],
                        parcelada=True,
                        parcela_atual=i + 1,
                        parcelas_totais=num_parcelas,
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
                    user=user,
                    descricao=dados['descricao'], valor=dados['valor'], data=data_recorrencia,
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
                    user=user,
                    descricao=dados['descricao'], valor=dados['valor'], data=data_recorrencia,
                    categoria=dados['categoria'], conta=dados['conta'],
                    recorrente=True, id_recorrencia=id_rec
                )
            messages.success(request, f"{dados['repeticoes']} receitas recorrentes foram criadas com sucesso!")
            return redirect('lista_receitas')
    else:
        form = RecorrenteReceitaForm(user=user)
    contexto = {'form': form, 'tipo': 'Receita'}
    return render(request, 'core/adicionar_recorrente.html', contexto)

@login_required
def lista_contas(request):
    hoje = date.today()
    user = request.user
    familia = user.perfil.familia
    contas = Conta.objects.filter(familia=familia) if familia else []
    saldos = []
    for conta in contas:
        total_receitas = Receita.objects.filter(user=user, conta=conta, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
        total_despesas = Despesa.objects.filter(user=user, conta=conta, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
        saldo_atual = (conta.saldo_inicial + total_receitas) - total_despesas
        saldos.append({'conta': conta, 'saldo_atual': saldo_atual})
    contexto = {'contas_com_saldo': saldos}
    return render(request, 'core/lista_contas.html', contexto)

@login_required
def detalhe_conta(request, id):
    hoje = date.today()
    user = request.user
    familia = user.perfil.familia
    conta = get_object_or_404(Conta, id=id, familia=familia)
    total_receitas = Receita.objects.filter(user=user, conta=conta, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    total_despesas = Despesa.objects.filter(user=user, conta=conta, data__lte=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    saldo_atual = (conta.saldo_inicial + total_receitas) - total_despesas
    despesas = Despesa.objects.filter(user=user, conta=conta).order_by('-data')
    receitas = Receita.objects.filter(user=user, conta=conta).order_by('-data')
    contexto = {
        'conta': conta, 'saldo_atual': saldo_atual,
        'despesas': despesas, 'receitas': receitas,
    }
    return render(request, 'core/detalhe_conta.html', contexto)

@login_required
def lista_cartoes(request):
    familia = request.user.perfil.familia
    cartoes = CartaoDeCredito.objects.filter(familia=familia) if familia else []
    contexto = {'cartoes': cartoes}
    return render(request, 'core/lista_cartoes.html', contexto)

@login_required
def fatura_cartao(request, id):
    user = request.user
    familia = user.perfil.familia
    cartao = get_object_or_404(CartaoDeCredito, id=id, familia=familia)
    hoje = date.today()
    visao = request.GET.get('visao', 'conjunto')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)
    if hoje.day <= cartao.dia_fechamento:
        data_fechamento_fatura = hoje.replace(day=cartao.dia_fechamento)
    else:
        data_fechamento_fatura = (hoje + relativedelta(months=1)).replace(day=cartao.dia_fechamento)
    data_inicio_fatura = (data_fechamento_fatura - relativedelta(months=1)) + relativedelta(days=1)
    despesas = Despesa.objects.filter(
        user__in=usuarios_a_filtrar,
        cartao=cartao,
        data__gte=data_inicio_fatura,
        data__lte=data_fechamento_fatura
    ).order_by('data')
    total_fatura = despesas.aggregate(Sum('valor'))['valor__sum'] or 0
    contexto = {
        'cartao': cartao, 'despesas': despesas, 'total_fatura': total_fatura,
        'data_inicio': data_inicio_fatura, 'data_fechamento': data_fechamento_fatura,
    }
    return render(request, 'core/fatura_cartao.html', contexto)

@login_required
def analise_gastos(request):
    hoje = date.today()
    user = request.user
    familia = user.perfil.familia
    visao = request.GET.get('visao', 'conjunto')
    if visao == 'individual' or not familia:
        usuarios_a_filtrar = [user]
    else:
        usuarios_a_filtrar = User.objects.filter(perfil__familia=familia)
    gastos_por_categoria = Despesa.objects.filter(
        user__in=usuarios_a_filtrar, data__year=hoje.year, data__month=hoje.month
    ).values('categoria__nome').annotate(total=Sum('valor')).order_by('-total')
    labels = [gasto['categoria__nome'] for gasto in gastos_por_categoria]
    data = [float(gasto['total']) for gasto in gastos_por_categoria]
    contexto = {
        'gastos_por_categoria': gastos_por_categoria,
        'labels': labels, 'data': data,
    }
    return render(request, 'core/analise_gastos.html', contexto)

@login_required
def lista_metas(request):
    user = request.user
    familia = user.perfil.familia
    if request.method == 'POST':
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
    form_aporte = AporteForm()
    contexto = {'metas': metas, 'form_meta': form_meta, 'form_aporte': form_aporte}
    return render(request, 'core/lista_metas.html', contexto)

@login_required
def adicionar_aporte(request, id):
    if request.method == 'POST':
        familia = request.user.perfil.familia
        meta = get_object_or_404(MetaFinanceira, id=id, familia=familia)
        form = AporteForm(request.POST)
        if form.is_valid():
            valor_aporte = form.cleaned_data['valor']
            meta.valor_atual += valor_aporte
            meta.save()
            messages.success(request, 'Aporte adicionado com sucesso!')
    return redirect('lista_metas')

@login_required
def configuracoes(request):
    user = request.user
    try:
        familia = user.perfil.familia
    except (Perfil.DoesNotExist, AttributeError):
        familia = None
    if request.method == 'POST':
        if not familia:
            messages.error(request, "Você precisa criar ou pertencer a uma família para adicionar itens.")
            return redirect('gerenciar_familia')
        active_tab = request.POST.get('active_tab', 'cat-despesas')
        if 'form_categoria' in request.POST:
            form = CategoriaForm(request.POST)
            if form.is_valid():
                categoria = form.save(commit=False)
                categoria.familia = familia
                categoria.save()
                messages.success(request, 'Categoria de despesa adicionada!')
        elif 'form_categoria_receita' in request.POST:
            form = CategoriaReceitaForm(request.POST)
            if form.is_valid():
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
        return redirect(f"{reverse('configuracoes')}?active_tab={active_tab}")
    active_tab_get = request.GET.get('active_tab', 'cat-despesas')
    contexto = {
        'categorias': Categoria.objects.filter(familia=familia) if familia else [],
        'categorias_receita': CategoriaReceita.objects.filter(familia=familia) if familia else [],
        'contas': Conta.objects.filter(familia=familia) if familia else [],
        'cartoes': CartaoDeCredito.objects.filter(familia=familia) if familia else [],
        'form_categoria': CategoriaForm(),
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

# --- VIEW DE GERENCIAMENTO DE FAMÍLIA ---
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