# financas_pessoais/urls.py

from django.contrib import admin
from django.urls import path, include # Adicione o 'include'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')), # Adicione esta linha
]