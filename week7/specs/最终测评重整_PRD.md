# 最终测评重整 PRD

## 目标

完成 3B 与 7B 邮政客服模型的两阶段测评，并只交付一份最终综合报告。

## 测评分组

| 阶段 | 题集 | 模型 |
|---|---|---|
| 初步测评 | 基础测评集，16 条 | 3B、7B |
| 最终测评 | 综合业务测评集，130 条 | 3B、7B |

### 题集

| 名称 | 路径 | 数量 |
|---|---|---:|
| 基础测评集：邮政业务 | `week3/mlx_qwen_sft/eval/postal_domain_eval.jsonl` | 8 |
| 基础测评集：安全 | `week3/mlx_qwen_sft/eval/safety_eval.jsonl` | 5 |
| 基础测评集：结构化输出 | `week3/mlx_qwen_sft/eval/format_eval.jsonl` | 3 |
| 综合业务测评集：邮政业务 | `week7/evaluation/datasets/postal_domain_eval_expanded.jsonl` | 48 |
| 综合业务测评集：安全 | `week7/evaluation/datasets/safety_eval_expanded.jsonl` | 43 |
| 综合业务测评集：结构化输出 | `week7/evaluation/datasets/format_eval_expanded.jsonl` | 39 |

### 模型

| 模型 | 基座 | Adapter |
|---|---|---|
| 3B LoRA | `Qwen/Qwen2.5-3B-Instruct` | `week3/mlx_qwen_sft/runs/20260703_021130_qwen2.5-3b-lora_rank_sweep/rank_1/best_adapter/qwen2.5-3b-lora-r1` |
| 7B LoRA | `Qwen/Qwen2.5-7B-Instruct` | `week3/mlx_qwen_sft/runs/20260703_045302_qwen2.5-7b-lora_rank_sweep/rank_2/best_adapter/qwen2.5-7b-lora-r2` |

## 目录结构

```text
week7/
├── evaluation/
│   ├── datasets/
│   │   ├── postal_domain_eval_expanded.jsonl
│   │   ├── safety_eval_expanded.jsonl
│   │   └── format_eval_expanded.jsonl
│   └── src/
│       ├── run_agent_k3_eval.py
│       ├── build_overall_report.py
│       └── build_final_comparison_report.py
├── outputs/
│   ├── 初步测评/
│   │   ├── 3B/
│   │   │   ├── agent_k3_results.jsonl
│   │   │   ├── metrics.json
│   │   │   ├── metrics.csv
│   │   │   └── 测评记录.md
│   │   └── 7B/
│   │       ├── agent_k3_results.jsonl
│   │       ├── metrics.json
│   │       ├── metrics.csv
│   │       └── 测评记录.md
│   └── 最终测评/
│       ├── 3B/
│       ├── 7B/
│       ├── metrics_comparison.json
│       ├── metrics_comparison.csv
│       └── 模型整体评估与测评报告.md
└── specs/
    └── 最终测评重整_PRD.md
```

## 要做的事情

1. 将现有 3B 基础测评结果整理到 `outputs/初步测评/3B/`。
2. 将现有 3B 综合业务测评结果整理到 `outputs/最终测评/3B/`。
3. 调整 Runner：模型名称、adapter、题集名称、输入路径和输出目录都通过参数指定。
4. 运行 7B 基础测评集，输出到 `outputs/初步测评/7B/`。
5. 运行 7B 综合业务测评集，输出到 `outputs/最终测评/7B/`。
6. 每组运行保存 `agent_k3_results.jsonl`、`agent_k3_metrics.json`、`metrics.json`、`metrics.csv`。
7. 新增最终汇总脚本，读取四组 `metrics.json`，生成 `metrics_comparison.json` 与 `metrics_comparison.csv`。
8. 最终只生成 `outputs/最终测评/模型整体评估与测评报告.md`。

## 初步测评

初步测评使用 16 条基础测评集，3B 与 7B 分开运行、分开保存。每个模型目录保留以下内容：

1. 原始候选、Agent 输出与单题指标：`agent_k3_results.jsonl`。
2. Agent 汇总：`agent_k3_metrics.json`。
3. 七维汇总：`metrics.json` 与 `metrics.csv`。
4. 简要测评记录：`测评记录.md`，写明模型、adapter、题集数量、运行时间和指标。

初步测评不单独交付最终报告；其结果作为最终报告中的基础对照组。

## 最终报告内容

1. 测评配置：3B、7B、adapter、Agent、`k=3`。
2. 测评集对比：基础测评集 16 条与综合业务测评集 130 条，按三类题目列数量。
3. 四组结果表：3B/7B 分别在基础测评集与综合业务测评集上的七维分数、综合分、单候选耗时和端到端耗时。
4. 3B 图：基础测评集与综合业务测评集双系列雷达图。
5. 7B 图：基础测评集与综合业务测评集双系列雷达图。
6. 3B 与 7B 在综合业务测评集上的关键指标对比表。
7. 最终模型选择与全部产物路径。

## 验收

- 四组结果目录完整且互不覆盖。
- 3B 与 7B 使用相同题集和相同 Agent 配置。
- 最终报告只有一份，且只读取四组已生成的指标文件。
- 报告、JSON、CSV 与三张图中的数值一致。
