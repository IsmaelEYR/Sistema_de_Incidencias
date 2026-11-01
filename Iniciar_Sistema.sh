#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
xdg-open http://127.0.0.1:8000/panel
uvicorn main:app --log-level warning
read -p "Presiona Enter para salir..."