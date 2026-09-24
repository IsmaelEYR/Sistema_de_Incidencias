@echo off
title Sistema de Incidencias - Servidor Web
color 0A
mode con: cols=70 lines=20
cls
echo =================================================================
echo           SISTEMA DE GESTION DE INCIDENCIAS - ACTIVO
echo =================================================================
echo  [+] El servidor principal se ha iniciado correctamente.
echo  [+] Abriendo el panel de control en tu navegador...
echo.
echo  [!] IMPORTANTE: Deja esta ventana minimizada mientras trabajas.
echo  [X] Para APAGAR el sistema por completo, cierra esta ventana.
echo =================================================================
cd /d "%~dp0"
call venv\Scripts\activate
start http://127.0.0.1:8000/panel
uvicorn main:app --log-level warning