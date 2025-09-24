import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from django.db.models import Sum
from datetime import date
from dateutil.relativedelta import relativedelta

# --- Modelos Estruturais para Compartilhamento ---

class Familia(models.Model):
    """Representa um grupo familiar ou um espaço financeiro compartilhado."""
    nome = models.CharField(max_length=100)
    codigo_convite = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)


    def __str__(self):
        return self.nome

class Perfil(models.Model):
    """Estende o modelo de usuário padrão para incluir a associação a uma família."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    familia = models.ForeignKey(Familia, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username

# --- Modelos de Configuração (Compartilhados pela Família) ---

class Categoria(models.Model):
    """Categorias de despesa, compartilhadas pela família."""
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nome

class CategoriaReceita(models.Model):
    """Categorias de receita, compartilhadas pela família."""
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nome

class Conta(models.Model):
    familia = models.ForeignKey('Familia', on_delete=models.CASCADE)
    class TipoConta(models.TextChoices):
        CARTEIRA = 'CA', 'Carteira'
        CONTA_CORRENTE = 'CC', 'Conta Corrente'
        POUPANCA = 'PO', 'Poupança'
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=2, choices=TipoConta.choices, default=TipoConta.CONTA_CORRENTE)
    saldo_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    def __str__(self):
        return self.nome

    # --- MÉTODO ATUALIZADO ---
    def get_saldo_atual(self, usuarios, data_base=None):
        """Calcula o saldo realizado da conta com base em uma lista de usuários e uma data de referência."""
        if data_base is None:
            data_base = date.today()
        
        # Garante que 'usuarios' seja uma lista de IDs para a consulta
        user_ids = [u.id for u in usuarios]
        
        receitas = Receita.objects.filter(user_id__in=user_ids, conta=self, data__lte=data_base).aggregate(total=Sum('valor'))['total'] or 0
        despesas = Despesa.objects.filter(user_id__in=user_ids, conta=self, data__lte=data_base).aggregate(total=Sum('valor'))['total'] or 0
        
        return (self.saldo_inicial + receitas) - despesas

class CartaoDeCredito(models.Model):
    familia = models.ForeignKey('Familia', on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    limite = models.DecimalField(max_digits=10, decimal_places=2)
    dia_fechamento = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    dia_vencimento = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    
    def __str__(self):
        return self.nome

    # --- MÉTODO ATUALIZADO ---
    def get_fatura_aberta(self, usuarios, data_base=None):
        """Calcula o período, as despesas e o total da fatura em aberto com base em uma data."""
        if data_base is None:
            data_base = date.today()
        
        if data_base.day <= self.dia_fechamento:
            data_fechamento = data_base.replace(day=self.dia_fechamento)
        else:
            data_fechamento = (data_base + relativedelta(months=1)).replace(day=self.dia_fechamento)
        data_inicio = (data_fechamento - relativedelta(months=1)) + relativedelta(days=1)
        
        user_ids = [u.id for u in usuarios]
        
        despesas = Despesa.objects.filter(
            user_id__in=user_ids,
            cartao=self,
            data__gte=data_inicio,
            data__lte=data_fechamento,
            fatura_paga=False
        ).order_by('data')
        
        total = despesas.aggregate(total=Sum('valor'))['total'] or 0
        
        return {
            'despesas': despesas,
            'total': total,
            'data_inicio': data_inicio,
            'data_fechamento': data_fechamento,
        }

class Despesa(models.Model):
    """Representa uma despesa individual, feita por um usuário específico."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField()
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT, null=True, blank=True)
    cartao = models.ForeignKey(CartaoDeCredito, on_delete=models.PROTECT, null=True, blank=True)
    
    # Campos para parcelamento
    parcelada = models.BooleanField(default=False)
    parcela_atual = models.IntegerField(default=1)
    parcelas_totais = models.IntegerField(default=1)
    id_compra_parcelada = models.UUIDField(null=True, blank=True)
    fatura_paga = models.BooleanField(default=False, help_text="Indica se a despesa de cartão já foi paga na fatura")
    
    # Campos para recorrência
    recorrente = models.BooleanField(default=False)
    id_recorrencia = models.UUIDField(null=True, blank=True)
    
    def __str__(self):
        if self.parcelada:
            return f"{self.descricao} ({self.parcela_atual}/{self.parcelas_totais})"
        if self.recorrente:
            return f"{self.descricao} 🔁"
        return self.descricao

class Receita(models.Model):
    """Representa uma receita individual, recebida por um usuário específico."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField()
    categoria = models.ForeignKey(CategoriaReceita, on_delete=models.PROTECT)
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT)

    # Campos para recorrência
    recorrente = models.BooleanField(default=False)
    id_recorrencia = models.UUIDField(null=True, blank=True)
    
    def __str__(self):
        if self.recorrente:
            return f"{self.descricao} 🔁"
        return self.descricao

# --- Modelo de Planejamento (Compartilhado pela Família) ---

class MetaFinanceira(models.Model):
    """Metas financeiras, compartilhadas pela família."""
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    valor_objetivo = models.DecimalField(max_digits=15, decimal_places=2)
    valor_atual = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    data_criacao = models.DateField(auto_now_add=True)
    data_limite = models.DateField(null=True, blank=True)
    
    @property
    def progresso_percentual(self):
        if self.valor_objetivo > 0:
            progresso = (self.valor_atual / self.valor_objetivo) * 100
            return round(min(progresso, 100), 2)
        return 0
        
    def __str__(self):
        return self.nome
    
class Investimento(models.Model):
    """Representa um ativo de investimento específico, compartilhado pela família."""
    class TipoInvestimento(models.TextChoices):
        RENDA_FIXA = 'RF', 'Renda Fixa'
        RENDA_VARIAVEL = 'RV', 'Renda Variável'

    familia = models.ForeignKey('Familia', on_delete=models.CASCADE)
    nome = models.CharField(max_length=100, help_text="Ex: Tesouro Selic 2029, Ações WEG, FII MXRF11")
    tipo = models.CharField(max_length=2, choices=TipoInvestimento.choices)
    valor_atual = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, help_text="Valor de mercado atual de todo o montante investido.")
    taxa_rendimento_anual = models.DecimalField(max_digits=5, decimal_places=2, help_text="Para Renda Fixa, a taxa contratada. Para Renda Variável, uma estimativa.")
    # --- CAMPO ADICIONADO ---
    data_criacao = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

class AporteInvestimento(models.Model):
    """Representa uma transação de aporte (depósito) em um investimento."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    investimento = models.ForeignKey(Investimento, on_delete=models.CASCADE, related_name='aportes')
    conta_origem = models.ForeignKey(Conta, on_delete=models.PROTECT, help_text="Conta da qual o dinheiro saiu para o aporte.")
    data = models.DateField()
    valor = models.DecimalField(max_digits=15, decimal_places=2)

    def __str__(self):
        return f"Aporte de R$ {self.valor} em {self.investimento.nome} por {self.user.username}"
