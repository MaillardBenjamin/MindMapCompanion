#!/usr/bin/env bash
# Démarre le serveur en mode dev avec reload, en excluant venv pour éviter les redémarrages en boucle.
cd "$(dirname "$0")"
PORT="${PORT:-8001}"
uvicorn app.main:app --reload --host 0.0.0.0 --port "$PORT" \
  --reload-exclude 'venv/*' \
  --reload-exclude '.git/*'
