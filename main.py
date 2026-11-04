#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ponto de Entrada Principal
===========================

Script principal para iniciar a aplicação de download DATASUS.
"""

import tkinter as tk

try:
    from .gui import DownloaderUI
except ImportError:  # pragma: no cover - execução direta
    from gui import DownloaderUI


def main() -> None:
    """Função principal - inicializa a aplicação."""
    root = tk.Tk()
    DownloaderUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
