@echo off
setlocal
title Git Push - Market Platform Unified

set REPO_URL=https://github.com/mullerdoskov/Global_Mkt.git
set BRANCH=main

cd /d "%~dp0"

echo.
echo   ========================================
echo    GIT PUSH - Market Platform Unified
echo   ========================================
echo.

:: Verificar Git
git --version >nul 2>&1
if errorlevel 1 (
    echo   [ERRO] Git nao encontrado.
    pause
    exit /b 1
)

:: Inicializar repo se necessario
if not exist ".git" (
    echo   [1] Inicializando repositorio Git...
    git init
    git branch -M %BRANCH%
    echo.
    echo   [2] Configurando remote origin...
    git remote add origin %REPO_URL%
    echo       %REPO_URL%
    echo.
) else (
    echo   [OK] Repositorio Git ja inicializado
    echo.
)

:: Mostrar status
echo   -- Status atual --
echo.
git status --short
echo.

:: Staging
echo   -- Staging --
echo.
echo   [1] Adicionar TUDO
echo   [2] Apenas backend + configs
echo   [3] Cancelar
echo.
set /p STAGE_CHOICE="  Escolha [1-3]: "

if "%STAGE_CHOICE%"=="1" goto :stage_all
if "%STAGE_CHOICE%"=="2" goto :stage_backend
if "%STAGE_CHOICE%"=="3" goto :fim
goto :stage_all

:stage_all
git add .
echo   Todos os arquivos adicionados.
goto :commit

:stage_backend
git add backend/ market.bat git_push.bat .gitignore .env.example README.md diagrama_arquitetura.html
echo   Backend e configs adicionados.
goto :commit

:: Commit
:commit
echo.
echo   -- Commit --
echo.
echo   Sugestoes:  feat: / fix: / refactor: / docs: / chore:
echo.
set /p COMMIT_MSG="  Mensagem do commit: "

if "%COMMIT_MSG%"=="" (
    echo   [ERRO] Mensagem vazia.
    pause
    goto :fim
)

git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
    echo.
    echo   [ERRO] Commit falhou.
    pause
    goto :fim
)

:: Push
:push
echo.
echo   -- Push --
echo   Enviando para %REPO_URL% [%BRANCH%]
echo.

git push -u origin %BRANCH%
if errorlevel 1 goto :push_failed
goto :push_ok

:push_failed
echo.
echo   [!] Push falhou.
echo       - Repositorio existe no GitHub?
echo       - Autenticacao configurada? (gh auth login)
echo.
set /p FORCE="  Tentar force push? [s/N]: "
if /i "%FORCE%"=="s" (
    git push -u origin %BRANCH% --force
    if errorlevel 1 (
        echo   [ERRO] Force push tambem falhou.
    ) else (
        goto :push_ok
    )
)
goto :fim

:push_ok
echo.
echo   ========================================
echo    PUSH CONCLUIDO COM SUCESSO
echo   ========================================
echo.
echo   Repo:   %REPO_URL%
echo   Branch: %BRANCH%
echo.
git log --oneline -1
echo.

:fim
pause
