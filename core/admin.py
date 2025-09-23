# core/admin.py
from django.contrib import admin
# Adicione os novos models à importação
from .models import (
    Categoria, Despesa, Conta, CartaoDeCredito,
    CategoriaReceita, Receita
)
from .models import MetaFinanceira # Adicione a importação


admin.site.register(Categoria)
admin.site.register(Despesa)
admin.site.register(Conta)
admin.site.register(CartaoDeCredito)
admin.site.register(CategoriaReceita) # Adicione esta linha
admin.site.register(Receita) # Adicione esta linha
admin.site.register(MetaFinanceira) # Adicione o registro