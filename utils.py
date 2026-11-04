#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Funções Utilitárias do DATASUS Downloader
==========================================

Módulo com funções auxiliares reutilizáveis.
"""

import os
from pathlib import Path


def get_desktop_directory() -> Path:
    """
    Detecta o diretório da área de trabalho do usuário.
    
    Tenta encontrar o diretório Desktop nos caminhos mais comuns:
    - ~/Desktop (Unix-like)
    - %USERPROFILE%/Desktop (Windows)
    
    Returns:
        Path: Caminho para o Desktop ou Home do usuário como fallback.
    
    Examples:
        >>> from pathlib import Path
        >>> desktop = get_desktop_directory()
        >>> isinstance(desktop, Path)
        True
    """
    desktop_candidates = [
        Path(os.path.expanduser("~/Desktop")),
        Path(os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")),
    ]
    
    for candidate in desktop_candidates:
        if candidate.is_dir():
            return candidate
    
    # Fallback para o diretório home se Desktop não for encontrado
    return Path.home()


def format_bytes_to_mb(bytes_value: int) -> str:
    """
    Formata um valor em bytes para megabytes com duas casas decimais.
    
    Args:
        bytes_value: Valor em bytes.
    
    Returns:
        str: Valor formatado em MB (ex: "15.23 MB").
    
    Examples:
        >>> format_bytes_to_mb(1048576)
        '1.00 MB'
        >>> format_bytes_to_mb(15728640)
        '15.00 MB'
    """
    mb_value = bytes_value / (1024 * 1024)
    return f"{mb_value:.2f} MB"


def generate_filename(year: str, month: str, letter: str, extension: str = ".dbc") -> str:
    """
    Gera o nome do arquivo PASP baseado em ano, mês e letra.
    
    Args:
        year: Ano completo (ex: "2025").
        month: Mês no formato "01" a "12".
        letter: Letra sufixo do arquivo ("a", "b", "c", "d").
        extension: Extensão do arquivo (padrão: ".dbc").
    
    Returns:
        str: Nome do arquivo no formato "PASPYYMMl.dbc".
    
    Examples:
        >>> generate_filename("2025", "01", "a")
        'PASP2501a.dbc'
        >>> generate_filename("2024", "12", "d")
        'PASP2412d.dbc'
    """
    year_suffix = f"{int(year) % 100:02d}"
    return f"PASP{year_suffix}{month}{letter}{extension}"


def generate_sihsus_filename(
    file_type: str,
    year: str,
    month: str,
    state: str = "SP",
    extension: str = ".dbc",
) -> str:
    """Gera nomes SIHSUS no formato ``TIPOUFYYMM.dbc``."""
    normalized_type = file_type.upper()
    normalized_state = state.upper()
    if normalized_type not in {"RD", "SP"}:
        raise ValueError("Tipo SIHSUS deve ser RD ou SP.")
    if len(normalized_state) != 2 or not normalized_state.isalpha():
        raise ValueError("UF deve conter duas letras.")
    year_suffix = f"{int(year) % 100:02d}"
    return f"{normalized_type}{normalized_state}{year_suffix}{month}{extension}"
