from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Perfil, Familia, Categoria, CategoriaReceita

# --- Sinal para criar Perfil (já existente) ---
@receiver(post_save, sender=User)
def criar_perfil(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)

@receiver(post_save, sender=User)
def salvar_perfil(sender, instance, **kwargs):
    if hasattr(instance, 'perfil'):
        instance.perfil.save()

# --- NOVO SINAL PARA CRIAR CATEGORIAS PADRÃO ---

# Definindo nossas categorias padrão
CATEGORIAS_DESPESA_PADRAO = [
    {"nome": "Moradia", "sub": ["Aluguel", "Condomínio", "Contas de Casa", "Manutenção"]},
    {"nome": "Alimentação", "sub": ["Supermercado", "Restaurantes", "Delivery"]},
    {"nome": "Transporte", "sub": ["Gasolina", "Transporte Público", "Uber/Táxi"]},
    {"nome": "Lazer", "sub": ["Hobbies", "Streaming", "Viagens"]},
    {"nome": "Saúde", "sub": ["Farmácia", "Plano de Saúde", "Consultas"]},
    {"nome": "Financeiro", "sub": ["Pagamento de Fatura", "Aportes em Metas", "Investimentos"]},
]

CATEGORIAS_RECEITA_PADRAO = [
    "Salário", "Renda Extra", "Presente", "Investimentos"
]

@receiver(post_save, sender=Familia)
def criar_categorias_padrao(sender, instance, created, **kwargs):
    # 'created' é um booleano que nos diz se o objeto foi criado agora ou apenas atualizado
    if created:
        familia = instance

        # Cria as categorias de despesa com suas subcategorias
        for cat_data in CATEGORIAS_DESPESA_PADRAO:
            cat_principal = Categoria.objects.create(
                familia=familia,
                nome=cat_data["nome"],
                macro_categoria=Categoria.MacroCategoria.NECESSIDADE if cat_data["nome"] in ["Moradia", "Alimentação", "Saúde"] else Categoria.MacroCategoria.NAO_CLASSIFICADO
            )
            for sub_nome in cat_data["sub"]:
                macro = Categoria.MacroCategoria.NAO_CLASSIFICADO
                if sub_nome in ["Aluguel", "Condomínio", "Contas de Casa", "Supermercado", "Gasolina", "Transporte Público", "Plano de Saúde", "Farmácia"]:
                    macro = Categoria.MacroCategoria.NECESSIDADE
                elif sub_nome in ["Restaurantes", "Delivery", "Hobbies", "Streaming", "Viagens", "Uber/Táxi"]:
                    macro = Categoria.MacroCategoria.DESEJO
                elif sub_nome in ["Pagamento de Fatura", "Aportes em Metas", "Investimentos"]:
                    macro = Categoria.MacroCategoria.META
                
                Categoria.objects.create(
                    familia=familia,
                    nome=sub_nome,
                    categoria_mae=cat_principal,
                    macro_categoria=macro
                )

        # Cria as categorias de receita
        for nome_cat in CATEGORIAS_RECEITA_PADRAO:
            CategoriaReceita.objects.create(familia=familia, nome=nome_cat)