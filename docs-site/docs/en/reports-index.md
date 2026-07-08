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

- Markdown: [MkDocs page](report-step1-model-selection.md) (source: `week1/第一版/docs/模型选型报告.md`)
- PDF: [中文邮政客服任务开源大模型选型研究报告.pdf](https://github.com/billzi2016/chinapost-internship/blob/main/reports/step1_%E6%A8%A1%E5%9E%8B%E9%80%89%E5%9E%8B%E4%B8%8E%E6%95%B0%E6%8D%AE%E9%9B%86%E5%88%86%E6%9E%90/%E4%B8%AD%E6%96%87%E9%82%AE%E6%94%BF%E5%AE%A2%E6%9C%8D%E4%BB%BB%E5%8A%A1%E5%BC%80%E6%BA%90%E5%A4%A7%E6%A8%A1%E5%9E%8B%E9%80%89%E5%9E%8B%E7%A0%94%E7%A9%B6%E6%8A%A5%E5%91%8A.pdf)

### SFT Training Plan and Risk Control Report

- Markdown: [MkDocs page](report-step1-sft-risk.md) (source: `week1/第一版/docs/SFT训练与风险控制.md`)
- PDF: [中文邮政客服任务SFT训练方案与风险控制报告.pdf](https://github.com/billzi2016/chinapost-internship/blob/main/reports/step1_%E6%A8%A1%E5%9E%8B%E9%80%89%E5%9E%8B%E4%B8%8E%E6%95%B0%E6%8D%AE%E9%9B%86%E5%88%86%E6%9E%90/%E4%B8%AD%E6%96%87%E9%82%AE%E6%94%BF%E5%AE%A2%E6%9C%8D%E4%BB%BB%E5%8A%A1SFT%E8%AE%AD%E7%BB%83%E6%96%B9%E6%A1%88%E4%B8%8E%E9%A3%8E%E9%99%A9%E6%8E%A7%E5%88%B6%E6%8A%A5%E5%91%8A.pdf)

### CSDS Statistics and Keyword Extraction Report

- Markdown: [MkDocs page](report-step1-csds-stats.md) (source: `week1/第一版/stats/outputs/report.md`)
- PDF: [CSDS数据集统计分析与关键词提取结果报告.pdf](https://github.com/billzi2016/chinapost-internship/blob/main/reports/step1_%E6%A8%A1%E5%9E%8B%E9%80%89%E5%9E%8B%E4%B8%8E%E6%95%B0%E6%8D%AE%E9%9B%86%E5%88%86%E6%9E%90/CSDS%E6%95%B0%E6%8D%AE%E9%9B%86%E7%BB%9F%E8%AE%A1%E5%88%86%E6%9E%90%E4%B8%8E%E5%85%B3%E9%94%AE%E8%AF%8D%E6%8F%90%E5%8F%96%E7%BB%93%E6%9E%9C%E6%8A%A5%E5%91%8A.pdf)

### Postal Conversation Filtering and Vector-Space Visualization Report

- Markdown: [MkDocs page](report-step1-postal-filter.md) (source: `week1/第一版/filter/outputs/report.md`)
- PDF: [邮政相关对话筛选与向量空间可视化结果报告.pdf](https://github.com/billzi2016/chinapost-internship/blob/main/reports/step1_%E6%A8%A1%E5%9E%8B%E9%80%89%E5%9E%8B%E4%B8%8E%E6%95%B0%E6%8D%AE%E9%9B%86%E5%88%86%E6%9E%90/%E9%82%AE%E6%94%BF%E7%9B%B8%E5%85%B3%E5%AF%B9%E8%AF%9D%E7%AD%9B%E9%80%89%E4%B8%8E%E5%90%91%E9%87%8F%E7%A9%BA%E9%97%B4%E5%8F%AF%E8%A7%86%E5%8C%96%E7%BB%93%E6%9E%9C%E6%8A%A5%E5%91%8A.pdf)

### Classification Evaluation and Boundary-Case Analysis Report

- Markdown: [MkDocs page](report-step1-classification-cases.md) (source: `week1/第二版/01_分类效果评估与边界case分析/outputs/report.md`)
- PDF: [分类效果评估与边界case分析报告.pdf](https://github.com/billzi2016/chinapost-internship/blob/main/reports/step1_%E6%A8%A1%E5%9E%8B%E9%80%89%E5%9E%8B%E4%B8%8E%E6%95%B0%E6%8D%AE%E9%9B%86%E5%88%86%E6%9E%90/%E5%88%86%E7%B1%BB%E6%95%88%E6%9E%9C%E8%AF%84%E4%BC%B0%E4%B8%8E%E8%BE%B9%E7%95%8Ccase%E5%88%86%E6%9E%90%E6%8A%A5%E5%91%8A.pdf)

### Cluster Visualization and Label Optimization Report

- Markdown: [MkDocs page](report-step1-cluster-labels.md) (source: `week1/第二版/04_可视化聚类与标签优化/outputs/report.md`)
- PDF: [可视化聚类与标签优化报告.pdf](https://github.com/billzi2016/chinapost-internship/blob/main/reports/step1_%E6%A8%A1%E5%9E%8B%E9%80%89%E5%9E%8B%E4%B8%8E%E6%95%B0%E6%8D%AE%E9%9B%86%E5%88%86%E6%9E%90/%E5%8F%AF%E8%A7%86%E5%8C%96%E8%81%9A%E7%B1%BB%E4%B8%8E%E6%A0%87%E7%AD%BE%E4%BC%98%E5%8C%96%E6%8A%A5%E5%91%8A.pdf)

## Step 2: Dataset Collection and Framework Setup

### Postal FAQ Crawler Training Sample Report

- Markdown: [MkDocs page](report-step2-training-samples.md) (source: `week1-module-Web-Crawler/report/training_samples_report.md`)
- PDF: [邮政FAQ爬虫训练样本构建报告.pdf](https://github.com/billzi2016/chinapost-internship/blob/main/reports/step2_%E6%94%B6%E9%9B%86%E6%95%B0%E6%8D%AE%E9%9B%86%E5%92%8C%E6%A1%86%E6%9E%B6%E6%90%AD%E5%BB%BA/%E9%82%AE%E6%94%BFFAQ%E7%88%AC%E8%99%AB%E8%AE%AD%E7%BB%83%E6%A0%B7%E6%9C%AC%E6%9E%84%E5%BB%BA%E6%8A%A5%E5%91%8A.pdf)

### Postal Customer-Service LLM System Design Report

- Markdown: [MkDocs page](report-step2-llm-system-design.md) (source: `week1-module-Web-Crawler/report/llm_system_design_report.md`)
- PDF: [邮政客服LLM系统设计报告.pdf](https://github.com/billzi2016/chinapost-internship/blob/main/reports/step2_%E6%94%B6%E9%9B%86%E6%95%B0%E6%8D%AE%E9%9B%86%E5%92%8C%E6%A1%86%E6%9E%B6%E6%90%AD%E5%BB%BA/%E9%82%AE%E6%94%BF%E5%AE%A2%E6%9C%8DLLM%E7%B3%BB%E7%BB%9F%E8%AE%BE%E8%AE%A1%E6%8A%A5%E5%91%8A.pdf)

## Step 3: LoRA Fine-Tuning

### Full Apple MLX Qwen2.5 Postal Fine-Tuning Report

- Markdown: [MkDocs page](report-step3-qwen25-full.md) (source: `week3/reports/qwen2.5_mlx_sft_full_experiment_report.md`)
- PDF: [基于AppleMLX的Qwen2.5邮政客服模型微调完整实验报告.pdf](https://github.com/billzi2016/chinapost-internship/blob/main/reports/step3_lora%E5%BE%AE%E8%B0%83/%E5%9F%BA%E4%BA%8EAppleMLX%E7%9A%84Qwen2.5%E9%82%AE%E6%94%BF%E5%AE%A2%E6%9C%8D%E6%A8%A1%E5%9E%8B%E5%BE%AE%E8%B0%83%E5%AE%8C%E6%95%B4%E5%AE%9E%E9%AA%8C%E6%8A%A5%E5%91%8A.pdf)

### Qwen2.5-3B Postal LoRA Rank Sweep Report

- Markdown: [MkDocs page](report-step3-qwen25-3b-rank-sweep.md) (source: `week3/reports/qwen2.5-3b_rank_sweep_report.md`)
- PDF: [Qwen2.5-3B邮政客服LoRA RankSweep实验报告.pdf](https://github.com/billzi2016/chinapost-internship/blob/main/reports/step3_lora%E5%BE%AE%E8%B0%83/Qwen2.5-3B%E9%82%AE%E6%94%BF%E5%AE%A2%E6%9C%8DLoRA%20RankSweep%E5%AE%9E%E9%AA%8C%E6%8A%A5%E5%91%8A.pdf)

### Qwen2.5-7B Postal LoRA Rank Sweep Report

- Markdown: [MkDocs page](report-step3-qwen25-7b-rank-sweep.md) (source: `week3/reports/qwen2.5-7b_rank_sweep_report.md`)
- PDF: [Qwen2.5-7B邮政客服LoRA RankSweep实验报告.pdf](https://github.com/billzi2016/chinapost-internship/blob/main/reports/step3_lora%E5%BE%AE%E8%B0%83/Qwen2.5-7B%E9%82%AE%E6%94%BF%E5%AE%A2%E6%9C%8DLoRA%20RankSweep%E5%AE%9E%E9%AA%8C%E6%8A%A5%E5%91%8A.pdf)

### Qwen2.5 Postal SFT Final Comparison Report

- Markdown: [MkDocs page](report-step3-qwen25-final-comparison.md) (source: `week3/reports/qwen2.5_final_comparison_report.md`)
- PDF: [Qwen2.5邮政客服SFT最终对比报告.pdf](https://github.com/billzi2016/chinapost-internship/blob/main/reports/step3_lora%E5%BE%AE%E8%B0%83/Qwen2.5%E9%82%AE%E6%94%BF%E5%AE%A2%E6%9C%8DSFT%E6%9C%80%E7%BB%88%E5%AF%B9%E6%AF%94%E6%8A%A5%E5%91%8A.pdf)
