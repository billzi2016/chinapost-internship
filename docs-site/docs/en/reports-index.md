# Reports Index

The `reports/` directory is the formal report entry point for the reconstructed project. Its role is to keep the Markdown source files and the final PDF outputs organized in one place.

The current export path is:

```text
Markdown -> HTML -> Chromium PDF printing
```

The script that maintains this mapping is:

```text
reports/build_reports.py
```

## Current Status

The PDFs in this repository are not treated as permanently stable artifacts. They change often and can grow the repository size quickly, so the final PDF set will be cleaned up again in a later push.

At the current stage:

1. some PDFs already exist,
2. some PDFs may be temporarily missing,
3. the Markdown source files still remain the formal report sources.

If the goal is to read report content, the Markdown files are the primary source. If the goal is to collect final deliverables, the later cleaned PDF set should be treated as the final version.

## Step 1: Model Selection and Dataset Analysis

### Open-Source Model Selection Report for the China Post Customer-Service Task

- Markdown: `week1/第一版/docs/模型选型报告.md`
- PDF: `reports/step1_模型选型与数据集分析/中文邮政客服任务开源大模型选型研究报告.pdf`

### SFT Training Plan and Risk Control Report

- Markdown: `week1/第一版/docs/SFT训练与风险控制.md`
- PDF: `reports/step1_模型选型与数据集分析/中文邮政客服任务SFT训练方案与风险控制报告.pdf`

### CSDS Statistics and Keyword Extraction Report

- Markdown: `week1/第一版/stats/outputs/report.md`
- PDF: `reports/step1_模型选型与数据集分析/CSDS数据集统计分析与关键词提取结果报告.pdf`

### Postal Conversation Filtering and Vector-Space Visualization Report

- Markdown: `week1/第一版/filter/outputs/report.md`
- PDF: `reports/step1_模型选型与数据集分析/邮政相关对话筛选与向量空间可视化结果报告.pdf`

### Classification Evaluation and Boundary-Case Analysis Report

- Markdown: `week1/第二版/01_分类效果评估与边界case分析/outputs/report.md`
- PDF: `reports/step1_模型选型与数据集分析/分类效果评估与边界case分析报告.pdf`

### Cluster Visualization and Label Optimization Report

- Markdown: `week1/第二版/04_可视化聚类与标签优化/outputs/report.md`
- PDF: `reports/step1_模型选型与数据集分析/可视化聚类与标签优化报告.pdf`

## Step 2: Dataset Collection and Framework Setup

### Postal FAQ Crawler Training Sample Report

- Markdown: `week1-module-Web-Crawler/report/training_samples_report.md`
- PDF: `reports/step2_收集数据集和框架搭建/邮政FAQ爬虫训练样本构建报告.pdf`

### Postal Customer-Service LLM System Design Report

- Markdown: `week1-module-Web-Crawler/report/llm_system_design_report.md`
- PDF: `reports/step2_收集数据集和框架搭建/邮政客服LLM系统设计报告.pdf`

## Step 3: LoRA Fine-Tuning

### Full Apple MLX Qwen2.5 Postal Fine-Tuning Report

- Markdown: `week3/reports/qwen2.5_mlx_sft_full_experiment_report.md`
- PDF: `reports/step3_lora微调/基于AppleMLX的Qwen2.5邮政客服模型微调完整实验报告.pdf`

### Qwen2.5-3B Postal LoRA Rank Sweep Report

- Markdown: `week3/reports/qwen2.5-3b_rank_sweep_report.md`
- PDF: `reports/step3_lora微调/Qwen2.5-3B邮政客服LoRA RankSweep实验报告.pdf`

### Qwen2.5-7B Postal LoRA Rank Sweep Report

- Markdown: `week3/reports/qwen2.5-7b_rank_sweep_report.md`
- PDF: `reports/step3_lora微调/Qwen2.5-7B邮政客服LoRA RankSweep实验报告.pdf`

