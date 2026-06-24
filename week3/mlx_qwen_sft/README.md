# Week3 MLX Qwen2.5 LoRA 微调工程

本目录用于在 Apple MLX 上微调 Qwen2.5 3B 和 7B。训练脚本、评估脚本、绘图脚本都放在 `scripts/`，不使用临时命令替代工程流程。

## 目录

```text
mlx_qwen_sft/
├── configs/
│   ├── qwen2.5-3b-lora.yaml
│   └── qwen2.5-7b-lora.yaml
├── data/
│   └── raw/                 # 已加入 .gitignore
├── eval/
├── scripts/
├── train_3b_tmux.sh
├── train_7b_tmux.sh
├── requirements.txt
├── pyproject.toml
├── adapters/                # 已加入 .gitignore
├── logs/                    # 已加入 .gitignore
├── eval_outputs/            # 已加入 .gitignore
└── plots/                   # 已加入 .gitignore，输出 JPG
```

## 1. 安装依赖

```bash
python3 -m pip install -r requirements.txt
```

如果使用 `pyproject.toml` 管理环境，也可以在本目录执行：

```bash
python3 -m pip install -e .
```

## 2. 整理原始数据

如果数据还在 `week3/sft_training/`，运行：

```bash
python3 scripts/organize_sft_data.py
```

当前 raw 数据应位于：

```text
data/raw/train.json
data/raw/val.json
data/raw/test.json
data/raw/who_am_i.json
```

## 3. 转换 MLX 训练数据

```bash
python3 scripts/prepare_mlx_data.py
```

输出：

```text
data/train.jsonl
data/valid.jsonl
data/test.jsonl
data/prepare_summary.json
```

## 4. 下载并生成评估集

```bash
python3 scripts/download_eval_datasets.py
```

输出：

```text
eval/general_regression_eval.jsonl
eval/postal_domain_eval.jsonl
eval/format_eval.jsonl
eval/safety_eval.jsonl
eval/download_metadata.json
```

## 5. 分段训练并同时评估

3B：

```bash
python3 scripts/train_with_eval.py \
  --config configs/qwen2.5-3b-lora.yaml \
  --label qwen2.5-3b-lora \
  --chunk-iters 100 \
  --eval-limit 20
```

7B：

```bash
python3 scripts/train_with_eval.py \
  --config configs/qwen2.5-7b-lora.yaml \
  --label qwen2.5-7b-lora \
  --chunk-iters 100 \
  --eval-limit 20
```

训练脚本每个 chunk 后会运行自动评估。gate 不会因为单个小样本指标波动就停止训练；JSON 字段不完整、轻微安全风险或单个通用任务疑似污染会写入 `collapse_warnings`。只有出现明显崩坏，例如 JSON 大面积不可解析、安全风险率明显过高、多个通用任务严重被邮政话术污染时，脚本才会停止。

训练过程中只保留一个 best adapter：

```text
adapters/best/<label>/
```

每轮评估会计算一个综合分。只有当前 adapter 没有触发 gate，并且综合分高于历史 best，脚本才会覆盖 `adapters/best/<label>/`。这样不会为每个 chunk 保存一份完整历史，只保留一个当前最好的 adapter。触发 gate 时，最后一轮退化 adapter 不会覆盖 best，直接回到 `adapters/best/<label>/` 使用即可。

best 元数据会写入：

```text
logs/best_adapter_<label>_<run_id>.json
```

每个 chunk 评估后会自动覆盖生成 JPG 图表到 `plots/`：

```text
plots/<label>_score_curve.jpg
plots/<label>_json_quality.jpg
plots/<label>_risk_monitor.jpg
plots/<label>_postal_signals.jpg
plots/<label>_best_updates.jpg
plots/<label>_latest_output_length.jpg
plots/<label>_latest_risk_rate.jpg
```

图表只放短标题、坐标轴和图例；解释文字放到最终报告中，不写在图里。

## 6. tmux 后台训练

3B：

```bash
chmod +x train_3b_tmux.sh
./train_3b_tmux.sh
tmux attach -t qwen25_3b_lora
```

7B：

```bash
chmod +x train_7b_tmux.sh
./train_7b_tmux.sh
tmux attach -t qwen25_7b_lora
```

脚本会在 tmux 中运行同样的分段训练命令：

```bash
python3 scripts/train_with_eval.py \
  --config configs/qwen2.5-3b-lora.yaml \
  --label qwen2.5-3b-lora \
  --chunk-iters 100 \
  --eval-limit 20
```

```bash
python3 scripts/train_with_eval.py \
  --config configs/qwen2.5-7b-lora.yaml \
  --label qwen2.5-7b-lora \
  --chunk-iters 100 \
  --eval-limit 20
```

训练和评估的进度输出来自 `mlx-lm` 和脚本中的 `tqdm`。退出 tmux 但不中断训练使用 `Ctrl-b` 后按 `d`。

## 7. 单独评估模型

评估 base 模型：

```bash
python3 scripts/evaluate_model.py \
  --model Qwen/Qwen2.5-7B-Instruct \
  --label qwen2.5-7b-base \
  --limit 20
```

评估 LoRA 模型：

```bash
python3 scripts/evaluate_model.py \
  --model Qwen/Qwen2.5-7B-Instruct \
  --adapter-path adapters/best/qwen2.5-7b-lora \
  --label qwen2.5-7b-lora \
  --limit 20
```

## 8. 绘图

```bash
python3 scripts/plot_eval_metrics.py
```

所有图输出为 JPG，脚本不显式设置 DPI，使用 Matplotlib 原始默认 DPI。训练脚本会自动调用绘图脚本；也可以手动运行该命令重新覆盖生成。

## 9. 生成评估汇总

```bash
python3 scripts/report_eval_summary.py
```

输出：

```text
eval_summary.md
```

## 10. 常规训练命令

如果只想使用 `mlx_lm.lora` 直接训练，不启用分段评估：

```bash
mlx_lm.lora --config configs/qwen2.5-3b-lora.yaml
mlx_lm.lora --config configs/qwen2.5-7b-lora.yaml
```

更推荐使用 `scripts/train_with_eval.py`，因为它会在训练过程中检查模型是否退化。
