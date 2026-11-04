#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DATASUS PASP File Downloader
=============================

Baixador de arquivos PASP do FTP do DATASUS com interface gráfica moderna.
Permite seleção de ano/mês e exibe progresso em tempo real do download.

Autor: Sistema de Download DATASUS
Versão: 2.0.0
Data: 2025
"""

__version__ = "2.1.0"
__author__ = "Sistema de Download DATASUS"
__all__ = [
    "config",
    "utils",
    "downloader",
    "gui",
    "DATASUSDownloader",
    "DownloadSummary",
    "DownloaderUI",
]

# Imports principais para facilitar uso do pacote
from .downloader import DATASUSDownloader, DownloadSummary
from .gui import DownloaderUI
