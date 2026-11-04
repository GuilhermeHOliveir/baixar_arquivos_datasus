# Histórico de alterações

## 2026-11-04 — Download de competências SIGTAP

### Funcionalidade

- Adicionado o cartão **Tabela SIGTAP** com o botão **Baixar SIGTAP**, seguindo
  as cores, tipografia, estrutura e comportamento dos cartões PASP, RD e SP.
- Ampliada a janela para 1120 × 760, com tamanho mínimo de 1080 × 700,
  para acomodar os quatro cartões.
- Reutilizados os seletores de ano e mês, a pasta de destino, a barra de
  progresso, o log e a abertura da pasta após o processamento.
- Incluída a consulta automática da última competência SIGTAP publicada.

### Fonte e seleção dos arquivos

- Servidor: `ftp2.datasus.gov.br`, com acesso FTP anônimo.
- Diretório: `/pub/sistemas/tup/downloads`.
- Padrão: `TabelaUnificada_AAAAMM_vVERSAO.zip`.
- Exemplo confirmado no servidor: `TabelaUnificada_202610_v2610271043.zip`.
- A competência é obtida do trecho `AAAAMM`; o sufixo de versão é descoberto
  na listagem FTP, sem construir um nome fixo a partir da data atual.
- Quando há mais de uma versão para a competência, é selecionado o maior
  número de versão. Entradas fora do padrão e meses inválidos são ignorados.
- O ZIP é salvo sem extração em `PASTA_ESCOLHIDA/SIGTAP/ANO/MÊS/`.
- Reutilizado o download com arquivo temporário `.part`, conferência de tamanho
  quando disponível, reconhecimento de arquivos existentes e resumo de resultados.

### Arquivos alterados

- `config.py`: host e diretório FTP específicos do SIGTAP.
- `downloader.py`: descoberta de arquivos e competências e download da versão
  mais recente da tabela para o período selecionado.
- `gui.py`: cartão SIGTAP, escolha do servidor por tipo, integração do download
  e ajuste das dimensões da janela.
- `tests/test_downloader.py`: testes de seleção de versão, descoberta de
  competências, arquivo existente, substituição de arquivo incompleto,
  competência ausente, falha de download e validação de período.
- `README.md`: funcionalidade, organização das pastas e fonte SIGTAP.

### Validação realizada

- `python -m unittest discover -v`: 13 testes aprovados.
- `python -m doctest utils.py`: concluído sem falhas.
- `python -m py_compile gui.py downloader.py config.py`: concluído sem erros.
- Fluxo dos quatro botões verificado com mocks: chamada do método correto,
  desconexão, resumo e encaminhamento da pasta correspondente.
- Dimensões dos widgets verificadas via Tkinter nos tamanhos 1120 × 760 e
  1080 × 700, sem exceder a largura disponível nos cartões.
- Downloads reais por FTP nas competências mais recentes encontradas:

| Tipo | Competência | Arquivos baixados | Total em bytes |
| --- | --- | ---: | ---: |
| PASP | 08/2026 | 4 | 538.847.863 |
| RD | 08/2026 | 1 | 20.522.295 |
| SP | 08/2026 | 1 | 80.589.383 |
| SIGTAP | 10/2026 | 1 | 2.163.764 |

- Tamanhos locais comparados com o comando `SIZE` do FTP para todos os arquivos.
- Repetição do download nos quatro tipos reconheceu todos os arquivos como
  existentes, sem novos downloads ou falhas.
- ZIP SIGTAP 10/2026 verificado com `ZipFile.testzip()`: 87 entradas,
  sem erro de integridade.
- Downloads de teste realizados em diretórios temporários, removidos ao final;
  confirmada a ausência de arquivos de teste remanescentes no projeto.

### Compilação e controle de versão

- Executável recompilado após a regressão com `build_exe.bat`, usando
  PyInstaller 6.18.0 e Python 3.8.10.
- Artefato: `dist/DATASUS-Downloader.exe`.
- O número declarado em `pyproject.toml` permanece `2.1.0`; esta alteração
  não recebeu um novo número de versão no pacote.
- Em 04/11/2026, a pasta não era um repositório Git: não havia metadados `.git`
  reconhecidos e `git rev-parse --show-toplevel` retornou erro.
- O Git estava instalado (2.50.1.windows.1) e havia um arquivo `.gitignore`,
  o que por si só não inicializa o controle de versão.

### Publicação inicial do código

- Repositório Git inicializado posteriormente em 04/11/2026, na branch `main`.
- Configurados `origin` para o GitLab da Santa Casa e `github` para o
  repositório privado `GuilhermeHOliveir/baixar_arquivos_datasus` no GitHub.
- Incluídos código-fonte, testes, documentação, recursos visuais e script de build.
- Executáveis, artefatos de compilação e caches permanecem fora do versionamento.
