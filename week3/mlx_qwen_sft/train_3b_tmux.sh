#!/usr/bin/env bash
# 用 tmux 启动 Qwen2.5 3B LoRA 分段训练。
#
# 这个脚本只负责启动训练会话，不直接在当前终端里长时间阻塞。
# 训练主体仍然走 scripts/train_with_eval.py：
# - 每个 chunk 后自动评估。
# - 未触发 gate 且分数更好时覆盖 adapters/best/qwen2.5-3b-lora/。
# - 触发 gate 时停止，并保留历史 best adapter。

set -euo pipefail

SESSION_NAME="qwen25_3b_lora"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is not installed or not in PATH."
  exit 1
fi

if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
  echo "tmux session already exists: ${SESSION_NAME}"
  echo "Attach with: tmux attach -t ${SESSION_NAME}"
  exit 0
fi

tmux new-session -d -s "${SESSION_NAME}" -c "${PROJECT_DIR}" \
  "python3 scripts/train_with_eval.py \
    --config configs/qwen2.5-3b-lora.yaml \
    --label qwen2.5-3b-lora \
    --chunk-iters 100 \
    --eval-limit 20"

echo "Started tmux session: ${SESSION_NAME}"
echo "Attach with: tmux attach -t ${SESSION_NAME}"
echo "Detach from tmux with: Ctrl-b then d"
