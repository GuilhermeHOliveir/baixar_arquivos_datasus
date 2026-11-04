#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Download FTP do DATASUS
==================================

Gerencia conexões FTP e downloads de arquivos PASP do DATASUS.
"""

import ftplib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple

try:  # Permite uso como pacote e execução direta dos scripts.
    from .config import (
        FTP_HOST,
        FTP_BASE_PATH,
        FTP_TIMEOUT,
        FILE_EXTENSION,
        CHUNK_SIZE,
        DEFAULT_DEST_FOLDER,
    )
    from .utils import (
        format_bytes_to_mb,
        generate_sihsus_filename,
        get_desktop_directory,
    )
except ImportError:  # pragma: no cover - caminho de compatibilidade
    from config import (
        FTP_HOST,
        FTP_BASE_PATH,
        FTP_TIMEOUT,
        FILE_EXTENSION,
        CHUNK_SIZE,
        DEFAULT_DEST_FOLDER,
    )
    from utils import (
        format_bytes_to_mb,
        generate_sihsus_filename,
        get_desktop_directory,
    )


PERIOD_FILENAME_RE = re.compile(r"^PASP(\d{2})(\d{2})[a-z]\.dbc$", re.IGNORECASE)

SIGTAP_FILENAME_RE = re.compile(
    r"^TabelaUnificada_(\d{4})(0[1-9]|1[0-2])_v(\d+)\.zip$", re.IGNORECASE
)


@dataclass(frozen=True)
class DownloadSummary:
    """Resultado detalhado de um download mensal."""

    downloaded: int = 0
    existing: int = 0
    unavailable: int = 0
    failed: int = 0


class DATASUSDownloader:
    """
    Gerenciador de downloads de arquivos PASP do servidor FTP do DATASUS.
    
    Attributes:
        host: Endereço do servidor FTP.
        base_path: Caminho base no servidor FTP.
        ftp: Conexão FTP ativa (ou None se desconectado).
    """
    
    def __init__(
        self,
        host: str = FTP_HOST,
        base_path: str = FTP_BASE_PATH,
        timeout: int = FTP_TIMEOUT,
    ):
        """
        Inicializa o downloader.
        
        Args:
            host: Endereço do servidor FTP (padrão: FTP_HOST).
            base_path: Caminho base no servidor (padrão: FTP_BASE_PATH).
        """
        self.host = host
        self.base_path = base_path
        self.timeout = timeout
        self.ftp: Optional[ftplib.FTP] = None
    
    def connect(self, log_callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Conecta ao servidor FTP do DATASUS.
        
        Args:
            log_callback: Função opcional para registrar mensagens de log.
        
        Raises:
            ftplib.all_errors: Em caso de erro na conexão FTP.
        """
        if log_callback:
            log_callback(f"🔌 Conectando ao servidor {self.host}...")
        
        ftp = ftplib.FTP(timeout=self.timeout)
        try:
            ftp.connect(self.host)
            ftp.login()
            ftp.cwd(self.base_path)
        except Exception:
            try:
                ftp.close()
            finally:
                self.ftp = None
            raise

        self.ftp = ftp
        
        if log_callback:
            log_callback("✓ Conectado ao servidor FTP.")
    
    def disconnect(self) -> None:
        """Desconecta do servidor FTP se estiver conectado."""
        if self.ftp:
            try:
                self.ftp.quit()
            except ftplib.all_errors + (OSError,):
                pass
            finally:
                self.ftp = None
    
    def list_available_files(self) -> Set[str]:
        """
        Lista todos os arquivos disponíveis no diretório atual do FTP.
        
        Returns:
            Set[str]: Conjunto com nomes dos arquivos disponíveis.
        
        Raises:
            RuntimeError: Se não estiver conectado ao servidor.
        """
        if not self.ftp:
            raise RuntimeError("Não conectado ao servidor FTP. Chame connect() primeiro.")
        
        try:
            names = self.ftp.nlst("PASP*.dbc")
        except ftplib.error_perm:
            # Alguns servidores não aceitam curingas em NLST.
            names = self.ftp.nlst()
        return {Path(name).name for name in names if PERIOD_FILENAME_RE.match(Path(name).name)}

    def list_available_periods(
        self, file_type: str = "PASP", state: str = "SP"
    ) -> List[Tuple[str, str]]:
        """Retorna os períodos publicados para PASP, RD, SP ou SIGTAP."""
        normalized_type = file_type.upper()
        if normalized_type == "PASP":
            filenames = self.list_available_files()
            filename_re = PERIOD_FILENAME_RE
        elif normalized_type == "SIGTAP":
            return sorted({
                match.groups()[:2]
                for filename in self.list_sigtap_files()
                for match in [SIGTAP_FILENAME_RE.fullmatch(filename)]
                if match
            })
        elif normalized_type in {"RD", "SP"}:
            if not self.ftp:
                raise RuntimeError("Não conectado ao servidor FTP. Chame connect() primeiro.")
            normalized_state = state.upper()
            filename_re = re.compile(
                rf"^{normalized_type}{normalized_state}(\d{{2}})(\d{{2}})\.dbc$",
                re.IGNORECASE,
            )
            try:
                names = self.ftp.nlst(f"{normalized_type}{normalized_state}*.dbc")
            except ftplib.error_perm:
                names = self.ftp.nlst()
            filenames = {Path(name).name for name in names}
        else:
            raise ValueError("Tipo de arquivo deve ser PASP, RD, SP ou SIGTAP.")

        periods = set()
        for filename in filenames:
            match = filename_re.match(filename)
            if match:
                year_suffix, month = match.groups()
                periods.add((f"20{year_suffix}", month))
        return sorted(periods)

    def list_sigtap_files(self) -> Set[str]:
        """Descobre os ZIPs da tabela, sem presumir a versão de publicação."""
        if not self.ftp:
            raise RuntimeError("Não conectado ao servidor FTP. Chame connect() primeiro.")
        try:
            names = self.ftp.nlst("TabelaUnificada_*.zip")
        except ftplib.error_perm:
            names = self.ftp.nlst()
        return {
            Path(name).name for name in names
            if SIGTAP_FILENAME_RE.fullmatch(Path(name).name)
        }

    def download_sigtap_file(
        self,
        year: str,
        month: str,
        destination_base: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> DownloadSummary:
        """Baixa a versão mais recente publicada para a competência SIGTAP."""
        if not re.fullmatch(r"\d{4}", year):
            raise ValueError("Ano deve ter quatro algarismos.")
        if not re.fullmatch(r"(?:0[1-9]|1[0-2])", month):
            raise ValueError("Mês deve estar entre 01 e 12.")
        candidates = []
        for filename in self.list_sigtap_files():
            match = SIGTAP_FILENAME_RE.fullmatch(filename)
            if match and match.groups()[:2] == (year, month):
                candidates.append((int(match.group(3)), filename))
        if not candidates:
            if log_callback:
                log_callback(f"⚠️  Nenhuma tabela SIGTAP publicada para {month}/{year}.")
            return DownloadSummary(unavailable=1)
        filename = max(candidates)[1]
        if destination_base is None:
            destination_base = get_desktop_directory() / DEFAULT_DEST_FOLDER
        destination_dir = destination_base / "SIGTAP" / year / month
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / filename
        if log_callback:
            log_callback(f"📂 Diretório: {destination_dir}")
        if destination.exists():
            remote_size = self._remote_size(filename)
            if remote_size is None or destination.stat().st_size == remote_size:
                if log_callback:
                    log_callback(f"⏭️  Já existe e está íntegro: {filename}")
                return DownloadSummary(existing=1)
        success = self.download_file(
            filename, destination, progress_callback, log_callback
        )
        return DownloadSummary(downloaded=int(success), failed=int(not success))

    def _remote_size(self, filename: str) -> Optional[int]:
        """Obtém o tamanho remoto quando o servidor oferece o comando SIZE."""
        if not self.ftp:
            raise RuntimeError("Não conectado ao servidor FTP. Chame connect() primeiro.")
        try:
            return self.ftp.size(filename)
        except ftplib.error_perm:
            return None
    
    def download_file(
        self,
        filename: str,
        destination: Path,
        progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Baixa um único arquivo do servidor FTP.
        
        Args:
            filename: Nome do arquivo no servidor.
            destination: Caminho local de destino.
            progress_callback: Callback para atualizar progresso (bytes_baixados, total_bytes).
            log_callback: Callback para mensagens de log.
        
        Returns:
            bool: True se o download foi bem-sucedido, False caso contrário.
        
        Raises:
            RuntimeError: Se não estiver conectado ao servidor.
        """
        if not self.ftp:
            raise RuntimeError("Não conectado ao servidor FTP. Chame connect() primeiro.")
        
        if log_callback:
            log_callback(f"⬇️  Baixando {filename}...")
        
        # Tenta obter o tamanho do arquivo
        file_size = self._remote_size(filename)
        
        bytes_downloaded = 0
        
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial_destination = destination.with_name(destination.name + ".part")

        try:
            partial_destination.unlink(missing_ok=True)
            with open(partial_destination, "wb") as output_file:
                # Callback para cada chunk recebido
                def write_chunk(chunk: bytes) -> None:
                    """Escreve chunk no arquivo e atualiza progresso."""
                    nonlocal bytes_downloaded
                    output_file.write(chunk)
                    bytes_downloaded += len(chunk)
                    
                    # Atualiza callback de progresso se fornecido
                    if progress_callback:
                        progress_callback(bytes_downloaded, file_size)
                
                # Baixa o arquivo em modo binário
                self.ftp.retrbinary(f"RETR {filename}", write_chunk, blocksize=CHUNK_SIZE)

            if file_size is not None and bytes_downloaded != file_size:
                raise OSError(
                    f"arquivo incompleto: recebido {bytes_downloaded}, esperado {file_size} bytes"
                )

            partial_destination.replace(destination)
            
            # Sucesso
            if log_callback:
                size_str = format_bytes_to_mb(bytes_downloaded)
                log_callback(f"✓ Baixado: {filename} ({size_str})")
            
            return True
            
        except Exception as exc:
            # Remove arquivo parcial em caso de erro
            partial_destination.unlink(missing_ok=True)
            
            if log_callback:
                log_callback(f"❌ Falha: {filename} - {exc}")
            
            return False
    
    def download_monthly_files(
        self,
        year: str,
        month: str,
        destination_base: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        category: Optional[str] = None,
    ) -> DownloadSummary:
        """
        Baixa todas as partes PASP publicadas para um mês específico.
        
        Args:
            year: Ano dos arquivos (ex: "2025").
            month: Mês dos arquivos (formato: "01" a "12").
            destination_base: Diretório base de destino (padrão: Desktop/ARQUIVOS-DATASUS).
            progress_callback: Callback para atualizar progresso.
            log_callback: Callback para mensagens de log.
        
        Returns:
            DownloadSummary: Contadores de baixados, existentes, indisponíveis e falhos.
        
        Raises:
            RuntimeError: Se não estiver conectado ao servidor.
        """
        if not self.ftp:
            raise RuntimeError("Não conectado ao servidor FTP. Chame connect() primeiro.")

        if not re.fullmatch(r"\d{4}", year):
            raise ValueError("Ano deve ter quatro algarismos.")
        if not re.fullmatch(r"(?:0[1-9]|1[0-2])", month):
            raise ValueError("Mês deve estar entre 01 e 12.")
        
        # Define diretório de destino
        if destination_base is None:
            desktop = get_desktop_directory()
            destination_base = desktop / DEFAULT_DEST_FOLDER
        
        destination_dir = destination_base
        if category:
            destination_dir = destination_dir / category
        destination_dir = destination_dir / year / month
        destination_dir.mkdir(parents=True, exist_ok=True)
        
        if log_callback:
            log_callback(f"📂 Diretório: {destination_dir}")
        
        # Lista arquivos disponíveis no servidor
        available_files = self.list_available_files()
        
        if log_callback:
            log_callback(f"✓ {len(available_files)} arquivos disponíveis no servidor.")
        
        files_downloaded = 0
        files_existing = 0
        files_unavailable = 0
        files_failed = 0
        
        year_suffix = f"{int(year) % 100:02d}"
        selected_period_re = re.compile(
            rf"^PASP{year_suffix}{month}[a-z]\.dbc$", re.IGNORECASE
        )
        period_files = sorted(
            filename for filename in available_files if selected_period_re.match(filename)
        )

        if not period_files:
            if log_callback:
                log_callback(f"⚠️  Nenhum arquivo PASP publicado para {month}/{year}.")
            return DownloadSummary(unavailable=1)

        if log_callback:
            log_callback(
                f"✓ {len(period_files)} arquivo(s) PASP encontrado(s) para {month}/{year}."
            )

        # Baixa exatamente todas as partes publicadas para o período escolhido.
        for filename in period_files:
            destination_file = destination_dir / filename
            
            # Verifica se já foi baixado anteriormente
            if destination_file.exists():
                remote_size = self._remote_size(filename)
                if remote_size is None or destination_file.stat().st_size == remote_size:
                    if log_callback:
                        log_callback(f"⏭️  Já existe e está íntegro: {filename}")
                    files_existing += 1
                    continue
                if log_callback:
                    log_callback(f"🔄 Arquivo local incompleto; baixando novamente: {filename}")
            
            # Baixa o arquivo
            success = self.download_file(
                filename,
                destination_file,
                progress_callback=progress_callback,
                log_callback=log_callback
            )
            
            if success:
                files_downloaded += 1
            else:
                files_failed += 1
        
        return DownloadSummary(
            downloaded=files_downloaded,
            existing=files_existing,
            unavailable=files_unavailable,
            failed=files_failed,
        )

    def download_sihsus_file(
        self,
        file_type: str,
        year: str,
        month: str,
        state: str = "SP",
        destination_base: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> DownloadSummary:
        """Baixa um arquivo mensal RD ou SP do SIHSUS para a UF informada."""
        if not self.ftp:
            raise RuntimeError("Não conectado ao servidor FTP. Chame connect() primeiro.")
        if not re.fullmatch(r"\d{4}", year):
            raise ValueError("Ano deve ter quatro algarismos.")
        if not re.fullmatch(r"(?:0[1-9]|1[0-2])", month):
            raise ValueError("Mês deve estar entre 01 e 12.")

        normalized_type = file_type.upper()
        filename = generate_sihsus_filename(
            normalized_type, year, month, state, FILE_EXTENSION
        )
        if destination_base is None:
            destination_base = get_desktop_directory() / DEFAULT_DEST_FOLDER

        destination_dir = destination_base / normalized_type / year / month
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_file = destination_dir / filename
        if log_callback:
            log_callback(f"📂 Diretório: {destination_dir}")

        try:
            listed_names = self.ftp.nlst(filename)
            is_available = filename in {Path(name).name for name in listed_names}
        except ftplib.error_perm:
            is_available = False

        if not is_available:
            if log_callback:
                log_callback(f"⚠️  Não encontrado: {filename}")
            return DownloadSummary(unavailable=1)

        if destination_file.exists():
            remote_size = self._remote_size(filename)
            if remote_size is None or destination_file.stat().st_size == remote_size:
                if log_callback:
                    log_callback(f"⏭️  Já existe e está íntegro: {filename}")
                return DownloadSummary(existing=1)
            if log_callback:
                log_callback(f"🔄 Arquivo local incompleto; baixando novamente: {filename}")

        success = self.download_file(
            filename,
            destination_file,
            progress_callback=progress_callback,
            log_callback=log_callback,
        )
        return DownloadSummary(downloaded=1) if success else DownloadSummary(failed=1)
    
    def __enter__(self):
        """Suporte para context manager (with statement)."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Desconecta automaticamente ao sair do context manager."""
        self.disconnect()
        return False
