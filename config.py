#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurações e Constantes do DATASUS Downloader
=================================================

Módulo centralizado com todas as configurações e constantes da aplicação.
"""

from datetime import datetime


# ============================================================================
# CONFIGURAÇÕES DO SERVIDOR FTP
# ============================================================================

FTP_HOST = "ftp.datasus.gov.br"
"""Host do servidor FTP do DATASUS."""

FTP_BASE_PATH = "/dissemin/publicos/SIASUS/200801_/Dados"
"""Caminho base no servidor FTP onde estão os arquivos PASP."""

SIHSUS_FTP_BASE_PATH = "/dissemin/publicos/SIHSUS/200801_/Dados"
"""Caminho base dos arquivos hospitalares RD e SP."""

SIGTAP_FTP_HOST = "ftp2.datasus.gov.br"
SIGTAP_FTP_BASE_PATH = "/pub/sistemas/tup/downloads"

SIHSUS_STATE = "SP"
"""UF usada nos arquivos SIHSUS disponibilizados por esta aplicação."""


# ============================================================================
# CONFIGURAÇÕES DE ARQUIVO
# ============================================================================

FILE_LETTERS = ["a", "b", "c", "d"]
"""Sufixos de letra dos arquivos PASP (PASPYYMMa.dbc, PASPYYMMb.dbc, etc.)."""

FILE_EXTENSION = ".dbc"
"""Extensão dos arquivos PASP."""

CHUNK_SIZE = 8192
"""Tamanho do bloco de download em bytes (8KB)."""

FTP_TIMEOUT = 30
"""Tempo limite, em segundos, para operações de rede FTP."""


# ============================================================================
# CONFIGURAÇÕES DE PERÍODO
# ============================================================================

AVAILABLE_MONTHS = [f"{m:02d}" for m in range(1, 13)]
"""Lista de meses disponíveis no formato "01" a "12"."""

FIRST_AVAILABLE_YEAR = 2008
"""Primeiro ano contemplado pelo diretório de disseminação utilizado."""

AVAILABLE_YEARS = [
    str(y) for y in range(FIRST_AVAILABLE_YEAR, datetime.now().year + 1)
]
"""Lista de anos disponíveis para download."""


# ============================================================================
# CONFIGURAÇÕES DE INTERFACE
# ============================================================================

WINDOW_TITLE = "Central de Arquivos DATASUS"
"""Título da janela principal da aplicação."""

DEFAULT_DEST_FOLDER = "ARQUIVOS-DATASUS"
"""Nome da pasta padrão onde os arquivos serão salvos."""

PROGRESS_ANIMATION_SPEED = 10
"""Velocidade da animação da barra de progresso em modo indeterminado (ms)."""


# ============================================================================
# CONFIGURAÇÕES DE LOG
# ============================================================================

LOG_TIMESTAMP_FORMAT = "%H:%M:%S"
"""Formato do timestamp nas mensagens de log."""

LOG_HEIGHT = 14
"""Altura do widget de log em linhas."""

LOG_WIDTH = 55
"""Largura do widget de log em caracteres."""
