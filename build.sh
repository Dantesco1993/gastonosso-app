#!/usr/bin/env bash
set -euo pipefail

python --version
python -m pip install --upgrade pip
pip install -r requirements.txt

# Coleta estáticos para produção
python manage.py collectstatic --noinput
