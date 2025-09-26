from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Perfil, Familia, Categoria, CategoriaReceita, Plano, Assinatura

# --- Sinal para criar Perfil ---
@receiver(post_save, sender=User)
def criar_perfil(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)

@receiver(post_save, sender=User)
def salvar_perfil(sender, instance, **kwargs):
    if hasattr(instance, 'perfil'):
        instance.perfil.save()


# --- Sinal para criar Associações Padrão para uma nova Família ---

# Definindo nossas categorias padrão
CATEGORIAS_DESPESA_PADRAO = [
    {"nome": "Moradia", "macro": "NE", "sub": ["Aluguel", "Condomínio", "Contas de Casa", "Manutenção"]},
    {"nome": "Alimentação", "macro": "NE", "sub": ["Supermercado", "Restaurantes", "Delivery"]},
    {"nome": "Transporte", "macro": "NE", "sub": ["Gasolina", "Transporte Público", "Uber/Táxi"]},
    {"nome": "Lazer", "macro": "DE", "sub": ["Hobbies", "Streaming", "Viagens", "Compras"]},
    {"nome": "Saúde", "macro": "NE", "sub": ["Farmácia", "Plano de Saúde", "Consultas"]},
    {"nome": "Financeiro", "macro": "ME", "sub": ["Pagamento de Fatura", "Aportes em Metas", "Investimentos"]},
]

CATEGORIAS_RECEITA_PADRAO = [
    "Salário", "Renda Extra", "Presente", "Reembolso", "Vendas"
]

@receiver(post_save, sender=Familia)
def criar_associacoes_padrao(sender, instance, created, **kwargs):
    """
    Este sinal é acionado sempre que uma nova Família é criada.
    Ele cria as categorias padrão e a assinatura gratuita.
    """
    if created:
        familia = instance

        # 1. Cria as categorias de despesa com suas subcategorias e macro-categorias
        for cat_data in CATEGORIAS_DESPESA_PADRAO:
            cat_principal = Categoria.objects.create(
                familia=familia,
                nome=cat_data["nome"],
                macro_categoria=cat_data["macro"]
            )
            for sub_nome in cat_data["sub"]:
                # Uma lógica simples para atribuir macro-categorias às subcategorias
                macro_sub = Categoria.MacroCategoria.NAO_CLASSIFICADO
                if sub_nome in ["Aluguel", "Condomínio", "Contas de Casa", "Supermercado", "Transporte Público", "Plano de Saúde", "Farmácia"]:
                    macro_sub = Categoria.MacroCategoria.NECESSIDADE
                elif sub_nome in ["Restaurantes", "Delivery", "Hobbies", "Streaming", "Viagens", "Compras", "Uber/Táxi"]:
                    macro_sub = Categoria.MacroCategoria.DESEJO
                elif sub_nome in ["Pagamento de Fatura", "Aportes em Metas", "Investimentos"]:
                    macro_sub = Categoria.MacroCategoria.META
                
                Categoria.objects.create(
                    familia=familia,
                    nome=sub_nome,
                    categoria_mae=cat_principal,
                    macro_categoria=macro_sub
                )

        # 2. Cria as categorias de receita
        for nome_cat in CATEGORIAS_RECEITA_PADRAO:
            CategoriaReceita.objects.create(familia=familia, nome=nome_cat)

        # 3. Inscreve a nova família no plano Gratuito
        plano_gratuito = Plano.objects.filter(preco_mensal=0).first()
        if plano_gratuito:
            Assinatura.objects.create(
                familia=familia, 
                plano=plano_gratuito, 
                status=Assinatura.StatusAssinatura.ATIVA
            )