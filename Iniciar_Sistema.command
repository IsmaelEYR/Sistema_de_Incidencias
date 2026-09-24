#!/bin/bash
echo -n -e "\033]0;Sistema de Incidencias - Servidor Web\007"
printf '\e[8;16;65t'
clear

echo "================================================================="
echo "          SISTEMA DE GESTIÓN DE INCIDENCIAS - ACTIVO"
echo "================================================================="
echo " 🟢 El servidor principal se ha iniciado correctamente."
echo " 🌐 Abriendo el panel de control en tu navegador..."
echo ""
echo " ⚠️  IMPORTANTE: Deja esta ventana minimizada mientras trabajas."
echo " 🛑 Para APAGAR el sistema por completo, cierra esta ventana."
echo "================================================================="

cd "$(dirname "$0")"
source venv/bin/activate
open http://127.0.0.1:8000/panel

uvicorn main:app --log-level warning