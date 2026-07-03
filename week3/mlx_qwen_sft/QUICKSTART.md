# Quickstart

## Final Commands

```bash
cd /Users/bizi/Desktop/邮政实习/week3/mlx_qwen_sft
./train_3b_tmux.sh
./train_7b_tmux.sh
```

## 3B

```bash
./train_3b_tmux.sh
tmux attach -t qwen25_3b_lora
```

## 7B

```bash
./train_7b_tmux.sh
tmux attach -t qwen25_7b_lora
```

## Attach

```bash
tmux attach -t qwen25_3b_lora
tmux attach -t qwen25_7b_lora
```

Detach: `Ctrl-b` then `d`.

## Chat

7B rank 2:

```bash
python3 scripts/chat_with_adapter.py \
  --model Qwen/Qwen2.5-7B-Instruct \
  --adapter-path runs/20260625_233007_qwen2.5-7b-lora_rank_sweep/rank_2/best_adapter/qwen2.5-7b-lora-r2
```

3B rank 4:

```bash
python3 scripts/chat_with_adapter.py \
  --model Qwen/Qwen2.5-3B-Instruct \
  --adapter-path runs/20260623_224112_3b_rank_sweep/rank_4/best_adapter/qwen2.5-3b-lora-r4
```

Commands:

```text
/reset  清空对话历史
/exit   退出聊天
```

## Rank Sweep

Outputs are grouped under `runs/<timestamp>_<run-name>/`. Rank logs, eval outputs and adapters stay in `rank_<rank>/`; all JPG plots are saved in the top-level `plots/`.

3B:

```bash
python3 scripts/run_rank_sweep.py \
  --config configs/qwen2.5-3b-lora.yaml \
  --label-prefix qwen2.5-3b-lora \
  --adapter-prefix ./adapters/qwen2.5-3b \
  --ranks 1 2 4 8 16 32
```

7B:

```bash
python3 scripts/run_rank_sweep.py \
  --config configs/qwen2.5-7b-lora.yaml \
  --label-prefix qwen2.5-7b-lora \
  --adapter-prefix ./adapters/qwen2.5-7b \
  --ranks 1 2 4 8 16 32
```

## Current Sweep Resume

Current 3B:

```bash
cd /Users/bizi/Desktop/邮政实习/week3/mlx_qwen_sft
python3 scripts/run_rank_sweep.py \
  --config configs/qwen2.5-3b-lora.yaml \
  --label-prefix qwen2.5-3b-lora \
  --adapter-prefix ./adapters/qwen2.5-3b \
  --ranks 1 2 4 8 16 32 \
  --resume-run-dir runs/20260703_021130_qwen2.5-3b-lora_rank_sweep
```

Current 7B:

```bash
cd /Users/bizi/Desktop/邮政实习/week3/mlx_qwen_sft
python3 scripts/run_rank_sweep.py \
  --config configs/qwen2.5-7b-lora.yaml \
  --label-prefix qwen2.5-7b-lora \
  --adapter-prefix ./adapters/qwen2.5-7b \
  --ranks 1 2 4 8 16 32 \
  --resume-run-dir runs/20260703_045302_qwen2.5-7b-lora_rank_sweep
```
