# 报告导出说明

本目录用于统一管理项目报告的导出脚本和 PDF 结果。报告按阶段目录组织，不再按“第一版 / 第二版”拆分。

当前阶段目录：

- `step1_模型选型与数据集分析/`
- `step3_lora微调/`

## 1. 当前脚本

- `build_reports.py`

当前脚本导出项目阶段报告，输出到对应阶段目录：

```text
reports/step1_模型选型与数据集分析/
reports/step3_lora微调/
```

step1 当前包含：

1. `week1/第一版/docs/模型选型报告.md`
2. `week1/第一版/docs/SFT训练与风险控制.md`
3. `week1/第一版/stats/outputs/report.md`
4. `week1/第一版/filter/outputs/report.md`
5. `week1/第二版/01_分类效果评估与边界case分析/outputs/report.md`
6. `week1/第二版/04_可视化聚类与标签优化/outputs/report.md`
7. `week1-module-Web-Crawler/pycrawler/report/training_samples_report.md`

step3 当前包含：

1. `week3/reports/qwen2.5_mlx_sft_full_experiment_report.md`
2. `week3/reports/qwen2.5-3b_rank_sweep_report.md`
3. `week3/reports/qwen2.5-7b_rank_sweep_report.md`

## 2. 导出方式

脚本使用：

1. `Markdown -> HTML`
2. `HTML -> Playwright / Chromium`
3. `Chromium` 无头打印 PDF

这样做的原因是中文排版更自然，图片、表格、代码块和 Markdown 标题层级在 PDF 中更稳定。

## 3. 使用方式

在项目根目录执行：

```bash
python reports/build_reports.py
```

或进入 `reports` 目录执行：

```bash
python build_reports.py
```

列出所有可渲染报告：

```bash
python reports/build_reports.py --list
```

只渲染指定报告：

```bash
python reports/build_reports.py --only week1-training-samples
python reports/build_reports.py --only week3-qwen25-7b-rank-sweep
```

一次渲染多个指定报告：

```bash
python reports/build_reports.py --only week1-training-samples week3-qwen25-7b-rank-sweep
```

脚本会自动：

1. 检查 Playwright Chromium 运行时
2. 读取配置中的 Markdown
3. 转成 HTML
4. 套用统一 CSS
5. 输出 PDF 到对应阶段目录

## 4. 当前输出

当前会生成以下 PDF：

- `reports/step1_模型选型与数据集分析/中文邮政客服任务开源大模型选型研究报告.pdf`
- `reports/step1_模型选型与数据集分析/中文邮政客服任务SFT训练方案与风险控制报告.pdf`
- `reports/step1_模型选型与数据集分析/CSDS数据集统计分析与关键词提取结果报告.pdf`
- `reports/step1_模型选型与数据集分析/邮政相关对话筛选与向量空间可视化结果报告.pdf`
- `reports/step1_模型选型与数据集分析/分类效果评估与边界case分析报告.pdf`
- `reports/step1_模型选型与数据集分析/可视化聚类与标签优化报告.pdf`
- `reports/step1_模型选型与数据集分析/邮政FAQ爬虫训练样本构建报告.pdf`
- `reports/step3_lora微调/基于AppleMLX的Qwen2.5邮政客服模型微调完整实验报告.pdf`
- `reports/step3_lora微调/Qwen2.5-3B邮政客服LoRA RankSweep实验报告.pdf`
- `reports/step3_lora微调/Qwen2.5-7B邮政客服LoRA RankSweep实验报告.pdf`

## 5. 维护规则

- 内容问题改对应 Markdown。
- 排版问题改 `build_reports.py` 中的 CSS。
- 新阶段报告新增一个阶段目录，并在 `REPORT_SPECS` 里增加对应输入和输出路径。
- 不需要在报告正文中写内部任务编号；PDF 文件名和阶段目录负责表达报告归属。
