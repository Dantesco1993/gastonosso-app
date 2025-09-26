#!/usr/bin/env python
import os
import sys

def main():
    # aponte para o pacote correto do projeto
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "financas_pessoais.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django não está instalado no ambiente virtual atual."
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
