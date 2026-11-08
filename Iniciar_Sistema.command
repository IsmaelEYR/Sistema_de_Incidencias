#!/bin/bash
echo -n -e "\033]0;Sistema de Incidencias - Servidor Web\007"
printf '\e[8;18;70t'
clear

echo "======================================================================"
echo "          SISTEMA DE GESTIÓN DE INCIDENCIAS - ACTIVO"
echo "======================================================================"
echo " 🟢 Iniciando entorno virtual y servicios..."
echo " 🌐 El panel de control se abrirá automáticamente en tu navegador."
echo ""
echo " ⚠️  IMPORTANTE: Deja esta ventana minimizada mientras trabajas."
echo " 🛑 Para APAGAR el sistema por completo, presiona Ctrl+C o cierra aquí."
echo "======================================================================"

# Posicionarse en la carpeta donde reside el script
cd "$(dirname "$0")"

# Validar y activar entorno virtual
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Error: No se encontró la carpeta 'venv'. Asegúrate de que existe el entorno virtual."
    exit 1
fi

# Abrir el navegador en segundo plano tras 1.5 segundos (garantiza que Uvicorn ya esté escuchando)
(sleep 1.5 && open http://127.0.0.1:8000/panel) &

# Arrancar Uvicorn con recarga automática para desarrollo
exec uvicorn main:app --host 127.0.0.1 --port 8000 --reload --log-level info