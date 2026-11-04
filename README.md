# DATASUS Downloader

Aplicativo desktop para localizar e baixar arquivos mensais do SIASUS, do
SIHSUS e do SIGTAP publicados nos servidores FTP do DATASUS.

## Funcionalidades

- consulta automaticamente o período mais recente publicado;
- baixa todas as partes ambulatoriais `PASPYYMM[letra].dbc` publicadas;
- baixa `RDUFYYMM.dbc` (AIH Reduzida) e `SPUFYYMM.dbc` (Serviços
  Profissionais) do SIHSUS para a UF São Paulo;
- baixa a tabela SIGTAP em ZIP, escolhendo a versão mais recente da competência;
- apresenta cada tipo de arquivo em uma área própria, com botão independente;
- consulta e mostra automaticamente o último período disponível de cada tipo;
- permite escolher a pasta de destino;
- exibe progresso e log sem bloquear a interface;
- valida o tamanho de arquivos existentes e refaz downloads incompletos;
- usa arquivos temporários `.part`, renomeados apenas após o download completo;
- informa separadamente arquivos baixados, existentes, indisponíveis e falhos.
- abre automaticamente a pasta correspondente quando o download termina com
  arquivos baixados ou já existentes.

Ao baixar PASP, o aplicativo consulta o conteúdo publicado para o mês escolhido
e baixa todas as partes encontradas, sem presumir uma quantidade fixa.

Os arquivos baixados pela interface são organizados por tipo:

```text
PASTA_ESCOLHIDA/
├── PASP/ANO/MÊS/PASPYYMM[letra].dbc
├── RD/ANO/MÊS/RDSPYYMM.dbc
├── SP/ANO/MÊS/SPSPYYMM.dbc
└── SIGTAP/ANO/MÊS/TabelaUnificada_AAAAMM_vVERSAO.zip
```

## Executar pelo código-fonte

Requer Python 3.8 ou superior com suporte ao Tkinter. Não existem dependências
de execução externas.

```bash
python baixar_arquivos_datasus.py
```

Como pacote, a partir do diretório pai:

```bash
python -m baixar_arquivos_datasus
```

## Testes

```bash
python -m unittest discover -v
python -m doctest utils.py
```

Os testes de download usam um servidor FTP simulado e não gravam dados fora de
um diretório temporário.

## Gerar o executável Windows

Instale o PyInstaller e execute o script de build:

```bat
py -m pip install pyinstaller
build_exe.bat
```

O resultado será criado em `dist\DATASUS-Downloader.exe`.

## Observações

- O acesso do DATASUS utilizado por este aplicativo é FTP anônimo.
- O período mais recente pode ter atraso de alguns meses em relação à data atual.
- O aplicativo usa timeout de rede de 30 segundos para evitar esperas indefinidas.

O SIGTAP é consultado em `ftp2.datasus.gov.br/pub/sistemas/tup/downloads`.
O programa identifica a competência pelo trecho `AAAAMM` e descobre o sufixo
de versão na listagem FTP. O ZIP é preservado sem extração automática.

## Histórico de alterações

Consulte [CHANGELOG.md](CHANGELOG.md) para as alterações e a validação
da inclusão do SIGTAP em 04/11/2026.

## Repositórios Git

A branch principal é `main`. O projeto é mantido nos dois destinos:

- GitLab Santa Casa (`origin`):
  https://gitlabdocker.santacasadepiracicaba.com.br/desenvolvimento/baixar_arquivos_datasus
- GitHub privado (`github`):
  https://github.com/GuilhermeHOliveir/baixar_arquivos_datasus

Para publicar novos commits nos dois servidores:

```bash
git push origin main
git push github main
```

Executáveis (`dist/`), arquivos de compilação (`build/`) e caches são ignorados
pelo Git. Para gerar o executável localmente, use `build_exe.bat`.
