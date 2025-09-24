from django import forms
from django.contrib.auth.forms import UserCreationForm
from datetime import date
from .models import (
    Despesa, Receita, MetaFinanceira, Categoria, CategoriaReceita,
    Conta, CartaoDeCredito, Investimento, AporteInvestimento
)

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email',)

# ... (todos os formulários de Despesa, Receita, Recorrentes, etc., sem alteração) ...
class DespesaForm(forms.ModelForm):
    numero_parcelas = forms.IntegerField(label='Número de Parcelas', min_value=1, initial=1, required=True)
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'perfil') and user.perfil.familia:
            familia = user.perfil.familia
            self.fields['categoria'].queryset = Categoria.objects.filter(familia=familia)
            self.fields['conta'].queryset = Conta.objects.filter(familia=familia)
            self.fields['cartao'].queryset = CartaoDeCredito.objects.filter(familia=familia)
        else:
            self.fields['categoria'].queryset = Categoria.objects.none()
            self.fields['conta'].queryset = Conta.objects.none()
            self.fields['cartao'].queryset = CartaoDeCredito.objects.none()
    class Meta:
        model = Despesa
        exclude = ['user', 'parcelada', 'parcela_atual', 'parcelas_totais', 'id_compra_parcelada', 'recorrente', 'id_recorrencia']
        widgets = {'data': forms.DateInput(attrs={'type': 'date'})}

class ReceitaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'perfil') and user.perfil.familia:
            familia = user.perfil.familia
            self.fields['categoria'].queryset = CategoriaReceita.objects.filter(familia=familia)
            self.fields['conta'].queryset = Conta.objects.filter(familia=familia)
        else:
            self.fields['categoria'].queryset = CategoriaReceita.objects.none()
            self.fields['conta'].queryset = Conta.objects.none()
    class Meta:
        model = Receita
        exclude = ['user', 'recorrente', 'id_recorrencia']
        widgets = {'data': forms.DateInput(attrs={'type': 'date'})}

FREQUENCIA_CHOICES = [
    ('semanal', 'Semanal'), ('quinzenal', 'Quinzenal'), ('mensal', 'Mensal'),
    ('trimestral', 'Trimestral'), ('semestral', 'Semestral'), ('anual', 'Anual'),
]

class RecorrenteDespesaForm(forms.ModelForm):
    data_inicio = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    frequencia = forms.ChoiceField(choices=FREQUENCIA_CHOICES)
    repeticoes = forms.IntegerField(min_value=2, label="Número de Repetições")
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'perfil') and user.perfil.familia:
            familia = user.perfil.familia
            self.fields['categoria'].queryset = Categoria.objects.filter(familia=familia)
            self.fields['conta'].queryset = Conta.objects.filter(familia=familia)
            self.fields['cartao'].queryset = CartaoDeCredito.objects.filter(familia=familia)
        else:
            self.fields['categoria'].queryset = Categoria.objects.none()
            self.fields['conta'].queryset = Conta.objects.none()
            self.fields['cartao'].queryset = CartaoDeCredito.objects.none()
    class Meta:
        model = Despesa
        fields = ['descricao', 'valor', 'categoria', 'conta', 'cartao']

class RecorrenteReceitaForm(forms.ModelForm):
    data_inicio = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    frequencia = forms.ChoiceField(choices=FREQUENCIA_CHOICES)
    repeticoes = forms.IntegerField(min_value=2, label="Número de Repetições")
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'perfil') and user.perfil.familia:
            familia = user.perfil.familia
            self.fields['categoria'].queryset = CategoriaReceita.objects.filter(familia=familia)
            self.fields['conta'].queryset = Conta.objects.filter(familia=familia)
        else:
            self.fields['categoria'].queryset = CategoriaReceita.objects.none()
            self.fields['conta'].queryset = Conta.objects.none()
    class Meta:
        model = Receita
        fields = ['descricao', 'valor', 'categoria', 'conta']

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'orcamento_mensal', 'categoria_mae']

    def __init__(self, *args, **kwargs):
        # Pega a família que a view vai passar
        familia = kwargs.pop('familia', None)
        super().__init__(*args, **kwargs)

        if familia:
            # Mostra apenas as categorias principais da família como opções para "categoria_mae"
            self.fields['categoria_mae'].queryset = Categoria.objects.filter(
                familia=familia, 
                categoria_mae__isnull=True
            )

class CategoriaReceitaForm(forms.ModelForm):
    class Meta:
        model = CategoriaReceita
        fields = ['nome']

class ContaForm(forms.ModelForm):
    class Meta:
        model = Conta
        fields = ['nome', 'tipo', 'saldo_inicial']

class CartaoDeCreditoForm(forms.ModelForm):
    class Meta:
        model = CartaoDeCredito
        fields = ['nome', 'limite', 'dia_fechamento', 'dia_vencimento']

class MetaFinanceiraForm(forms.ModelForm):
    class Meta:
        model = MetaFinanceira
        fields = ['nome', 'valor_objetivo', 'data_limite']
        widgets = {'data_limite': forms.DateInput(attrs={'type': 'date'})}

class EntrarFamiliaForm(forms.Form):
    codigo_convite = forms.UUIDField(label="Código de Convite da Família")

class InvestimentoForm(forms.ModelForm):
    class Meta:
        model = Investimento
        fields = ['nome', 'tipo', 'valor_atual', 'taxa_rendimento_anual']

class AporteInvestimentoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'perfil') and user.perfil.familia:
            self.fields['conta_origem'].queryset = Conta.objects.filter(familia=user.perfil.familia)
        else:
            self.fields['conta_origem'].queryset = Conta.objects.none()
    class Meta:
        model = AporteInvestimento
        fields = ['valor', 'data', 'conta_origem']
        widgets = {'data': forms.DateInput(attrs={'type': 'date'})}

class PagamentoFaturaForm(forms.Form):
    conta_pagamento = forms.ModelChoiceField(queryset=Conta.objects.all(), label="Pagar com a conta", widget=forms.Select(attrs={'class': 'form-select'}))
    data_pagamento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), initial=date.today, label="Data do Pagamento")
    def __init__(self, *args, **kwargs):
        familia = kwargs.pop('familia', None)
        super().__init__(*args, **kwargs)
        if familia:
            self.fields['conta_pagamento'].queryset = Conta.objects.filter(familia=familia)


# --- APORTEFORM ATUALIZADO ---
class AporteForm(forms.Form):
    valor = forms.DecimalField(max_digits=15, decimal_places=2, label="Valor do Aporte")
    conta_origem = forms.ModelChoiceField(queryset=Conta.objects.all(), label="Conta de Origem")

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'perfil') and user.perfil.familia:
            self.fields['conta_origem'].queryset = Conta.objects.filter(familia=user.perfil.familia)
        else:
            self.fields['conta_origem'].queryset = Conta.objects.none()