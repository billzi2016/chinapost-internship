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
├── adapters/                # 已加入 .gitignore
├── logs/                    # 已加入 .gitignore
├── eval_outputs/            # 已加入 .gitignore
└── plots/                   # 已加入 .gitignore，输出 JPG
```

## 1. 安装依赖

```bash
pip install -U "mlx-lm[train]" datasets matplotlib tqdm pyyaml
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

训练脚本每个 chunk 后会运行自动评估。如果 JSON 可解析率、安全风险率或通用任务邮政话术污染率触发阈值，脚本会停止，避免继续训练出退化模型。

## 6. 单独评估模型

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
  --adapter-path adapters/qwen2.5-7b \
  --label qwen2.5-7b-lora \
  --limit 20
```

## 7. 绘图

```bash
python3 scripts/plot_eval_metrics.py
```

所有图输出为 JPG，脚本不显式设置 DPI，使用 Matplotlib 原始默认 DPI。

## 8. 生成评估汇总

```bash
python3 scripts/report_eval_summary.py
```

输出：

```text
eval_summary.md
```

## 9. 常规训练命令

如果只想使用 `mlx_lm.lora` 直接训练，不启用分段评估：

```bash
mlx_lm.lora --config configs/qwen2.5-3b-lora.yaml
mlx_lm.lora --config configs/qwen2.5-7b-lora.yaml
```

更推荐使用 `scripts/train_with_eval.py`，因为它会在训练过程中检查模型是否退化。
