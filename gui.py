#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interface gráfica da Central de Arquivos DATASUS."""

import ftplib
import os
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

try:  # Permite uso como pacote e execução direta.
    from .config import (
        AVAILABLE_MONTHS,
        AVAILABLE_YEARS,
        DEFAULT_DEST_FOLDER,
        FTP_BASE_PATH,
        FTP_HOST,
        SIGTAP_FTP_HOST,
        SIGTAP_FTP_BASE_PATH,
        LOG_HEIGHT,
        LOG_TIMESTAMP_FORMAT,
        PROGRESS_ANIMATION_SPEED,
        SIHSUS_FTP_BASE_PATH,
        SIHSUS_STATE,
        WINDOW_TITLE,
    )
    from .downloader import DATASUSDownloader, DownloadSummary
    from .utils import get_desktop_directory
except ImportError:  # pragma: no cover - compatibilidade com scripts
    from config import (
        AVAILABLE_MONTHS,
        AVAILABLE_YEARS,
        DEFAULT_DEST_FOLDER,
        FTP_BASE_PATH,
        FTP_HOST,
        SIGTAP_FTP_HOST,
        SIGTAP_FTP_BASE_PATH,
        LOG_HEIGHT,
        LOG_TIMESTAMP_FORMAT,
        PROGRESS_ANIMATION_SPEED,
        SIHSUS_FTP_BASE_PATH,
        SIHSUS_STATE,
        WINDOW_TITLE,
    )
    from downloader import DATASUSDownloader, DownloadSummary
    from utils import get_desktop_directory


MONTH_LABELS = (
    "01 · Janeiro", "02 · Fevereiro", "03 · Março", "04 · Abril",
    "05 · Maio", "06 · Junho", "07 · Julho", "08 · Agosto",
    "09 · Setembro", "10 · Outubro", "11 · Novembro", "12 · Dezembro",
)

DOWNLOAD_TYPES = {
    "PASP": {
        "eyebrow": "SIASUS · PRODUÇÃO AMBULATORIAL",
        "title": "Arquivos PASP",
        "description": "Baixa todas as partes publicadas para o período selecionado.",
        "color": "#176B87",
        "base_path": FTP_BASE_PATH,
    },
    "RD": {
        "eyebrow": "SIHSUS · SÃO PAULO",
        "title": "AIH Reduzida",
        "description": "Dados hospitalares consolidados da AIH para a UF São Paulo.",
        "color": "#C25832",
        "base_path": SIHSUS_FTP_BASE_PATH,
    },
    "SP": {
        "eyebrow": "SIHSUS · SÃO PAULO",
        "title": "Serviços Profissionais",
        "description": "Procedimentos e serviços profissionais vinculados às internações.",
        "color": "#5B5F97",
        "base_path": SIHSUS_FTP_BASE_PATH,
    },
    "SIGTAP": {
        "eyebrow": "SIGTAP · TABELA UNIFICADA",
        "title": "Tabela SIGTAP",
        "description": "Tabela de procedimentos do SUS na versão mais recente da competência.",
        "color": "#167D62",
        "base_path": SIGTAP_FTP_BASE_PATH,
        "host": SIGTAP_FTP_HOST,
    },
}


def resource_path(relative_path: str) -> Path:
    """Resolve recursos tanto no código-fonte quanto no executável PyInstaller."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


class DownloaderUI:
    """Interface Tkinter para downloads mensais PASP, RD, SP e SIGTAP."""

    BG = "#F3F6F7"
    CARD = "#FFFFFF"
    INK = "#18323B"
    MUTED = "#607780"
    BORDER = "#D8E2E5"
    SUCCESS = "#167D62"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry("1120x760")
        self.root.minsize(1080, 700)
        self.root.configure(bg=self.BG)
        self._icon_image: Optional[tk.PhotoImage] = None
        self._apply_window_icon()

        current_month = datetime.now().month
        self.year_var = tk.StringVar(value=str(datetime.now().year))
        self.month_var = tk.StringVar(value=MONTH_LABELS[current_month - 1])
        self.destination_var = tk.StringVar(
            value=str(get_desktop_directory() / DEFAULT_DEST_FOLDER)
        )
        self.status_var = tk.StringVar(value="Pronto para baixar")
        self.latest_period_vars = {
            file_type: tk.StringVar(value="Consultando último período…")
            for file_type in DOWNLOAD_TYPES
        }
        self.progress_var = tk.IntVar(value=0)
        self.downloader: Optional[DATASUSDownloader] = None
        self._active_type: Optional[str] = None
        self._is_downloading = False
        self._ui_queue = Queue()  # type: Queue[Tuple[Callable[..., Any], tuple]]
        self.download_buttons: Dict[str, tk.Button] = {}

        self._configure_styles()
        self._build_user_interface()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(50, self._process_ui_queue)
        self._start_period_discovery()

    def _apply_window_icon(self) -> None:
        """Aplica o ícone do aplicativo na janela e na barra de tarefas."""
        try:
            icon_path = resource_path("assets/datasus-downloader.ico")
            self.root.iconbitmap(default=str(icon_path))
        except tk.TclError:
            pass
        try:
            png_path = resource_path("assets/datasus-downloader.png")
            self._icon_image = tk.PhotoImage(file=str(png_path))
            self.root.iconphoto(True, self._icon_image)
        except (tk.TclError, OSError):
            self._icon_image = None

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure(
            "Period.TCombobox",
            padding=7,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Data.Horizontal.TProgressbar",
            troughcolor="#E1E9EB",
            background="#1A809B",
            bordercolor="#E1E9EB",
            lightcolor="#1A809B",
            darkcolor="#1A809B",
        )

    def _build_user_interface(self) -> None:
        shell = tk.Frame(self.root, bg=self.BG, padx=30, pady=24)
        shell.pack(fill="both", expand=True)

        tk.Label(
            shell, text="CENTRAL DATASUS", bg=self.BG, fg="#1A809B",
            font=("Segoe UI Semibold", 9),
        ).pack(anchor="w")
        tk.Label(
            shell, text="Download de arquivos mensais", bg=self.BG, fg=self.INK,
            font=("Segoe UI Semibold", 24),
        ).pack(anchor="w", pady=(2, 2))
        tk.Label(
            shell,
            text="Escolha o período uma vez e baixe somente a base de que precisa.",
            bg=self.BG, fg=self.MUTED, font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 18))

        controls = tk.Frame(
            shell, bg=self.CARD, highlightbackground=self.BORDER,
            highlightthickness=1, padx=18, pady=14,
        )
        controls.pack(fill="x", pady=(0, 14))
        controls.grid_columnconfigure(2, weight=1)

        self._field_label(controls, "ANO").grid(row=0, column=0, sticky="w")
        self._field_label(controls, "MÊS").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self._field_label(controls, "PASTA DE DESTINO").grid(
            row=0, column=2, sticky="w", padx=(12, 0)
        )

        self.year_combo = ttk.Combobox(
            controls, textvariable=self.year_var,
            values=tuple(reversed(AVAILABLE_YEARS)), state="readonly", width=9,
            style="Period.TCombobox",
        )
        self.year_combo.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.month_combo = ttk.Combobox(
            controls, textvariable=self.month_var, values=MONTH_LABELS,
            state="readonly", width=17, style="Period.TCombobox",
        )
        self.month_combo.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(5, 0))

        destination_row = tk.Frame(controls, bg=self.CARD)
        destination_row.grid(row=1, column=2, sticky="ew", padx=(12, 0), pady=(5, 0))
        destination_row.grid_columnconfigure(0, weight=1)
        destination_entry = tk.Entry(
            destination_row, textvariable=self.destination_var, state="readonly",
            readonlybackground="#F7F9FA", fg=self.INK, relief="flat",
            highlightbackground=self.BORDER, highlightthickness=1,
            font=("Segoe UI", 9),
        )
        destination_entry.grid(row=0, column=0, sticky="nsew", ipady=8)
        tk.Button(
            destination_row, text="Escolher", command=self.choose_destination,
            bg="#E8EFF1", fg=self.INK, activebackground="#DCE7EA",
            activeforeground=self.INK, relief="flat", bd=0, cursor="hand2",
            font=("Segoe UI Semibold", 9), padx=12, pady=7,
        ).grid(row=0, column=1, padx=(8, 0))

        cards = tk.Frame(shell, bg=self.BG)
        cards.pack(fill="x")
        for index, (file_type, details) in enumerate(DOWNLOAD_TYPES.items()):
            cards.grid_columnconfigure(index, weight=1, uniform="cards")
            self._build_download_card(cards, file_type, details, index)

        activity = tk.Frame(
            shell, bg=self.CARD, highlightbackground=self.BORDER,
            highlightthickness=1, padx=16, pady=14,
        )
        activity.pack(fill="both", expand=True, pady=(14, 0))
        header = tk.Frame(activity, bg=self.CARD)
        header.pack(fill="x")
        tk.Label(
            header, text="ATIVIDADE", bg=self.CARD, fg=self.MUTED,
            font=("Segoe UI Semibold", 8),
        ).pack(side="left")
        tk.Label(
            header, textvariable=self.status_var, bg=self.CARD, fg=self.SUCCESS,
            font=("Segoe UI Semibold", 9),
        ).pack(side="right")
        self.progress_bar = ttk.Progressbar(
            activity, orient="horizontal", mode="determinate", maximum=100,
            variable=self.progress_var, style="Data.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill="x", pady=(10, 10))

        log_frame = tk.Frame(activity, bg="#102A33")
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(
            log_frame, height=LOG_HEIGHT, state="disabled", wrap="word",
            font=("Cascadia Mono", 8), bg="#102A33", fg="#D7E7EA",
            insertbackground="#D7E7EA", selectbackground="#285868",
            relief="flat", borderwidth=0, padx=12, pady=10,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

    def _field_label(self, parent: tk.Widget, text: str) -> tk.Label:
        return tk.Label(
            parent, text=text, bg=self.CARD, fg=self.MUTED,
            font=("Segoe UI Semibold", 8),
        )

    def _build_download_card(
        self, parent: tk.Frame, file_type: str, details: Dict[str, str], column: int
    ) -> None:
        card = tk.Frame(
            parent, bg=self.CARD, highlightbackground=self.BORDER,
            highlightthickness=1, padx=16, pady=15,
        )
        card.grid(
            row=0, column=column, sticky="nsew",
            padx=(0 if column == 0 else 6, 0 if column == len(DOWNLOAD_TYPES) - 1 else 6),
        )
        tk.Frame(card, bg=details["color"], height=4).pack(fill="x", pady=(0, 12))
        tk.Label(
            card, text=details["eyebrow"], bg=self.CARD, fg=details["color"],
            font=("Segoe UI Semibold", 7),
        ).pack(anchor="w")
        tk.Label(
            card, text=details["title"], bg=self.CARD, fg=self.INK,
            font=("Segoe UI Semibold", 14),
        ).pack(anchor="w", pady=(3, 6))
        tk.Label(
            card, text=details["description"], bg=self.CARD, fg=self.MUTED,
            font=("Segoe UI", 9), justify="left", wraplength=210,
        ).pack(anchor="w")
        tk.Label(
            card, textvariable=self.latest_period_vars[file_type],
            bg=self.CARD, fg=details["color"],
            font=("Segoe UI Semibold", 8),
        ).pack(anchor="w", pady=(10, 12))
        button = tk.Button(
            card, text=f"Baixar {file_type}",
            command=lambda selected=file_type: self.start_download_thread(selected),
            bg=details["color"], fg="#FFFFFF", activebackground=details["color"],
            activeforeground="#FFFFFF", disabledforeground="#D8E2E5",
            relief="flat", bd=0, cursor="hand2", font=("Segoe UI Semibold", 9),
            padx=14, pady=9,
        )
        button.pack(fill="x", side="bottom")
        self.download_buttons[file_type] = button

    def choose_destination(self) -> None:
        selected = filedialog.askdirectory(
            title="Escolha a pasta de destino", initialdir=self.destination_var.get()
        )
        if selected:
            self.destination_var.set(selected)

    def _enqueue_ui(self, callback: Callable[..., Any], *args: Any) -> None:
        self._ui_queue.put((callback, args))

    def _process_ui_queue(self) -> None:
        try:
            while True:
                callback, args = self._ui_queue.get_nowait()
                callback(*args)
        except Empty:
            pass
        try:
            if self.root.winfo_exists():
                self.root.after(50, self._process_ui_queue)
        except tk.TclError:
            pass

    def _start_period_discovery(self) -> None:
        self.status_var.set("Consultando últimos períodos…")
        threading.Thread(target=self._discover_periods, daemon=True).start()

    def _discover_periods(self) -> None:
        latest_periods = {}  # type: Dict[str, Optional[Tuple[str, str]]]
        for file_type, details in DOWNLOAD_TYPES.items():
            downloader = DATASUSDownloader(
                host=details.get("host", FTP_HOST), base_path=details["base_path"]
            )
            try:
                downloader.connect()
                periods = downloader.list_available_periods(file_type, SIHSUS_STATE)
                latest_periods[file_type] = periods[-1] if periods else None
            except Exception as exc:
                latest_periods[file_type] = None
                self.log_message(
                    f"Aviso: não foi possível consultar o último período {file_type}: {exc}"
                )
            finally:
                downloader.disconnect()
        self._enqueue_ui(self._apply_available_periods, latest_periods)

    def _apply_available_periods(
        self, latest_periods: Dict[str, Optional[Tuple[str, str]]]
    ) -> None:
        available_labels = []
        for file_type, period in latest_periods.items():
            if period:
                year, month = period
                label = f"Último disponível: {month}/{year}"
                available_labels.append(f"{file_type} {month}/{year}")
            else:
                label = "Último período indisponível"
            self.latest_period_vars[file_type].set(label)
        self.status_var.set("Períodos atualizados")
        if available_labels:
            self._append_to_log("Últimos períodos: " + " · ".join(available_labels) + ".")

    def start_download_thread(self, file_type: str = "PASP") -> None:
        year = self.year_var.get()
        month = self.month_var.get()[:2]
        destination = self.destination_var.get().strip()
        if year not in AVAILABLE_YEARS:
            messagebox.showerror("Período inválido", "Selecione um ano válido.")
            return
        if month not in AVAILABLE_MONTHS:
            messagebox.showerror("Período inválido", "Selecione um mês válido.")
            return
        if not destination:
            messagebox.showerror("Destino inválido", "Selecione uma pasta de destino.")
            return
        if file_type not in DOWNLOAD_TYPES:
            messagebox.showerror("Tipo inválido", "Selecione um tipo de arquivo válido.")
            return

        self._set_download_controls(False)
        self._active_type = file_type
        self._is_downloading = True
        self.status_var.set(f"Baixando {file_type}…")
        self.log_message(f"Iniciando {file_type} para {month}/{year}.")
        threading.Thread(
            target=self.execute_download,
            args=(file_type, year, month, Path(destination)), daemon=True,
        ).start()

    def execute_download(
        self, file_type: str, year: str, month: str, destination: Path
    ) -> None:
        details = DOWNLOAD_TYPES[file_type]
        download_directory = destination / file_type / year / month
        should_open_directory = False
        try:
            self.downloader = DATASUSDownloader(
                host=details.get("host", FTP_HOST), base_path=details["base_path"]
            )
            self.downloader.connect(log_callback=self.log_message)
            if file_type == "PASP":
                summary = self.downloader.download_monthly_files(
                    year=year, month=month, destination_base=destination,
                    category="PASP", progress_callback=self.handle_progress,
                    log_callback=self.log_message,
                )
            elif file_type == "SIGTAP":
                summary = self.downloader.download_sigtap_file(
                    year=year, month=month, destination_base=destination,
                    progress_callback=self.handle_progress,
                    log_callback=self.log_message,
                )
            else:
                summary = self.downloader.download_sihsus_file(
                    file_type=file_type, year=year, month=month, state=SIHSUS_STATE,
                    destination_base=destination,
                    progress_callback=self.handle_progress,
                    log_callback=self.log_message,
                )
            self._log_summary(file_type, summary)
            should_open_directory = summary.downloaded > 0 or summary.existing > 0
        except ftplib.all_errors as ftp_error:
            error_msg = f"Erro FTP: {ftp_error}"
            self.log_message(error_msg)
            self._enqueue_ui(messagebox.showerror, "Erro de conexão FTP", error_msg)
        except Exception as exc:
            error_msg = f"Erro inesperado: {exc}"
            self.log_message(error_msg)
            self._enqueue_ui(messagebox.showerror, "Erro", error_msg)
        finally:
            if self.downloader:
                self.downloader.disconnect()
                self.downloader = None
            self._enqueue_ui(
                self._finish_download,
                download_directory if should_open_directory else None,
            )

    def _log_summary(self, file_type: str, summary: DownloadSummary) -> None:
        self.log_message(
            f"{file_type} concluído: {summary.downloaded} baixado(s), "
            f"{summary.existing} já existente(s), "
            f"{summary.unavailable} indisponível(is), {summary.failed} falha(s)."
        )

    def _set_download_controls(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        cursor = "hand2" if enabled else "arrow"
        for button in self.download_buttons.values():
            button.config(state=state, cursor=cursor)
        self.year_combo.config(state="readonly" if enabled else "disabled")
        self.month_combo.config(state="readonly" if enabled else "disabled")

    def _finish_download(self, download_directory: Optional[Path] = None) -> None:
        completed_type = self._active_type or "Download"
        self._is_downloading = False
        self._active_type = None
        self.status_var.set(f"{completed_type} finalizado")
        self.progress_bar.stop()
        self.progress_bar.config(mode="determinate", maximum=100)
        self.progress_var.set(0)
        self._set_download_controls(True)
        if download_directory:
            self._open_download_folder(download_directory)

    def _open_download_folder(self, download_directory: Path) -> None:
        """Abre no Explorador a pasta que contém os arquivos processados."""
        try:
            os.startfile(str(download_directory))  # type: ignore[attr-defined]
            self._append_to_log(f"Pasta aberta: {download_directory}")
        except OSError as exc:
            self._append_to_log(f"Não foi possível abrir a pasta: {exc}")

    def handle_progress(self, current: int, maximum: Optional[int]) -> None:
        self._enqueue_ui(self._apply_progress, current, maximum)

    def _apply_progress(self, current: int, maximum: Optional[int]) -> None:
        if maximum is None:
            if self.progress_bar.cget("mode") != "indeterminate":
                self.progress_bar.config(mode="indeterminate", maximum=100)
                self.progress_bar.start(PROGRESS_ANIMATION_SPEED)
        else:
            if self.progress_bar.cget("mode") != "determinate":
                self.progress_bar.stop()
                self.progress_bar.config(mode="determinate")
            self.progress_bar.config(maximum=maximum)
            self.progress_var.set(current)

    def log_message(self, message: str) -> None:
        self._enqueue_ui(self._append_to_log, message)

    def _append_to_log(self, message: str) -> None:
        self.log_text.config(state="normal")
        timestamp = datetime.now().strftime(LOG_TIMESTAMP_FORMAT)
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def set_status(self, message: str) -> None:
        self._enqueue_ui(self.status_var.set, message)

    def _on_close(self) -> None:
        if self._is_downloading and not messagebox.askyesno(
            "Download em andamento",
            "Um download está em andamento. Deseja fechar mesmo assim?",
        ):
            return
        self.root.destroy()
