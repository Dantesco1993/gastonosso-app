# core/views/auth.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from core.forms import CustomUserCreationForm

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