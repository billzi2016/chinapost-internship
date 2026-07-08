# Week 7：实验评测、报告生成与文档站整理

本周目标是把训练、评测、图表、报告和文档站整理成可复查的交付材料，而不是只保留零散脚本和图片。

## 主要工作

- 整理 Qwen2.5-3B 和 Qwen2.5-7B LoRA rank sweep 结果。
- 生成不同 rank 之间、3B 与 7B 之间的全局对比图。
- 编写综合对比报告，说明当前数据量和资源约束下的最优模型选择。
- 将报告接入 `reports/build_reports.py`，统一渲染 PDF。
- 整理 `docs-site`，尽量通过 include 原始 Markdown 保持 DRY，不重复维护同一份报告内容。
- 对历史缺口补充站内 wrapper 页面和报告索引入口。

## 当前产物

- `week3/mlx_qwen_sft/runs/`：rank sweep 训练结果目录。
- `week3/mlx_qwen_sft/global_compare/`：全局对比代码和图。
- `week3/reports/`：3B、7B、完整实验和最终综合对比报告。
- `reports/build_reports.py`：报告到 PDF 的渲染入口。
- `docs-site/`：MkDocs 文档站。

## 验证方式

```bash
cd /Users/bizi/Desktop/邮政实习
python3 reports/build_reports.py
cd docs-site
mkdocs build --strict
```

## 交付重点

- 图表数据必须来自数据表或实验结果文件，不能通过读图猜数据。
- 报告要说明“当前情况下”的结论和限制，避免把小数据实验结论写成绝对结论。
- 文档站优先 include 原始 Markdown；已经整理好的历史页面不强行重构。
