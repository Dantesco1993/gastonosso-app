# GastoNosso — Controle Financeiro Familiar

Aplicação web em **Django** para gerenciar finanças pessoais e familiares: múltiplos usuários em “Famílias”, transações (recorrentes/parceladas), dashboards (Chart.js), metas e painel de configurações.  
Front-end com **Bootstrap 5** e **Chart.js**.

---

## Sumário
- [Stack](#stack)
- [Pré-requisitos](#pré-requisitos)
- [Como rodar localmente](#como-rodar-localmente)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Comandos úteis](#comandos-úteis)
- [Executando testes e lint](#executando-testes-e-lint)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Deploy (Heroku/Fly/Render)](#deploy-herokuflyrender)
- [Boas práticas de produção](#boas-práticas-de-produção)
- [Troubleshooting](#troubleshooting)
- [Licença](#licença)

---

## Stack
- **Python** / **Django**
- **django-crispy-forms** + **crispy-bootstrap5**
- **python-decouple** (variáveis de ambiente)
- **python-dateutil** (datas/`relativedelta`)
- **dj-database-url** (config de DB via `DATABASE_URL`)
- **Whitenoise** (estáticos em produção)
- **Gunicorn** (WSGI server)
- (Opcional) **PostgreSQL** via `DATABASE_URL`

---

## Pré-requisitos
- Python 3.11+ (recomendado)
- pip
- (Opcional) Postgres 13+ se for usar em produção/local com banco externo
- Make (opcional) ou bash/powershell para rodar scripts

---

## Como rodar localmente

```bash
# 1) Criar e ativar venv
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2) Instalar dependências
pip install -r requirements.txt

# 3) Gerar .env a partir do exemplo
cp .env.example .env
# -> edite .env e defina SECRET_KEY, DEBUG, ALLOWED_HOSTS etc.

# 4) Migrar o banco
python manage.py migrate

# 5) (Opcional) Criar superusuário
python manage.py createsuperuser

# 6) Coletar estáticos (mesmo em dev, para validar pipeline)
python manage.py collectstatic --noinput

# 7) Subir o servidor
python manage.py runserver
