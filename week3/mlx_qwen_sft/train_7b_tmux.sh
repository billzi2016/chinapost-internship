#!/usr/bin/env bash
# 用 tmux 启动 Qwen2.5 7B LoRA rank sweep 分段训练。
#
# 7B 是主交付候选模型，训练耗时更长，建议放在 tmux 后台会话中运行。
# 训练主体走 scripts/run_rank_sweep.py，再由它逐个调用 scripts/train_with_eval.py：
# - 每个 chunk 后自动评估。
# - 每个 rank 的日志、评估结果和 best adapter 归档到 runs/*_qwen2.5-7b-lora_rank_sweep/rank_*。
# - 触发 gate 时停止，并保留历史 best adapter。

set -euo pipefail

SESSION_NAME="qwen25_7b_lora"
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
  "python3 scripts/run_rank_sweep.py \
    --config configs/qwen2.5-7b-lora.yaml \
    --label-prefix qwen2.5-7b-lora \
    --adapter-prefix ./adapters/qwen2.5-7b \
    --ranks 1 2 4 8 16 32 \
    --chunk-iters 100 \
    --eval-limit 20"

echo "Started tmux session: ${SESSION_NAME}"
echo "Attach with: tmux attach -t ${SESSION_NAME}"
echo "Detach from tmux with: Ctrl-b then d"
