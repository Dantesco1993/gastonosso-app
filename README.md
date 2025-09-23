# Meu Controle Financeiro 💸

## Sobre o Projeto

**Meu Controle Financeiro** é uma aplicação web completa para gerenciamento de finanças pessoais e familiares, desenvolvida do zero com o framework Django. A plataforma permite que múltiplos usuários, organizados em "Famílias", controlem suas transações, analisem seus gastos, definam metas de economia e compartilhem um orçamento de forma segura e intuitiva.

Este projeto foi construído de forma incremental com o objetivo de criar uma ferramenta robusta e prática, explorando diversas funcionalidades do Django, desde o básico até conceitos mais avançados como múltiplos usuários, geração de transações recorrentes e visualização de dados.

## Funcionalidades Principais ✨

* **Autenticação de Usuários**: Sistema completo de Login, Cadastro e Logout.
* **Dashboard Interativo**: Visão geral da saúde financeira com saldo total, balanço do mês e faturas em aberto.
* **Orçamento Familiar Compartilhado**:
    * Criação de "Famílias" através de um código de convite único.
    * Alternância entre a **visão individual** (apenas suas transações) e a **visão em conjunto** (transações de toda a família).
* **Controle de Transações**:
    * Cadastro detalhado de Despesas e Receitas.
    * Suporte a **compras parceladas**.
    * Criação de **transações recorrentes** com frequência flexível (semanal, mensal, anual, etc.).
* **Gerenciamento de Contas e Cartões**: Cadastro de diferentes tipos de contas e cartões de crédito, compartilhados entre a família.
* **Fatura de Cartão de Crédito**: Cálculo e visualização da fatura em aberto com base no dia de fechamento do cartão.
* **Análise de Gastos**: Gráfico de rosca interativo (usando Chart.js) que mostra a distribuição de gastos por categoria no mês.
* **Metas Financeiras**: Definição de metas de economia com acompanhamento visual do progresso (barra de progresso).
* **Painel de Configurações**: Interface amigável para gerenciar Categorias, Contas e Cartões.

## Tecnologias Utilizadas 🛠️

* **Backend**: Python, Django
* **Frontend**: HTML5, CSS3, Bootstrap 5
* **JavaScript**: Chart.js
* **Banco de Dados**: SQLite3 (para desenvolvimento)
* **Bibliotecas Python Notáveis**:
    * `django-crispy-forms` e `crispy-bootstrap5` para renderização de formulários.
    * `python-decouple` para gerenciamento de variáveis de ambiente.
    * `python-dateutil` para cálculos de data avançados.

## Como Executar o Projeto Localmente

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/Dantesco1993/meu-controle-financeiro.git](https://github.com/Dantesco1993/meu-controle-financeiro.git)
    cd meu-controle-financeiro
    ```
    *(Substitua pela URL do seu repositório)*

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS / Linux
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as variáveis de ambiente:**
    * Crie um arquivo chamado `.env` na raiz do projeto.
    * Adicione a seguinte linha dentro dele e gere uma nova chave secreta:
        ```
        SECRET_KEY=sua_nova_chave_secreta_aqui
        ```

5.  **Execute as migrações e crie um superusuário:**
    ```bash
    python manage.py migrate
    python manage.py createsuperuser
    ```

6.  **Rode o servidor de desenvolvimento:**
    ```bash
    python manage.py runserver
    ```
    A aplicação estará disponível em `http://127.0.0.1:8000/`.