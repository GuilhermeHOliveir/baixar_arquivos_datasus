#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DATASUS PASP File Downloader - Wrapper de Compatibilidade
==========================================================

Este arquivo mantém compatibilidade com execuções do script original.
A aplicação foi modularizada em vários arquivos separados.

Para modificar o código, veja os módulos individuais:
- config.py: Configurações e constantes
- utils.py: Funções auxiliares
- downloader.py: Lógica de download FTP
- gui.py: Interface gráfica
- main.py: Ponto de entrada principal

Autor: Sistema de Download DATASUS
Versão: 2.0.0 (Modular)
Data: 2025
"""

# Importa e executa o módulo principal
try:
    from .main import main
except ImportError:  # pragma: no cover - execução direta
    from main import main

if __name__ == "__main__":
    main()

