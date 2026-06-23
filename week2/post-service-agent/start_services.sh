#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${POST_AI_PYTHON:-/opt/anaconda3/bin/python}"
DJANGO_HOST="${DJANGO_HOST:-127.0.0.1}"
DJANGO_PORT="${DJANGO_PORT:-9999}"

cd "$ROOT_DIR"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required. Install it first: brew install tmux" >&2
  exit 1
fi

start_task() {
  local name="$1"
  local command="$2"
  if tmux has-session -t "$name" 2>/dev/null; then
    echo "tmux task '$name' already exists. Attach: tmux attach -t $name"
    return
  fi
  tmux new-session -d -s "$name" -n "$name"
  tmux send-keys -t "$name" "$command" C-m
  echo "Started tmux task: $name"
}

start_task "post-ai-postgres" "cd '$ROOT_DIR' && docker compose up postgres"
start_task "post-ai-ollama" "ollama serve"
start_task "post-ai-django" "cd '$ROOT_DIR' && PYTHONPATH=. '$PYTHON_BIN' manage.py runserver '$DJANGO_HOST:$DJANGO_PORT'"

echo "Attach examples:"
echo "  tmux attach -t post-ai-postgres"
echo "  tmux attach -t post-ai-ollama"
echo "  tmux attach -t post-ai-django"
