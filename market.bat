@echo off
setlocal
title Market Platform Unified v2.0

set "PROJECT_DIR=%~dp0"
set "VENV_DIR=%PROJECT_DIR%venv"
set "PYTHON=python"
set "PIP=pip"

if exist "%VENV_DIR%\Scripts\python.exe" (
    set "PYTHON=%VENV_DIR%\Scripts\python.exe"
    set "PIP=%VENV_DIR%\Scripts\pip.exe"
)

cd /d "%PROJECT_DIR%"

:: Com argumento = execucao direta
if not "%~1"=="" goto :direct

:: Sem argumento = menu
goto :menu

:direct
if /i "%~1"=="setup"    goto :cmd_setup
if /i "%~1"=="install"  goto :cmd_install
if /i "%~1"=="init"     goto :cmd_db_init
if /i "%~1"=="status"   goto :cmd_db_status
if /i "%~1"=="server"   goto :cmd_server
if /i "%~1"=="api"      goto :cmd_server
if /i "%~1"=="docs"     goto :cmd_docs
if /i "%~1"=="frontend" goto :cmd_frontend
if /i "%~1"=="test"     goto :cmd_test
if /i "%~1"=="reset"    goto :cmd_reset
if /i "%~1"=="help"     goto :cmd_help
if /i "%~1"=="cli"      goto :cmd_cli_pass
if /i "%~1"=="ingest"   goto :cmd_ingest_pass

echo.
echo   [ERRO] Comando desconhecido: %~1
echo   Use: market.bat help
goto :fim

:: =============================================
::  MENU INTERATIVO
:: =============================================
:menu
cls
echo.
echo   ========================================
echo    MARKET PLATFORM UNIFIED v2.0
echo    Inteligencia de Mercado
echo   ========================================
echo.
echo   -- SETUP ---------------------
echo     [1] Setup completo (venv + deps + db)
echo     [2] Instalar dependencias
echo.
echo   -- BANCO DE DADOS ------------
echo     [3] Inicializar banco (db-init)
echo     [4] Status do banco
echo     [5] Reset do banco
echo.
echo   -- SERVIDOR ------------------
echo     [6] Iniciar API (uvicorn :8000)
echo     [7] Abrir Swagger UI
echo     [8] Servir frontend (:3000)
echo.
echo   -- INGESTAO ------------------
echo     [9]  Ingerir indices (rapido)
echo     [10] Ingerir stocks BR
echo     [11] Ingerir stocks US
echo     [12] Ingerir TUDO
echo     [13] Ingestao personalizada
echo.
echo   -- CONSULTAS -----------------
echo     [14] Listar assets
echo     [15] Buscar ativo
echo     [16] Top movers
echo     [17] Exportar CSV
echo.
echo   -- OUTROS --------------------
echo     [18] CLI interativo
echo     [0]  Sair
echo.
set /p CHOICE="  Escolha [0-18]: "

if "%CHOICE%"=="1"  goto :cmd_setup
if "%CHOICE%"=="2"  goto :cmd_install
if "%CHOICE%"=="3"  goto :cmd_db_init
if "%CHOICE%"=="4"  goto :cmd_db_status
if "%CHOICE%"=="5"  goto :cmd_reset
if "%CHOICE%"=="6"  goto :cmd_server
if "%CHOICE%"=="7"  goto :cmd_docs
if "%CHOICE%"=="8"  goto :cmd_frontend
if "%CHOICE%"=="9"  goto :cmd_ingest_index
if "%CHOICE%"=="10" goto :cmd_ingest_br
if "%CHOICE%"=="11" goto :cmd_ingest_us
if "%CHOICE%"=="12" goto :cmd_ingest_all
if "%CHOICE%"=="13" goto :cmd_ingest_custom
if "%CHOICE%"=="14" goto :cmd_list_assets
if "%CHOICE%"=="15" goto :cmd_search
if "%CHOICE%"=="16" goto :cmd_top_movers
if "%CHOICE%"=="17" goto :cmd_export
if "%CHOICE%"=="18" goto :cmd_cli_interactive
if "%CHOICE%"=="0"  goto :fim

echo   Opcao invalida.
timeout /t 2 >nul
goto :menu

:: =============================================
::  SETUP
:: =============================================
:cmd_setup
echo.
echo   == SETUP COMPLETO ==
echo.
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo   [1/3] Criando virtual environment...
    python -m venv venv
    set "PYTHON=%VENV_DIR%\Scripts\python.exe"
    set "PIP=%VENV_DIR%\Scripts\pip.exe"
) else (
    echo   [1/3] Venv ja existe
)
echo   [2/3] Instalando dependencias...
"%PIP%" install -r backend\requirements.txt -q
if not exist "%PROJECT_DIR%.env" (
    if exist "%PROJECT_DIR%.env.example" (
        copy "%PROJECT_DIR%.env.example" "%PROJECT_DIR%.env" >nul
        echo   [!] .env criado - EDITE a senha do PostgreSQL!
    )
)
echo   [3/3] Inicializando banco...
"%PYTHON%" -m backend.cli db-init --force
echo.
echo   == SETUP CONCLUIDO ==
echo.
pause
if "%~1"=="" goto :menu
goto :fim

:cmd_install
echo.
"%PIP%" install -r backend\requirements.txt
echo.
pause
if "%~1"=="" goto :menu
goto :fim

:: =============================================
::  BANCO
:: =============================================
:cmd_db_init
echo.
"%PYTHON%" -m backend.cli db-init
echo.
pause
if "%~1"=="" goto :menu
goto :fim

:cmd_db_status
echo.
"%PYTHON%" -m backend.cli db-status
echo.
pause
if "%~1"=="" goto :menu
goto :fim

:cmd_reset
echo.
"%PYTHON%" -m backend.cli db-reset
echo.
pause
if "%~1"=="" goto :menu
goto :fim

:: =============================================
::  SERVIDOR
:: =============================================
:cmd_server
echo.
echo   Iniciando API em http://localhost:8000
echo   Swagger: http://localhost:8000/docs
echo   Ctrl+C para parar
echo.
if exist "%VENV_DIR%\Scripts\uvicorn.exe" (
    "%VENV_DIR%\Scripts\uvicorn.exe" backend.app:app --reload --port 8000
) else (
    uvicorn backend.app:app --reload --port 8000
)
if "%~1"=="" goto :menu
goto :fim

:cmd_docs
start http://localhost:8000/docs
if "%~1"=="" goto :menu
goto :fim

:cmd_frontend
echo.
echo   Frontend em http://localhost:3000
echo   Ctrl+C para parar
echo.
cd frontend
"%PYTHON%" -m http.server 3000
cd ..
if "%~1"=="" goto :menu
goto :fim

:: =============================================
::  INGESTAO
:: =============================================
:cmd_ingest_pass
shift
"%PYTHON%" -m backend.cli ingest-prices %1 %2 %3 %4 %5 %6 %7 %8 %9
goto :fim

:cmd_ingest_index
echo.
"%PYTHON%" -m backend.cli ingest-prices --type index --period 3mo
echo.
pause
goto :menu

:cmd_ingest_br
echo.
"%PYTHON%" -m backend.cli ingest-prices --type stock --country BR --period 1y
echo.
pause
goto :menu

:cmd_ingest_us
echo.
"%PYTHON%" -m backend.cli ingest-prices --type stock --country US --period 1y
echo.
pause
goto :menu

:cmd_ingest_all
echo.
echo   Isso vai baixar ~371 tickers. Pode levar 15-30 min.
set /p CONFIRM="  Continuar? [s/N]: "
if /i not "%CONFIRM%"=="s" goto :menu
echo.
echo   [1/6] Indices...
"%PYTHON%" -m backend.cli ingest-prices --type index --period 1y
echo   [2/6] Stocks BR...
"%PYTHON%" -m backend.cli ingest-prices --type stock --country BR --period 1y
echo   [3/6] Stocks US...
"%PYTHON%" -m backend.cli ingest-prices --type stock --country US --period 1y
echo   [4/6] ETFs...
"%PYTHON%" -m backend.cli ingest-prices --type etf --period 1y
echo   [5/6] Commodities + FX...
"%PYTHON%" -m backend.cli ingest-prices --type commodity --period 1y
"%PYTHON%" -m backend.cli ingest-prices --type fx --period 1y
echo   [6/6] Crypto...
"%PYTHON%" -m backend.cli ingest-prices --type crypto --period 1y
echo.
"%PYTHON%" -m backend.cli db-status
echo.
pause
goto :menu

:cmd_ingest_custom
echo.
echo   -- Ingestao Personalizada --
echo.
set /p I_TYPE="  Tipo (stock/index/etf/commodity/fx/crypto) [Enter=todos]: "
set /p I_COUNTRY="  Pais (BR/US/GB/etc) [Enter=todos]: "
set /p I_START="  Data inicio YYYY-MM-DD [Enter=usar periodo]: "
set /p I_PERIOD="  Periodo (7d/30d/90d/1y) [Enter=1y]: "
if "%I_PERIOD%"=="" set I_PERIOD=1y

set CMD_ARGS=
if not "%I_TYPE%"=="" set CMD_ARGS=%CMD_ARGS% --type %I_TYPE%
if not "%I_COUNTRY%"=="" set CMD_ARGS=%CMD_ARGS% --country %I_COUNTRY%
if not "%I_START%"=="" (
    set CMD_ARGS=%CMD_ARGS% --start %I_START%
) else (
    set CMD_ARGS=%CMD_ARGS% --period %I_PERIOD%
)

echo.
echo   Executando: python -m backend.cli ingest-prices %CMD_ARGS%
echo.
"%PYTHON%" -m backend.cli ingest-prices %CMD_ARGS%
echo.
pause
goto :menu

:: =============================================
::  CONSULTAS
:: =============================================
:cmd_list_assets
echo.
set /p LA_TYPE="  Tipo [Enter=todos]: "
set /p LA_COUNTRY="  Pais [Enter=todos]: "
set LA_ARGS=
if not "%LA_TYPE%"=="" set LA_ARGS=%LA_ARGS% --type %LA_TYPE%
if not "%LA_COUNTRY%"=="" set LA_ARGS=%LA_ARGS% --country %LA_COUNTRY%
"%PYTHON%" -m backend.cli list-assets %LA_ARGS%
echo.
pause
goto :menu

:cmd_search
echo.
set /p SEARCH_Q="  Buscar: "
"%PYTHON%" -m backend.cli search "%SEARCH_Q%"
echo.
pause
goto :menu

:cmd_top_movers
echo.
set /p TM_COUNTRY="  Pais [Enter=todos]: "
set TM_ARGS=
if not "%TM_COUNTRY%"=="" set TM_ARGS=--country %TM_COUNTRY%
"%PYTHON%" -m backend.cli top-movers %TM_ARGS%
echo.
pause
goto :menu

:cmd_export
echo.
set /p EX_DATA="  O que exportar (assets/prices): "
set /p EX_TYPE="  Tipo de ativo [Enter=todos]: "
set /p EX_COUNTRY="  Pais [Enter=todos]: "
set /p EX_OUTPUT="  Arquivo de saida [Enter=auto]: "
set EX_ARGS=%EX_DATA%
if not "%EX_TYPE%"=="" set EX_ARGS=%EX_ARGS% --type %EX_TYPE%
if not "%EX_COUNTRY%"=="" set EX_ARGS=%EX_ARGS% --country %EX_COUNTRY%
if not "%EX_OUTPUT%"=="" set EX_ARGS=%EX_ARGS% -o %EX_OUTPUT%
"%PYTHON%" -m backend.cli export %EX_ARGS%
echo.
pause
goto :menu

:: =============================================
::  CLI
:: =============================================
:cmd_cli_pass
shift
"%PYTHON%" -m backend.cli %1 %2 %3 %4 %5 %6 %7 %8 %9
goto :fim

:cmd_cli_interactive
echo.
echo   == CLI Interativo ==
echo   Digite comandos (ex: show PETR4.SA)
echo   Digite 'sair' para voltar
echo.
:cli_loop
set /p CLI_CMD="  market> "
if /i "%CLI_CMD%"=="sair" goto :menu
if /i "%CLI_CMD%"=="exit" goto :menu
if "%CLI_CMD%"=="" goto :cli_loop
"%PYTHON%" -m backend.cli %CLI_CMD%
echo.
goto :cli_loop

:: =============================================
::  TEST
:: =============================================
:cmd_test
echo.
echo   == Testes Rapidos ==
echo.
echo   [1] Conexao com banco...
"%PYTHON%" -c "from backend.db.connection import check_connection; r=check_connection(); print('  DB:', r['status'])"
echo.
echo   [2] Imports...
"%PYTHON%" -c "from backend.config.symbols import TOTAL_SYMBOLS; print('  Symbols:', TOTAL_SYMBOLS, 'tickers')"
"%PYTHON%" -c "from backend.db.schema import Base; print('  Schema:', len(Base.metadata.tables), 'tabelas')"
echo.
pause
if "%~1"=="" goto :menu
goto :fim

:: =============================================
::  HELP
:: =============================================
:cmd_help
echo.
echo   ========================================
echo    MARKET PLATFORM v2.0 - Ajuda
echo   ========================================
echo.
echo   USO:
echo     market.bat              Menu interativo
echo     market.bat [comando]    Execucao direta
echo.
echo   COMANDOS:
echo     setup      Setup completo (venv + deps + db)
echo     install    Instalar dependencias
echo     init       Inicializar banco
echo     status     Status do banco
echo     server     Iniciar API (uvicorn :8000)
echo     docs       Abrir Swagger UI
echo     frontend   Servir frontend :3000
echo     ingest     Ingestao (passa args ao CLI)
echo     test       Testes de sanidade
echo     reset      Reset do banco
echo     cli        Passthrough pro CLI
echo     help       Esta mensagem
echo.
echo   EXEMPLOS:
echo     market.bat setup
echo     market.bat server
echo     market.bat ingest --type stock --country BR
echo     market.bat cli show PETR4.SA
echo     market.bat cli prices AAPL --period 30d
echo.
pause
if "%~1"=="" goto :menu
goto :fim

:fim
