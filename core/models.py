import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User

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
    """Contas bancárias ou carteiras, compartilhadas pela família."""
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE)
    
    class TipoConta(models.TextChoices):
        CARTEIRA = 'CA', 'Carteira'
        CONTA_CORRENTE = 'CC', 'Conta Corrente'
        POUPANCA = 'PO', 'Poupança'
        
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=2, choices=TipoConta.choices, default=TipoConta.CONTA_CORRENTE)
    saldo_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    def __str__(self):
        return self.nome

class CartaoDeCredito(models.Model):
    """Cartões de crédito, compartilhados pela família."""
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    limite = models.DecimalField(max_digits=10, decimal_places=2)
    dia_fechamento = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    dia_vencimento = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    
    def __str__(self):
        return self.nome

# --- Modelos de Transação (Pertencem a um Usuário Individual) ---

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