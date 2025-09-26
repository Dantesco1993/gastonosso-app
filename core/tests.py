from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date
from django.urls import reverse

from core.models import (
    Familia, Perfil, Conta, CartaoDeCredito, Categoria, 
    CategoriaReceita, Despesa, Receita
)

class ContaModelTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='usuarioteste', password='123')
        cls.perfil = Perfil.objects.get(user=cls.user)
        cls.familia = Familia.objects.create(nome="Família Teste")
        cls.perfil.familia = cls.familia
        cls.perfil.save()
        cls.cat_despesa = Categoria.objects.create(familia=cls.familia, nome="Teste Despesa")
        cls.cat_receita = CategoriaReceita.objects.create(familia=cls.familia, nome="Teste Receita")

    def test_get_saldo_atual_calcula_corretamente(self):
        conta = Conta.objects.create(familia=self.familia, nome="Conta de Teste", saldo_inicial=Decimal('1000.00'))
        Receita.objects.create(user=self.user, conta=conta, valor=Decimal('500.00'), data="2025-01-10", descricao="Receita de teste", categoria=self.cat_receita)
        Despesa.objects.create(user=self.user, conta=conta, valor=Decimal('150.00'), data="2025-01-15", descricao="Despesa de teste", categoria=self.cat_despesa)
        saldo_calculado = conta.get_saldo_atual(usuarios=[self.user])
        saldo_esperado = Decimal('1350.00')
        self.assertEqual(saldo_calculado, saldo_esperado)


class CartaoModelTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='usuarioteste2', password='123')
        cls.perfil = Perfil.objects.get(user=cls.user)
        cls.familia = Familia.objects.create(nome="Família Teste Cartão")
        cls.perfil.familia = cls.familia
        cls.perfil.save()
        cls.cat_cartao = Categoria.objects.create(familia=cls.familia, nome="Compras Cartão")

    def test_get_fatura_aberta_calcula_corretamente(self):
        hoje = date(2025, 10, 15)
        cartao = CartaoDeCredito.objects.create(
            familia=self.familia, nome="Cartão de Teste",
            limite=Decimal('5000.00'), dia_fechamento=25, dia_vencimento=10
        )
        Despesa.objects.create(user=self.user, cartao=cartao, categoria=self.cat_cartao, valor=Decimal('100.00'), data=date(2025, 10, 5), descricao="Compra no mercado")
        Despesa.objects.create(user=self.user, cartao=cartao, categoria=self.cat_cartao, valor=Decimal('50.00'), data=date(2025, 9, 20), descricao="Compra antiga")
        Despesa.objects.create(user=self.user, cartao=cartao, categoria=self.cat_cartao, valor=Decimal('200.00'), data=date(2025, 10, 1), descricao="Compra online paga", fatura_paga=True)
        fatura = cartao.get_fatura_aberta(usuarios=[self.user], data_base=hoje)
        self.assertEqual(fatura['total'], Decimal('100.00'))
        self.assertEqual(fatura['despesas'].count(), 1)
        self.assertEqual(fatura['despesas'].first().descricao, "Compra no mercado")


class DashboardViewTest(TestCase):

    def setUp(self):
        """
        Configuração que roda ANTES de cada teste nesta classe.
        """
        self.user = User.objects.create_user(username='testuser', password='password123')
        # --- CORREÇÃO: Configurando a família para o usuário de teste ---
        self.familia = Familia.objects.create(nome="Familia de Teste do Dashboard")
        self.user.perfil.familia = self.familia
        self.user.perfil.save()

    def test_dashboard_redireciona_usuario_nao_logado(self):
        """
        Verifica se um usuário não logado é redirecionado para a página de login.
        """
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('login')}?next=/")

    def test_dashboard_acessivel_para_usuario_logado(self):
        """
        Verifica se um usuário logado consegue acessar o dashboard com sucesso.
        """
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/dashboard.html')
        self.assertContains(response, "Dashboard Financeiro")