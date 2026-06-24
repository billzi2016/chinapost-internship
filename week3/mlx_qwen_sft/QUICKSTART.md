# Quickstart

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

## Rank Sweep

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
