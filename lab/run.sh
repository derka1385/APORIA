#!/usr/bin/env bash
# One command: bash lab/run.sh   ->  http://localhost:8740
set -e
cd "$(dirname "$0")"
MODEL="${APORIA_MODEL:-qwen2.5:3b}"
command -v ollama >/dev/null || { echo "Install Ollama first: https://ollama.com/download"; exit 1; }
curl -sf http://127.0.0.1:11434/api/tags >/dev/null || { (ollama serve >/dev/null 2>&1 &); sleep 2; }
for m in "$MODEL" nomic-embed-text; do
  ollama list | grep -q "^${m%%:*}" || ollama pull "$m"
done
(sleep 1.5; open "http://localhost:${APORIA_PORT:-8740}" 2>/dev/null || true) &
exec python3 server.py
