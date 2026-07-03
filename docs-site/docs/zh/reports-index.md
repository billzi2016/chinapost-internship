# 报告索引

`reports/` 目录维护的是这一套项目整理版里的正式报告入口，核心作用是把 Markdown 前体和最终 PDF 成品统一管理起来。

当前报告导出不是 LaTeX 路线，而是：

```text
Markdown -> HTML -> Chromium 打印 PDF
```

对应脚本是：

```text
reports/build_reports.py
```

## 当前状态说明

当前仓库中的 PDF 不是永久稳定不变的产物。因为这类文件经常改动，而且体积增长很快，所以最终 push 时会再统一整理一次。

因此在当前阶段：

1. 某些 PDF 已经存在。
2. 某些 PDF 可能暂时缺失。
3. 这不影响对应 Markdown 前体已经作为正式报告来源存在。

如果只想看报告源文件，应以 Markdown 为准；如果需要最终成品，则以后续统一整理后的 PDF 为准。

## Step 1：模型选型与数据集分析

### 中文邮政客服任务开源大模型选型研究报告

- Markdown：`week1/第一版/docs/模型选型报告.md`
- PDF：`reports/step1_模型选型与数据集分析/中文邮政客服任务开源大模型选型研究报告.pdf`

### 中文邮政客服任务SFT训练方案与风险控制报告

- Markdown：`week1/第一版/docs/SFT训练与风险控制.md`
- PDF：`reports/step1_模型选型与数据集分析/中文邮政客服任务SFT训练方案与风险控制报告.pdf`

### CSDS数据集统计分析与关键词提取结果报告

- Markdown：`week1/第一版/stats/outputs/report.md`
- PDF：`reports/step1_模型选型与数据集分析/CSDS数据集统计分析与关键词提取结果报告.pdf`

### 邮政相关对话筛选与向量空间可视化结果报告

- Markdown：`week1/第一版/filter/outputs/report.md`
- PDF：`reports/step1_模型选型与数据集分析/邮政相关对话筛选与向量空间可视化结果报告.pdf`

### 分类效果评估与边界 case 分析报告

- Markdown：`week1/第二版/01_分类效果评估与边界case分析/outputs/report.md`
- PDF：`reports/step1_模型选型与数据集分析/分类效果评估与边界case分析报告.pdf`

### 可视化聚类与标签优化报告

- Markdown：`week1/第二版/04_可视化聚类与标签优化/outputs/report.md`
- PDF：`reports/step1_模型选型与数据集分析/可视化聚类与标签优化报告.pdf`

## Step 2：收集数据集和框架搭建

### 邮政 FAQ 爬虫训练样本构建报告

- Markdown：`week1-module-Web-Crawler/report/training_samples_report.md`
- PDF：`reports/step2_收集数据集和框架搭建/邮政FAQ爬虫训练样本构建报告.pdf`

### 邮政客服 LLM 系统设计报告

- Markdown：`week1-module-Web-Crawler/report/llm_system_design_report.md`
- PDF：`reports/step2_收集数据集和框架搭建/邮政客服LLM系统设计报告.pdf`

## Step 3：LoRA 微调

### 基于 Apple MLX 的 Qwen2.5 邮政客服模型微调完整实验报告

- Markdown：`week3/reports/qwen2.5_mlx_sft_full_experiment_report.md`
- PDF：`reports/step3_lora微调/基于AppleMLX的Qwen2.5邮政客服模型微调完整实验报告.pdf`

### Qwen2.5-3B 邮政客服 LoRA Rank Sweep 实验报告

- Markdown：`week3/reports/qwen2.5-3b_rank_sweep_report.md`
- PDF：`reports/step3_lora微调/Qwen2.5-3B邮政客服LoRA RankSweep实验报告.pdf`

### Qwen2.5-7B 邮政客服 LoRA Rank Sweep 实验报告

- Markdown：`week3/reports/qwen2.5-7b_rank_sweep_report.md`
- PDF：`reports/step3_lora微调/Qwen2.5-7B邮政客服LoRA RankSweep实验报告.pdf`

