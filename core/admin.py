from django.contrib import admin
from .models import (
    Categoria, Despesa, Conta, CartaoDeCredito, Receita, CategoriaReceita,
    MetaFinanceira, Familia, Perfil, Investimento, AporteInvestimento, Plano, Assinatura
)

# ... (todos os outros registros: admin.site.register(Categoria), etc.)
admin.site.register(Categoria)
admin.site.register(Despesa)
admin.site.register(Conta)
admin.site.register(CartaoDeCredito)
admin.site.register(Receita)
admin.site.register(CategoriaReceita)
admin.site.register(MetaFinanceira)
admin.site.register(Familia)
admin.site.register(Perfil)

# Adicione estas duas linhas
admin.site.register(Investimento)
admin.site.register(AporteInvestimento)

admin.site.register(Plano)
admin.site.register(Assinatura)